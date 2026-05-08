"""Face anonymization helpers built around Open3D proxy simplification.

The important invariant is that the production mesh keeps its original
vertices and faces. Open3D is used to create a simplified proxy surface, then
the original face-region vertices are smoothed toward that proxy. This avoids
cut-and-stitch cracks around the anonymized face patch.
"""

from dataclasses import dataclass

import numpy as np
import trimesh
from scipy.spatial import cKDTree


@dataclass
class FaceRegion:
    selected_vertices: np.ndarray
    selected_faces: np.ndarray
    boundary_vertices: np.ndarray


@dataclass
class FaceAnonymizationResult:
    mesh: trimesh.Trimesh
    selected_vertices: np.ndarray
    selected_face_count: int
    selected_vertex_count: int
    boundary_vertex_count: int
    proxy_face_count: int
    max_displacement_mm: float
    mean_displacement_mm: float
    before_boundary_edges: tuple
    after_boundary_edges: tuple
    before_components: list
    after_components: list


def boundary_edge_counts(faces):
    """Return (boundary_edges, nonmanifold_edges) for triangle faces."""
    faces = np.asarray(faces, dtype=np.int64)
    if len(faces) == 0:
        return (0, 0)
    edges = np.vstack(
        [
            faces[:, [0, 1]],
            faces[:, [1, 2]],
            faces[:, [2, 0]],
        ]
    )
    edges.sort(axis=1)
    _, counts = np.unique(edges, axis=0, return_counts=True)
    return (int(np.count_nonzero(counts == 1)), int(np.count_nonzero(counts > 2)))


def connected_component_face_counts(faces):
    """Return sorted face counts for components connected by shared edges."""
    faces = np.asarray(faces, dtype=np.int64)
    n_faces = len(faces)
    if n_faces == 0:
        return []

    parent = np.arange(n_faces, dtype=np.int64)
    rank = np.zeros(n_faces, dtype=np.int8)

    def find(idx):
        root = idx
        while parent[root] != root:
            root = parent[root]
        while parent[idx] != idx:
            nxt = parent[idx]
            parent[idx] = root
            idx = nxt
        return root

    def union(a, b):
        ra = find(a)
        rb = find(b)
        if ra == rb:
            return
        if rank[ra] < rank[rb]:
            parent[ra] = rb
        elif rank[ra] > rank[rb]:
            parent[rb] = ra
        else:
            parent[rb] = ra
            rank[ra] += 1

    edge_owner = {}
    for face_idx, face in enumerate(faces):
        for a, b in ((face[0], face[1]), (face[1], face[2]), (face[2], face[0])):
            edge = (int(a), int(b)) if a < b else (int(b), int(a))
            owner = edge_owner.get(edge)
            if owner is None:
                edge_owner[edge] = face_idx
            else:
                union(owner, face_idx)

    counts = {}
    for idx in range(n_faces):
        root = find(idx)
        counts[root] = counts.get(root, 0) + 1
    return sorted(counts.values(), reverse=True)


