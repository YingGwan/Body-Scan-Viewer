# Shoulder & Derived Landmarks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 4 Armhole Depth landmarks + 4 geodesic shoulder measurements with a reusable barycentric-coordinate derived landmark framework and interactive GUI Panel E.

**Architecture:** New `derived_landmarks.py` provides stateless pure functions (YAML loading, barycentric math, mesh projection, init methods). `geometry_backend.py` VisContent gets 3 new methods that orchestrate these functions. `gui_panel.py` gets Panel E with real-time sliders. All landmark weights stored in `config/derived_landmarks.yaml`.

**Tech Stack:** trimesh 4.11 (`mesh.section()`), PyYAML, numpy, scipy (cKDTree), existing `geodesic_utils.compute_geodesic()`, Polyscope 2.5 ImGui, openpyxl. **Must run in conda FastIKD env.**

**Test runner:** `conda run -n FastIKD python -m pytest` from project root.

---

## File Map

| File | Role | Action |
|---|---|---|
| `derived_landmarks.py` | Stateless framework: YAML, barycentric, init methods, measurements | CREATE |
| `config/derived_landmarks.yaml` | Landmark + measurement definitions | CREATE |
| `geometry_backend.py` | VisContent: state + orchestration + Polyscope registration | MODIFY |
| `gui_panel.py` | Panel E: sliders, measurements, buttons | MODIFY |
| `requirements.txt` | Add PyYAML | MODIFY |
| `tests/test_derived_landmarks.py` | Unit tests for framework | CREATE |
| `tests/test_shoulder_behavior.py` | Integration tests | CREATE |

---

### Task 1: Add PyYAML dependency + YAML config file

**Files:**
- Modify: `requirements.txt:18` (append)
- Create: `config/derived_landmarks.yaml`

- [ ] **Step 1: Add PyYAML to requirements.txt**

Append to the end of `requirements.txt`:
```
PyYAML>=6.0
```

- [ ] **Step 2: Create `config/derived_landmarks.yaml`**

```yaml
version: 1

landmarks:

  ArmholeDepthFrontLeft:
    triangle: [ShoulderLeft, ArmpitLeft, NeckLeft]
    weights: null
    init_method: contour_z_extremum
    init_params:
      extremum: max
      plane_landmarks: [ShoulderLeft, ArmpitLeft]
    family: Armhole

  ArmholeDepthBackLeft:
    triangle: [ShoulderLeft, ArmpitLeft, NeckBack]
    weights: null
    init_method: contour_z_extremum
    init_params:
      extremum: min
      plane_landmarks: [ShoulderLeft, ArmpitLeft]
    family: Armhole

  ArmholeDepthFrontRight:
    triangle: [ShoulderRight, ArmpitRight, NeckRight]
    weights: null
    init_method: contour_z_extremum
    init_params:
      extremum: max
      plane_landmarks: [ShoulderRight, ArmpitRight]
    family: Armhole

  ArmholeDepthBackRight:
    triangle: [ShoulderRight, ArmpitRight, NeckBack]
    weights: null
    init_method: contour_z_extremum
    init_params:
      extremum: min
      plane_landmarks: [ShoulderRight, ArmpitRight]
    family: Armhole

measurements:

  MidShoulderToApexLeft:
    type: geodesic
    from: "Mid Shoulder Left"
    to: ApexBustLeft
    family: Shoulder
    also_output_y_projection: true

  MidShoulderToApexRight:
    type: geodesic
    from: "Mid Shoulder Right"
    to: ApexBustRight
    family: Shoulder
    also_output_y_projection: true

  ApexToLowerBustLeft:
    type: geodesic
    from: ApexBustLeft
    to: LowerBustLeft
    family: Shoulder
    also_output_y_projection: true

  ApexToLowerBustRight:
    type: geodesic
    from: ApexBustRight
    to: LowerBustRight
    family: Shoulder
    also_output_y_projection: true
```

- [ ] **Step 3: Verify PyYAML loads the config**

Run: `conda run -n FastIKD python -c "import yaml; d=yaml.safe_load(open('config/derived_landmarks.yaml')); print(d['version']); print(list(d['landmarks'].keys())); print(list(d['measurements'].keys()))"`

Expected:
```
1
['ArmholeDepthFrontLeft', 'ArmholeDepthBackLeft', 'ArmholeDepthFrontRight', 'ArmholeDepthBackRight']
['MidShoulderToApexLeft', 'MidShoulderToApexRight', 'ApexToLowerBustLeft', 'ApexToLowerBustRight']
```

- [ ] **Step 4: Commit**

```bash
git add requirements.txt config/derived_landmarks.yaml
git commit -m "feat: add derived_landmarks YAML config and PyYAML dependency"
```

---

### Task 2: Barycentric engine + YAML loader (TDD)

**Files:**
- Create: `derived_landmarks.py`
- Create: `tests/test_derived_landmarks.py`

- [ ] **Step 1: Write failing tests for barycentric roundtrip and YAML loading**

