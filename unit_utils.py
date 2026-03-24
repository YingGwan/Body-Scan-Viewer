"""
Helpers for mesh unit normalization.

Runtime geometry operations use millimeters so that registration, distance,
and geodesic computations all operate in one consistent unit system.
"""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class MeshUnitContext:
    """Describes the original mesh unit and how to convert it to millimeters."""

    original_unit: str
    to_mm_scale: float


def infer_mesh_unit_context(vertices: np.ndarray) -> MeshUnitContext:
    """
    Infer the mesh length unit from its overall body-size extent.

    Human body scans in this project fall into two stable buckets:
    - around 1-3 units tall   -> meters
    - around 1000-3000 tall   -> millimeters
    """
    extent = float(np.ptp(np.asarray(vertices, dtype=float), axis=0).max())

    if extent < 10.0:
        return MeshUnitContext(original_unit="m", to_mm_scale=1000.0)
    return MeshUnitContext(original_unit="mm", to_mm_scale=1.0)


def to_runtime_mm_vertices(vertices: np.ndarray, ctx: MeshUnitContext) -> np.ndarray:
    """Convert mesh vertices from their original unit to runtime millimeters."""
    return np.asarray(vertices, dtype=float) * ctx.to_mm_scale


def from_runtime_mm_vertices(vertices_mm: np.ndarray, ctx: MeshUnitContext) -> np.ndarray:
    """Convert runtime millimeter vertices back to the original mesh unit."""
    return np.asarray(vertices_mm, dtype=float) / ctx.to_mm_scale


def transform_mm_to_original_units(
    transform_mm: np.ndarray, ctx: MeshUnitContext
) -> np.ndarray:
    """
    Convert a rigid transform expressed in millimeters back to the original unit.

    Uniform unit scaling leaves rotation unchanged and only rescales translation.
    """
    transform_out = np.array(transform_mm, dtype=float, copy=True)
    transform_out[:3, 3] /= ctx.to_mm_scale
    return transform_out