def select_face_region(vertices, faces, landmarks):
    """Select the frontal face area from SizeStream landmarks."""
    verts = np.asarray(vertices, dtype=float)
    faces = np.asarray(faces, dtype=np.int64)
    chin = _landmark(landmarks, "Chin")
    hcf = _landmark(landmarks, "Head Circum Front")
    hcr = _landmark(landmarks, "Head Circum Right")

    hcl = _optional_landmark(landmarks, "Head Circum Left")
    head_half_width = abs(hcl[0] - hcr[0]) * 0.5 if hcl is not None else None

    center_x = float((chin[0] + hcf[0]) * 0.5)
    center_y = float((chin[1] + hcf[1]) * 0.5)
    half_height = max(abs(hcf[1] - chin[1]) * 0.5 + 12.0, 35.0)
    half_width = max(half_height * 0.78, 35.0)
    if head_half_width is not None:
        half_width = min(max(head_half_width * 0.92, 35.0), half_width * 1.2)

    # SizeStream is Y-up; larger Z is frontal for the current SS scans. The old
    # cylinder extended all the way to the back of the skull. This keeps the
    # operation on the face instead of the whole head shell.
    side_z = float(hcr[2])
    front_z = float(max(hcf[2], chin[2]) + 12.0)
    back_z = float(min(chin[2], side_z) - 18.0)

    dx = (verts[:, 0] - center_x) / half_width
    dy = (verts[:, 1] - center_y) / half_height
    in_ellipse = (dx * dx + dy * dy) <= 1.0
    in_depth = (verts[:, 2] >= back_z) & (verts[:, 2] <= front_z)
    selected_vertices = in_ellipse & in_depth

    face_selected_verts = selected_vertices[faces]
    selected_faces = face_selected_verts.all(axis=1)
    crossing_faces = face_selected_verts.any(axis=1) & ~selected_faces

    boundary_vertices = np.zeros(len(verts), dtype=bool)
    if np.any(crossing_faces):
        boundary_vertices[faces[crossing_faces].ravel()] = True
        boundary_vertices &= selected_vertices

    return FaceRegion(
        selected_vertices=selected_vertices,
        selected_faces=selected_faces,
        boundary_vertices=boundary_vertices,
    )


def anonymize_face_open3d(
    mesh,
    landmarks,
    target_ratio=0.05,
    smoothing_iterations=18,
    proxy_strength=0.72,
    smoothing_strength=0.38,
    boundary_falloff_mm=35.0,
):
    """Smooth facial detail while preserving the original mesh topology."""
    verts = np.asarray(mesh.vertices, dtype=float)
    faces = np.asarray(mesh.faces, dtype=np.int64)
    region = select_face_region(verts, faces, landmarks)

    selected_face_count = int(np.count_nonzero(region.selected_faces))
    selected_vertex_count = int(np.count_nonzero(region.selected_vertices))
    if selected_face_count == 0 or selected_vertex_count == 0:
        raise ValueError("No face region selected from Chin/Head Circum landmarks")

    before_boundary_edges = boundary_edge_counts(faces)
    before_components = connected_component_face_counts(faces)
    proxy_vertices, proxy_face_count = _build_decimated_proxy(
        verts,
        faces,
        region.selected_faces,
        target_ratio=target_ratio,
    )

    modified = verts.copy()
    influence = _boundary_falloff(
        verts,
        region.selected_vertices,
        region.boundary_vertices,
        boundary_falloff_mm,
    )

    active_vertices = region.selected_vertices & (influence > 1e-6)
    if not np.any(active_vertices):
        raise ValueError("Selected face region has no movable interior vertices")

    proxy_tree = cKDTree(proxy_vertices)
    _, nearest_idx = proxy_tree.query(verts[active_vertices], k=1)
    nearest_proxy = proxy_vertices[nearest_idx]
    active_weight = influence[active_vertices, None] * float(proxy_strength)
    modified[active_vertices] = (
        verts[active_vertices] * (1.0 - active_weight)
        + nearest_proxy * active_weight
    )

    neighbors = _vertex_neighbors(faces, len(verts))
    active_indices = np.flatnonzero(active_vertices)
    for _ in range(int(smoothing_iterations)):
        previous = modified.copy()
        for vid in active_indices:
            nbrs = neighbors[vid]
            if len(nbrs) == 0:
                continue
            weight = float(influence[vid] * smoothing_strength)
            modified[vid] = previous[vid] * (1.0 - weight) + previous[nbrs].mean(axis=0) * weight

    anonymized = trimesh.Trimesh(vertices=modified, faces=faces.copy(), process=False)
    displacement = np.linalg.norm(modified - verts, axis=1)
    after_boundary_edges = boundary_edge_counts(anonymized.faces)
    after_components = connected_component_face_counts(anonymized.faces)

    return FaceAnonymizationResult(
        mesh=anonymized,
        selected_vertices=region.selected_vertices.copy(),
        selected_face_count=selected_face_count,
        selected_vertex_count=selected_vertex_count,
        boundary_vertex_count=int(np.count_nonzero(region.boundary_vertices)),
        proxy_face_count=proxy_face_count,
        max_displacement_mm=float(displacement[region.selected_vertices].max()),
        mean_displacement_mm=float(displacement[region.selected_vertices].mean()),
        before_boundary_edges=before_boundary_edges,
        after_boundary_edges=after_boundary_edges,
        before_components=before_components,
        after_components=after_components,
    )