Create `tests/test_derived_landmarks.py`:
```python
"""Unit tests for derived_landmarks.py — barycentric engine + YAML loader."""
import numpy as np
import pytest
import tempfile, pathlib, yaml


def test_from_barycentric_midpoint():
    from derived_landmarks import from_barycentric
    A = np.array([0.0, 0.0, 0.0])
    B = np.array([10.0, 0.0, 0.0])
    C = np.array([0.0, 10.0, 0.0])
    result = from_barycentric(0.5, 0.5, 0.0, A, B, C)
    np.testing.assert_allclose(result, [5.0, 0.0, 0.0])


def test_from_barycentric_centroid():
    from derived_landmarks import from_barycentric
    A = np.array([0.0, 0.0, 0.0])
    B = np.array([9.0, 0.0, 0.0])
    C = np.array([0.0, 9.0, 0.0])
    result = from_barycentric(1/3, 1/3, 1/3, A, B, C)
    np.testing.assert_allclose(result, [3.0, 3.0, 0.0])


def test_to_barycentric_roundtrip():
    from derived_landmarks import to_barycentric, from_barycentric
    A = np.array([10.0, 20.0, 30.0])
    B = np.array([40.0, 50.0, 60.0])
    C = np.array([70.0, 10.0, 20.0])
    P = np.array([35.0, 30.0, 40.0])
    alpha, beta, gamma = to_barycentric(P, A, B, C)
    assert abs(alpha + beta + gamma - 1.0) < 1e-10
    P_reconstructed = from_barycentric(alpha, beta, gamma, A, B, C)
    np.testing.assert_allclose(P_reconstructed, P, atol=1e-8)


def test_to_barycentric_outside_triangle():
    from derived_landmarks import to_barycentric
    A = np.array([0.0, 0.0, 0.0])
    B = np.array([10.0, 0.0, 0.0])
    C = np.array([0.0, 10.0, 0.0])
    P = np.array([15.0, 15.0, 0.0])  # outside triangle
    alpha, beta, gamma = to_barycentric(P, A, B, C)
    assert abs(alpha + beta + gamma - 1.0) < 1e-10
    # At least one weight should be negative for outside point
    assert min(alpha, beta, gamma) < 0


def test_load_config_valid():
    from derived_landmarks import load_derived_landmark_config
    config = load_derived_landmark_config("config/derived_landmarks.yaml")
    assert config["version"] == 1
    assert "ArmholeDepthFrontLeft" in config["landmarks"]
    lm = config["landmarks"]["ArmholeDepthFrontLeft"]
    assert lm["triangle"] == ["ShoulderLeft", "ArmpitLeft", "NeckLeft"]
    assert lm["weights"] is None
    assert lm["init_method"] == "contour_z_extremum"
    assert lm["family"] == "Armhole"
    assert "MidShoulderToApexLeft" in config["measurements"]


def test_load_config_invalid_version():
    from derived_landmarks import load_derived_landmark_config
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.safe_dump({"version": 99, "landmarks": {}, "measurements": {}}, f)
        f.flush()
        with pytest.raises(ValueError, match="version"):
            load_derived_landmark_config(f.name)


def test_save_weights_roundtrip():
    from derived_landmarks import load_derived_landmark_config, save_weights_to_yaml
    import shutil
    tmp = pathlib.Path(tempfile.mkdtemp()) / "test.yaml"
    shutil.copy("config/derived_landmarks.yaml", tmp)
    save_weights_to_yaml(tmp, "ArmholeDepthFrontLeft", [0.35, 0.55, 0.10])
    config = load_derived_landmark_config(tmp)
    w = config["landmarks"]["ArmholeDepthFrontLeft"]["weights"]
    np.testing.assert_allclose(w, [0.35, 0.55, 0.10])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda run -n FastIKD python -m pytest tests/test_derived_landmarks.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'derived_landmarks'`

- [ ] **Step 3: Implement barycentric engine + YAML loader**

Create `derived_landmarks.py`:
```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda run -n FastIKD python -m pytest tests/test_derived_landmarks.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add derived_landmarks.py tests/test_derived_landmarks.py
git commit -m "feat: add barycentric engine, YAML loader/saver with tests"
```

---

### Task 3: `init_contour_z_extremum` + stubs (TDD)

**Files:**
- Modify: `tests/test_derived_landmarks.py` (append tests)
- Modify: `derived_landmarks.py` (add init methods)

- [ ] **Step 1: Write failing tests for init methods**

