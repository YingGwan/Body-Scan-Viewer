"""
Strict JSON configuration loading for the body scan viewer.

Two config files are used:
  config/project_config.json  — dataset-specific settings (paths, registration, distance).
                                 Swap this file when switching to a different project.
  config/render_config.json   — visual appearance settings (viewer, render).
                                 Shared across all projects; rarely needs editing.
"""

import json
import pathlib
from dataclasses import dataclass
from typing import Any, Iterable, Optional, Tuple


PROJECT_ROOT = pathlib.Path(__file__).resolve().parent
DEFAULT_PROJECT_CONFIG_PATH = PROJECT_ROOT / "config" / "project_config.json"
DEFAULT_RENDER_CONFIG_PATH  = PROJECT_ROOT / "config" / "render_config.json"

UP_DIR_VALUES = (
    "x_up",
    "neg_x_up",
    "y_up",
    "neg_y_up",
    "z_up",
    "neg_z_up",
)
GROUND_PLANE_MODE_VALUES = (
    "none",
    "tile",
    "tile_reflection",
    "shadow_only",
)
TRANSPARENCY_MODE_VALUES = (
    "none",
    "simple",
    "pretty",
)


class ConfigError(ValueError):
    """Raised when a config file is missing, malformed, or semantically invalid."""


@dataclass(frozen=True)
class PathsConfig:
    data_root: pathlib.Path
    size_stream_dir: pathlib.Path
    caesar_dir: pathlib.Path
    processed_dir: pathlib.Path


@dataclass(frozen=True)
class ViewerConfig:
    up_dir: str
    ground_plane_mode: str
    transparency_mode: str
    transparency_render_passes: int


@dataclass(frozen=True)
class MeshRenderConfig:
    color: Tuple[float, float, float]
    enabled: bool
    smooth_shade: bool
    transparency: float = 0.0


@dataclass(frozen=True)
class PointRenderConfig:
    color: Tuple[float, float, float]
    enabled: bool
    radius: float


@dataclass(frozen=True)
class CurveRenderConfig:
    color: Tuple[float, float, float]
    radius: float


@dataclass(frozen=True)
class GeodesicEndpointsRenderConfig:
    radius: float
    start_color: Tuple[float, float, float]
    end_color: Tuple[float, float, float]


@dataclass(frozen=True)
class RenderConfig:
    sizestream_mesh: MeshRenderConfig
    sizestream_landmarks: PointRenderConfig
    caesar_mesh: MeshRenderConfig
    caesar_landmarks: PointRenderConfig
    registered_mesh: MeshRenderConfig
    registered_landmarks: PointRenderConfig
    landmark_errors: CurveRenderConfig
    geodesic_path: CurveRenderConfig
    geodesic_endpoints: GeodesicEndpointsRenderConfig


@dataclass(frozen=True)
class DistanceConfig:
    default_color_max_mm: float
    slider_min_mm: float
    slider_max_mm: float


@dataclass(frozen=True)
class RegistrationSamplingConfig:
    max_points: int
    random_seed: int


@dataclass(frozen=True)
class RegistrationNormalsConfig:
    radius_mm: float
    max_nn: int


@dataclass(frozen=True)
class ICPStageConfig:
    max_correspondence_distance_mm: float
    max_iteration: int
    relative_fitness: float
    relative_rmse: float


@dataclass(frozen=True)
class RegistrationQualityConfig:
    fitness_fail_below: float
    excellent_rmse_below_mm: float
    acceptable_rmse_below_mm: float


@dataclass(frozen=True)
class RegistrationConfig:
    sampling: RegistrationSamplingConfig
    target_normals: RegistrationNormalsConfig
    coarse_icp: ICPStageConfig
    fine_icp: ICPStageConfig
    quality: RegistrationQualityConfig


@dataclass(frozen=True)
class AppConfig:
    version: int
    paths: PathsConfig
    viewer: ViewerConfig
    render: RenderConfig
    distance: DistanceConfig
    registration: RegistrationConfig


def _raise(path: str, message: str):
    raise ConfigError(f"{path}: {message}")


def _require_object(value: Any, path: str) -> dict:
    if not isinstance(value, dict):
        _raise(path, "expected an object")
    return value