def _build_decimated_proxy(verts, faces, selected_faces, target_ratio):
    import open3d as o3d

    patch_faces = faces[selected_faces]
    patch_vids = np.unique(patch_faces)
    if len(patch_vids) < 4:
        raise ValueError("Selected face region is too small for simplification")

    vid_map = np.full(len(verts), -1, dtype=np.int64)
    vid_map[patch_vids] = np.arange(len(patch_vids), dtype=np.int64)
    local_faces = vid_map[patch_faces]

    patch = o3d.geometry.TriangleMesh()
    patch.vertices = o3d.utility.Vector3dVector(verts[patch_vids])
    patch.triangles = o3d.utility.Vector3iVector(local_faces)
    patch.remove_duplicated_vertices()
    patch.remove_duplicated_triangles()
    patch.remove_degenerate_triangles()
    patch.remove_unreferenced_vertices()

    n_faces = len(np.asarray(patch.triangles))
    target_faces = max(int(n_faces * float(target_ratio)), 16)
    target_faces = min(target_faces, max(n_faces - 1, 1))

    try:
        decimated = patch.simplify_quadric_decimation(
            target_number_of_triangles=target_faces,
            boundary_weight=100.0,
        )
    except TypeError:
        decimated = patch.simplify_quadric_decimation(
            target_number_of_triangles=target_faces,
        )
    decimated.remove_duplicated_vertices()
    decimated.remove_duplicated_triangles()
    decimated.remove_degenerate_triangles()
    decimated.remove_unreferenced_vertices()

    dec_vertices = np.asarray(decimated.vertices, dtype=float)
    dec_faces = np.asarray(decimated.triangles, dtype=np.int64)
    if len(dec_vertices) == 0:
        raise ValueError("Open3D returned an empty face proxy")
    return dec_vertices, int(len(dec_faces))


def _boundary_falloff(verts, selected_vertices, boundary_vertices, falloff_mm):
    influence = np.zeros(len(verts), dtype=float)
    if not np.any(boundary_vertices):
        influence[selected_vertices] = 1.0
        return influence

    boundary_tree = cKDTree(verts[boundary_vertices])
    selected_idx = np.flatnonzero(selected_vertices)
    dist, _ = boundary_tree.query(verts[selected_idx], k=1)
    t = np.clip(dist / max(float(falloff_mm), 1e-6), 0.0, 1.0)
    smooth = t * t * (3.0 - 2.0 * t)
    influence[selected_idx] = smooth
    influence[boundary_vertices] = 0.0
    return influence


def _vertex_neighbors(faces, n_vertices):
    neighbors = [set() for _ in range(n_vertices)]
    for a, b, c in np.asarray(faces, dtype=np.int64):
        neighbors[int(a)].update((int(b), int(c)))
        neighbors[int(b)].update((int(a), int(c)))
        neighbors[int(c)].update((int(a), int(b)))
    return [np.fromiter(nbrs, dtype=np.int64) for nbrs in neighbors]


def _landmark(landmarks, name):
    value = landmarks.get(name)
    if value is None:
        raise KeyError(f"Missing landmark: {name}")
    return np.asarray(value, dtype=float)


def _optional_landmark(landmarks, name):
    value = landmarks.get(name)
    if value is None:
        return None
    return np.asarray(value, dtype=float)