Append to `tests/test_derived_landmarks.py`:
```python
def test_init_contour_z_extremum_max(shared_mesh_and_landmarks):
    from derived_landmarks import init_contour_z_extremum
    mesh, lms = shared_mesh_and_landmarks
    params = {"extremum": "max", "plane_landmarks": ["ShoulderLeft", "ArmpitLeft"]}
    pt = init_contour_z_extremum(mesh, lms, params)
    assert pt.shape == (3,)
    # Max Z should be greater than ArmpitLeft Z (front-ish)
    assert pt[2] > lms["ArmpitLeft"][2]


def test_init_contour_z_extremum_min(shared_mesh_and_landmarks):
    from derived_landmarks import init_contour_z_extremum
    mesh, lms = shared_mesh_and_landmarks
    params = {"extremum": "min", "plane_landmarks": ["ShoulderLeft", "ArmpitLeft"]}
    pt = init_contour_z_extremum(mesh, lms, params)
    assert pt.shape == (3,)
    # Min Z should be less than ShoulderLeft Z (back-ish)
    assert pt[2] < lms["ShoulderLeft"][2]


def test_init_contour_z_extremum_none_mesh():
    from derived_landmarks import init_contour_z_extremum
    mesh = trimesh.Trimesh(vertices=[[0,0,0],[1,0,0],[0,1,0]], faces=[[0,1,2]])
    lms = {"A": np.array([100.0, 100.0, 100.0]), "B": np.array([200.0, 200.0, 200.0])}
    params = {"extremum": "max", "plane_landmarks": ["A", "B"]}
    with pytest.raises(ValueError, match="did not intersect"):
        init_contour_z_extremum(mesh, lms, params)


def test_init_plane_intersection_stub():
    from derived_landmarks import init_plane_intersection
    with pytest.raises(NotImplementedError):
        init_plane_intersection(None, {}, {})


def test_init_arc_length_ratio_stub():
    from derived_landmarks import init_arc_length_ratio
    with pytest.raises(NotImplementedError):
        init_arc_length_ratio(None, {}, {})


def test_init_three_plane_intersection_stub():
    from derived_landmarks import init_three_plane_intersection
    with pytest.raises(NotImplementedError):
        init_three_plane_intersection(None, {}, {})


import trimesh

@pytest.fixture(scope="module")
def shared_mesh_and_landmarks():
    """Load real SizeStream mesh and landmarks for integration tests."""
    import sys
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
    from data_loader import scan_data_folders
    catalog = scan_data_folders()
    entry = catalog.subjects[list(catalog.subjects.keys())[0]]
    mesh = trimesh.load(str(entry.ss_obj_path), process=False)
    lm3d = catalog.lm_data["landmarks_3d"]
    lms = {name: coords[0] for name, coords in lm3d.items()}
    return mesh, lms
```

- [ ] **Step 2: Run tests to verify new ones fail**

Run: `conda run -n FastIKD python -m pytest tests/test_derived_landmarks.py::test_init_contour_z_extremum_max -v`
Expected: FAIL — `ImportError: cannot import name 'init_contour_z_extremum'`

- [ ] **Step 3: Implement init methods**

Append to `derived_landmarks.py`:
```python
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
def init_contour_z_extremum(mesh, landmark_dict, params):
    lm_names = params["plane_landmarks"]
    p0 = np.asarray(landmark_dict[lm_names[0]])
    p1 = np.asarray(landmark_dict[lm_names[1]])

    origin = (p0 + p1) / 2.0
    direction = p1 - p0
    direction = direction / np.linalg.norm(direction)
    x_axis = np.array([1.0, 0.0, 0.0])
    normal = np.cross(direction, x_axis)
    norm_len = np.linalg.norm(normal)
    if norm_len < 1e-10:
        raise ValueError(f"Plane landmarks {lm_names} are parallel to X-axis, cannot compute normal")
    normal = normal / norm_len

    path3d = mesh.section(plane_origin=origin, plane_normal=normal)
    if path3d is None or len(path3d.entities) == 0:
        raise ValueError(f"Plane did not intersect mesh for landmarks {lm_names}")

    largest_entity = max(path3d.entities, key=lambda e: len(e.discrete(path3d.vertices)))
    contour_pts = largest_entity.discrete(path3d.vertices)

    extremum = params.get("extremum", "max")
    if extremum == "max":
        idx = np.argmax(contour_pts[:, 2])
    elif extremum == "min":
        idx = np.argmin(contour_pts[:, 2])
    else:
        raise ValueError(f"Unknown extremum type: {extremum}")

    return contour_pts[idx].copy()


@_register_init("plane_intersection")
def init_plane_intersection(mesh, landmark_dict, params):
    raise NotImplementedError("Planned for Neck/Waist module")


@_register_init("arc_length_ratio")
def init_arc_length_ratio(mesh, landmark_dict, params):
    raise NotImplementedError("Planned for Neck/Waist module")


@_register_init("three_plane_intersection")
def init_three_plane_intersection(mesh, landmark_dict, params):
    raise NotImplementedError("Planned for Neck/Waist module")
```

- [ ] **Step 4: Run all tests**

Run: `conda run -n FastIKD python -m pytest tests/test_derived_landmarks.py -v`
Expected: All tests PASS (including the 3 new contour tests and 3 stub tests)

- [ ] **Step 5: Commit**

```bash
git add derived_landmarks.py tests/test_derived_landmarks.py
git commit -m "feat: add init_contour_z_extremum and stub init methods with tests"
```

---

### Task 4: Unified entry points (`compute_derived_landmark` / `compute_all`) (TDD)

**Files:**
- Modify: `tests/test_derived_landmarks.py` (append)
- Modify: `derived_landmarks.py` (append)

