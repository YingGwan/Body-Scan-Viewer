"""
Regression tests for geodesic_utils.

The geodesic path should use potpourri3d's exact surface solver when available,
instead of returning a vertex-only Dijkstra polyline.
"""

import importlib
import os
import sys
import types

import numpy as np


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class FakeEdgeFlipGeodesicSolver:
    def __init__(self, vertices, faces):
        self.vertices = np.asarray(vertices)
        self.faces = np.asarray(faces)
        self.calls = []

    def find_geodesic_path(self, src, tgt, max_iterations=None, max_relative_length_decrease=None):
        self.calls.append((src, tgt, max_iterations, max_relative_length_decrease))
        return np.array([
            self.vertices[src],
            (self.vertices[src] + self.vertices[tgt]) / 2.0 + np.array([0.0, 0.2, 0.0]),
            self.vertices[tgt],
        ])


def test_build_geodesic_solver_uses_potpourri3d(monkeypatch):
    fake_pp3d = types.ModuleType("potpourri3d")
    fake_pp3d.EdgeFlipGeodesicSolver = FakeEdgeFlipGeodesicSolver
    monkeypatch.setitem(sys.modules, "potpourri3d", fake_pp3d)
    sys.modules.pop("geodesic_utils", None)
    mod = importlib.import_module("geodesic_utils")

    mesh = types.SimpleNamespace(
        vertices=np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]),
        faces=np.array([[0, 1, 2]], dtype=np.int32),
    )

    solver = mod.build_geodesic_solver(mesh)

    assert isinstance(solver, FakeEdgeFlipGeodesicSolver)
    np.testing.assert_allclose(solver.vertices, mesh.vertices)
    np.testing.assert_array_equal(solver.faces, mesh.faces)


def test_build_geodesic_solver_cleans_nonmanifold_faces(monkeypatch):
    fake_pp3d = types.ModuleType("potpourri3d")
    fake_pp3d.EdgeFlipGeodesicSolver = FakeEdgeFlipGeodesicSolver
    monkeypatch.setitem(sys.modules, "potpourri3d", fake_pp3d)
    sys.modules.pop("geodesic_utils", None)
    mod = importlib.import_module("geodesic_utils")

    mesh = types.SimpleNamespace(
        vertices=np.array([
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [1.0, 1.0, 0.0],
        ]),
        faces=np.array([
            [0, 1, 2],
            [0, 2, 1],  # duplicate triangle with reversed winding
            [0, 1, 3],
            [0, 1, 4],  # third face on edge (0,1) -> non-manifold
        ], dtype=np.int32),
    )

    solver = mod.build_geodesic_solver(mesh)

    cleaned_faces = np.asarray(solver.faces)
    assert len(cleaned_faces) == 2
    unique_faces = np.unique(np.sort(cleaned_faces, axis=1), axis=0)
    assert len(unique_faces) == 2

    edges = np.vstack([
        cleaned_faces[:, [0, 1]],
        cleaned_faces[:, [1, 2]],
        cleaned_faces[:, [2, 0]],
    ])
    edges = np.sort(edges, axis=1)
    _, inverse = np.unique(edges, axis=0, return_inverse=True)
    counts = np.bincount(inverse)
    assert counts.max() <= 2


def test_compute_geodesic_prefers_exact_solver(monkeypatch):
    sys.modules.pop("geodesic_utils", None)
    mod = importlib.import_module("geodesic_utils")

    vertices = np.array([
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [1.0, 1.0, 0.0],
    ])
    solver = FakeEdgeFlipGeodesicSolver(vertices, np.array([[0, 1, 2]], dtype=np.int32))

    length, path = mod.compute_geodesic(
        graph=None,
        vertices=vertices,
        pt_a=vertices[0],
        pt_b=vertices[2],
        kdtree=None,
        exact_solver=solver,
    )

    assert solver.calls, "exact solver was not used"
    assert path.shape == (3, 3)
    assert not np.allclose(path[1], vertices[1]), "path should not collapse to edge-graph vertices"
    np.testing.assert_allclose(path[0], vertices[0])
    np.testing.assert_allclose(path[-1], vertices[2])
    expected = np.linalg.norm(path[1] - path[0]) + np.linalg.norm(path[2] - path[1])
    np.testing.assert_allclose(length, expected)
