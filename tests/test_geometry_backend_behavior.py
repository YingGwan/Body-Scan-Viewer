"""
Behavior guards for geometry_backend without requiring heavy GUI/geometry deps.

These tests replace third-party modules with small fakes so we can verify
the runtime-unit and UI-facing behavior in the default test environment.
"""

import importlib
import os
import pathlib
import subprocess
import sys
import types

import numpy as np


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class FakeMesh:
    def __init__(self, vertices, faces=None, vertex_colors=None):
        self.vertices = np.array(vertices, dtype=float)
        self.faces = np.array(faces if faces is not None else [[0, 1, 2]], dtype=int)
        if vertex_colors is None:
            vertex_colors = np.tile(np.array([[255, 255, 255, 255]], dtype=np.uint8), (len(self.vertices), 1))
        self.visual = types.SimpleNamespace(
            vertex_colors=np.array(vertex_colors, dtype=np.uint8)
        )

    def copy(self):
        return FakeMesh(
            self.vertices.copy(),
            self.faces.copy(),
            self.visual.vertex_colors.copy(),
        )


class FakeSurfaceMeshHandle:
    def __init__(self):
        self.quantities = []
        self.color_quantities = []
        self.material = None
        self.smooth_shade = None

    def add_color_quantity(self, name, colors, enabled=True):
        item = (name, np.asarray(colors), enabled)
        self.quantities.append(item)
        self.color_quantities.append(item)

    def set_material(self, material):
        self.material = material

    def set_smooth_shade(self, smooth):
        self.smooth_shade = smooth


class FakePointCloudHandle:
    def __init__(self):
        self.color_quantities = []
        self.color = None
        self.radius = None

    def add_color_quantity(self, name, colors, enabled=True):
        self.color_quantities.append((name, np.asarray(colors), enabled))

    def set_color(self, color):
        self.color = tuple(color)

    def set_radius(self, radius):
        self.radius = radius


class FakePolyscopeModule(types.ModuleType):
    def __init__(self):
        super().__init__("polyscope")
        self.surface_calls = []
        self.curve_calls = []
        self.point_calls = []
        self.surface_handles = {}
        self.point_handles = {}

    def register_surface_mesh(self, name, verts, faces, **kwargs):
        self.surface_calls.append((name, np.asarray(verts), np.asarray(faces), kwargs))
        handle = FakeSurfaceMeshHandle()
        self.surface_handles[name] = handle
        return handle

    def get_surface_mesh(self, name):
        if name not in self.surface_handles:
            self.surface_handles[name] = FakeSurfaceMeshHandle()
        return self.surface_handles[name]

    def register_curve_network(self, name, verts, edges, **kwargs):
        self.curve_calls.append((name, np.asarray(verts), np.asarray(edges), kwargs))

    def register_point_cloud(self, name, points, **kwargs):
        self.point_calls.append((name, np.asarray(points), kwargs))
        handle = FakePointCloudHandle()
        self.point_handles[name] = handle
        return handle

    def has_surface_mesh(self, name):
        return False

    def has_point_cloud(self, name):
        return name in self.point_handles

    def get_point_cloud(self, name):
        if name not in self.point_handles:
            self.point_handles[name] = FakePointCloudHandle()
        return self.point_handles[name]

    def has_curve_network(self, name):
        return False

    def remove_surface_mesh(self, name):
        pass

    def remove_point_cloud(self, name):
        self.point_handles.pop(name, None)

    def remove_curve_network(self, name):
        pass