- [ ] **Step 1: Write failing tests**

Append to `tests/test_derived_landmarks.py`:
```python
def test_compute_derived_landmark_null_weights(shared_mesh_and_landmarks):
    from derived_landmarks import compute_derived_landmark
    mesh, lms = shared_mesh_and_landmarks
    lm_config = {
        "triangle": ["ShoulderLeft", "ArmpitLeft", "NeckLeft"],
        "weights": None,
        "init_method": "contour_z_extremum",
        "init_params": {"extremum": "max", "plane_landmarks": ["ShoulderLeft", "ArmpitLeft"]},
        "family": "Armhole",
    }
    pos, weights = compute_derived_landmark(mesh, lms, "ArmholeDepthFrontLeft", lm_config)
    assert pos.shape == (3,)
    assert len(weights) == 3
    assert abs(sum(weights) - 1.0) < 1e-8


def test_compute_derived_landmark_preset_weights(shared_mesh_and_landmarks):
    from derived_landmarks import compute_derived_landmark
    mesh, lms = shared_mesh_and_landmarks
    lm_config = {
        "triangle": ["ShoulderLeft", "ArmpitLeft", "NeckLeft"],
        "weights": [0.4, 0.4, 0.2],
        "init_method": "contour_z_extremum",
        "init_params": {"extremum": "max", "plane_landmarks": ["ShoulderLeft", "ArmpitLeft"]},
        "family": "Armhole",
    }
    pos, weights = compute_derived_landmark(mesh, lms, "test", lm_config)
    assert pos.shape == (3,)
    np.testing.assert_allclose(weights, [0.4, 0.4, 0.2])


def test_compute_all_derived_landmarks(shared_mesh_and_landmarks):
    from derived_landmarks import compute_all_derived_landmarks, load_derived_landmark_config
    mesh, lms = shared_mesh_and_landmarks
    config = load_derived_landmark_config("config/derived_landmarks.yaml")
    result = compute_all_derived_landmarks(mesh, lms, config)
    assert len(result) == 4
    for name in ["ArmholeDepthFrontLeft", "ArmholeDepthBackLeft",
                 "ArmholeDepthFrontRight", "ArmholeDepthBackRight"]:
        assert name in result
        assert result[name]["position"].shape == (3,)
        assert len(result[name]["weights"]) == 3
        assert result[name]["family"] == "Armhole"
```

- [ ] **Step 2: Run to verify fail**

Run: `conda run -n FastIKD python -m pytest tests/test_derived_landmarks.py::test_compute_derived_landmark_null_weights -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement unified entry points**

Append to `derived_landmarks.py`:
```python
# =========================================================================
# Unified entry points
# =========================================================================

def compute_derived_landmark(mesh, landmark_dict, lm_name, lm_config):
    triangle_names = lm_config["triangle"]
    A = np.asarray(landmark_dict[triangle_names[0]])
    B = np.asarray(landmark_dict[triangle_names[1]])
    C = np.asarray(landmark_dict[triangle_names[2]])

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
    P_init = init_fn(mesh, landmark_dict, params)
    P_surface = project_to_mesh(P_init, mesh)
    alpha, beta, gamma = to_barycentric(P_surface, A, B, C)
    return P_surface, (alpha, beta, gamma)


def compute_all_derived_landmarks(mesh, landmark_dict, config):
    results = {}
    for name, lm_config in config["landmarks"].items():
        pos, weights = compute_derived_landmark(mesh, landmark_dict, name, lm_config)
        results[name] = {
            "position": pos,
            "weights": weights,
            "family": lm_config["family"],
        }
    return results
```

- [ ] **Step 4: Run all tests**

Run: `conda run -n FastIKD python -m pytest tests/test_derived_landmarks.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add derived_landmarks.py tests/test_derived_landmarks.py
git commit -m "feat: add compute_derived_landmark and compute_all with tests"
```

---

### Task 5: Measurement computation (TDD)

**Files:**
- Modify: `tests/test_derived_landmarks.py` (append)
- Modify: `derived_landmarks.py` (append)

- [ ] **Step 1: Write failing tests**

Append to `tests/test_derived_landmarks.py`:
```python
def test_compute_configured_measurements(shared_mesh_and_landmarks):
    from derived_landmarks import (
        compute_configured_measurements, load_derived_landmark_config,
        compute_all_derived_landmarks, MeasurementRecord,
    )
    mesh, lms = shared_mesh_and_landmarks
    config = load_derived_landmark_config("config/derived_landmarks.yaml")
    derived = compute_all_derived_landmarks(mesh, lms, config)
    derived_flat = {n: d["position"] for n, d in derived.items()}

    def mock_geodesic(pt_a, pt_b):
        dist = float(np.linalg.norm(pt_a - pt_b))
        return dist, np.array([pt_a, pt_b])

    records = compute_configured_measurements(
        mesh, lms, derived_flat, config["measurements"], mock_geodesic
    )
    assert len(records) >= 8  # 4 geodesic + 4 y_projection
    families = {r.family for r in records}
    assert "Shoulder" in families
    methods = {r.method for r in records}
    assert "geodesic" in methods
    assert "y_projection" in methods
    for r in records:
        assert r.value_mm > 0
