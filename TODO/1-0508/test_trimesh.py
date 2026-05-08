"""Test trimesh native section/path capabilities with real SizeStream mesh."""
import trimesh
import numpy as np
from scipy.spatial import cKDTree
from data_loader import scan_data_folders

catalog = scan_data_folders()
entry = catalog.subjects[list(catalog.subjects.keys())[0]]
mesh = trimesh.load(str(entry.ss_obj_path), process=False)
lms = catalog.lm_data['landmarks_3d']
print(f"Mesh: {mesh.vertices.shape[0]}v {mesh.faces.shape[0]}f")

# ============================================================
print("\n" + "="*60)
print("TEST 1: mesh.section() -> Path3D (WAIST)")
print("="*60)
waist_y = lms['WaistFront'][0][1]
path3d = mesh.section(plane_origin=[0, waist_y, 0], plane_normal=[0, 1, 0])
if path3d is None:
    print("  section() returned None!")
else:
    print(f"  Type: {type(path3d).__name__}")
    print(f"  Entities: {len(path3d.entities)}")
    print(f"  Vertices: {path3d.vertices.shape}")
    for i, entity in enumerate(path3d.entities):
        pts = entity.discrete(path3d.vertices)
        arc = np.sum(np.linalg.norm(np.diff(pts, axis=0), axis=1))
        closed = entity.closed
        print(f"  Entity {i}: {len(pts)} pts, arc={arc:.1f}mm, closed={closed}")

    # Convert to 2D for area/length analysis
    path2d, to_3d = path3d.to_planar()
    print(f"\n  Path2D polygons: {len(path2d.polygons_full)}")
    for i, poly in enumerate(path2d.polygons_full):
        print(f"    Polygon {i}: area={poly.area:.1f}mm^2, perimeter={poly.length:.1f}mm")

    # Snap waist landmarks to main contour
    print("\n  Landmark snap to largest polygon:")
    largest_poly = max(path2d.polygons_full, key=lambda p: p.area)
    from shapely.geometry import Point
    for name in ['WaistFront','WaistBack','WaistLeft','WaistRight']:
        pt3d = lms[name][0]
        pt2d_h = np.append(pt3d, 1) @ np.linalg.inv(to_3d).T
        pt2d = pt2d_h[:2] / pt2d_h[3] if abs(pt2d_h[3]) > 1e-10 else pt2d_h[:2]
        sp = Point(pt2d)
        dist = largest_poly.exterior.distance(sp)
        nearest = largest_poly.exterior.interpolate(largest_poly.exterior.project(sp))
        print(f"    {name}: snap_dist={dist:.2f}mm, nearest=({nearest.x:.1f}, {nearest.y:.1f})")

# ============================================================
print("\n" + "="*60)
print("TEST 2: mesh.section() -> Path3D (BUST)")
print("="*60)
bust_y = lms['BustFront'][0][1]
path_bust = mesh.section(plane_origin=[0, bust_y, 0], plane_normal=[0, 1, 0])
if path_bust is not None:
    print(f"  Entities: {len(path_bust.entities)}")
    for i, entity in enumerate(path_bust.entities):
        pts = entity.discrete(path_bust.vertices)
        arc = np.sum(np.linalg.norm(np.diff(pts, axis=0), axis=1))
        print(f"  Entity {i}: {len(pts)} pts, arc={arc:.1f}mm, closed={entity.closed}")

# ============================================================
print("\n" + "="*60)
print("TEST 3: mesh.section() -> Path3D (THIGH at crotch-50)")
print("="*60)
crotch_y = lms['CrotchPoint'][0][1]
path_thigh = mesh.section(plane_origin=[0, crotch_y - 50, 0], plane_normal=[0, 1, 0])
if path_thigh is not None:
    print(f"  Entities: {len(path_thigh.entities)}")
    for i, entity in enumerate(path_thigh.entities):
        pts = entity.discrete(path_thigh.vertices)
        arc = np.sum(np.linalg.norm(np.diff(pts, axis=0), axis=1))
        cx = np.mean(pts[:, 0])
        print(f"  Entity {i}: {len(pts)} pts, arc={arc:.1f}mm, closed={entity.closed}, centroid_x={cx:.0f}")

