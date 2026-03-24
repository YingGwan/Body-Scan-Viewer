"""
Tests for mesh unit normalization helpers.

These tests cover the runtime rule introduced for mixed-unit datasets:
internal computations use millimeters, while exported data keeps the
original mesh unit.
"""

import numpy as np

from unit_utils import (
    infer_mesh_unit_context,
    to_runtime_mm_vertices,
    from_runtime_mm_vertices,
    transform_mm_to_original_units,
)


def test_infer_millimeter_mesh():
    vertices = np.array([
        [-476.6, -0.1, -158.0],
        [371.2, 1584.9, 119.8],
    ])

    ctx = infer_mesh_unit_context(vertices)

    assert ctx.original_unit == "mm"
    assert ctx.to_mm_scale == 1.0


def test_infer_meter_mesh():
    vertices = np.array([
        [-0.563, -0.384, -1.0],
        [0.620, 0.617, 0.584],
    ])

    ctx = infer_mesh_unit_context(vertices)

    assert ctx.original_unit == "m"
    assert ctx.to_mm_scale == 1000.0


def test_runtime_mm_roundtrip_for_vertices():
    vertices_m = np.array([
        [0.1, 0.2, 1.5],
        [-0.3, 0.0, 0.8],
    ])
    ctx = infer_mesh_unit_context(vertices_m)

    vertices_mm = to_runtime_mm_vertices(vertices_m, ctx)
    restored = from_runtime_mm_vertices(vertices_mm, ctx)

    np.testing.assert_allclose(vertices_mm, vertices_m * 1000.0)
    np.testing.assert_allclose(restored, vertices_m)


def test_transform_translation_is_scaled_back_for_export():
    transform_mm = np.eye(4)
    transform_mm[:3, :3] = np.array([
        [0.0, -1.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0],
    ])
    transform_mm[:3, 3] = np.array([125.0, -40.0, 1580.0])
    ctx = infer_mesh_unit_context(np.array([
        [-0.56, -0.38, -1.0],
        [0.62, 0.62, 0.58],
    ]))

    exported = transform_mm_to_original_units(transform_mm, ctx)

    np.testing.assert_allclose(exported[:3, :3], transform_mm[:3, :3])
    np.testing.assert_allclose(exported[:3, 3], np.array([0.125, -0.04, 1.58]))