```

- [ ] **Step 2: Run to verify fail**

Run: `conda run -n FastIKD python -m pytest tests/test_derived_landmarks.py::test_compute_configured_measurements -v`
Expected: FAIL

- [ ] **Step 3: Implement measurement computation**

Append to `derived_landmarks.py`:
```python
# =========================================================================
# Measurement computation
# =========================================================================

def compute_configured_measurements(mesh, landmark_dict, derived_dict, measurements_config, geodesic_fn):
    combined = dict(landmark_dict)
    combined.update(derived_dict)

    records = []
    for name, m_config in measurements_config.items():
        from_name = m_config["from"]
        to_name = m_config["to"]
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

    return records
```

- [ ] **Step 4: Run all tests**

Run: `conda run -n FastIKD python -m pytest tests/test_derived_landmarks.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add derived_landmarks.py tests/test_derived_landmarks.py
git commit -m "feat: add compute_configured_measurements with tests"
```

---

### Task 6: Integrate into `geometry_backend.py`

**Files:**
- Modify: `geometry_backend.py:56-98` (_init_state), `geometry_backend.py:148-170` (reset_subject)
- Modify: `geometry_backend.py` (append 3 new methods)
- Create: `tests/test_shoulder_behavior.py`

- [ ] **Step 1: Write failing integration test**

Create `tests/test_shoulder_behavior.py`:
```python
"""Integration tests for shoulder landmark and measurement pipeline."""
import numpy as np
import pathlib, sys
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))


@pytest.fixture(scope="module")
def loaded_content():
    from geometry_backend import VisContent
    vc = VisContent()
    sid = list(vc.catalog.subjects.keys())[0]
    vc.load_sizestream(sid)
    return vc


def test_compute_derived_landmarks(loaded_content):
    vc = loaded_content
    vc.compute_derived_landmarks()
    assert len(vc.derived_lm_dict) == 4
    for name in ["ArmholeDepthFrontLeft", "ArmholeDepthBackLeft",
                 "ArmholeDepthFrontRight", "ArmholeDepthBackRight"]:
        assert name in vc.derived_lm_dict
        pos = vc.derived_lm_dict[name]["position"]
        assert pos.shape == (3,)
        # Y should be in armhole region (roughly between armpit and shoulder height)
        assert 1150 < pos[1] < 1350


def test_compute_shoulder_measurements(loaded_content):
    vc = loaded_content
    if not vc.derived_lm_dict:
        vc.compute_derived_landmarks()
    vc.compute_shoulder_measurements()
    assert len(vc.measurement_results) >= 8
    geo_results = [r for r in vc.measurement_results if r.method == "geodesic"]
    y_results = [r for r in vc.measurement_results if r.method == "y_projection"]
    assert len(geo_results) == 4
    assert len(y_results) == 4
    for r in geo_results:
        assert r.value_mm > 0
        assert r.value_mm < 1000  # sanity: less than 1 meter
```

- [ ] **Step 2: Run to verify fail**

Run: `conda run -n FastIKD python -m pytest tests/test_shoulder_behavior.py -v`
Expected: FAIL — `AttributeError: 'VisContent' object has no attribute 'compute_derived_landmarks'`

- [ ] **Step 3: Add state fields to `_init_state`**

In `geometry_backend.py`, after line 97 (`self.geodesic_length = 0.0`), add:
```python
        # Derived landmarks (V3)
        self.derived_lm_config  = None
        self.derived_lm_dict    = {}
        self.measurement_results = []
```

- [ ] **Step 4: Extend `reset_subject()` known_structures**

In `geometry_backend.py`, modify the `known_structures` list at line 154 to add the 7 new names:
```python
        known_structures = [
            "SizeStream", "SS_Landmarks", "CAESAR", "CAESAR_Registered",
            "CAESAR_Landmarks", "CAESAR_Landmarks_Registered",
            "Landmark_Errors", "Geodesic_Path", "Geo_Endpoints",
            "Distance_to_CAESAR",
            # V3 derived landmarks
            "Derived_Armhole",
            "Armhole_Section_L", "Armhole_Section_R",
            "Geo_MidShoulderToApexLeft", "Geo_MidShoulderToApexRight",
            "Geo_ApexToLowerBustLeft", "Geo_ApexToLowerBustRight",
        ]