def _import_geometry_backend_with_fakes(
    monkeypatch,
    mesh_vertices,
    closest_point_fn,
    parse_lnd_fn=None,
    align_lnd_fn=None,
    mesh_vertex_colors=None,
    registration_fn=None,
    app_config=None,
):
    fake_ps = FakePolyscopeModule()
    monkeypatch.setitem(sys.modules, "polyscope", fake_ps)
    monkeypatch.setitem(sys.modules, "polyscope.imgui", types.ModuleType("polyscope.imgui"))

    fake_trimesh = types.ModuleType("trimesh")
    fake_trimesh.Trimesh = FakeMesh
    fake_trimesh.load = lambda *args, **kwargs: FakeMesh(
        mesh_vertices,
        vertex_colors=mesh_vertex_colors,
    )
    fake_trimesh.proximity = types.SimpleNamespace(closest_point=closest_point_fn)
    monkeypatch.setitem(sys.modules, "trimesh", fake_trimesh)

    fake_data_loader = types.ModuleType("data_loader")
    fake_data_loader.scan_data_folders = lambda: types.SimpleNamespace(subjects={})
    fake_data_loader.parse_lnd = parse_lnd_fn or (lambda path, **kwargs: {})
    fake_data_loader.align_caesar_landmarks_to_mesh = align_lnd_fn or (
        lambda landmarks, mesh_vertices: (
            landmarks,
            {
                "rotation_label": "identity",
                "rotation_matrix": np.eye(3),
                "mean_mesh_error_mm": 0.0,
                "max_mesh_error_mm": 0.0,
                "fitness": 1.0,
                "rmse": 0.0,
            },
        )
    )
    fake_data_loader.diagnose_coordinate_systems = lambda *args, **kwargs: None
    fake_data_loader.build_axis_swap_matrix = lambda *args, **kwargs: np.eye(4)
    fake_data_loader.PROCESSED_DIR = None
    monkeypatch.setitem(sys.modules, "data_loader", fake_data_loader)

    fake_geodesic = types.ModuleType("geodesic_utils")
    fake_geodesic.build_edge_graph = lambda mesh: None
    geodesic_state = types.SimpleNamespace(
        solver=object(),
        last_compute_kwargs=None,
        result=(0.0, None),
    )

    def fake_compute_geodesic(*args, **kwargs):
        geodesic_state.last_compute_kwargs = kwargs
        return geodesic_state.result

    fake_geodesic.build_geodesic_solver = lambda mesh: geodesic_state.solver
    fake_geodesic.compute_geodesic = fake_compute_geodesic
    monkeypatch.setitem(sys.modules, "geodesic_utils", fake_geodesic)

    fake_registration = types.ModuleType("registration")
    fake_registration.run_icp_registration = registration_fn or (lambda *args, **kwargs: None)
    monkeypatch.setitem(sys.modules, "registration", fake_registration)

    fake_config_loader = types.ModuleType("config_loader")
    fake_config_loader.APP_CONFIG = app_config or types.SimpleNamespace(
        distance=types.SimpleNamespace(
            default_color_max_mm=30.0,
            slider_min_mm=1.0,
            slider_max_mm=100.0,
        ),
        render=types.SimpleNamespace(
            sizestream_mesh=types.SimpleNamespace(
                color=(0.2, 0.4, 1.0),
                enabled=True,
                transparency=0.5,
                smooth_shade=True,
            ),
            sizestream_landmarks=types.SimpleNamespace(
                color=(0.2, 0.4, 1.0),
                enabled=True,
                radius=0.006,
            ),
            caesar_mesh=types.SimpleNamespace(
                color=(1.0, 0.55, 0.1),
                enabled=False,
                smooth_shade=True,
            ),
            caesar_landmarks=types.SimpleNamespace(
                color=(1.0, 0.55, 0.1),
                enabled=False,
                radius=0.006,
            ),
            registered_mesh=types.SimpleNamespace(
                color=(0.2, 0.85, 0.3),
                enabled=True,
                smooth_shade=True,
            ),
            registered_landmarks=types.SimpleNamespace(
                color=(1.0, 0.75, 0.2),
                enabled=False,
                radius=0.006,
            ),
            landmark_errors=types.SimpleNamespace(
                color=(1.0, 0.3, 0.2),
                radius=0.001,
            ),
            geodesic_path=types.SimpleNamespace(
                color=(1.0, 0.85, 0.1),
                radius=0.003,
            ),
            geodesic_endpoints=types.SimpleNamespace(
                radius=0.008,
                start_color=(1.0, 0.2, 0.2),
                end_color=(0.05, 0.35, 0.18),
            ),
        ),
        registration=types.SimpleNamespace(
            quality=types.SimpleNamespace(
                fitness_fail_below=0.1,
                excellent_rmse_below_mm=5.0,
                acceptable_rmse_below_mm=15.0,
            ),
        ),
    )
    monkeypatch.setitem(sys.modules, "config_loader", fake_config_loader)

    fake_colorbar = types.ModuleType("colorBar")
    fake_colorbar._changeValueToColor = lambda maxv, minv, value: [value, 0.0, 0.0]
    monkeypatch.setitem(sys.modules, "colorBar", fake_colorbar)

    fake_scipy = types.ModuleType("scipy")
    fake_spatial = types.ModuleType("scipy.spatial")

    class FakeKDTree:
        def __init__(self, points):
            self.points = np.asarray(points, dtype=float)

        def query(self, point):
            point = np.asarray(point, dtype=float)
            dists = np.linalg.norm(self.points - point, axis=1)
            idx = int(np.argmin(dists))
            return float(dists[idx]), idx

    fake_spatial.cKDTree = FakeKDTree
    monkeypatch.setitem(sys.modules, "scipy", fake_scipy)
    monkeypatch.setitem(sys.modules, "scipy.spatial", fake_spatial)

    sys.modules.pop("geometry_backend", None)
    mod = importlib.import_module("geometry_backend")
    return mod, fake_ps, geodesic_state


