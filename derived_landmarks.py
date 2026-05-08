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


def resolve_landmark_name(name, config):
    """Resolve a canonical landmark name to the dataset-specific name via landmark_name_map."""
    name_map = config.get("landmark_name_map", {})
    return name_map.get(name, name)


def resolve_landmark_names(names, config):
    """Resolve a list of canonical names."""
    return [resolve_landmark_name(n, config) for n in names]


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
def init_contour_z_extremum(mesh, landmark_dict, params, config=None):
    lm_names = params["plane_landmarks"]
    resolved = resolve_landmark_names(lm_names, config) if config else lm_names
    p0 = np.asarray(landmark_dict[resolved[0]])
    p1 = np.asarray(landmark_dict[resolved[1]])

    origin = (p0 + p1) / 2.0
    direction = p1 - p0
    direction = direction / np.linalg.norm(direction)
    z_axis = np.array([0.0, 0.0, 1.0])
    normal = np.cross(direction, z_axis)
    norm_len = np.linalg.norm(normal)
    if norm_len < 1e-10:
        raise ValueError(f"Plane landmarks {lm_names} are parallel to Z-axis, cannot compute normal")
    normal = normal / norm_len

    path3d = mesh.section(plane_origin=origin, plane_normal=normal)
    if path3d is None or len(path3d.entities) == 0:
        raise ValueError(f"Plane did not intersect mesh for landmarks {lm_names}")

    ref_y = origin[1]
    y_margin = np.linalg.norm(p1 - p0) * 0.8

    best_entity = None
    best_dist = float("inf")
    for entity in path3d.entities:
        pts = entity.discrete(path3d.vertices)
        centroid_y = np.mean(pts[:, 1])
        dist = abs(centroid_y - ref_y)
        if dist < best_dist:
            best_dist = dist
            best_entity = entity

    if best_entity is None:
        raise ValueError(f"No contour entity found for landmarks {lm_names}")

    contour_pts = best_entity.discrete(path3d.vertices)
    y_min_bound = min(p0[1], p1[1]) - y_margin
    y_max_bound = max(p0[1], p1[1]) + y_margin
    mask = (contour_pts[:, 1] >= y_min_bound) & (contour_pts[:, 1] <= y_max_bound)
    local_pts = contour_pts[mask]
    if len(local_pts) == 0:
        local_pts = contour_pts

    extremum = params.get("extremum", "max")
    if extremum == "max":
        idx = np.argmax(local_pts[:, 2])
    elif extremum == "min":
        idx = np.argmin(local_pts[:, 2])
    else:
        raise ValueError(f"Unknown extremum type: {extremum}")

    return local_pts[idx].copy()


@_register_init("plane_intersection")
def init_plane_intersection(mesh, landmark_dict, params, config=None):
    coronal_name = params["coronal_landmark"]
    sagittal_name = params["sagittal_landmark"]
    if config:
        coronal_name = resolve_landmark_name(coronal_name, config)
        sagittal_name = resolve_landmark_name(sagittal_name, config)

    coronal_pt = np.asarray(landmark_dict[coronal_name])
    sagittal_pt = np.asarray(landmark_dict[sagittal_name])

    line_x = sagittal_pt[0]
    line_z = coronal_pt[2]

    y_min = min(coronal_pt[1], sagittal_pt[1]) - 100.0
    y_max = max(coronal_pt[1], sagittal_pt[1]) + 100.0
    origins = np.array([[line_x, y, line_z] for y in np.linspace(y_min, y_max, 300)])
    dirs = np.tile([0.0, 1.0, 0.0], (300, 1))

    locs, _, _ = mesh.ray.intersects_location(ray_origins=origins, ray_directions=dirs)
    if len(locs) == 0:
        raise ValueError(
            f"Plane intersection did not hit mesh for {coronal_name}/{sagittal_name}"
        )

    y_range_min = min(coronal_pt[1], sagittal_pt[1]) - 50.0
    y_range_max = max(coronal_pt[1], sagittal_pt[1]) + 50.0
    mask = (locs[:, 1] >= y_range_min) & (locs[:, 1] <= y_range_max)
    filtered = locs[mask]
    if len(filtered) == 0:
        filtered = locs

    ref_mid = (coronal_pt + sagittal_pt) / 2.0
    dists = np.linalg.norm(filtered - ref_mid, axis=1)
    return filtered[np.argmin(dists)].copy()