```

- [ ] **Step 5: Add import and 3 new methods**

At the top of `geometry_backend.py`, after the existing imports (line 34), add:
```python
from derived_landmarks import (
    load_derived_landmark_config, compute_all_derived_landmarks,
    compute_configured_measurements, from_barycentric, project_to_mesh,
    MeasurementRecord,
)
```

After the `compute_and_show_geodesic` method (after line 559), append:
```python
    # ==========================================================================
    # E. Derived Landmarks (V3)
    # ==========================================================================

    _DERIVED_YAML = pathlib.Path(__file__).resolve().parent / "config" / "derived_landmarks.yaml"

    def compute_derived_landmarks(self):
        if self.mesh_ss is None or not self.ss_lm_dict:
            raise RuntimeError("Load SizeStream mesh + landmarks first")

        if self.derived_lm_config is None:
            self.derived_lm_config = load_derived_landmark_config(str(self._DERIVED_YAML))

        self.derived_lm_dict = compute_all_derived_landmarks(
            self.mesh_ss, self.ss_lm_dict, self.derived_lm_config,
        )

        families = {}
        for name, info in self.derived_lm_dict.items():
            families.setdefault(info["family"], []).append(info["position"])

        for family, positions in families.items():
            ps.register_point_cloud(
                f"Derived_{family}",
                np.array(positions),
                color=[0.2, 0.4, 0.9],
                enabled=True,
                radius=0.003,
            )

    def compute_shoulder_measurements(self):
        if not self.derived_lm_dict:
            raise RuntimeError("Compute derived landmarks first")

        config = self.derived_lm_config
        derived_flat = {n: d["position"] for n, d in self.derived_lm_dict.items()}

        def geodesic_fn(pt_a, pt_b):
            return compute_geodesic(
                self.ss_edge_graph, self.mesh_ss.vertices,
                pt_a, pt_b,
                kdtree=self.ss_kdtree,
                exact_solver=self.ss_geodesic_solver,
            )

        self.measurement_results = compute_configured_measurements(
            self.mesh_ss, self.ss_lm_dict, derived_flat,
            config["measurements"], geodesic_fn,
        )

        for r in self.measurement_results:
            if r.method == "geodesic":
                _, path_verts = geodesic_fn(
                    np.asarray((self.ss_lm_dict | derived_flat)[r.source_landmarks[0]]),
                    np.asarray((self.ss_lm_dict | derived_flat)[r.source_landmarks[1]]),
                )
                if path_verts is not None and len(path_verts) >= 2:
                    n = len(path_verts)
                    edges = np.array([[i, i + 1] for i in range(n - 1)])
                    color = [0.2, 0.8, 0.3] if "Apex" in r.name and "Shoulder" in r.name else [0.2, 0.7, 0.7]
                    ps.register_curve_network(
                        f"Geo_{r.name}", path_verts, edges,
                        color=color, radius=0.001,
                    )

    def export_results_to_excel(self, output_path: str):
        import openpyxl

        wb = openpyxl.Workbook()
        ws_lm = wb.active
        ws_lm.title = "Landmarks"
        ws_lm.append(["Name", "X_mm", "Y_mm", "Z_mm", "Type", "Family"])

        for name, pos in self.ss_lm_dict.items():
            ws_lm.append([name, float(pos[0]), float(pos[1]), float(pos[2]), "original", ""])

        for name, info in self.derived_lm_dict.items():
            p = info["position"]
            ws_lm.append([name, float(p[0]), float(p[1]), float(p[2]), "derived", info["family"]])

        ws_m = wb.create_sheet("Measurements")
        ws_m.append(["Family", "Name", "Value_mm", "Value_cm", "Method", "From", "To"])
        for r in self.measurement_results:
            ws_m.append([
                r.family, r.name, round(r.value_mm, 2), round(r.value_mm / 10, 2),
                r.method, r.source_landmarks[0], r.source_landmarks[1],
            ])

        wb.save(output_path)
```

Also add `import pathlib` near the top if not present (check: it's already used by data_loader but not directly imported in geometry_backend).

- [ ] **Step 6: Run integration tests**

Run: `conda run -n FastIKD python -m pytest tests/test_shoulder_behavior.py -v`
Expected: All PASS

- [ ] **Step 7: Commit**

```bash
git add geometry_backend.py tests/test_shoulder_behavior.py
git commit -m "feat: integrate derived landmarks into VisContent with Polyscope registration"
```

---

### Task 7: GUI Panel E — compute button + landmark display

**Files:**
- Modify: `gui_panel.py:59-85` (__init__), `gui_panel.py:130-144` (render), `gui_panel.py:189-196` (subject switch)

- [ ] **Step 1: Add Panel E state variables to `__init__`**

In `gui_panel.py`, after line 85 (`self._geo_preview_key = None`), add:
```python
        # Panel E: Derived Landmarks
        self._derived_computed = False
        self._derived_weights = {}
        self._derived_positions = {}
        self._derived_dirty = set()
        self._measurements_cache = {}
        self._weights_unsaved = False
        self._geo_needs_refresh = False
        self._lock_sum = True
```

- [ ] **Step 2: Add subject-switch reset**

In `gui_panel.py`, after line 196 (`self.color_max_mm = APP_CONFIG.distance.default_color_max_mm`), add:
```python
            self._derived_computed = False
            self._derived_weights = {}
            self._derived_positions = {}
            self._derived_dirty = set()
            self._measurements_cache = {}
            self._weights_unsaved = False
            self._geo_needs_refresh = False
