"""Unit tests for derived_landmarks.py — barycentric engine + YAML loader."""
import numpy as np
import pytest
import tempfile, pathlib, yaml


def test_from_barycentric_midpoint():
    from derived_landmarks import from_barycentric
    A = np.array([0.0, 0.0, 0.0])
    B = np.array([10.0, 0.0, 0.0])
    C = np.array([0.0, 10.0, 0.0])
    result = from_barycentric(0.5, 0.5, 0.0, A, B, C)
    np.testing.assert_allclose(result, [5.0, 0.0, 0.0])


def test_from_barycentric_centroid():
    from derived_landmarks import from_barycentric
    A = np.array([0.0, 0.0, 0.0])
    B = np.array([9.0, 0.0, 0.0])
    C = np.array([0.0, 9.0, 0.0])
    result = from_barycentric(1/3, 1/3, 1/3, A, B, C)
    np.testing.assert_allclose(result, [3.0, 3.0, 0.0])


def test_to_barycentric_roundtrip():
    from derived_landmarks import to_barycentric, from_barycentric
    A = np.array([10.0, 20.0, 30.0])
    B = np.array([40.0, 50.0, 60.0])
    C = np.array([70.0, 10.0, 20.0])
    P = np.array([35.0, 30.0, 40.0])
    alpha, beta, gamma = to_barycentric(P, A, B, C)
    assert abs(alpha + beta + gamma - 1.0) < 1e-10
    P_reconstructed = from_barycentric(alpha, beta, gamma, A, B, C)
    np.testing.assert_allclose(P_reconstructed, P, atol=1e-8)


def test_to_barycentric_outside_triangle():
    from derived_landmarks import to_barycentric
    A = np.array([0.0, 0.0, 0.0])
    B = np.array([10.0, 0.0, 0.0])
    C = np.array([0.0, 10.0, 0.0])
    P = np.array([15.0, 15.0, 0.0])
    alpha, beta, gamma = to_barycentric(P, A, B, C)
    assert abs(alpha + beta + gamma - 1.0) < 1e-10
    assert min(alpha, beta, gamma) < 0


def test_load_config_valid():
    from derived_landmarks import load_derived_landmark_config
    config = load_derived_landmark_config("config/derived_landmarks.yaml")
    assert config["version"] == 1
    assert "ArmholeDepthFrontLeft" in config["landmarks"]
    lm = config["landmarks"]["ArmholeDepthFrontLeft"]
    assert lm["triangle"] == ["ShoulderLeft", "ArmpitLeft", "NeckLeft"]
    assert lm["weights"] is None
    assert lm["init_method"] == "contour_z_extremum"
    assert lm["family"] == "Armhole"
    assert "MidShoulderToApexLeft" in config["measurements"]


def test_load_config_invalid_version():
    from derived_landmarks import load_derived_landmark_config
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.safe_dump({"version": 99, "landmarks": {}, "measurements": {}}, f)
        f.flush()
        with pytest.raises(ValueError, match="version"):
            load_derived_landmark_config(f.name)


def test_save_weights_roundtrip():
    from derived_landmarks import load_derived_landmark_config, save_weights_to_yaml
    import shutil
    tmp = pathlib.Path(tempfile.mkdtemp()) / "test.yaml"
    shutil.copy("config/derived_landmarks.yaml", tmp)
    save_weights_to_yaml(tmp, "ArmholeDepthFrontLeft", [0.35, 0.55, 0.10])
    config = load_derived_landmark_config(tmp)
    w = config["landmarks"]["ArmholeDepthFrontLeft"]["weights"]
    np.testing.assert_allclose(w, [0.35, 0.55, 0.10])


import trimesh


@pytest.fixture(scope="module")
def shared_mesh_and_landmarks():
    """Load real SizeStream mesh and landmarks for integration tests."""
    import sys
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
    from data_loader import scan_data_folders
    catalog = scan_data_folders()
    entry = catalog.subjects[list(catalog.subjects.keys())[0]]
    mesh = trimesh.load(str(entry.ss_obj_path), process=False)
    lm3d = catalog.lm_data["landmarks_3d"]
    lms = {name: coords[0] for name, coords in lm3d.items()}
    return mesh, lms


def test_init_contour_z_extremum_max(shared_mesh_and_landmarks):
    from derived_landmarks import init_contour_z_extremum
    mesh, lms = shared_mesh_and_landmarks
    params = {"extremum": "max", "plane_landmarks": ["ShoulderLeft", "ArmpitLeft"]}
    pt = init_contour_z_extremum(mesh, lms, params)
    assert pt.shape == (3,)
    assert pt[2] > lms["ArmpitLeft"][2]


def test_init_contour_z_extremum_min(shared_mesh_and_landmarks):
    from derived_landmarks import init_contour_z_extremum
    mesh, lms = shared_mesh_and_landmarks
    params = {"extremum": "min", "plane_landmarks": ["ShoulderLeft", "ArmpitLeft"]}
    pt = init_contour_z_extremum(mesh, lms, params)
    assert pt.shape == (3,)
    assert pt[2] < lms["ShoulderLeft"][2]