def test_load_caesar_registers_runtime_mm_vertices(monkeypatch):
    meter_vertices = np.array([
        [0.0, 0.0, -1.0],
        [0.6, 0.2, 0.584],
        [-0.563, -0.384, 0.1],
    ])
    mod, fake_ps, _ = _import_geometry_backend_with_fakes(
        monkeypatch,
        meter_vertices,
        closest_point_fn=lambda *args, **kwargs: None,
    )

    obj = mod.VisContent.__new__(mod.VisContent)
    obj.catalog = types.SimpleNamespace(subjects={
        "csr0052a": types.SimpleNamespace(
            caesar_ply_path="unused.ply",
            caesar_lnd_path=None,
        )
    })
    obj.mesh_ss = None
    obj.caesar_lnd = {}
    obj.coord_diag = None

    obj.load_caesar("csr0052a")

    _, registered_vertices, _, _ = fake_ps.surface_calls[0]
    np.testing.assert_allclose(np.ptp(registered_vertices, axis=0), np.ptp(meter_vertices, axis=0) * 1000.0)
    np.testing.assert_allclose(np.ptp(obj.mesh_caesar.vertices, axis=0), np.ptp(meter_vertices, axis=0) * 1000.0)
    assert obj.caesar_unit_ctx.original_unit == "m"


def test_compare_landmark_distances_keeps_user_color_max(monkeypatch):
    mesh_vertices = np.array([
        [0.0, 0.0, 0.0],
        [100.0, 0.0, 0.0],
        [0.0, 100.0, 0.0],
    ])

    def fake_closest_point(mesh, points):
        points = np.asarray(points, dtype=float)
        closest = points + 1.0
        distances = np.full(len(points), 12.5, dtype=float)
        triangle_ids = np.zeros(len(points), dtype=int)
        return closest, distances, triangle_ids

    mod, fake_ps, _ = _import_geometry_backend_with_fakes(
        monkeypatch,
        mesh_vertices,
        closest_point_fn=fake_closest_point,
    )

    obj = mod.VisContent.__new__(mod.VisContent)
    obj.lm_pos_ss = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
    obj.mesh_registered = FakeMesh(mesh_vertices)
    obj.mesh_ss = FakeMesh(mesh_vertices)
    obj.landmark_distances = None
    obj.color_max_mm = 42.0

    obj.compare_landmark_distances()

    assert obj.color_max_mm == 42.0
    assert fake_ps.get_surface_mesh("SizeStream").quantities[0][0] == "Distance_to_CAESAR"