# ============================================================
print("\n" + "="*60)
print("TEST 4: mesh.section() -> Path3D (NECK coronal)")
print("="*60)
nf = lms['NeckFront'][0]
path_neck = mesh.section(plane_origin=nf, plane_normal=[0, 0, 1])
if path_neck is not None:
    print(f"  Entities: {len(path_neck.entities)}")
    for i, entity in enumerate(sorted(path_neck.entities,
                                       key=lambda e: len(e.discrete(path_neck.vertices)),
                                       reverse=True)[:5]):
        pts = entity.discrete(path_neck.vertices)
        arc = np.sum(np.linalg.norm(np.diff(pts, axis=0), axis=1))
        print(f"  Entity: {len(pts)} pts, arc={arc:.1f}mm, closed={entity.closed}")

# ============================================================
print("\n" + "="*60)
print("TEST 5: mesh.section() -> Path3D (ARMHOLE)")
print("="*60)
sl = lms['ShoulderLeft'][0]
al = lms['ArmpitLeft'][0]
sa_dir = (al - sl) / np.linalg.norm(al - sl)
pn_arm = np.cross(sa_dir, [1, 0, 0])
pn_arm /= np.linalg.norm(pn_arm)
path_arm = mesh.section(plane_origin=(sl + al) / 2, plane_normal=pn_arm)
if path_arm is not None:
    print(f"  Entities: {len(path_arm.entities)}")
    for i, entity in enumerate(sorted(path_arm.entities,
                                       key=lambda e: len(e.discrete(path_arm.vertices)),
                                       reverse=True)[:5]):
        pts = entity.discrete(path_arm.vertices)
        arc = np.sum(np.linalg.norm(np.diff(pts, axis=0), axis=1))
        print(f"  Entity: {len(pts)} pts, arc={arc:.1f}mm, closed={entity.closed}")

# ============================================================
print("\n" + "="*60)
print("TEST 6: slice_mesh_plane with cap=True (needs shapely+rtree)")
print("="*60)
from trimesh.intersections import slice_mesh_plane
try:
    upper = slice_mesh_plane(mesh, plane_normal=[0,-1,0], plane_origin=[0,waist_y,0], cap=True)
    print(f"  Upper (cap): {upper.vertices.shape[0]}v {upper.faces.shape[0]}f")
except Exception as e:
    print(f"  cap=True failed: {e}")
upper_nc = slice_mesh_plane(mesh, plane_normal=[0,-1,0], plane_origin=[0,waist_y,0], cap=False)
print(f"  Upper (no cap): {upper_nc.vertices.shape[0]}v {upper_nc.faces.shape[0]}f")

# ============================================================
print("\n" + "="*60)
print("TEST 7: Ray casting for neck intersection (needs rtree)")
print("="*60)
nl = lms['NeckLeft'][0]
try:
    origins = np.array([[nl[0], t, nf[2]] for t in np.linspace(1200, 1400, 100)])
    dirs = np.tile([0, 1, 0], (100, 1)).astype(float)
    locs, ri, ti = mesh.ray.intersects_location(ray_origins=origins, ray_directions=dirs)
    print(f"  Ray hits: {len(locs)}")
    if len(locs) > 0:
        mask = (locs[:, 1] > 1250) & (locs[:, 1] < 1400)
        neck_hits = locs[mask]
        print(f"  Hits in neck region: {len(neck_hits)}")
        for h in neck_hits[:10]:
            d_nl = np.linalg.norm(h - nl)
            print(f"    [{h[0]:.1f}, {h[1]:.1f}, {h[2]:.1f}] dist_to_NL={d_nl:.1f}mm")
except Exception as e:
    print(f"  Ray failed: {e}")

