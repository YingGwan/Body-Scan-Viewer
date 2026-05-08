import numpy as np, trimesh
from data_loader import scan_data_folders
from derived_landmarks import init_plane_intersection, load_derived_landmark_config

c = scan_data_folders()
e = c.subjects[list(c.subjects.keys())[0]]
mesh = trimesh.load(str(e.ss_obj_path), process=False)
lms = {n: v[0] for n, v in c.lm_data["landmarks_3d"].items()}
cfg = load_derived_landmark_config("config/derived_landmarks.yaml")

print(f"NeckFront:      {lms['NeckFront']}")
print(f"NeckBack:       {lms['NeckBack']}")
print(f"Mid Neck Left:  {lms['Mid Neck Left']}")
print(f"Mid Neck Right: {lms['Mid Neck Right']}")
print()

for name in ["NeckFrontLeft", "NeckFrontRight", "NeckBackLeft", "NeckBackRight"]:
    lm_cfg = cfg["landmarks"][name]
    params = lm_cfg["init_params"]
    pt = init_plane_intersection(mesh, lms, params, config=cfg)
    print(f"{name}: [{pt[0]:.1f}, {pt[1]:.1f}, {pt[2]:.1f}]")