def test_load_caesar_registers_caesar_landmarks(monkeypatch):
    meter_vertices = np.array([
        [0.0, 0.0, -1.0],
        [0.6, 0.2, 0.584],
        [-0.563, -0.384, 0.1],
    ])
    raw_landmarks = {
        "RawA": np.array([464.0, -4.0, 17.0]),
        "RawB": np.array([583.0, 63.0, 219.0]),
    }
    aligned_landmarks = {
        "Heel": np.array([10.0, 20.0, -1000.0]),
        "HeadTop": np.array([12.0, 24.0, 584.0]),
    }
    mod, fake_ps, _ = _import_geometry_backend_with_fakes(
        monkeypatch,
        meter_vertices,
        closest_point_fn=lambda *args, **kwargs: None,
        parse_lnd_fn=lambda path, **kwargs: raw_landmarks,
        align_lnd_fn=lambda landmarks, mesh_vertices: (
            aligned_landmarks,
            {
                "rotation_label": "Ry(+90 deg)",
                "rotation_matrix": np.array([
                    [0.0, 0.0, 1.0],
                    [0.0, 1.0, 0.0],
                    [-1.0, 0.0, 0.0],
                ]),
                "mean_mesh_error_mm": 28.5,
                "max_mesh_error_mm": 77.9,
                "fitness": 1.0,
                "rmse": 34.0,
            },
        ),
    )

    obj = mod.VisContent.__new__(mod.VisContent)
    obj.catalog = types.SimpleNamespace(subjects={
        "csr0052a": types.SimpleNamespace(
            caesar_ply_path="unused.ply",
            caesar_lnd_path="unused.lnd",
        )
    })
    obj.mesh_ss = None
    obj.caesar_lnd = {}
    obj.coord_diag = None

    obj.load_caesar("csr0052a")

    assert obj.caesar_lnd.keys() == aligned_landmarks.keys()
    assert fake_ps.point_calls[0][0] == "CAESAR_Landmarks"
    np.testing.assert_allclose(
        fake_ps.point_calls[0][1],
        np.array(list(aligned_landmarks.values())),
    )
    assert obj.caesar_lm_warning is None
    assert obj.caesar_lm_alignment["rotation_label"] == "Ry(+90 deg)"


def test_load_caesar_keeps_nonprojected_aligned_landmarks(monkeypatch):
    meter_vertices = np.array([
        [0.0, 0.0, -1.0],
        [0.6, 0.2, 0.584],
        [-0.563, -0.384, 0.1],
    ])
    raw_landmarks = {
        "Sellion": np.array([464.0, -4.0, 17.0]),
        "Nuchale": np.array([441.0, 114.0, 137.0]),
    }
    aligned_landmarks = {
        # Deliberately off-surface: backend should keep these exact values
        "Sellion": np.array([55.0, 15.0, -300.0]),
        "Nuchale": np.array([90.0, 80.0, -250.0]),
    }
    mod, fake_ps, _ = _import_geometry_backend_with_fakes(
        monkeypatch,
        meter_vertices,
        closest_point_fn=lambda *args, **kwargs: None,
        parse_lnd_fn=lambda path, **kwargs: raw_landmarks,
        align_lnd_fn=lambda landmarks, mesh_vertices: (
            aligned_landmarks,
            {
                "rotation_label": "Ry(+90 deg)",
                "rotation_matrix": np.array([
                    [0.0, 0.0, 1.0],
                    [0.0, 1.0, 0.0],
                    [-1.0, 0.0, 0.0],
                ]),
                "mean_mesh_error_mm": 32.0,
                "max_mesh_error_mm": 61.0,
                "fitness": 1.0,
                "rmse": 35.0,
            },
        ),
    )

    obj = mod.VisContent.__new__(mod.VisContent)
    obj.catalog = types.SimpleNamespace(subjects={
        "csr0052a": types.SimpleNamespace(
            caesar_ply_path="unused.ply",
            caesar_lnd_path="unused.lnd",
        )
    })
    obj.mesh_ss = None
    obj.caesar_lnd = {}
    obj.coord_diag = None

    obj.load_caesar("csr0052a")

    np.testing.assert_allclose(
        obj.caesar_lm_pos,
        np.array(list(aligned_landmarks.values())),
    )
    np.testing.assert_allclose(
        fake_ps.point_calls[0][1],
        np.array(list(aligned_landmarks.values())),
    )
    assert obj.caesar_lm_warning is None


def test_load_caesar_registers_vertex_color_rendering(monkeypatch):
    meter_vertices = np.array([
        [0.0, 0.0, -1.0],
        [0.6, 0.2, 0.584],
        [-0.563, -0.384, 0.1],
    ])
    vertex_colors = np.array([
        [10, 20, 30, 255],
        [100, 110, 120, 255],
        [200, 210, 220, 255],
    ], dtype=np.uint8)
    mod, fake_ps, _ = _import_geometry_backend_with_fakes(
        monkeypatch,
        meter_vertices,
        closest_point_fn=lambda *args, **kwargs: None,
        mesh_vertex_colors=vertex_colors,
    )

    obj = mod.VisContent.__new__(mod.VisContent)
    obj.catalog = types.SimpleNamespace(subjects={
        "csr0052a": types.SimpleNamespace(
            caesar_ply_path="unused.ply",
            caesar_lnd_path=None,
        )
    })
    obj.mesh_ss = None
    obj.caesar_lnd = {}
    obj.coord_diag = None

    obj.load_caesar("csr0052a")

    handle = fake_ps.get_surface_mesh("CAESAR")
    assert handle.color_quantities[0][0] == "PLY_RGB"
    np.testing.assert_allclose(
        handle.color_quantities[0][1],
        vertex_colors[:, :3] / 255.0,
    )