@_register_init("arc_length_ratio")
def init_arc_length_ratio(mesh, landmark_dict, params, config=None):
    start_name = params["start_landmark"]
    end_name = params["end_landmark"]
    ratio = params.get("ratio", 0.5)
    plane_landmark = params.get("plane_landmark", start_name)

    if config:
        start_name = resolve_landmark_name(start_name, config)
        end_name = resolve_landmark_name(end_name, config)
        plane_landmark = resolve_landmark_name(plane_landmark, config)

    start_pt = np.asarray(landmark_dict[start_name])
    end_pt = np.asarray(landmark_dict[end_name])
    plane_pt = np.asarray(landmark_dict[plane_landmark])

    plane_y = float(plane_pt[1])
    path3d = mesh.section(plane_origin=[0, plane_y, 0], plane_normal=[0, 1, 0])
    if path3d is None or len(path3d.entities) == 0:
        raise ValueError(f"Transverse section at Y={plane_y:.1f} did not intersect mesh")

    path2d, to_3d = path3d.to_planar()
    if not path2d.polygons_full:
        raise ValueError(f"No closed polygons from transverse section at Y={plane_y:.1f}")
    ring = max(path2d.polygons_full, key=lambda p: p.area).exterior

    from shapely.geometry import Point
    inv_3d = np.linalg.inv(to_3d)

    def to_2d(pt3d):
        h = np.append(np.asarray(pt3d), 1.0) @ inv_3d.T
        return h[:2] / h[3] if abs(h[3]) > 1e-10 else h[:2]

    start_2d = to_2d(start_pt)
    end_2d = to_2d(end_pt)

    pos_start = ring.project(Point(start_2d))
    pos_end = ring.project(Point(end_2d))

    arc_forward = pos_end - pos_start
    if arc_forward < 0:
        arc_forward += ring.length
    arc_backward = ring.length - arc_forward
    if arc_forward <= arc_backward:
        target_pos = pos_start + ratio * arc_forward
    else:
        target_pos = pos_start - ratio * arc_backward
    target_pos = target_pos % ring.length

    pt_2d = ring.interpolate(target_pos)
    pt_3d_h = np.array([pt_2d.x, pt_2d.y, 0.0, 1.0]) @ to_3d.T
    return (pt_3d_h[:3] / pt_3d_h[3] if abs(pt_3d_h[3]) > 1e-10 else pt_3d_h[:3]).copy()


@_register_init("three_plane_intersection")
def init_three_plane_intersection(mesh, landmark_dict, params, config=None):
    apex_name = params["apex_landmark"]
    waist_plane_name = params["waist_plane_landmark"]
    bust_front_name = params["bust_front_landmark"]
    bust_side_name = params["bust_side_landmark"]

    if config:
        apex_name = resolve_landmark_name(apex_name, config)
        waist_plane_name = resolve_landmark_name(waist_plane_name, config)
        bust_front_name = resolve_landmark_name(bust_front_name, config)
        bust_side_name = resolve_landmark_name(bust_side_name, config)

    apex = np.asarray(landmark_dict[apex_name])
    waist_ref = np.asarray(landmark_dict[waist_plane_name])
    bust_front = np.asarray(landmark_dict[bust_front_name])
    bust_side = np.asarray(landmark_dict[bust_side_name])

    plane_y = float(waist_ref[1])
    apex_proj = np.array([apex[0], plane_y, apex[2]])
    bf_proj = np.array([bust_front[0], plane_y, bust_front[2]])
    bs_proj = np.array([bust_side[0], plane_y, bust_side[2]])

    path3d = mesh.section(plane_origin=[0, plane_y, 0], plane_normal=[0, 1, 0])
    if path3d is None or len(path3d.entities) == 0:
        raise ValueError(f"Transverse section at Y={plane_y:.1f} did not intersect mesh")

    path2d, to_3d = path3d.to_planar()
    if not path2d.polygons_full:
        raise ValueError(f"No closed polygons from transverse section at Y={plane_y:.1f}")
    ring = max(path2d.polygons_full, key=lambda p: p.area).exterior

    from shapely.geometry import Point, LineString
    inv_3d = np.linalg.inv(to_3d)

    def to_2d(pt3d):
        h = np.append(np.asarray(pt3d), 1.0) @ inv_3d.T
        return h[:2] / h[3] if abs(h[3]) > 1e-10 else h[:2]

    apex_2d = to_2d(apex_proj)
    bf_2d = to_2d(bf_proj)
    bs_2d = to_2d(bs_proj)

    d_2d = bs_2d - bf_2d
    perp_2d = np.array([-d_2d[1], d_2d[0]])
    perp_len = np.linalg.norm(perp_2d)
    if perp_len < 1e-10:
        raise ValueError("BustFront and BustSide have same 2D projection")
    perp_2d = perp_2d / perp_len

    ray_line = LineString([
        apex_2d - 500.0 * perp_2d,
        apex_2d + 500.0 * perp_2d,
    ])
    intersection = ray_line.intersection(ring)

    if intersection.is_empty:
        hit = ring.interpolate(ring.project(Point(apex_2d)))
    elif intersection.geom_type == "Point":
        hit = intersection
    else:
        candidates = [g for g in intersection.geoms if g.geom_type == "Point"]
        if not candidates:
            hit = ring.interpolate(ring.project(Point(apex_2d)))
        else:
            apex_pt = Point(apex_2d)
            hit = min(candidates, key=lambda p: apex_pt.distance(p))

    pt_3d_h = np.array([hit.x, hit.y, 0.0, 1.0]) @ to_3d.T
    return (pt_3d_h[:3] / pt_3d_h[3] if abs(pt_3d_h[3]) > 1e-10 else pt_3d_h[:3]).copy()


# =========================================================================
# Unified entry points
# =========================================================================