def _require_commented_object(obj: dict, path: str, keys: Iterable[str]) -> dict:
    expected = tuple(keys)
    allowed = set(expected)
    allowed.update(f"{key}__comment" for key in expected)
    unknown = sorted(set(obj.keys()) - allowed)
    if unknown:
        _raise(f"{path}.{unknown[0]}", "unknown key")

    for key in expected:
        if key not in obj:
            _raise(f"{path}.{key}", "missing required key")
        comment_key = f"{key}__comment"
        if comment_key not in obj:
            _raise(f"{path}.{comment_key}", "missing required comment")
        if not isinstance(obj[comment_key], str) or not obj[comment_key].strip():
            _raise(f"{path}.{comment_key}", "comment must be a non-empty string")
    return obj


def _require_bool(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        _raise(path, "expected a boolean")
    return value


def _require_int(value: Any, path: str, *, minimum: Optional[int] = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        _raise(path, "expected an integer")
    if minimum is not None and value < minimum:
        _raise(path, f"must be >= {minimum}")
    return value


def _require_float(
    value: Any,
    path: str,
    *,
    minimum: Optional[float] = None,
    maximum: Optional[float] = None,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _raise(path, "expected a number")
    result = float(value)
    if minimum is not None and result < minimum:
        _raise(path, f"must be >= {minimum}")
    if maximum is not None and result > maximum:
        _raise(path, f"must be <= {maximum}")
    return result


def _require_enum(value: Any, path: str, allowed: Iterable[str]) -> str:
    if not isinstance(value, str):
        _raise(path, "expected a string")
    if value not in allowed:
        _raise(path, f"must be one of {list(allowed)}")
    return value


def _require_color(value: Any, path: str) -> Tuple[float, float, float]:
    if not isinstance(value, list) or len(value) != 3:
        _raise(path, "expected an RGB array of length 3")
    color = tuple(_require_float(channel, f"{path}[{idx}]", minimum=0.0, maximum=1.0) for idx, channel in enumerate(value))
    return color


def _require_path(value: Any, path: str) -> pathlib.Path:
    if not isinstance(value, str) or not value.strip():
        _raise(path, "expected a non-empty path string")
    resolved = pathlib.Path(value)
    if not resolved.is_absolute():
        resolved = (PROJECT_ROOT / resolved).resolve()
    if not resolved.exists():
        _raise(path, f"path does not exist: {resolved}")
    return resolved


def _validate_paths(obj: dict) -> PathsConfig:
    path = "paths"
    obj = _require_commented_object(
        _require_object(obj, path),
        path,
        ("data_root", "size_stream_dir", "caesar_dir", "processed_dir"),
    )
    return PathsConfig(
        data_root=_require_path(obj["data_root"], f"{path}.data_root"),
        size_stream_dir=_require_path(obj["size_stream_dir"], f"{path}.size_stream_dir"),
        caesar_dir=_require_path(obj["caesar_dir"], f"{path}.caesar_dir"),
        processed_dir=_require_path(obj["processed_dir"], f"{path}.processed_dir"),
    )


def _validate_viewer(obj: dict) -> ViewerConfig:
    path = "viewer"
    obj = _require_commented_object(
        _require_object(obj, path),
        path,
        ("up_dir", "ground_plane_mode", "transparency_mode", "transparency_render_passes"),
    )
    return ViewerConfig(
        up_dir=_require_enum(obj["up_dir"], f"{path}.up_dir", UP_DIR_VALUES),
        ground_plane_mode=_require_enum(
            obj["ground_plane_mode"], f"{path}.ground_plane_mode", GROUND_PLANE_MODE_VALUES
        ),
        transparency_mode=_require_enum(
            obj["transparency_mode"], f"{path}.transparency_mode", TRANSPARENCY_MODE_VALUES
        ),
        transparency_render_passes=_require_int(
            obj["transparency_render_passes"],
            f"{path}.transparency_render_passes",
            minimum=1,
        ),
    )


def _validate_mesh_render(obj: dict, path: str, *, allow_transparency: bool) -> MeshRenderConfig:
    keys = ["color", "enabled", "smooth_shade"]
    if allow_transparency:
        keys.append("transparency")
    obj = _require_commented_object(_require_object(obj, path), path, keys)
    transparency = 0.0
    if allow_transparency:
        transparency = _require_float(obj["transparency"], f"{path}.transparency", minimum=0.0, maximum=1.0)
    return MeshRenderConfig(
        color=_require_color(obj["color"], f"{path}.color"),
        enabled=_require_bool(obj["enabled"], f"{path}.enabled"),
        smooth_shade=_require_bool(obj["smooth_shade"], f"{path}.smooth_shade"),
        transparency=transparency,
    )


def _validate_point_render(obj: dict, path: str) -> PointRenderConfig:
    obj = _require_commented_object(_require_object(obj, path), path, ("color", "enabled", "radius"))
    return PointRenderConfig(
        color=_require_color(obj["color"], f"{path}.color"),
        enabled=_require_bool(obj["enabled"], f"{path}.enabled"),
        radius=_require_float(obj["radius"], f"{path}.radius", minimum=0.0),
    )


def _validate_curve_render(obj: dict, path: str) -> CurveRenderConfig:
    obj = _require_commented_object(_require_object(obj, path), path, ("color", "radius"))
    return CurveRenderConfig(
        color=_require_color(obj["color"], f"{path}.color"),
        radius=_require_float(obj["radius"], f"{path}.radius", minimum=0.0),
    )


def _validate_geodesic_endpoints_render(obj: dict) -> GeodesicEndpointsRenderConfig:
    path = "render.geodesic_endpoints"
    obj = _require_commented_object(_require_object(obj, path), path, ("radius", "start_color", "end_color"))
    return GeodesicEndpointsRenderConfig(
        radius=_require_float(obj["radius"], f"{path}.radius", minimum=0.0),
        start_color=_require_color(obj["start_color"], f"{path}.start_color"),
        end_color=_require_color(obj["end_color"], f"{path}.end_color"),
    )


def _validate_render(obj: dict) -> RenderConfig:
    path = "render"
    obj = _require_commented_object(
        _require_object(obj, path),
        path,
        (
            "sizestream_mesh",
            "sizestream_landmarks",
            "caesar_mesh",
            "caesar_landmarks",
            "registered_mesh",
            "registered_landmarks",
            "landmark_errors",
            "geodesic_path",
            "geodesic_endpoints",
        ),
    )
    return RenderConfig(
        sizestream_mesh=_validate_mesh_render(obj["sizestream_mesh"], f"{path}.sizestream_mesh", allow_transparency=True),
        sizestream_landmarks=_validate_point_render(obj["sizestream_landmarks"], f"{path}.sizestream_landmarks"),
        caesar_mesh=_validate_mesh_render(obj["caesar_mesh"], f"{path}.caesar_mesh", allow_transparency=False),
        caesar_landmarks=_validate_point_render(obj["caesar_landmarks"], f"{path}.caesar_landmarks"),
        registered_mesh=_validate_mesh_render(obj["registered_mesh"], f"{path}.registered_mesh", allow_transparency=False),
        registered_landmarks=_validate_point_render(obj["registered_landmarks"], f"{path}.registered_landmarks"),
        landmark_errors=_validate_curve_render(obj["landmark_errors"], f"{path}.landmark_errors"),
        geodesic_path=_validate_curve_render(obj["geodesic_path"], f"{path}.geodesic_path"),
        geodesic_endpoints=_validate_geodesic_endpoints_render(obj["geodesic_endpoints"]),
    )


def _validate_distance(obj: dict) -> DistanceConfig:
    path = "distance"
    obj = _require_commented_object(
        _require_object(obj, path),
        path,
        ("default_color_max_mm", "slider_min_mm", "slider_max_mm"),
    )
    result = DistanceConfig(
        default_color_max_mm=_require_float(obj["default_color_max_mm"], f"{path}.default_color_max_mm", minimum=0.0),
        slider_min_mm=_require_float(obj["slider_min_mm"], f"{path}.slider_min_mm", minimum=0.0),
        slider_max_mm=_require_float(obj["slider_max_mm"], f"{path}.slider_max_mm", minimum=0.0),
    )
    if result.slider_max_mm < result.slider_min_mm:
        _raise(f"{path}.slider_max_mm", "must be >= distance.slider_min_mm")
    if not (result.slider_min_mm <= result.default_color_max_mm <= result.slider_max_mm):
        _raise(
            f"{path}.default_color_max_mm",
            "must lie within [distance.slider_min_mm, distance.slider_max_mm]",
        )
    return result


def _validate_sampling(obj: dict) -> RegistrationSamplingConfig:
    path = "registration.sampling"
    obj = _require_commented_object(_require_object(obj, path), path, ("max_points", "random_seed"))
    return RegistrationSamplingConfig(
        max_points=_require_int(obj["max_points"], f"{path}.max_points", minimum=1),
        random_seed=_require_int(obj["random_seed"], f"{path}.random_seed", minimum=0),
    )


def _validate_target_normals(obj: dict) -> RegistrationNormalsConfig:
    path = "registration.target_normals"
    obj = _require_commented_object(_require_object(obj, path), path, ("radius_mm", "max_nn"))
    return RegistrationNormalsConfig(
        radius_mm=_require_float(obj["radius_mm"], f"{path}.radius_mm", minimum=0.0),
        max_nn=_require_int(obj["max_nn"], f"{path}.max_nn", minimum=1),
    )


def _validate_icp_stage(obj: dict, path: str) -> ICPStageConfig:
    obj = _require_commented_object(
        _require_object(obj, path),
        path,
        ("max_correspondence_distance_mm", "max_iteration", "relative_fitness", "relative_rmse"),
    )
    return ICPStageConfig(
        max_correspondence_distance_mm=_require_float(
            obj["max_correspondence_distance_mm"],
            f"{path}.max_correspondence_distance_mm",
            minimum=0.0,
        ),
        max_iteration=_require_int(obj["max_iteration"], f"{path}.max_iteration", minimum=1),
        relative_fitness=_require_float(obj["relative_fitness"], f"{path}.relative_fitness", minimum=0.0),
        relative_rmse=_require_float(obj["relative_rmse"], f"{path}.relative_rmse", minimum=0.0),
    )


def _validate_quality(obj: dict) -> RegistrationQualityConfig:
    path = "registration.quality"
    obj = _require_commented_object(
        _require_object(obj, path),
        path,
        ("fitness_fail_below", "excellent_rmse_below_mm", "acceptable_rmse_below_mm"),
    )
    result = RegistrationQualityConfig(
        fitness_fail_below=_require_float(obj["fitness_fail_below"], f"{path}.fitness_fail_below", minimum=0.0, maximum=1.0),
        excellent_rmse_below_mm=_require_float(
            obj["excellent_rmse_below_mm"],
            f"{path}.excellent_rmse_below_mm",
            minimum=0.0,
        ),
        acceptable_rmse_below_mm=_require_float(
            obj["acceptable_rmse_below_mm"],
            f"{path}.acceptable_rmse_below_mm",
            minimum=0.0,
        ),
    )
    if result.acceptable_rmse_below_mm < result.excellent_rmse_below_mm:
        _raise(
            f"{path}.acceptable_rmse_below_mm",
            "must be >= registration.quality.excellent_rmse_below_mm",
        )
    return result


def _validate_registration(obj: dict) -> RegistrationConfig:
    path = "registration"
    obj = _require_commented_object(
        _require_object(obj, path),
        path,
        ("sampling", "target_normals", "coarse_icp", "fine_icp", "quality"),
    )
    return RegistrationConfig(
        sampling=_validate_sampling(obj["sampling"]),
        target_normals=_validate_target_normals(obj["target_normals"]),
        coarse_icp=_validate_icp_stage(obj["coarse_icp"], "registration.coarse_icp"),
        fine_icp=_validate_icp_stage(obj["fine_icp"], "registration.fine_icp"),
        quality=_validate_quality(obj["quality"]),
    )


def _load_json(path: pathlib.Path) -> dict:
    if not path.exists():
        raise ConfigError(f"config file not found: {path}")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        raise ConfigError(
            f"{path}:{exc.lineno}:{exc.colno}: invalid JSON: {exc.msg}"
        ) from exc


def load_app_config(
    project_config_path: Optional[pathlib.Path] = None,
    render_config_path:  Optional[pathlib.Path] = None,
) -> AppConfig:
    """Load, validate, and return the application configuration from two config files."""
    proj_path   = pathlib.Path(project_config_path) if project_config_path  else DEFAULT_PROJECT_CONFIG_PATH
    render_path = pathlib.Path(render_config_path)  if render_config_path   else DEFAULT_RENDER_CONFIG_PATH

    proj_payload   = _load_json(proj_path)
    render_payload = _load_json(render_path)

    proj_root = _require_commented_object(
        _require_object(proj_payload, "root"),
        "root",
        ("version", "paths", "registration", "distance"),
    )
    proj_version = _require_int(proj_root["version"], "version", minimum=1)
    if proj_version != 1:
        _raise("version", "unsupported project_config.json schema version (expected 1)")

    render_root = _require_commented_object(
        _require_object(render_payload, "root"),
        "root",
        ("version", "viewer", "render"),
    )
    render_version = _require_int(render_root["version"], "version", minimum=1)
    if render_version != 1:
        _raise("version", "unsupported render_config.json schema version (expected 1)")

    return AppConfig(
        version=proj_version,
        paths=_validate_paths(proj_root["paths"]),
        viewer=_validate_viewer(render_root["viewer"]),
        render=_validate_render(render_root["render"]),
        distance=_validate_distance(proj_root["distance"]),
        registration=_validate_registration(proj_root["registration"]),
    )


APP_CONFIG = load_app_config()