def test_run_registration_preserves_caesar_vertex_colors(monkeypatch):
    meter_vertices = np.array([
        [0.0, 0.0, -1.0],
        [0.6, 0.2, 0.584],
        [-0.563, -0.384, 0.1],
    ])
    vertex_colors = np.array([
        [10, 20, 30, 255],
        [100, 110, 120, 255],
        [200, 210, 220, 255],
    ], dtype=np.uint8)

    reg_mesh = FakeMesh(meter_vertices * 1000.0, vertex_colors=vertex_colors)

    def fake_registration(mesh_ss, mesh_caesar, coord_diag, build_axis_swap_matrix):
        return reg_mesh, np.eye(4), 4.0, 0.99, "Excellent (<5mm)"

    mod, fake_ps, _ = _import_geometry_backend_with_fakes(
        monkeypatch,
        meter_vertices,
        closest_point_fn=lambda *args, **kwargs: None,
        mesh_vertex_colors=vertex_colors,
        registration_fn=fake_registration,
    )

    obj = mod.VisContent.__new__(mod.VisContent)
    obj.catalog = types.SimpleNamespace(subjects={
        "csr0052a": types.SimpleNamespace(
            caesar_ply_path="unused.ply",
            caesar_lnd_path=None,
        )
    })
    obj.mesh_ss = FakeMesh(meter_vertices * 1000.0)
    obj.caesar_lnd = {}
    obj.coord_diag = None

    obj.load_caesar("csr0052a")
    obj.run_registration()

    handle = fake_ps.get_surface_mesh("CAESAR_Registered")
    assert handle.color_quantities[0][0] == "PLY_RGB"
    np.testing.assert_allclose(
        handle.color_quantities[0][1],
        vertex_colors[:, :3] / 255.0,
    )


