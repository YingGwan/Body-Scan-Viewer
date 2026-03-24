"""
Tests for strict JSON app configuration loading.
"""

import json
import os
import pathlib
import shutil
import sys
import uuid

import pytest


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _build_valid_config(tmp_path):
    data_root = tmp_path / "dataset"
    size_stream_dir = data_root / "SIZE_STREAM"
    caesar_dir = data_root / "CAESAR"
    processed_dir = tmp_path / "processed"
    size_stream_dir.mkdir(parents=True)
    caesar_dir.mkdir(parents=True)
    processed_dir.mkdir(parents=True)

    return {
        "version": 1,
        "version__comment": "Schema version for the body scan viewer configuration.",
        "paths": {
            "data_root": str(data_root),
            "data_root__comment": "Absolute or project-relative folder containing the dataset tree.",
            "size_stream_dir": str(size_stream_dir),
            "size_stream_dir__comment": "Folder containing SS_OUT_*.obj and the SizeStream XLSX landmark file.",
            "caesar_dir": str(caesar_dir),
            "caesar_dir__comment": "Folder containing CAESAR csr*.ply and optional csr*.lnd files.",
            "processed_dir": str(processed_dir),
            "processed_dir__comment": "Folder where registered outputs are written.",
        },
        "paths__comment": "Input and output directory settings.",
        "viewer": {
            "up_dir": "y_up",
            "up_dir__comment": "Polyscope up direction enum.",
            "ground_plane_mode": "none",
            "ground_plane_mode__comment": "Polyscope ground plane mode enum.",
            "transparency_mode": "pretty",
            "transparency_mode__comment": "Polyscope transparency mode enum.",
            "transparency_render_passes": 2,
            "transparency_render_passes__comment": "Render passes for pretty transparency; integer >= 1.",
        },
        "viewer__comment": "Global Polyscope viewer defaults applied at startup.",
        "render": {
            "sizestream_mesh": {
                "color": [0.2, 0.4, 1.0],
                "color__comment": "Default RGB color for the SizeStream mesh.",
                "enabled": True,
                "enabled__comment": "Whether the mesh is visible immediately after registration.",
                "transparency": 0.5,
                "transparency__comment": "Mesh transparency in [0, 1].",
                "smooth_shade": True,
                "smooth_shade__comment": "Whether to enable smooth shading.",
            },
            "sizestream_mesh__comment": "SizeStream mesh render parameters.",
            "sizestream_landmarks": {
                "color": [0.2, 0.4, 1.0],
                "color__comment": "Default RGB color for SizeStream landmarks.",
                "enabled": True,
                "enabled__comment": "Whether SizeStream landmarks are shown on load.",
                "radius": 0.006,
                "radius__comment": "Relative landmark point radius.",
            },
            "sizestream_landmarks__comment": "SizeStream landmark point render parameters.",
            "caesar_mesh": {
                "color": [1.0, 0.55, 0.1],
                "color__comment": "Fallback base color when PLY vertex RGB is not present.",
                "enabled": False,
                "enabled__comment": "Whether the raw CAESAR mesh is visible immediately after load.",
                "smooth_shade": True,
                "smooth_shade__comment": "Whether to enable smooth shading.",
            },
            "caesar_mesh__comment": "CAESAR mesh render parameters.",
            "caesar_landmarks": {
                "color": [1.0, 0.55, 0.1],
                "color__comment": "Default RGB color for CAESAR landmarks.",
                "enabled": False,
                "enabled__comment": "Whether raw CAESAR landmarks are visible immediately after load.",
                "radius": 0.006,
                "radius__comment": "Relative landmark point radius.",
            },
            "caesar_landmarks__comment": "Raw CAESAR landmark render parameters.",
            "registered_mesh": {
                "color": [0.2, 0.85, 0.3],
                "color__comment": "Fallback base color for the registered CAESAR mesh.",
                "enabled": True,
                "enabled__comment": "Whether the registered mesh is visible after ICP.",
                "smooth_shade": True,
                "smooth_shade__comment": "Whether to enable smooth shading.",
            },
            "registered_mesh__comment": "Registered CAESAR mesh render parameters.",
            "registered_landmarks": {
                "color": [1.0, 0.75, 0.2],
                "color__comment": "Default RGB color for registered CAESAR landmarks.",
                "enabled": False,
                "enabled__comment": "Whether registered CAESAR landmarks are visible after ICP.",
                "radius": 0.006,
                "radius__comment": "Relative landmark point radius.",
            },
            "registered_landmarks__comment": "Registered CAESAR landmark render parameters.",
            "landmark_errors": {
                "color": [1.0, 0.3, 0.2],
                "color__comment": "Default RGB color for landmark error vectors.",
                "radius": 0.001,
                "radius__comment": "Curve radius for landmark error vectors.",
            },
            "landmark_errors__comment": "Landmark error curve render parameters.",
            "geodesic_path": {
                "color": [1.0, 0.85, 0.1],
                "color__comment": "Default RGB color for the geodesic path.",
                "radius": 0.003,
                "radius__comment": "Curve radius for the geodesic path.",
            },
            "geodesic_path__comment": "Geodesic path render parameters.",
            "geodesic_endpoints": {
                "radius": 0.008,
                "radius__comment": "Point radius for the selected geodesic endpoints.",
                "start_color": [1.0, 0.2, 0.2],
                "start_color__comment": "RGB color for the first selected endpoint.",
                "end_color": [0.05, 0.35, 0.18],
                "end_color__comment": "RGB color for the second selected endpoint.",
            },
            "geodesic_endpoints__comment": "Geodesic endpoint preview render parameters.",
        },
        "render__comment": "Rendering defaults for meshes, landmarks, curves, and endpoint previews.",
        "distance": {
            "default_color_max_mm": 30.0,
            "default_color_max_mm__comment": "Default upper bound for the distance heatmap color scale.",
            "slider_min_mm": 1.0,
            "slider_min_mm__comment": "Lower UI bound for the distance color scale slider.",
            "slider_max_mm": 100.0,
            "slider_max_mm__comment": "Upper UI bound for the distance color scale slider.",
        },
        "distance__comment": "Distance heatmap and slider defaults.",
        "registration": {
            "sampling": {
                "max_points": 30000,
                "max_points__comment": "Maximum number of points sampled from each mesh for ICP.",
                "random_seed": 42,
                "random_seed__comment": "Seed used for reproducible point sampling.",
            },
            "sampling__comment": "Sampling parameters for ICP point clouds.",
            "target_normals": {
                "radius_mm": 30.0,
                "radius_mm__comment": "Neighborhood radius used when estimating target normals.",
                "max_nn": 30,
                "max_nn__comment": "Maximum neighbors used when estimating target normals.",
            },
            "target_normals__comment": "Normal estimation settings for the SizeStream target point cloud.",
            "coarse_icp": {
                "max_correspondence_distance_mm": 150.0,
                "max_correspondence_distance_mm__comment": "Distance gate for the coarse ICP stage.",
                "max_iteration": 50,
                "max_iteration__comment": "Maximum iterations for the coarse ICP stage.",
                "relative_fitness": 1e-4,
                "relative_fitness__comment": "Early-stop threshold for coarse ICP fitness changes.",
                "relative_rmse": 1e-4,
                "relative_rmse__comment": "Early-stop threshold for coarse ICP RMSE changes.",
            },
            "coarse_icp__comment": "Coarse ICP stage parameters.",
            "fine_icp": {
                "max_correspondence_distance_mm": 25.0,
                "max_correspondence_distance_mm__comment": "Distance gate for the fine ICP stage.",
                "max_iteration": 100,
                "max_iteration__comment": "Maximum iterations for the fine ICP stage.",
                "relative_fitness": 1e-6,
                "relative_fitness__comment": "Early-stop threshold for fine ICP fitness changes.",
                "relative_rmse": 1e-6,
                "relative_rmse__comment": "Early-stop threshold for fine ICP RMSE changes.",
            },
            "fine_icp__comment": "Fine ICP stage parameters.",
            "quality": {
                "fitness_fail_below": 0.1,
                "fitness_fail_below__comment": "Registrations below this fitness are marked failed.",
                "excellent_rmse_below_mm": 5.0,
                "excellent_rmse_below_mm__comment": "RMSE threshold for the excellent registration label.",
                "acceptable_rmse_below_mm": 15.0,
                "acceptable_rmse_below_mm__comment": "RMSE threshold for the acceptable registration label.",
            },
            "quality__comment": "Registration quality thresholds.",
        },
        "registration__comment": "Sampling, ICP, and registration-quality settings.",
    }


