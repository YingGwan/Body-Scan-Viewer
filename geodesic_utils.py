"""
geodesic_utils.py — Geodesic Distance Computation on Triangle Meshes

Provides Dijkstra-based approximate geodesic distance computation
on a triangle mesh edge graph. Used by the "D. Geodesic" panel.

Key functions:
    - build_edge_graph(): construct a sparse weighted edge graph from a trimesh
    - build_geodesic_solver(): construct a potpourri3d exact geodesic solver
    - compute_geodesic(): find shortest path between two 3D points on the mesh
"""

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra


def _clean_edge_flip_faces(faces: np.ndarray) -> np.ndarray:
    """
    Remove face patterns that EdgeFlipGeodesicSolver rejects.

    The SizeStream meshes can contain:
        - duplicate triangles with reversed winding
        - non-manifold edges shared by more than two faces

    We keep vertex indices unchanged and only prune the face list, so existing
    KDTree snapping and vertex indexing remain valid.
    """
    faces = np.asarray(faces, dtype=np.int32)
    if faces.size == 0:
        return faces

    # Drop duplicate triangles while ignoring winding order.
    sorted_faces = np.sort(faces, axis=1)
    _, unique_idx = np.unique(sorted_faces, axis=0, return_index=True)
    faces = faces[np.sort(unique_idx)]

    # EdgeFlipGeodesicSolver requires each undirected edge to be used by <= 2 faces.
    while True:
        n_faces = len(faces)
        raw_edges = np.vstack([
            faces[:, [0, 1]],
            faces[:, [1, 2]],
            faces[:, [2, 0]],
        ])
        raw_edges = np.sort(raw_edges, axis=1)
        _, inverse = np.unique(raw_edges, axis=0, return_inverse=True)
        counts = np.bincount(inverse)
        bad_edges = np.where(counts > 2)[0]
        if len(bad_edges) == 0:
            return faces

        keep = np.ones(n_faces, dtype=bool)
        for edge_id in bad_edges:
            rows = np.where(inverse == edge_id)[0]
            face_ids = np.unique(rows % n_faces)
            for face_id in face_ids[2:]:
                keep[int(face_id)] = False
        faces = faces[keep]


def build_edge_graph(mesh) -> csr_matrix:
    """
    Build a symmetric sparse edge-weight matrix from a trimesh.Trimesh.

    Each edge weight is the Euclidean distance between the two vertices.
    The result is a CSR sparse matrix of shape (n_vertices, n_vertices).

    Args:
        mesh: trimesh.Trimesh object

    Returns:
        csr_matrix of shape (n, n) with edge weights
    """
    edges   = mesh.edges_unique               # shape (E, 2)
    weights = mesh.edges_unique_length        # shape (E,), Euclidean edge lengths
    n       = len(mesh.vertices)

    # Symmetric: add both directions
    row = np.concatenate([edges[:, 0], edges[:, 1]])
    col = np.concatenate([edges[:, 1], edges[:, 0]])
    dat = np.concatenate([weights, weights])

    return csr_matrix((dat, (row, col)), shape=(n, n))


def build_geodesic_solver(mesh):
    """
    Build a potpourri3d exact geodesic solver for a triangle mesh.

    Returns:
        potpourri3d.EdgeFlipGeodesicSolver, or None if potpourri3d is unavailable
    """
    try:
        import potpourri3d as pp3d
    except ImportError:
        return None

    vertices = np.asarray(mesh.vertices, dtype=np.float64)
    faces_raw = np.asarray(mesh.faces, dtype=np.int32)
    faces_clean = _clean_edge_flip_faces(faces_raw)

    if len(faces_clean) != len(faces_raw):
        print(
            f"[geo] Cleaned mesh for potpourri3d: "
            f"{len(faces_raw)} -> {len(faces_clean)} faces"
        )

    try:
        return pp3d.EdgeFlipGeodesicSolver(vertices, faces_clean)
    except Exception as exc:
        print(f"[geo] Exact geodesic unavailable, falling back to Dijkstra: {exc}")
        return None


def compute_geodesic(graph: csr_matrix, vertices: np.ndarray,
                     pt_a: np.ndarray, pt_b: np.ndarray,
                     kdtree=None,
                     exact_solver=None) -> tuple:
    """
    Compute the geodesic between two 3D points on the mesh surface.

    Steps:
        1. Snap pt_a and pt_b to the nearest mesh vertices (via KDTree)
        2. If available, query potpourri3d for an exact continuous surface path
        3. Otherwise fall back to Dijkstra on the mesh edge graph

    Args:
        graph:    sparse edge-weight matrix from build_edge_graph(), used for fallback
        vertices: mesh vertex positions, shape (n, 3)
        pt_a:     start point in 3D space (snapped to nearest vertex)
        pt_b:     end point in 3D space (snapped to nearest vertex)
        kdtree:   optional pre-built scipy.spatial.cKDTree for vertex lookup.
                  If None, a new one is created (slower for repeated calls).
        exact_solver:
                  optional potpourri3d exact geodesic solver. When present,
                  returns a continuous surface polyline instead of an edge-only
                  vertex path.

    Returns:
        (length, path_vertices):
            length:        float, geodesic distance in mm (inf if disconnected)
            path_vertices: np.ndarray of shape (n_path, 3), or None if disconnected
    """
    if kdtree is None:
        from scipy.spatial import cKDTree
        kdtree = cKDTree(vertices)

    # Snap input points to nearest mesh vertices
    _, src = kdtree.query(pt_a)
    _, tgt = kdtree.query(pt_b)

    if src == tgt:
        return 0.0, vertices[[src]]

    if exact_solver is not None:
        path_vertices = np.asarray(
            exact_solver.find_geodesic_path(int(src), int(tgt)),
            dtype=float,
        )
        if path_vertices.ndim != 2 or path_vertices.shape[0] < 2:
            return float("inf"), None
        length = float(np.linalg.norm(np.diff(path_vertices, axis=0), axis=1).sum())
        return length, path_vertices

    if graph is None:
        raise ValueError("Need either an exact geodesic solver or a fallback graph")

    # Dijkstra single-source shortest path
    dist_matrix, predecessors = dijkstra(
        graph, indices=src, return_predecessors=True, directed=False
    )

    length = float(dist_matrix[tgt])
    if np.isinf(length):
        return length, None  # Mesh is disconnected between these two vertices

    # Backtrack path from target to source
    path_indices = []
    curr = tgt
    while curr != src and curr >= 0:
        path_indices.append(curr)
        curr = predecessors[curr]
    path_indices.append(src)
    path_indices.reverse()

    return length, vertices[path_indices]