```

- [ ] **Step 3: Register Panel E in render()**

In `gui_panel.py`, after line 144 (`psim.TreePop()` for Panel D), add:
```python
        if psim.TreeNode("E. Derived Landmarks"):
            self._panel_derived()
            psim.TreePop()
```

- [ ] **Step 4: Implement `_panel_derived()` — compute button + display**

Append to the `UI_Menu` class in `gui_panel.py`:
```python
    # --------------------------------------------------------------------------
    # Panel E: Derived Landmarks
    # --------------------------------------------------------------------------

    def _panel_derived(self):
        c = self.content

        can_compute = c.mesh_ss is not None and bool(c.ss_lm_dict)
        if not can_compute:
            _warn("Load SizeStream mesh + landmarks first")
            return

        if psim.Button("Compute / Initialize"):
            try:
                c.compute_derived_landmarks()
                c.compute_shoulder_measurements()
                self._derived_computed = True
                self._derived_weights = {
                    name: list(info["weights"])
                    for name, info in c.derived_lm_dict.items()
                }
                self._derived_positions = {
                    name: info["position"].copy()
                    for name, info in c.derived_lm_dict.items()
                }
                self._measurements_cache = {}
                for r in c.measurement_results:
                    self._measurements_cache.setdefault(r.name, {})[r.method] = r.value_mm
                self._derived_dirty.clear()
                self._weights_unsaved = False
                self._geo_needs_refresh = False
                self._set_status("Derived landmarks computed", "ok")
            except Exception as e:
                self._set_status(f"Derived landmarks failed: {e}", "err")
                return

        if not self._derived_computed:
            return

        # -- Armhole landmarks with sliders --
        psim.Separator()
        psim.TextUnformatted("Armhole")
        for lm_name, info in c.derived_lm_dict.items():
            if info["family"] != "Armhole":
                continue
            if psim.TreeNode(lm_name):
                self._render_landmark_sliders(lm_name, info)
                psim.TreePop()

        # -- Shoulder measurements --
        psim.Separator()
        psim.TextUnformatted("Shoulder Measurements")
        for meas_name, vals in self._measurements_cache.items():
            geo_val = vals.get("geodesic", 0)
            y_val = vals.get("y_projection", 0)
            stale = " *" if self._geo_needs_refresh else ""
            if geo_val > 0:
                _ok(f"{meas_name}: geo {geo_val:.1f}mm  ΔY {y_val:.1f}mm{stale}")
            elif y_val > 0:
                psim.TextUnformatted(f"  {meas_name}: ΔY {y_val:.1f}mm")

        psim.Separator()
        if self._geo_needs_refresh:
            if psim.Button("Refresh Geodesics"):
                self._refresh_geodesics()

        if self._weights_unsaved:
            if psim.Button("Save Weights to YAML"):
                self._save_weights()

        if psim.Button("Export Excel"):
            self._export_excel()

    def _render_landmark_sliders(self, lm_name, info):
        import polyscope.imgui as psim
        from derived_landmarks import from_barycentric, project_to_mesh

        c = self.content
        w = self._derived_weights[lm_name]
        tri_names = info.get("_triangle_names")
        if tri_names is None:
            cfg = c.derived_lm_config["landmarks"][lm_name]
            tri_names = cfg["triangle"]
            info["_triangle_names"] = tri_names

        changed = False
        for i, (label, tri_name) in enumerate(zip(["α", "β", "γ"], tri_names)):
            ch, w[i] = psim.SliderFloat(f"{label} ({tri_name})##{lm_name}{i}", w[i], v_min=-2.0, v_max=2.0)
            if ch:
                changed = True

        _, self._lock_sum = psim.Checkbox(f"Lock α+β+γ=1##{lm_name}", self._lock_sum)

        if changed:
            if self._lock_sum:
                w[2] = 1.0 - w[0] - w[1]
            self._derived_weights[lm_name] = w
            A = np.asarray(c.ss_lm_dict[tri_names[0]])
            B = np.asarray(c.ss_lm_dict[tri_names[1]])
            C = np.asarray(c.ss_lm_dict[tri_names[2]])
            P_bary = from_barycentric(w[0], w[1], w[2], A, B, C)
            P_surface = project_to_mesh(P_bary, c.mesh_ss)
            self._derived_positions[lm_name] = P_surface
            c.derived_lm_dict[lm_name]["position"] = P_surface
            c.derived_lm_dict[lm_name]["weights"] = tuple(w)

            family = info["family"]
            positions = [d["position"] for n, d in c.derived_lm_dict.items() if d["family"] == family]
            ps.register_point_cloud(f"Derived_{family}", np.array(positions),
                                    color=[0.2, 0.4, 0.9], enabled=True, radius=0.003)

            self._update_y_projections()
            self._derived_dirty.add(lm_name)
            self._weights_unsaved = True
            self._geo_needs_refresh = True

        pos = self._derived_positions[lm_name]
        psim.TextUnformatted(f"  Position: [{pos[0]:.1f}, {pos[1]:.1f}, {pos[2]:.1f}]")

    def _update_y_projections(self):
        c = self.content
        combined = dict(c.ss_lm_dict)
        combined.update({n: d["position"] for n, d in c.derived_lm_dict.items()})
        config = c.derived_lm_config
        for meas_name, m_config in config["measurements"].items():
            if m_config.get("also_output_y_projection"):
                pt_a = combined.get(m_config["from"])
                pt_b = combined.get(m_config["to"])
                if pt_a is not None and pt_b is not None:
                    y_proj = abs(float(pt_a[1]) - float(pt_b[1]))
                    self._measurements_cache.setdefault(meas_name, {})["y_projection"] = y_proj
                    self._measurements_cache.setdefault(f"{meas_name}_Y", {})["y_projection"] = y_proj

    def _refresh_geodesics(self):
        c = self.content
        try:
            c.compute_shoulder_measurements()
            self._measurements_cache = {}
            for r in c.measurement_results:
                self._measurements_cache.setdefault(r.name, {})[r.method] = r.value_mm
            self._geo_needs_refresh = False
            self._set_status("Geodesics refreshed", "ok")
        except Exception as e:
            self._set_status(f"Geodesic refresh failed: {e}", "err")

    def _save_weights(self):
        from derived_landmarks import save_weights_to_yaml
        c = self.content
        yaml_path = c._DERIVED_YAML
        try:
            for lm_name in self._derived_dirty:
                w = self._derived_weights[lm_name]
                save_weights_to_yaml(yaml_path, lm_name, w)
            self._derived_dirty.clear()
            self._weights_unsaved = False
            self._set_status("Weights saved to YAML", "ok")
        except Exception as e:
            self._set_status(f"Save failed: {e}", "err")

    def _export_excel(self):
        c = self.content
        if not c.measurement_results:
            self._set_status("No measurements to export", "warn")
            return
        sid = c.current_subject or "unknown"
        out_path = str(PROCESSED_DIR / f"{sid}_v3_results.xlsx")
        try:
            c.export_results_to_excel(out_path)
            self._set_status(f"Exported to {out_path}", "ok")
        except Exception as e:
            self._set_status(f"Export failed: {e}", "err")