def _write_json(path, payload):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


@pytest.fixture
def workspace_tmp_path():
    root = pathlib.Path(__file__).resolve().parent / "_tmp_config_loader"
    path = root / uuid.uuid4().hex
    path.mkdir(parents=True, exist_ok=False)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def test_load_app_config_accepts_valid_config(workspace_tmp_path):
    from config_loader import load_app_config

    config_path = workspace_tmp_path / "app_config.json"
    _write_json(config_path, _build_valid_config(workspace_tmp_path))

    cfg = load_app_config(config_path)

    assert cfg.viewer.up_dir == "y_up"
    assert cfg.viewer.transparency_render_passes == 2
    assert cfg.paths.size_stream_dir.name == "SIZE_STREAM"
    assert cfg.render.geodesic_endpoints.radius == pytest.approx(0.008)


def test_load_app_config_rejects_missing_comment(workspace_tmp_path):
    from config_loader import ConfigError, load_app_config

    payload = _build_valid_config(workspace_tmp_path)
    del payload["viewer"]["up_dir__comment"]
    config_path = workspace_tmp_path / "app_config.json"
    _write_json(config_path, payload)

    with pytest.raises(ConfigError, match="up_dir__comment"):
        load_app_config(config_path)


def test_load_app_config_rejects_unknown_key(workspace_tmp_path):
    from config_loader import ConfigError, load_app_config

    payload = _build_valid_config(workspace_tmp_path)
    payload["viewer"]["mystery_mode"] = True
    payload["viewer"]["mystery_mode__comment"] = "Should not be accepted."
    config_path = workspace_tmp_path / "app_config.json"
    _write_json(config_path, payload)

    with pytest.raises(ConfigError, match="viewer\\.mystery_mode"):
        load_app_config(config_path)


def test_load_app_config_rejects_invalid_enum_and_range(workspace_tmp_path):
    from config_loader import ConfigError, load_app_config

    payload = _build_valid_config(workspace_tmp_path)
    payload["viewer"]["transparency_mode"] = "fast"
    payload["viewer"]["transparency_render_passes"] = 0
    config_path = workspace_tmp_path / "app_config.json"
    _write_json(config_path, payload)

    with pytest.raises(ConfigError, match="transparency_mode|transparency_render_passes"):
        load_app_config(config_path)


def test_load_app_config_rejects_missing_directory(workspace_tmp_path):
    from config_loader import ConfigError, load_app_config

    payload = _build_valid_config(workspace_tmp_path)
    payload["paths"]["caesar_dir"] = str(workspace_tmp_path / "missing_caesar")
    config_path = workspace_tmp_path / "app_config.json"
    _write_json(config_path, payload)

    with pytest.raises(ConfigError, match="caesar_dir"):
        load_app_config(config_path)