# ============================================================
print("\n" + "="*60)
print("TEST 8: Shapely arc length on waist contour")
print("="*60)
if path3d is not None:
    path2d, to_3d = path3d.to_planar()
    largest = max(path2d.polygons_full, key=lambda p: p.area)
    ring = largest.exterior
    print(f"  Shapely perimeter: {ring.length:.1f}mm")

    # Project waist landmarks to ring and measure arc between them
    inv_3d = np.linalg.inv(to_3d)
    def project_to_2d(pt3d):
        h = np.append(pt3d, 1) @ inv_3d.T
        return h[:2] / h[3] if abs(h[3]) > 1e-10 else h[:2]

    wf_2d = project_to_2d(lms['WaistFront'][0])
    wb_2d = project_to_2d(lms['WaistBack'][0])
    wl_2d = project_to_2d(lms['WaistLeft'][0])
    wr_2d = project_to_2d(lms['WaistRight'][0])

    # Shapely: project point onto ring -> get linear position along ring
    from shapely.geometry import Point
    pos_f = ring.project(Point(wf_2d))
    pos_b = ring.project(Point(wb_2d))
    pos_l = ring.project(Point(wl_2d))
    pos_r = ring.project(Point(wr_2d))

    total = ring.length
    print(f"  WaistFront pos: {pos_f:.1f}mm")
    print(f"  WaistBack  pos: {pos_b:.1f}mm")
    print(f"  WaistLeft  pos: {pos_l:.1f}mm")
    print(f"  WaistRight pos: {pos_r:.1f}mm")
    print(f"  Total perimeter: {total:.1f}mm")

    # Arc from WaistFront to WaistLeft (shorter arc)
    arc_fl = abs(pos_l - pos_f) if abs(pos_l - pos_f) < total / 2 else total - abs(pos_l - pos_f)
    arc_fb = abs(pos_b - pos_f) if abs(pos_b - pos_f) < total / 2 else total - abs(pos_b - pos_f)
    print(f"  Arc WaistFront->WaistLeft: {arc_fl:.1f}mm")
    print(f"  Arc WaistFront->WaistBack: {arc_fb:.1f}mm")

    # Locate midpoint between WaistBack and WaistLeft on ring (50% arc)
    arc_bl = abs(pos_l - pos_b) if abs(pos_l - pos_b) < total / 2 else total - abs(pos_l - pos_b)
    mid_pos = pos_b + arc_bl / 2  # simple case
    if mid_pos > total:
        mid_pos -= total
    mid_pt_2d = ring.interpolate(mid_pos)
    # Convert back to 3D
    mid_3d_h = np.array([mid_pt_2d.x, mid_pt_2d.y, 0, 1]) @ to_3d.T
    mid_3d = mid_3d_h[:3] / mid_3d_h[3] if abs(mid_3d_h[3]) > 1e-10 else mid_3d_h[:3]
    print(f"  Arc WaistBack->WaistLeft: {arc_bl:.1f}mm")
    print(f"  50% midpoint (WaistDartBackLeft): [{mid_3d[0]:.1f}, {mid_3d[1]:.1f}, {mid_3d[2]:.1f}]")

# ============================================================
print("\n" + "="*60)
print("TEST 9: Neck landmark via transverse section + projection")
print("="*60)
# Instead of two-plane intersection, cut at NeckFront Y height
nf_y = lms['NeckFront'][0][1]
path_neck_t = mesh.section(plane_origin=[0, nf_y, 0], plane_normal=[0, 1, 0])
if path_neck_t is not None:
    print(f"  Entities at NeckFront Y={nf_y:.0f}: {len(path_neck_t.entities)}")
    # Find the neck contour (closest to neck landmarks)
    nl = lms['NeckLeft'][0]
    nr = lms['NeckRight'][0]
    best_entity = None
    best_dist = float('inf')
    for entity in path_neck_t.entities:
        pts = entity.discrete(path_neck_t.vertices)
        tree = cKDTree(pts)
        d, _ = tree.query(nl)
        if d < best_dist:
            best_dist = d
            best_entity = entity

    if best_entity is not None:
        pts = best_entity.discrete(path_neck_t.vertices)
        print(f"  Best entity (closest to NeckLeft): {len(pts)} pts, snap_dist={best_dist:.1f}mm")
        # Find point on this contour closest to NeckLeft X coordinate
        x_diffs = np.abs(pts[:, 0] - nl[0])
        best_idx = np.argmin(x_diffs)
        candidate = pts[best_idx]
        print(f"  NeckFrontLeft candidate: [{candidate[0]:.1f}, {candidate[1]:.1f}, {candidate[2]:.1f}]")
        print(f"  NeckLeft actual:         [{nl[0]:.1f}, {nl[1]:.1f}, {nl[2]:.1f}]")
        print(f"  NeckFront actual:        [{nf[0]:.1f}, {nf[1]:.1f}, {nf[2]:.1f}]")

print("\n" + "="*60)
print("DONE")
print("="*60)
