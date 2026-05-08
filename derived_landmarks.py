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
