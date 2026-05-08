import trimesh, numpy as np
from scipy.spatial import cKDTree
from data_loader import scan_data_folders

c = scan_data_folders()
e = c.subjects[list(c.subjects.keys())[0]]
mesh = trimesh.load(str(e.ss_obj_path), process=False)
lms = c.lm_data['landmarks_3d']
nf = lms['NeckFront'][0]
nb = lms['NeckBack'][0]
nl = lms['NeckLeft'][0]
nr = lms['NeckRight'][0]

print(f"NF={nf}")
print(f"NB={nb}")
print(f"NL={nl}")
print(f"NR={nr}")

# V3: Plane1 = Coronal through NeckFront (normal=[0,0,1])
#     Plane2 = through NeckLeft, vertical, perpendicular to Plane1 (normal=[1,0,0])
# Intersection line: x=NL.x, z=NF.z, varying Y
lx, lz = nl[0], nf[2]
print(f"\nIntersection line: x={lx:.1f}, z={lz:.1f}, Y varies")
origins = np.array([[lx, t, lz] for t in np.linspace(1200, 1500, 300)])
dirs = np.tile([0., 1., 0.], (300, 1))
locs, ri, ti = mesh.ray.intersects_location(ray_origins=origins, ray_directions=dirs)
mask = (locs[:, 1] > 1250) & (locs[:, 1] < 1400)
hits = locs[mask]
print(f"Raw hits in neck region: {len(hits)}")

if len(hits) > 0:
    tree = cKDTree(hits)
    gs = tree.query_ball_tree(tree, r=3.0)
    seen = set()
    u = []
    for i, g in enumerate(gs):
        k = min(g)
        if k not in seen:
            seen.update(g)
            u.append(hits[k])
    u = np.array(u)
    u = u[np.argsort(u[:, 1])]
    print(f"Unique hits: {len(u)}")
    for h in u:
        print(f"  [{h[0]:.1f}, {h[1]:.1f}, {h[2]:.1f}]")
    print(f"\nLowest Y = NeckFrontLeft: [{u[0][0]:.1f}, {u[0][1]:.1f}, {u[0][2]:.1f}]")
    print(f"  dist to NeckFront: {np.linalg.norm(u[0]-nf):.1f}mm")
    print(f"  dist to NeckLeft:  {np.linalg.norm(u[0]-nl):.1f}mm")

# Now do the same for NeckFrontRight
lx2, lz2 = nr[0], nf[2]
print(f"\n--- NeckFrontRight ---")
print(f"Intersection line: x={lx2:.1f}, z={lz2:.1f}")
origins2 = np.array([[lx2, t, lz2] for t in np.linspace(1200, 1500, 300)])
locs2, _, _ = mesh.ray.intersects_location(ray_origins=origins2, ray_directions=dirs)
mask2 = (locs2[:, 1] > 1250) & (locs2[:, 1] < 1400)
hits2 = locs2[mask2]
if len(hits2) > 0:
    tree2 = cKDTree(hits2)
    gs2 = tree2.query_ball_tree(tree2, r=3.0)
    seen2 = set()
    u2 = []
    for i, g in enumerate(gs2):
        k = min(g)
        if k not in seen2:
            seen2.update(g)
            u2.append(hits2[k])
    u2 = np.array(u2)
    u2 = u2[np.argsort(u2[:, 1])]
    print(f"Unique hits: {len(u2)}")
    for h in u2:
        print(f"  [{h[0]:.1f}, {h[1]:.1f}, {h[2]:.1f}]")

# NeckBackLeft: Coronal through NeckBack, Sagittal through NeckLeft
lx3, lz3 = nl[0], nb[2]
print(f"\n--- NeckBackLeft ---")
print(f"Intersection line: x={lx3:.1f}, z={lz3:.1f}")
origins3 = np.array([[lx3, t, lz3] for t in np.linspace(1200, 1500, 300)])
locs3, _, _ = mesh.ray.intersects_location(ray_origins=origins3, ray_directions=dirs)
mask3 = (locs3[:, 1] > 1250) & (locs3[:, 1] < 1400)
hits3 = locs3[mask3]
if len(hits3) > 0:
    tree3 = cKDTree(hits3)
    gs3 = tree3.query_ball_tree(tree3, r=3.0)
    seen3 = set()
    u3 = []
    for i, g in enumerate(gs3):
        k = min(g)
        if k not in seen3:
            seen3.update(g)
            u3.append(hits3[k])
    u3 = np.array(u3)
    u3 = u3[np.argsort(u3[:, 1])]
    print(f"Unique hits: {len(u3)}")
    for h in u3:
        print(f"  [{h[0]:.1f}, {h[1]:.1f}, {h[2]:.1f}]")
else:
    print("  No hits!")