```

Also add these imports at the top of `gui_panel.py` (after existing imports):
```python
import numpy as np
import polyscope as ps
from data_loader import PROCESSED_DIR
```

- [ ] **Step 5: Manual test — launch viewer, load subject, click "Compute / Initialize"**

Run: `conda run -n FastIKD python main.py`

Verify:
1. Panel E appears in the sidebar
2. "Compute / Initialize" button works
3. 4 blue Armhole Depth points visible on the mesh
4. Geodesic curves visible (green + cyan)
5. Measurement values shown
6. Sliders move the points in real-time
7. "Save Weights to YAML" persists to `config/derived_landmarks.yaml`
8. "Export Excel" creates file in `processed/`

- [ ] **Step 6: Commit**

```bash
git add gui_panel.py
git commit -m "feat: add Panel E with interactive barycentric sliders and measurements"
```

---

### Task 8: Final integration test + cleanup

**Files:**
- Modify: `tests/test_shoulder_behavior.py` (add export test)

- [ ] **Step 1: Add export test**

Append to `tests/test_shoulder_behavior.py`:
```python
def test_export_to_excel(loaded_content, tmp_path):
    vc = loaded_content
    if not vc.derived_lm_dict:
        vc.compute_derived_landmarks()
    if not vc.measurement_results:
        vc.compute_shoulder_measurements()
    out = str(tmp_path / "test_export.xlsx")
    vc.export_results_to_excel(out)
    import openpyxl
    wb = openpyxl.load_workbook(out)
    assert "Landmarks" in wb.sheetnames
    assert "Measurements" in wb.sheetnames
    ws_lm = wb["Landmarks"]
    assert ws_lm.max_row > 5  # at least some landmarks
    ws_m = wb["Measurements"]
    assert ws_m.max_row > 1  # header + data
```

- [ ] **Step 2: Run full test suite**

Run: `conda run -n FastIKD python -m pytest tests/test_derived_landmarks.py tests/test_shoulder_behavior.py -v`
Expected: All PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_shoulder_behavior.py
git commit -m "test: add export integration test, all shoulder tests passing"
```

---

## Self-Review Checklist

- **Spec coverage:** Section 2 (framework) → Tasks 2-5. Section 3 (YAML) → Task 1. Section 4 (backend) → Task 6. Section 5 (GUI) → Task 7. Section 7 (file changes) → all tasks. Section 8 (testing) → Tasks 2-8. Section 4.1b (reset_subject) → Task 6 Step 4. requirements.txt → Task 1. All spec sections covered.
- **Placeholder scan:** All code blocks contain complete, copy-pasteable code. No "TBD" or "similar to above."
- **Type consistency:** `compute_geodesic` signature matches `geodesic_utils.py:116-119`. `MeasurementRecord` defined once in `derived_landmarks.py`, imported in `geometry_backend.py`. `from_barycentric`/`to_barycentric`/`project_to_mesh` signatures consistent across all tasks. `INIT_METHODS` registry used in both Task 3 (registration) and Task 4 (lookup).