def test_geometry_backend_imports_under_fastikd_py39_if_present():
    """geometry_backend should stay importable in the user's FastIKD Python 3.9 env."""
    fastikd_python = pathlib.Path(r"D:\conda\envs\FastIKD\python.exe")
    if not fastikd_python.exists():
        return

    script = (
        "import sys, types; "
        "sys.modules['pandas'] = types.ModuleType('pandas'); "
        "color_bar = types.ModuleType('colorBar'); "
        "color_bar._changeValueToColor = lambda *args, **kwargs: [0.0, 0.0, 0.0]; "
        "sys.modules['colorBar'] = color_bar; "
        "import geometry_backend; "
        "print('IMPORTED')"
    )
    result = subprocess.run(
        [str(fastikd_python), "-c", script],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "IMPORTED" in result.stdout


def test_load_sizestream_builds_and_uses_exact_geodesic_solver(monkeypatch):
    mesh_vertices = np.array([
        [0.0, 0.0, 0.0],
        [100.0, 0.0, 0.0],
        [100.0, 100.0, 0.0],
    ])
    path = np.array([
        [0.0, 0.0, 0.0],
        [50.0, 25.0, 0.0],
        [100.0, 100.0, 0.0],
    ])

    mod, fake_ps, geodesic_state = _import_geometry_backend_with_fakes(
        monkeypatch,
        mesh_vertices,
        closest_point_fn=lambda *args, **kwargs: None,
    )
    geodesic_state.result = (123.4, path)

    obj = mod.VisContent.__new__(mod.VisContent)
    obj.catalog = types.SimpleNamespace(
        subjects={
            "csr0052a": types.SimpleNamespace(
                ss_obj_path="unused.obj",
                has_landmarks=False,
            )
        },
        lm_data=None,
    )
    obj.mesh_caesar = None
    obj.coord_diag = None

    obj.load_sizestream("csr0052a")
    length = obj.compute_and_show_geodesic(path[0], path[-1])

    assert obj.ss_geodesic_solver is geodesic_state.solver
    assert geodesic_state.last_compute_kwargs["exact_solver"] is geodesic_state.solver
    assert length == 123.4
    assert fake_ps.curve_calls[0][0] == "Geodesic_Path"
    np.testing.assert_allclose(fake_ps.curve_calls[0][1], path)


def test_geodesic_endpoints_use_distinct_start_end_colors(monkeypatch):
    mesh_vertices = np.array([
        [0.0, 0.0, 0.0],
        [100.0, 0.0, 0.0],
        [100.0, 100.0, 0.0],
    ])
    path = np.array([
        [0.0, 0.0, 0.0],
        [50.0, 25.0, 0.0],
        [100.0, 100.0, 0.0],
    ])

    mod, fake_ps, geodesic_state = _import_geometry_backend_with_fakes(
        monkeypatch,
        mesh_vertices,
        closest_point_fn=lambda *args, **kwargs: None,
    )
    geodesic_state.result = (123.4, path)

    obj = mod.VisContent.__new__(mod.VisContent)
    obj.mesh_ss = FakeMesh(mesh_vertices)
    obj.ss_edge_graph = object()
    obj.ss_kdtree = object()
    obj.ss_geodesic_solver = object()

    obj.compute_and_show_geodesic(path[0], path[-1])

    handle = fake_ps.get_point_cloud("Geo_Endpoints")
    assert handle.color_quantities[0][0] == "Endpoint_Role"
    np.testing.assert_allclose(
        handle.color_quantities[0][1],
        np.array([
            [1.0, 0.2, 0.2],
            [0.05, 0.35, 0.18],
        ]),
    )


def test_load_sizestream_uses_render_config(monkeypatch):
    mesh_vertices = np.array([
        [0.0, 0.0, 0.0],
        [100.0, 0.0, 0.0],
        [100.0, 100.0, 0.0],
    ])
    app_config = types.SimpleNamespace(
        distance=types.SimpleNamespace(
            default_color_max_mm=30.0,
            slider_min_mm=1.0,
            slider_max_mm=100.0,
        ),
        render=types.SimpleNamespace(
            sizestream_mesh=types.SimpleNamespace(
                color=(0.9, 0.8, 0.7),
                enabled=True,
                transparency=0.25,
                smooth_shade=False,
            ),
            sizestream_landmarks=types.SimpleNamespace(
                color=(0.1, 0.2, 0.3),
                enabled=False,
                radius=0.012,
            ),
            caesar_mesh=types.SimpleNamespace(
                color=(1.0, 0.55, 0.1),
                enabled=False,
                smooth_shade=True,
            ),
            caesar_landmarks=types.SimpleNamespace(
                color=(1.0, 0.55, 0.1),
                enabled=False,
                radius=0.006,
            ),
            registered_mesh=types.SimpleNamespace(
                color=(0.2, 0.85, 0.3),
                enabled=True,
                smooth_shade=True,
            ),
            registered_landmarks=types.SimpleNamespace(
                color=(1.0, 0.75, 0.2),
                enabled=False,
                radius=0.006,
            ),
            landmark_errors=types.SimpleNamespace(
                color=(1.0, 0.3, 0.2),
                radius=0.001,
            ),
            geodesic_path=types.SimpleNamespace(
                color=(1.0, 0.85, 0.1),
                radius=0.003,
            ),
            geodesic_endpoints=types.SimpleNamespace(
                radius=0.008,
                start_color=(1.0, 0.2, 0.2),
                end_color=(0.05, 0.35, 0.18),
            ),
        ),
        registration=types.SimpleNamespace(
            quality=types.SimpleNamespace(
                fitness_fail_below=0.1,
                excellent_rmse_below_mm=5.0,
                acceptable_rmse_below_mm=15.0,
            ),
        ),
    )

    mod, fake_ps, _ = _import_geometry_backend_with_fakes(
        monkeypatch,
        mesh_vertices,
        closest_point_fn=lambda *args, **kwargs: None,
        app_config=app_config,
    )

    obj = mod.VisContent.__new__(mod.VisContent)
    obj.catalog = types.SimpleNamespace(
        subjects={
            "csr0052a": types.SimpleNamespace(
                ss_obj_path="unused.obj",
                has_landmarks=False,
            )
        },
        lm_data=None,
    )
    obj.mesh_caesar = None
    obj.coord_diag = None

    obj.load_sizestream("csr0052a")

    name, _, _, kwargs = fake_ps.surface_calls[0]
    assert name == "SizeStream"
    assert kwargs["color"] == (0.9, 0.8, 0.7)
    assert kwargs["transparency"] == 0.25
    assert kwargs["smooth_shade"] is False
