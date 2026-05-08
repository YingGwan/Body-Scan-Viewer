"""
geometry_backend.py — Backend (Model) Layer for the Body Scan Viewer

This is the core business logic class that manages all geometric data,
performs computations, and registers results to Polyscope for visualization.

Class VisContent:
    - Holds all mutable state (meshes, landmarks, registration results, etc.)
    - Provides methods for each pipeline step:
        load_sizestream()      -> Import SS OBJ + XLSX landmarks + precompute geodesic structures
        load_caesar()          -> Import CAESAR PLY + LND landmarks + coordinate diagnosis
        run_registration()     -> Coarse-to-fine ICP registration
        save_registered()      -> Export registered mesh to processed/
        compare_distances()    -> Landmark + vertex distance computation with color mapping
        compute_and_show_geodesic() -> Geodesic path via potpourri3d exact path
                                      with Dijkstra fallback
    - reset_subject() clears all state and Polyscope structures on subject switch
"""

import numpy as np
import trimesh
import polyscope as ps
from scipy.spatial import cKDTree
from typing import Optional
from config_loader import APP_CONFIG

from data_loader import (
    scan_data_folders, parse_lnd, align_caesar_landmarks_to_mesh,
    diagnose_coordinate_systems, build_axis_swap_matrix,
    PROCESSED_DIR,
)
from geodesic_utils import build_edge_graph, build_geodesic_solver, compute_geodesic
from registration import run_icp_registration
from colorBar import _changeValueToColor
import pathlib
from derived_landmarks import (
    load_derived_landmark_config, compute_all_derived_landmarks,
    compute_configured_measurements, from_barycentric, project_to_mesh,
    MeasurementRecord,
)
from unit_utils import (
    infer_mesh_unit_context,
    to_runtime_mm_vertices,
    from_runtime_mm_vertices,
    transform_mm_to_original_units,
)