def test_init_contour_z_extremum_no_intersection():
    from derived_landmarks import init_contour_z_extremum
    mesh = trimesh.Trimesh(
        vertices=[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        faces=[[0, 1, 2], [0, 1, 3], [0, 2, 3], [1, 2, 3]],
    )
    lms = {"A": np.array([500.0, 500.0, 500.0]), "B": np.array([500.0, 600.0, 500.0])}
    params = {"extremum": "max", "plane_landmarks": ["A", "B"]}
    with pytest.raises(ValueError, match="did not intersect"):
        init_contour_z_extremum(mesh, lms, params)


def test_init_plane_intersection(shared_mesh_and_landmarks):
    from derived_landmarks import init_plane_intersection, load_derived_landmark_config
    mesh, lms = shared_mesh_and_landmarks
    cfg = load_derived_landmark_config("config/derived_landmarks.yaml")
    params = {"coronal_landmark": "NeckFront", "sagittal_landmark": "NeckLeft"}
    pt = init_plane_intersection(mesh, lms, params, config=cfg)
    assert pt.shape == (3,)
    assert 1250 < pt[1] < 1400


def test_init_arc_length_ratio_stub():
    from derived_landmarks import init_arc_length_ratio
    with pytest.raises(NotImplementedError):
        init_arc_length_ratio(None, {}, {})


def test_init_three_plane_intersection_stub():
    from derived_landmarks import init_three_plane_intersection
    with pytest.raises(NotImplementedError):
        init_three_plane_intersection(None, {}, {})


def test_compute_derived_landmark_null_weights(shared_mesh_and_landmarks):
    from derived_landmarks import compute_derived_landmark
    mesh, lms = shared_mesh_and_landmarks
    lm_config = {
        "triangle": ["ShoulderLeft", "ArmpitLeft", "NeckLeft"],
        "weights": None,
        "init_method": "contour_z_extremum",
        "init_params": {"extremum": "max", "plane_landmarks": ["ShoulderLeft", "ArmpitLeft"]},
        "family": "Armhole",
    }
    pos, weights = compute_derived_landmark(mesh, lms, "ArmholeDepthFrontLeft", lm_config)
    assert pos.shape == (3,)
    assert len(weights) == 3
    assert abs(sum(weights) - 1.0) < 1e-8


def test_compute_derived_landmark_preset_weights(shared_mesh_and_landmarks):
    from derived_landmarks import compute_derived_landmark
    mesh, lms = shared_mesh_and_landmarks
    lm_config = {
        "triangle": ["ShoulderLeft", "ArmpitLeft", "NeckLeft"],
        "weights": [0.4, 0.4, 0.2],
        "init_method": "contour_z_extremum",
        "init_params": {"extremum": "max", "plane_landmarks": ["ShoulderLeft", "ArmpitLeft"]},
        "family": "Armhole",
    }
    pos, weights = compute_derived_landmark(mesh, lms, "test", lm_config)
    assert pos.shape == (3,)
    np.testing.assert_allclose(weights, [0.4, 0.4, 0.2])


def test_compute_all_derived_landmarks(shared_mesh_and_landmarks):
    from derived_landmarks import compute_all_derived_landmarks, load_derived_landmark_config
    mesh, lms = shared_mesh_and_landmarks
    config = load_derived_landmark_config("config/derived_landmarks.yaml")
    result = compute_all_derived_landmarks(mesh, lms, config)
    assert len(result) == 8
    for name in ["NeckFrontLeft", "NeckFrontRight", "NeckBackLeft", "NeckBackRight",
                 "ArmholeDepthFrontLeft", "ArmholeDepthBackLeft",
                 "ArmholeDepthFrontRight", "ArmholeDepthBackRight"]:
        assert name in result
        assert result[name]["position"].shape == (3,)
        assert len(result[name]["weights"]) == 3


def test_compute_configured_measurements(shared_mesh_and_landmarks):
    from derived_landmarks import (
        compute_configured_measurements, load_derived_landmark_config,
        compute_all_derived_landmarks, MeasurementRecord,
    )
    mesh, lms = shared_mesh_and_landmarks
    config = load_derived_landmark_config("config/derived_landmarks.yaml")
    derived = compute_all_derived_landmarks(mesh, lms, config)
    derived_flat = {n: d["position"] for n, d in derived.items()}

    def mock_geodesic(pt_a, pt_b):
        dist = float(np.linalg.norm(pt_a - pt_b))
        return dist, np.array([pt_a, pt_b])

    records = compute_configured_measurements(
        mesh, lms, derived_flat, config["measurements"], mock_geodesic
    )
    assert len(records) >= 8  # 4 geodesic + 4 y_projection
    families = {r.family for r in records}
    assert "Shoulder" in families
    methods = {r.method for r in records}
    assert "geodesic" in methods
    assert "y_projection" in methods
    for r in records:
        assert r.value_mm > 0
