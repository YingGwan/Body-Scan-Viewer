import numpy as np, trimesh
from data_loader import scan_data_folders
from derived_landmarks import init_contour_z_extremum, load_derived_landmark_config

c = scan_data_folders()
e = c.subjects[list(c.subjects.keys())[0]]
mesh = trimesh.load(str(e.ss_obj_path), process=False)
lms = {n: v[0] for n, v in c.lm_data["landmarks_3d"].items()}
cfg = load_derived_landmark_config("config/derived_landmarks.yaml")

print(f"ShoulderLeft  Y={lms['ShoulderLeft'][1]:.1f}")
print(f"ArmpitLeft    Y={lms['ArmpitLeft'][1]:.1f}")
print(f"ShoulderRight Y={lms['ShoulderRight'][1]:.1f}")
print(f"ArmpitRight   Y={lms['ArmpitRight'][1]:.1f}")
print()

for name in ["ArmholeDepthFrontLeft", "ArmholeDepthBackLeft",
             "ArmholeDepthFrontRight", "ArmholeDepthBackRight"]:
    lm_cfg = cfg["landmarks"][name]
    params = lm_cfg["init_params"]
    pt = init_contour_z_extremum(mesh, lms, params, config=cfg)
    print(f"{name}: [{pt[0]:.1f}, {pt[1]:.1f}, {pt[2]:.1f}]")