class VisContent:
    """
    Backend model for the Body Scan Viewer application.

    On construction, automatically scans data folders to build a DataCatalog.
    All other state is initialized to None/empty and populated by user actions.
    """

    def __init__(self):
        """Scan data folders on startup and initialize empty state."""
        self.catalog = scan_data_folders()
        self._init_state()

    def _init_state(self):
        """
        Initialize (or reset) all mutable state to default values.
        Called by __init__ and reset_subject().
        """
        self.current_subject    = None

        # SizeStream data
        self.mesh_ss            = None       # trimesh.Trimesh
        self.lm_pos_ss          = None       # np.ndarray (N, 3) landmark positions
        self.lm_names_ss        = None       # list[str] landmark names
        self.ss_lm_dict         = {}         # {name: np.array([X,Y,Z])} for geodesic UI
        self.ss_edge_graph      = None       # csr_matrix from build_edge_graph()
        self.ss_geodesic_solver = None       # potpourri3d exact geodesic solver
        self.ss_geodesic_mode   = "Dijkstra fallback"
        self.ss_kdtree          = None       # cKDTree for vertex snapping

        # CAESAR data
        self.mesh_caesar        = None       # trimesh.Trimesh in runtime mm
        self.caesar_lnd         = {}         # {name: np.array([X,Y,Z])} from parse_lnd
        self.caesar_lm_pos      = None       # np.ndarray (N, 3) raw CAESAR landmarks
        self.caesar_lm_names    = None       # list[str]
        self.caesar_lm_pos_reg  = None       # np.ndarray (N, 3) after registration
        self.caesar_lm_warning  = None       # str warning when .lnd is incompatible
        self.caesar_lm_alignment = None      # dict alignment metadata for raw .lnd XYZ
        self.caesar_unit_ctx    = None       # original CAESAR mesh unit for export round-trip

        # Coordinate system diagnosis
        self.coord_diag         = None       # dict from diagnose_coordinate_systems()

        # Registration results
        self.mesh_registered    = None       # trimesh.Trimesh (CAESAR after ICP)
        self.icp_rmse           = 0.0
        self.icp_fitness        = 0.0
        self.transform_total    = None       # 4x4 complete transform chain

        # Distance comparison results
        self.landmark_distances = None       # np.ndarray (N,), per-landmark distances
        self.color_max_mm       = APP_CONFIG.distance.default_color_max_mm

        # Geodesic
        self.geodesic_length    = 0.0

        # Derived landmarks (V3)
        self.derived_lm_config  = None
        self.derived_lm_dict    = {}
        self.measurement_results = []

    @staticmethod
    def _extract_mesh_vertex_colors(mesh) -> Optional[np.ndarray]:
        """
        Extract per-vertex RGB colors as floats in [0, 1], when available.

        CAESAR PLY files in this project include uchar RGB(A) vertex colors.
        We keep rendering resilient by gracefully falling back when visual/color
        metadata is absent or malformed.
        """
        visual = getattr(mesh, "visual", None)
        vertex_colors = getattr(visual, "vertex_colors", None) if visual is not None else None
        if vertex_colors is None:
            return None

        colors = np.asarray(vertex_colors)
        if colors.ndim != 2 or colors.shape[0] != len(mesh.vertices) or colors.shape[1] < 3:
            return None

        colors = colors[:, :3].astype(float)
        if colors.size == 0:
            return None
        if colors.max() > 1.0:
            colors /= 255.0
        return colors

    def _register_caesar_surface(self, name: str, mesh, render_cfg):
        """
        Register a CAESAR mesh with smooth shading and PLY vertex colors when available.

        Exact photorealistic texturing is not possible without UV textures, but
        using the PLY's native RGB vertex colors gets much closer to the source
        scan appearance than a flat orange/green mesh.
        """
        handle = ps.register_surface_mesh(
            name, mesh.vertices, mesh.faces,
            color=render_cfg.color,
            enabled=render_cfg.enabled,
            smooth_shade=render_cfg.smooth_shade,
        )

        colors = self._extract_mesh_vertex_colors(mesh)
        if colors is not None and hasattr(handle, "add_color_quantity"):
            handle.add_color_quantity("PLY_RGB", colors, enabled=True)
        return handle

    # ==========================================================================
    # Scene cleanup
    # ==========================================================================

    def reset_subject(self):
        """
        Clear all Polyscope structures and reset state for a subject switch.
        Uses per-name removal to preserve any global helper structures.
        """
        # WARNING: when adding new ps.register_*() calls, add the name here too
        known_structures = [
            "SizeStream", "SS_Landmarks", "CAESAR", "CAESAR_Registered",
            "CAESAR_Landmarks", "CAESAR_Landmarks_Registered",
            "Landmark_Errors", "Geodesic_Path", "Geo_Endpoints",
            "Distance_to_CAESAR",
            # V3 derived landmarks (static)
            "Ref_Triangle_Vertices", "Derived_Armhole", "Derived_Neck",
            "Armhole_Section_L", "Armhole_Section_R",
        ]
        if self.derived_lm_config and "measurements" in self.derived_lm_config:
            for mname in self.derived_lm_config["measurements"]:
                known_structures.append(f"Geo_{mname}")
        for name in known_structures:
            try:
                if ps.has_surface_mesh(name):
                    ps.remove_surface_mesh(name)
                elif ps.has_point_cloud(name):
                    ps.remove_point_cloud(name)
                elif ps.has_curve_network(name):
                    ps.remove_curve_network(name)
            except Exception:
                pass  # Structure type mismatch or already removed
        self._init_state()

    # ==========================================================================
    # A. SizeStream import
    # ==========================================================================

    def load_sizestream(self, subject_id: str):
        """
        Load SizeStream OBJ mesh and XLSX landmarks for the given subject.

        Registers to Polyscope:
            - "SizeStream": blue semi-transparent surface mesh
            - "SS_Landmarks": blue point cloud (if landmarks available)

        Also precomputes:
            - Edge graph (for geodesic)
            - Exact geodesic solver (potpourri3d, when available)
            - KDTree (for vertex snapping)
            - Landmark dict (for geodesic endpoint selection)

        Args:
            subject_id: e.g. "csr0052a"
        """
        entry = self.catalog.subjects[subject_id]

        # Load mesh
        mesh_ss = trimesh.load(str(entry.ss_obj_path), force='mesh')
        if not isinstance(mesh_ss, trimesh.Trimesh):
            raise ValueError(f"Cannot parse {entry.ss_obj_path.name} as triangle mesh")

        # Register in Polyscope (blue, 50% transparent)
        ss_mesh_cfg = APP_CONFIG.render.sizestream_mesh
        ps.register_surface_mesh(
            "SizeStream", mesh_ss.vertices, mesh_ss.faces,
            color=ss_mesh_cfg.color,
            enabled=ss_mesh_cfg.enabled,
            transparency=ss_mesh_cfg.transparency,
            smooth_shade=ss_mesh_cfg.smooth_shade,
        )

        # Parse landmarks from XLSX
        lm_dict = {}
        if entry.has_landmarks and self.catalog.lm_data:
            sid_idx = self.catalog.lm_data['subject_ids'].index(subject_id)
            for lm_name, coords in self.catalog.lm_data['landmarks_3d'].items():
                lm_dict[lm_name] = coords[sid_idx]  # shape (3,)

            if lm_dict:
                lm_names = list(lm_dict.keys())
                lm_pos   = np.array(list(lm_dict.values()))  # shape (N, 3)
                ss_lm_cfg = APP_CONFIG.render.sizestream_landmarks
                ps.register_point_cloud(
                    "SS_Landmarks", lm_pos,
                    color=ss_lm_cfg.color,
                    radius=ss_lm_cfg.radius,
                    enabled=ss_lm_cfg.enabled,
                )
                self.lm_pos_ss   = lm_pos
                self.lm_names_ss = lm_names

        # Store state
        self.mesh_ss         = mesh_ss
        self.ss_lm_dict      = lm_dict
        self.ss_edge_graph   = build_edge_graph(mesh_ss)
        self.ss_geodesic_solver = build_geodesic_solver(mesh_ss)
        self.ss_geodesic_mode = (
            "potpourri3d exact path"
            if self.ss_geodesic_solver is not None
            else "Dijkstra fallback"
        )
        self.ss_kdtree       = cKDTree(mesh_ss.vertices)
        self.current_subject = subject_id

        print(f"[load] SizeStream: {len(mesh_ss.vertices):,} verts, "
              f"{len(lm_dict)} landmarks | geodesic={self.ss_geodesic_mode}")

        # If CAESAR was loaded first, trigger coordinate diagnosis now
        if self.mesh_caesar is not None:
            self.coord_diag = diagnose_coordinate_systems(
                self.mesh_ss, self.mesh_caesar, self.caesar_lnd
            )

    # ==========================================================================
    # B. CAESAR import
    # ==========================================================================

    def load_caesar(self, subject_id: str):
        """
        Load CAESAR PLY mesh and .lnd landmarks for the given subject.

        The mesh is normalized to runtime millimeters immediately so the
        Polyscope view and all downstream geometry computations use the same
        unit system.

        Registers to Polyscope:
            - "CAESAR": orange surface mesh (hidden by default; shown after registration)

        Uses process=False to avoid trimesh mishandling the `confidence` float
        property in CAESAR PLY files.

        Args:
            subject_id: e.g. "csr0052a"
        """
        entry = self.catalog.subjects[subject_id]

        # Load PLY (process=False: preserve raw vertices, don't auto-fix winding)
        mesh_caesar = trimesh.load(
            str(entry.caesar_ply_path), force='mesh', process=False
        )
        caesar_unit_ctx = infer_mesh_unit_context(mesh_caesar.vertices)
        mesh_caesar.vertices = to_runtime_mm_vertices(
            mesh_caesar.vertices, caesar_unit_ctx
        )

        # Register in Polyscope (orange, hidden by default)
        self._register_caesar_surface(
            "CAESAR",
            mesh_caesar,
            APP_CONFIG.render.caesar_mesh,
        )

        # Parse .lnd landmarks
        caesar_lnd = {}
        caesar_lm_warning = None
        caesar_lm_alignment = None
        if entry.caesar_lnd_path:
            caesar_lnd_raw = parse_lnd(str(entry.caesar_lnd_path))
            if caesar_lnd_raw:
                caesar_lnd, caesar_lm_alignment = align_caesar_landmarks_to_mesh(
                    caesar_lnd_raw,
                    mesh_caesar.vertices,
                )
                if caesar_lm_alignment is not None and 'warning' in caesar_lm_alignment:
                    caesar_lm_warning = caesar_lm_alignment['warning']

        caesar_lm_names = None
        caesar_lm_pos = None
        if caesar_lnd:
            caesar_lm_names = list(caesar_lnd.keys())
            caesar_lm_pos = np.array(list(caesar_lnd.values()), dtype=float)
            caesar_lm_cfg = APP_CONFIG.render.caesar_landmarks
            ps.register_point_cloud(
                "CAESAR_Landmarks", caesar_lm_pos,
                color=caesar_lm_cfg.color,
                radius=caesar_lm_cfg.radius,
                enabled=caesar_lm_cfg.enabled,
            )

        self.mesh_caesar = mesh_caesar
        self.caesar_lnd  = caesar_lnd
        self.caesar_lm_names = caesar_lm_names
        self.caesar_lm_pos = caesar_lm_pos
        self.caesar_lm_pos_reg = None
        self.caesar_lm_warning = caesar_lm_warning
        self.caesar_lm_alignment = caesar_lm_alignment
        self.caesar_unit_ctx = caesar_unit_ctx

        print(f"[load] CAESAR: {len(mesh_caesar.vertices):,} verts, "
              f"{len(caesar_lnd)} landmarks | source_unit={self.caesar_unit_ctx.original_unit} "
              f"| runtime_unit=mm")
        if caesar_lm_alignment is not None:
            print(
                "  [load] CAESAR landmarks: "
                f"{caesar_lm_alignment['rotation_label']} + rigid fit | "
                f"mean mesh err={caesar_lm_alignment['mean_mesh_error_mm']:.2f}mm | "
                f"max={caesar_lm_alignment['max_mesh_error_mm']:.2f}mm"
            )
        if caesar_lm_warning is not None:
            print(f"  [load] {caesar_lm_warning}")

        # Trigger coordinate diagnosis if SizeStream is already loaded
        if self.mesh_ss is not None:
            self.coord_diag = diagnose_coordinate_systems(
                self.mesh_ss, self.mesh_caesar, self.caesar_lnd
            )

    # ==========================================================================
    # C. Registration
    # ==========================================================================

    def run_registration(self):
        """
        Run the full ICP registration pipeline (CAESAR -> SizeStream space).

        Runtime registration is executed in millimeters. load_caesar() already
        normalizes the CAESAR mesh into runtime mm, while exported files are
        later restored to the original source unit.

        Delegates to registration.run_icp_registration() which handles:
            axis swap -> centroid align -> coarse ICP -> fine ICP

        Registers "CAESAR_Registered" (green mesh) and hides raw "CAESAR".

        Returns:
            (rmse, fitness, quality_str)
        """
        mesh_reg, T_total, rmse, fitness, quality = run_icp_registration(
            self.mesh_ss, self.mesh_caesar,
            self.coord_diag, build_axis_swap_matrix,
        )

        # Register registered mesh in Polyscope (green)
        self._register_caesar_surface(
            "CAESAR_Registered",
            mesh_reg,
            APP_CONFIG.render.registered_mesh,
        )
        # Hide unregistered CAESAR
        if ps.has_surface_mesh("CAESAR"):
            ps.get_surface_mesh("CAESAR").set_enabled(False)

        self.mesh_registered = mesh_reg
        self.icp_rmse        = rmse
        self.icp_fitness     = fitness
        self.transform_total = T_total

        if self.caesar_lm_pos is not None and len(self.caesar_lm_pos) > 0:
            lm_h = np.column_stack([
                self.caesar_lm_pos,
                np.ones(len(self.caesar_lm_pos), dtype=float),
            ])
            self.caesar_lm_pos_reg = (lm_h @ T_total.T)[:, :3]
            reg_lm_cfg = APP_CONFIG.render.registered_landmarks
            ps.register_point_cloud(
                "CAESAR_Landmarks_Registered", self.caesar_lm_pos_reg,
                color=reg_lm_cfg.color,
                radius=reg_lm_cfg.radius,
                enabled=reg_lm_cfg.enabled,
            )

        return rmse, fitness, quality

    def save_registered(self, subject_id: str):
        """
        Save registered CAESAR mesh and transform matrix to processed/.

        Creates processed/ directory on first call. Exports:
            - {subject_id}_registered.ply  (mesh, restored to original CAESAR unit)
            - {subject_id}_transform.npy   (4x4 matrix in original CAESAR unit)

        Args:
            subject_id: e.g. "csr0052a"

        Returns:
            pathlib.Path to the saved PLY file
        """
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        out_ply = PROCESSED_DIR / f"{subject_id}_registered.ply"
        out_npy = PROCESSED_DIR / f"{subject_id}_transform.npy"

        mesh_to_save = self.mesh_registered.copy()
        transform_to_save = np.array(self.transform_total, dtype=float, copy=True)
        export_unit = "mm"
        if self.caesar_unit_ctx is not None:
            mesh_to_save.vertices = from_runtime_mm_vertices(
                mesh_to_save.vertices, self.caesar_unit_ctx
            )
            transform_to_save = transform_mm_to_original_units(
                transform_to_save, self.caesar_unit_ctx
            )
            export_unit = self.caesar_unit_ctx.original_unit

        mesh_to_save.export(str(out_ply))
        np.save(str(out_npy), transform_to_save)
        print(f"[save] {out_ply.name} + {out_npy.name} ({export_unit})")
        return out_ply

    # ==========================================================================
    # D. Distance comparison
    # ==========================================================================

    def compare_landmark_distances(self):
        """
        Compute distances from SS landmarks to the registered CAESAR surface.

        Two types of distance are computed:
            1. Per-landmark: SS landmark -> nearest point on CAESAR surface
            2. Per-vertex:   every SS vertex -> nearest point on CAESAR surface (heatmap)

        Color mapping uses self.color_max_mm (controlled by the UI slider).

        Registers to Polyscope:
            - "Distance_to_CAESAR": color quantity on "SizeStream" mesh
            - "Landmark_Errors": curve network showing error vectors
        """
        if self.lm_pos_ss is None or self.mesh_registered is None:
            raise ValueError("Need SS landmarks + completed registration first")

        # Per-landmark distance (also returns closest points for visualization)
        closest_pts, lm_distances, _ = trimesh.proximity.closest_point(
            self.mesh_registered, self.lm_pos_ss
        )

        # Per-vertex distance (for heatmap)
        _, vert_dists, _ = trimesh.proximity.closest_point(
            self.mesh_registered, self.mesh_ss.vertices
        )

        # Color mapping via colorBar
        d_max = self.color_max_mm
        colors = np.array([
            _changeValueToColor(d_max, 0.0, d) for d in vert_dists
        ])

        # Apply color to SizeStream mesh
        ps.get_surface_mesh("SizeStream").add_color_quantity(
            "Distance_to_CAESAR", colors, enabled=True
        )

        # Error vector lines: SS landmark -> closest point on CAESAR
        n = len(self.lm_pos_ss)
        lines_verts = np.concatenate([self.lm_pos_ss, closest_pts], axis=0)
        lines_edges = np.array([[i, i + n] for i in range(n)])
        error_cfg = APP_CONFIG.render.landmark_errors
        ps.register_curve_network(
            "Landmark_Errors", lines_verts, lines_edges,
            color=error_cfg.color, radius=error_cfg.radius,
        )

        self.landmark_distances = lm_distances

        print(f"[dist] {n} landmarks | mean={lm_distances.mean():.2f}mm "
              f"| max={lm_distances.max():.2f}mm | std={lm_distances.std():.2f}mm")

    # ==========================================================================
    # E. Geodesic
    # ==========================================================================

    def show_geodesic_endpoints(self, pt_a: np.ndarray, pt_b: np.ndarray):
        """
        Show the currently selected geodesic endpoints immediately.

        This preview is independent of the actual geodesic solve so the user can
        confirm the start/end selection before clicking "Compute Geodesic".
        """
        points = np.array([pt_a, pt_b], dtype=float)
        if ps.has_point_cloud("Geo_Endpoints"):
            ps.remove_point_cloud("Geo_Endpoints")

        endpoint_handle = ps.register_point_cloud(
            "Geo_Endpoints", points,
            radius=APP_CONFIG.render.geodesic_endpoints.radius,
        )
        if hasattr(endpoint_handle, "add_color_quantity"):
            endpoint_cfg = APP_CONFIG.render.geodesic_endpoints
            endpoint_handle.add_color_quantity(
                "Endpoint_Role",
                np.array([
                    endpoint_cfg.start_color,
                    endpoint_cfg.end_color,
                ], dtype=float),
                enabled=True,
            )

    def compute_and_show_geodesic(self, pt_a: np.ndarray, pt_b: np.ndarray) -> float:
        """
        Compute and visualize the geodesic path between two points on the SS mesh.

        Registers to Polyscope:
            - "Geodesic_Path": gold curve network along the mesh surface
            - "Geo_Endpoints": orange point cloud marking start and end

        Args:
            pt_a: 3D start point (snapped to nearest vertex internally)
            pt_b: 3D end point (snapped to nearest vertex internally)

        Returns:
            Geodesic length in mm (float; inf if path is disconnected)
        """
        self.show_geodesic_endpoints(pt_a, pt_b)

        length, path_verts = compute_geodesic(
            self.ss_edge_graph, self.mesh_ss.vertices,
            pt_a, pt_b,
            kdtree=self.ss_kdtree,
            exact_solver=self.ss_geodesic_solver,
        )

        if path_verts is not None and len(path_verts) >= 2:
            n = len(path_verts)
            edges = np.array([[i, i + 1] for i in range(n - 1)])
            geodesic_cfg = APP_CONFIG.render.geodesic_path
            ps.register_curve_network(
                "Geodesic_Path", path_verts, edges,
                color=geodesic_cfg.color,
                radius=geodesic_cfg.radius,
            )

        self.geodesic_length = length
        return length

    # ==========================================================================
    # E. Derived Landmarks (V3)
    # ==========================================================================

    _DERIVED_YAML = pathlib.Path(__file__).resolve().parent / "config" / "derived_landmarks.yaml"

    def compute_derived_landmarks(self):
        if self.mesh_ss is None or not self.ss_lm_dict:
            raise RuntimeError("Load SizeStream mesh + landmarks first")

        if self.derived_lm_config is None:
            self.derived_lm_config = load_derived_landmark_config(str(self._DERIVED_YAML))

        self.derived_lm_dict = compute_all_derived_landmarks(
            self.mesh_ss, self.ss_lm_dict, self.derived_lm_config,
        )

        families = {}
        ref_positions = []
        for name, info in self.derived_lm_dict.items():
            families.setdefault(info["family"], []).append(info["position"])
            cfg = self.derived_lm_config["landmarks"][name]
            from derived_landmarks import resolve_landmark_names
            tri_resolved = resolve_landmark_names(cfg["triangle"], self.derived_lm_config)
            for tri_name in tri_resolved:
                if tri_name in self.ss_lm_dict:
                    ref_positions.append(self.ss_lm_dict[tri_name])

        try:
            if ref_positions:
                ps.register_point_cloud(
                    "Ref_Triangle_Vertices",
                    np.array(ref_positions),
                    color=[1.0, 0.5, 0.5],
                    enabled=True,
                    radius=0.004,
                )
            for family, positions in families.items():
                ps.register_point_cloud(
                    f"Derived_{family}",
                    np.array(positions),
                    color=[0.8, 0.1, 0.1],
                    enabled=True,
                    radius=0.005,
                )
        except Exception:
            pass

    def compute_shoulder_measurements(self):
        if not self.derived_lm_dict:
            raise RuntimeError("Compute derived landmarks first")

        config = self.derived_lm_config
        derived_flat = {n: d["position"] for n, d in self.derived_lm_dict.items()}

        def geodesic_fn(pt_a, pt_b):
            return compute_geodesic(
                self.ss_edge_graph, self.mesh_ss.vertices,
                pt_a, pt_b,
                kdtree=self.ss_kdtree,
                exact_solver=self.ss_geodesic_solver,
            )

        self.measurement_results = compute_configured_measurements(
            self.mesh_ss, self.ss_lm_dict, derived_flat,
            config["measurements"], geodesic_fn, config=config,
        )

        combined = dict(self.ss_lm_dict)
        combined.update(derived_flat)
        for r in self.measurement_results:
            if r.method == "geodesic":
                pt_a = np.asarray(combined[r.source_landmarks[0]])
                pt_b = np.asarray(combined[r.source_landmarks[1]])
                _, path_verts = geodesic_fn(pt_a, pt_b)
                if path_verts is not None and len(path_verts) >= 2:
                    n = len(path_verts)
                    edges = np.array([[i, i + 1] for i in range(n - 1)])
                    if r.family == "Neck":
                        color = [0.9, 0.2, 0.7]
                    elif "MidShoulder" in r.name:
                        color = [0.2, 0.8, 0.3]
                    else:
                        color = [0.2, 0.7, 0.7]
                    try:
                        ps.register_curve_network(
                            f"Geo_{r.name}", path_verts, edges,
                            color=color, radius=0.001,
                        )
                    except Exception:
                        pass  # Polyscope not initialized in headless mode

    def export_results_to_excel(self, output_path: str):
        import openpyxl

        wb = openpyxl.Workbook()
        ws_lm = wb.active
        ws_lm.title = "Landmarks"
        ws_lm.append(["Name", "X_mm", "Y_mm", "Z_mm", "Type", "Family"])

        for name, pos in self.ss_lm_dict.items():
            ws_lm.append([name, float(pos[0]), float(pos[1]), float(pos[2]), "original", ""])

        for name, info in self.derived_lm_dict.items():
            p = info["position"]
            ws_lm.append([name, float(p[0]), float(p[1]), float(p[2]), "derived", info["family"]])

        ws_m = wb.create_sheet("Measurements")
        ws_m.append(["Family", "Name", "Value_mm", "Value_cm", "Method", "From", "To"])
        for r in self.measurement_results:
            ws_m.append([
                r.family, r.name, round(r.value_mm, 2), round(r.value_mm / 10, 2),
                r.method, r.source_landmarks[0], r.source_landmarks[1],
            ])

        wb.save(output_path)
