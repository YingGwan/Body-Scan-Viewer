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