def compute_derived_landmark(mesh, landmark_dict, lm_name, lm_config, config=None):
    triangle_names = lm_config["triangle"]
    resolved_tri = resolve_landmark_names(triangle_names, config) if config else triangle_names
    A = np.asarray(landmark_dict[resolved_tri[0]])
    B = np.asarray(landmark_dict[resolved_tri[1]])
    C = np.asarray(landmark_dict[resolved_tri[2]])

    weights = lm_config.get("weights")
    if weights is not None:
        alpha, beta, gamma = weights
        P_bary = from_barycentric(alpha, beta, gamma, A, B, C)
        P_surface = project_to_mesh(P_bary, mesh)
        return P_surface, tuple(weights)

    init_method_name = lm_config["init_method"]
    init_fn = INIT_METHODS.get(init_method_name)
    if init_fn is None:
        raise ValueError(f"Unknown init_method: {init_method_name}")
    params = lm_config.get("init_params", {})
    P_init = init_fn(mesh, landmark_dict, params, config=config)
    P_surface = project_to_mesh(P_init, mesh)
    alpha, beta, gamma = to_barycentric(P_surface, A, B, C)
    return P_surface, (alpha, beta, gamma)


def compute_all_derived_landmarks(mesh, landmark_dict, config):
    results = {}
    for name, lm_config in config["landmarks"].items():
        pos, weights = compute_derived_landmark(mesh, landmark_dict, name, lm_config, config=config)
        results[name] = {
            "position": pos,
            "weights": weights,
            "family": lm_config["family"],
        }
    return results


# =========================================================================
# Measurement computation
# =========================================================================

def _compute_arc_length(mesh, pt_a, pt_b, plane_landmark_pt):
    plane_y = float(plane_landmark_pt[1])
    path3d = mesh.section(plane_origin=[0, plane_y, 0], plane_normal=[0, 1, 0])
    if path3d is None or len(path3d.entities) == 0:
        raise ValueError(f"Transverse section at Y={plane_y:.1f} did not intersect mesh")

    path2d, to_3d = path3d.to_planar()
    if not path2d.polygons_full:
        raise ValueError(f"No closed polygons from transverse section at Y={plane_y:.1f}")

    from shapely.geometry import Point
    inv_3d = np.linalg.inv(to_3d)

    def to_2d(pt3d):
        h = np.append(np.asarray(pt3d), 1.0) @ inv_3d.T
        return h[:2] / h[3] if abs(h[3]) > 1e-10 else h[:2]

    mid_2d = Point(to_2d((pt_a + pt_b) / 2.0))
    ring = min(
        (p.exterior for p in path2d.polygons_full),
        key=lambda r: r.distance(mid_2d),
    )

    pos_a = ring.project(Point(to_2d(pt_a)))
    pos_b = ring.project(Point(to_2d(pt_b)))
    arc = abs(pos_b - pos_a)
    if arc > ring.length / 2:
        arc = ring.length - arc
    return arc


def compute_configured_measurements(mesh, landmark_dict, derived_dict, measurements_config, geodesic_fn, config=None):
    combined = dict(landmark_dict)
    combined.update(derived_dict)

    records = []
    for name, m_config in measurements_config.items():
        from_name = resolve_landmark_name(m_config["from"], config) if config else m_config["from"]
        to_name = resolve_landmark_name(m_config["to"], config) if config else m_config["to"]
        family = m_config["family"]

        if from_name not in combined:
            raise ValueError(f"Measurement '{name}': landmark '{from_name}' not found")
        if to_name not in combined:
            raise ValueError(f"Measurement '{name}': landmark '{to_name}' not found")

        pt_a = np.asarray(combined[from_name])
        pt_b = np.asarray(combined[to_name])
        src = (from_name, to_name)

        if m_config["type"] == "geodesic":
            length_mm, path_verts = geodesic_fn(pt_a, pt_b)
            records.append(MeasurementRecord(
                name=name, family=family, value_mm=length_mm,
                method="geodesic", source_landmarks=src,
            ))
            if m_config.get("also_output_y_projection", False):
                y_proj = abs(float(pt_a[1]) - float(pt_b[1]))
                records.append(MeasurementRecord(
                    name=f"{name}_Y", family=family, value_mm=y_proj,
                    method="y_projection", source_landmarks=src,
                ))
        elif m_config["type"] == "arc_length":
            plane_lm_name = m_config.get("plane_landmark", from_name)
            if config:
                plane_lm_name = resolve_landmark_name(plane_lm_name, config)
            if plane_lm_name in combined:
                plane_pt = np.asarray(combined[plane_lm_name])
            else:
                plane_pt = pt_a
            arc_mm = _compute_arc_length(mesh, pt_a, pt_b, plane_pt)
            records.append(MeasurementRecord(
                name=name, family=family, value_mm=arc_mm,
                method="arc_length", source_landmarks=src,
            ))
        elif m_config["type"] == "euclidean":
            dist = float(np.linalg.norm(pt_a - pt_b))
            records.append(MeasurementRecord(
                name=name, family=family, value_mm=dist,
                method="euclidean", source_landmarks=src,
            ))

    return records
