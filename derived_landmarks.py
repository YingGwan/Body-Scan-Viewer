"""
derived_landmarks.py — Generic Derived Landmark Framework

Stateless pure-function library for:
- Loading/saving derived landmark YAML configs
- Barycentric coordinate math (to/from)
- Mesh surface projection
- Geometric init methods for computing initial landmark positions
- Measurement computation (geodesic, Y projection)

No Polyscope or GUI imports.
"""

import pathlib
import numpy as np
import yaml
import trimesh
from dataclasses import dataclass
from typing import Optional


# =========================================================================
# Data structures
# =========================================================================

@dataclass
class MeasurementRecord:
    name: str
    family: str
    value_mm: float
    method: str
    source_landmarks: tuple


# =========================================================================
# YAML loading / saving
# =========================================================================

def load_derived_landmark_config(yaml_path) -> dict:
    path = pathlib.Path(yaml_path)
    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    if config.get("version") != 1:
        raise ValueError(f"Unsupported config version: {config.get('version')} (expected 1)")
    if "landmarks" not in config:
        raise ValueError("Config missing 'landmarks' section")
    if "measurements" not in config:
        raise ValueError("Config missing 'measurements' section")
    for name, lm in config["landmarks"].items():
        for key in ("triangle", "init_method", "family"):
            if key not in lm:
                raise ValueError(f"Landmark '{name}' missing required key '{key}'")
        if len(lm["triangle"]) != 3:
            raise ValueError(f"Landmark '{name}' triangle must have exactly 3 entries")
    return config


def save_weights_to_yaml(yaml_path, landmark_name, weights):
    path = pathlib.Path(yaml_path)
    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    if landmark_name not in config.get("landmarks", {}):
        raise ValueError(f"Landmark '{landmark_name}' not found in config")
    config["landmarks"][landmark_name]["weights"] = [float(w) for w in weights]
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)


# =========================================================================
# Barycentric coordinate engine
# =========================================================================

def from_barycentric(alpha, beta, gamma, A, B, C):
    return alpha * np.asarray(A) + beta * np.asarray(B) + gamma * np.asarray(C)


def to_barycentric(P, A, B, C):
    P, A, B, C = np.asarray(P), np.asarray(A), np.asarray(B), np.asarray(C)
    M = np.column_stack([A - C, B - C])
    rhs = P - C
    ab, _, _, _ = np.linalg.lstsq(M, rhs, rcond=None)
    alpha, beta = float(ab[0]), float(ab[1])
    gamma = 1.0 - alpha - beta
    return alpha, beta, gamma


def project_to_mesh(point, mesh):
    closest, _, _ = trimesh.proximity.closest_point(mesh, [np.asarray(point)])
    return closest[0]


# =========================================================================
# Init methods
# =========================================================================

INIT_METHODS = {}


def _register_init(name):
    def decorator(fn):
        INIT_METHODS[name] = fn
        return fn
    return decorator


@_register_init("contour_z_extremum")
def init_contour_z_extremum(mesh, landmark_dict, params):
    lm_names = params["plane_landmarks"]
    p0 = np.asarray(landmark_dict[lm_names[0]])
    p1 = np.asarray(landmark_dict[lm_names[1]])

    origin = (p0 + p1) / 2.0
    direction = p1 - p0
    direction = direction / np.linalg.norm(direction)
    x_axis = np.array([1.0, 0.0, 0.0])
    normal = np.cross(direction, x_axis)
    norm_len = np.linalg.norm(normal)
    if norm_len < 1e-10:
        raise ValueError(f"Plane landmarks {lm_names} are parallel to X-axis, cannot compute normal")
    normal = normal / norm_len

    path3d = mesh.section(plane_origin=origin, plane_normal=normal)
    if path3d is None or len(path3d.entities) == 0 or not path3d.is_closed:
        raise ValueError(f"Plane did not intersect mesh for landmarks {lm_names}")

    largest_entity = max(path3d.entities, key=lambda e: len(e.discrete(path3d.vertices)))
    contour_pts = largest_entity.discrete(path3d.vertices)

    extremum = params.get("extremum", "max")
    if extremum == "max":
        idx = np.argmax(contour_pts[:, 2])
    elif extremum == "min":
        idx = np.argmin(contour_pts[:, 2])
    else:
        raise ValueError(f"Unknown extremum type: {extremum}")

    return contour_pts[idx].copy()


@_register_init("plane_intersection")
def init_plane_intersection(mesh, landmark_dict, params):
    raise NotImplementedError("Planned for Neck/Waist module")


@_register_init("arc_length_ratio")
def init_arc_length_ratio(mesh, landmark_dict, params):
    raise NotImplementedError("Planned for Neck/Waist module")


@_register_init("three_plane_intersection")
def init_three_plane_intersection(mesh, landmark_dict, params):
    raise NotImplementedError("Planned for Neck/Waist module")
