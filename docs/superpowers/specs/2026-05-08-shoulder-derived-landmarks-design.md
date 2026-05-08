# Shoulder & Derived Landmarks — Design Spec

> Date: 2026-05-08
> Scope: 4 Armhole Depth landmarks + 4 Geodesic curves + generic derived landmark framework + interactive GUI Panel E
> Approach: A (single-file extension + new derived_landmarks.py module)
> Env: conda FastIKD

---

## 1. Overview

Implement the shoulder/armhole functionality from V3, while simultaneously building a reusable derived landmark framework that Neck/Waist modules can later plug into.

**Deliverables:**
- `derived_landmarks.py` — generic framework (YAML loading, barycentric engine, mesh projection, init methods)
- `config/derived_landmarks.yaml` — landmark + measurement definitions (Armhole entries for now)
- `geometry_backend.py` — 3 new methods on VisContent
- `gui_panel.py` — Panel E with interactive weight sliders and real-time measurement updates

**New landmarks (4):**
- ArmholeDepthFrontLeft, ArmholeDepthBackLeft
- ArmholeDepthFrontRight, ArmholeDepthBackRight

**New measurements (8 values from 4 curves):**
- Mid Shoulder Left → ApexBustLeft (geodesic + Y projection)
- Mid Shoulder Right → ApexBustRight (geodesic + Y projection)
- ApexBustLeft → LowerBustLeft (geodesic + Y projection)
- ApexBustRight → LowerBustRight (geodesic + Y projection)

---

## 2. `derived_landmarks.py` — Generic Framework

Stateless pure-function library. No Polyscope or GUI imports.

**Dependency:** Uses `PyYAML` (`yaml.safe_load` / `yaml.safe_dump`) for YAML I/O. PyYAML is already available in FastIKD conda env. Must be added to `requirements.txt`. Does NOT use `config_loader.py` (which is JSON-only); YAML loading is self-contained in this module.

### 2.1 YAML Loading

```python
def load_derived_landmark_config(yaml_path: str | Path) -> dict:
    """
    Load and validate derived_landmarks.yaml using PyYAML.
    Returns the parsed dict with 'landmarks' and 'measurements' sections.
    Raises ValueError on schema violations.
    """
```

Validation: version == 1, each landmark has triangle (list of 3 str), weights (list of 3 float or null), init_method (str), family (str). Each measurement has type, from, to, family. Landmark names in triangle/from/to may contain spaces (e.g., `"Mid Shoulder Left"`) — no identifier format restriction.

### 2.2 Barycentric Engine

```python
def to_barycentric(P: np.ndarray, A: np.ndarray, B: np.ndarray, C: np.ndarray) -> tuple[float, float, float]:
    """
    Compute barycentric coordinates (α, β, γ) such that P ≈ α·A + β·B + γ·C, α+β+γ=1.
    Uses least-squares (3 equations, 2 unknowns: α, β; γ = 1 - α - β).
    Points may be outside the triangle (negative weights allowed).
    """

def from_barycentric(alpha: float, beta: float, gamma: float,
                     A: np.ndarray, B: np.ndarray, C: np.ndarray) -> np.ndarray:
    """Reconstruct 3D point from barycentric coordinates. Returns α·A + β·B + γ·C."""

def project_to_mesh(point: np.ndarray, mesh: trimesh.Trimesh) -> np.ndarray:
    """Project a 3D point to the nearest point on mesh surface.
    Uses trimesh.proximity.closest_point(). Returns the surface point."""
```

### 2.3 Init Methods

Each init method computes an initial 3D position from raw geometry. Signature pattern:

```python
def init_<method>(mesh: trimesh.Trimesh, landmark_dict: dict, params: dict) -> np.ndarray:
```

**`init_contour_z_extremum`** (used for Armhole):
1. Read `params.plane_landmarks` → get 2 landmark positions (e.g., ShoulderLeft, ArmpitLeft)
2. Compute plane: origin = midpoint, normal = cross(shoulder→armpit direction, X-axis), normalized
3. `mesh.section(plane_origin, plane_normal)` → Path3D. If returns `None` (plane misses mesh), raise `ValueError(f"Plane did not intersect mesh for {landmark_name}")`
4. Get largest entity by point count (the body contour, not arm fragments)
5. On that contour, find point with max Z (`extremum: max`) or min Z (`extremum: min`)
6. Return that 3D point

**`init_plane_intersection`** (for future Neck):
1. Two planes defined by landmarks → intersection line
2. `mesh.ray.intersects_location()` along that line
3. Return hit point (filtered by region)

**`init_arc_length_ratio`** (for future Waist):
1. `mesh.section()` → Path3D → `to_planar()` → Shapely Polygon
2. `ring.project()` for start/end landmarks → arc positions
3. `ring.interpolate()` at target ratio → 2D point
4. Transform back to 3D via `to_3d` matrix

**`init_three_plane_intersection`** (for future Waist Dart Front):
1. Three plane normals and origins → solve 3×3 system for intersection point
2. Snap to nearest contour point

Only `init_contour_z_extremum` is implemented in this deliverable. The other three are stubs that raise `NotImplementedError("Planned for Neck/Waist module")`.

### 2.4 Unified Entry Points

```python
def compute_derived_landmark(mesh, landmark_dict, lm_name, lm_config) -> tuple[np.ndarray, tuple[float, float, float]]:
    """
    Compute one derived landmark.
    - If lm_config['weights'] is not None → from_barycentric + project_to_mesh
    - If weights is None → call init_method → project_to_mesh → to_barycentric
    Returns (surface_point, (alpha, beta, gamma)).
    """

def compute_all_derived_landmarks(mesh, landmark_dict, config) -> dict:
    """
    Compute all landmarks in config['landmarks'].
    Returns {name: {'position': np.ndarray, 'weights': (α,β,γ), 'family': str}}.
    """

def save_weights_to_yaml(yaml_path, landmark_name, weights):
    """Update a single landmark's weights in the YAML file.
    Loads full YAML with PyYAML, updates the weights field, writes back with yaml.safe_dump().
    Comments are NOT preserved (PyYAML limitation); acceptable since weights are the only field that changes."""
```

### 2.5 Measurement Computation

```python
def compute_configured_measurements(mesh, landmark_dict, derived_dict, measurements_config,
                                     geodesic_fn) -> list[MeasurementRecord]:
    """
    Compute all measurements defined in config['measurements'].
    - type: geodesic → call geodesic_fn(pt_a, pt_b) → returns (length_mm, path_verts)
    - also_output_y_projection: True → additionally compute |y1 - y2|
    Returns list of MeasurementRecord.
    """

@dataclass
class MeasurementRecord:
    name: str
    family: str
    value_mm: float
    method: str          # "geodesic" | "euclidean" | "y_projection"
    source_landmarks: tuple[str, ...]
```

---

## 3. `config/derived_landmarks.yaml`

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
      plane_constraint: "normal perpendicular to X-axis"
    family: Armhole

  ArmholeDepthBackLeft:
    triangle: [ShoulderLeft, ArmpitLeft, NeckBack]
    weights: null
    init_method: contour_z_extremum
    init_params:
      extremum: min
      plane_landmarks: [ShoulderLeft, ArmpitLeft]
      plane_constraint: "normal perpendicular to X-axis"
    family: Armhole

  ArmholeDepthFrontRight:
    triangle: [ShoulderRight, ArmpitRight, NeckRight]
    weights: null
    init_method: contour_z_extremum
    init_params:
      extremum: max
      plane_landmarks: [ShoulderRight, ArmpitRight]
      plane_constraint: "normal perpendicular to X-axis"
    family: Armhole

  ArmholeDepthBackRight:
    triangle: [ShoulderRight, ArmpitRight, NeckBack]
    weights: null
    init_method: contour_z_extremum
    init_params:
      extremum: min
      plane_landmarks: [ShoulderRight, ArmpitRight]
      plane_constraint: "normal perpendicular to X-axis"
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

---

## 4. `geometry_backend.py` — VisContent Extensions

### 4.1 State Additions

In `_init_state()`:
```python
self.derived_lm_config = None       # loaded YAML config
self.derived_lm_dict = {}           # {name: {'position': ndarray, 'weights': tuple, 'family': str}}
self.measurement_results = []       # list[MeasurementRecord]
```

### 4.1b `reset_subject()` Integration

Add all 7 new Polyscope structure names to `known_structures` in `reset_subject()`:
```python
"Derived_Armhole",
"Armhole_Section_L", "Armhole_Section_R",
"Geo_MidShoulderToApexLeft", "Geo_MidShoulderToApexRight",
"Geo_ApexToLowerBustLeft", "Geo_ApexToLowerBustRight",
```

Also reset derived state:
```python
self.derived_lm_dict = {}
self.measurement_results = []
```

### 4.2 New Methods

```python
def compute_derived_landmarks(self):
    """
    Batch-compute all derived landmarks from YAML config.
    1. Load config (lazy, once)
    2. Build combined landmark_dict: self.ss_lm_dict (original) merged with already-computed derived
    3. Call derived_landmarks.compute_all_derived_landmarks()
    4. Register to Polyscope: one point cloud per family ("Derived_Armhole" etc.)
    5. Store in self.derived_lm_dict
    Pre: self.mesh_ss loaded, self.ss_lm_dict populated.
    """

def compute_shoulder_measurements(self):
    """
    Compute geodesic + Y projection measurements from YAML measurements config.
    1. For each measurement with type=geodesic:
       - Resolve 'from' and 'to' landmark names → 3D positions (from ss_lm_dict or derived_lm_dict)
       - Call compute_geodesic() from geodesic_utils (NOT compute_and_show_geodesic to avoid overwriting Panel D state)
       - Register curve to Polyscope as "Geo_{measurement_name}"
    2. If also_output_y_projection: compute |y1 - y2|
    3. Append MeasurementRecord to self.measurement_results
    Pre: derived landmarks computed, geodesic solver built.
    """

def export_results_to_excel(self, output_path: str):
    """
    Export landmarks + measurements to Excel.
    Sheet "Landmarks": Name, X_mm, Y_mm, Z_mm, Type(original/derived), Family
    Sheet "Measurements": Family, Name, Value_mm, Value_cm, Method, From, To
    Uses openpyxl.
    """
```

### 4.3 Polyscope Registration

| Structure Name | Type | Content | Color | Default |
|---|---|---|---|---|
| `"Derived_Armhole"` | point cloud | 4 armhole depth points | blue `[0.2, 0.4, 0.9]` | enabled |
| `"Armhole_Section_L"` | curve network | left armhole cross-section contour | gray | disabled |
| `"Armhole_Section_R"` | curve network | right armhole cross-section contour | gray | disabled |
| `"Geo_MidShoulderToApexLeft"` | curve network | geodesic path | green `[0.2, 0.8, 0.3]` | enabled |
| `"Geo_MidShoulderToApexRight"` | curve network | geodesic path | green | enabled |
| `"Geo_ApexToLowerBustLeft"` | curve network | geodesic path | cyan `[0.2, 0.7, 0.7]` | enabled |
| `"Geo_ApexToLowerBustRight"` | curve network | geodesic path | cyan | enabled |

---

## 5. `gui_panel.py` — Panel E: Interactive Derived Landmarks

### 5.1 State Variables

```python
# In UI_Menu.__init__()
self._derived_computed = False
self._derived_weights = {}       # {lm_name: [α, β, γ]} — live slider values
self._derived_positions = {}     # {lm_name: np.ndarray(3,)} — current projected positions
self._derived_dirty = set()      # landmark names with modified weights
self._measurements_cache = {}    # {meas_name: {'geodesic': float, 'y_proj': float}}
self._weights_unsaved = False
self._geo_needs_refresh = False  # set True when sliders change; cleared after geodesic recompute
```

**Subject switch reset:** When subject changes (detected in `_panel_import()`), all 7 variables above must be reset to their init values. `_derived_computed = False` hides the slider section until the user clicks "Compute" again.

### 5.2 Layout

```
▼ E. Derived Landmarks
  [Compute / Initialize]                    ← Button, grayed if no mesh/landmarks

  ── Armhole ──
  ▶ ArmholeDepthFrontLeft                  ← TreeNode, expandable
    α (ShoulderLeft)   [====|========] 0.35   ← SliderFloat, range [-2, 2]
    β (ArmpitLeft)     [========|====] 0.55
    γ (NeckLeft)       [=|===========] 0.10
    ☑ Lock α+β+γ=1                          ← Checkbox, default on
    Position: [12.3, 1245.6, -8.9]
    Proj dist: 3.2mm

  ▶ ArmholeDepthBackLeft    (collapsed)
  ▶ ArmholeDepthFrontRight  (collapsed)
  ▶ ArmholeDepthBackRight   (collapsed)

  ── Shoulder Measurements ──
  MidShoulder→Apex L:  geo 245.3mm  ΔY 176.3mm
  MidShoulder→Apex R:  geo 243.1mm  ΔY 163.3mm
  Apex→LowerBust L:    geo  62.9mm  ΔY  62.8mm
  Apex→LowerBust R:    geo  63.5mm  ΔY  71.6mm

  [Refresh Geodesics]                       ← Manual trigger for expensive recompute
  [Save Weights to YAML]  [Export Excel]
  Status: Weights modified (unsaved)
```

### 5.3 Interaction Logic

**Slider change (per-frame):**
1. User drags α slider for ArmholeDepthFrontLeft
2. If "Lock sum=1" is on: γ = 1.0 - α - β (auto-adjust third weight)
3. Call `from_barycentric(α, β, γ, A, B, C)` → P_bary
4. Call `project_to_mesh(P_bary, mesh)` → P_surface
5. Update `self._derived_positions[name]` and Polyscope point cloud
6. Recompute Y-projection measurements instantly (cheap): `|y1 - y2|`
7. Mark `self._geo_needs_refresh = True`
8. Mark `self._weights_unsaved = True`

**"Refresh Geodesics" button (manual):**
1. For each measurement in `_measurements_cache`:
   - Resolve from/to positions (may include derived landmarks with updated positions)
   - Call `compute_geodesic()` → update geodesic value + Polyscope curve
2. Clear `self._geo_needs_refresh`

**"Save Weights to YAML" button:**
1. For each landmark in `_derived_dirty`:
   - Call `derived_landmarks.save_weights_to_yaml(yaml_path, name, weights)`
2. Clear `_derived_dirty` and `_weights_unsaved`
3. Status: "Weights saved"

**"Export Excel" button:**
1. Collect all landmark positions (original + derived) + all measurement results
2. Call `VisContent.export_results_to_excel()`
3. Status: "Exported to {path}"

### 5.4 Performance Budget

| Operation | Cost | Trigger |
|---|---|---|
| `from_barycentric` + `project_to_mesh` | < 1ms | Per-frame (slider drag) |
| Polyscope point cloud update via `ps.register_point_cloud()` re-register | < 2ms | Per-frame (note: re-register, not update-in-place; verify performance is acceptable) |
| Y projection `|y1 - y2|` | < 0.01ms | Per-frame |
| `compute_geodesic` (1 path) | ~50ms | Manual button only |
| `compute_geodesic` (4 paths) | ~200ms | Manual button only |
| YAML write | ~10ms | Manual button only |

All per-frame operations are under 2ms total. Geodesic is manual-trigger only.

---

## 6. Data Flow

```
User clicks "Compute / Initialize"
  │
  ├─ load YAML config (lazy)
  ├─ for each landmark in config:
  │    ├─ weights is null? → init_contour_z_extremum() → P₀
  │    │                     to_barycentric(P₀, A, B, C) → (α, β, γ)
  │    └─ weights exists?  → from_barycentric(α, β, γ, A, B, C) → P_bary
  │                          project_to_mesh(P_bary) → P_surface
  ├─ register Polyscope point clouds
  ├─ compute_shoulder_measurements() → geodesic + Y projection
  ├─ populate Panel E sliders and measurement display
  │
User drags slider
  │
  ├─ from_barycentric → project_to_mesh → update Polyscope + Y measurements (per-frame)
  ├─ geodesic values show "stale" indicator
  │
User clicks "Refresh Geodesics"
  │
  ├─ recompute 4 geodesic paths → update values + Polyscope curves
  │
User clicks "Save Weights to YAML"
  │
  └─ write (α, β, γ) back to config/derived_landmarks.yaml

User switches subject (Panel A)
  │
  ├─ geometry_backend.reset_subject() removes 7 new Polyscope structures
  ├─ gui_panel resets 7 Panel E state variables
  └─ Panel E shows "Compute / Initialize" button (sliders hidden)
```

---

## 7. File Changes Summary

| File | Change |
|---|---|
| **NEW** `derived_landmarks.py` | Generic framework: YAML load, barycentric engine, init methods, measurement compute |
| **NEW** `config/derived_landmarks.yaml` | 4 Armhole landmarks + 4 shoulder measurements |
| **MODIFY** `geometry_backend.py` | Add `_init_state` fields + 3 new methods + extend `reset_subject()` with 7 new structure names |
| **MODIFY** `gui_panel.py` | Add Panel E with sliders, measurements, buttons + subject-switch reset |
| **MODIFY** `requirements.txt` | Add `PyYAML>=6.0` |

No changes to: `data_loader.py`, `registration.py`, `geodesic_utils.py`, `config_loader.py`, `main.py`, `unit_utils.py`, `colorBar.py`.

---

## 8. Testing Strategy

**Unit tests** (`tests/test_derived_landmarks.py`):
- `to_barycentric` / `from_barycentric` roundtrip: P → (α,β,γ) → P' ≈ P
- `from_barycentric` with known weights: midpoint = (0.5, 0.5, 0.0)
- `init_contour_z_extremum` on real mesh: verify returned point has max/min Z on contour
- `compute_all_derived_landmarks` with null weights → weights get populated
- `compute_all_derived_landmarks` with preset weights → positions match expected
- `save_weights_to_yaml` roundtrip: write weights → reload → weights unchanged
- `init_contour_z_extremum` with plane missing mesh → raises `ValueError`

**Integration tests** (`tests/test_shoulder_behavior.py`):
- Load subject → compute derived landmarks → verify 4 Armhole points are on mesh surface (projection dist < 5mm)
- Compute measurements → verify geodesic > 0, Y projection > 0
- Verify cross-subject stability: same weights on 4 subjects produce anatomically plausible positions (Y within armhole range)

**Manual verification:**
- Visual: Polyscope shows Armhole points at correct anatomical positions
- Slider: adjusting weights moves points smoothly, Polyscope updates in real-time
- Save/load: weights persist across sessions

---

## 9. Decisions Log

| Decision | Choice | Rationale |
|---|---|---|
| Z direction | max Z = Front | Confirmed by data: NeckFront Z > NeckBack Z |
| Geodesic output | Both geodesic + Y projection | User request; let collaborator choose which to use |
| Landmark representation | Barycentric coords + YAML | Cross-subject adaptive, tunable, unified |
| Approach | A (extend geometry_backend + new derived_landmarks.py) | Consistent with existing codebase patterns |
| Slider geodesic update | Manual "Refresh" button, not per-frame | Geodesic ~50ms/path, too expensive for 60fps |
| Init method stubs | plane_intersection / arc_length_ratio / three_plane_intersection are NotImplementedError stubs | Scope limited to shoulder; stubs document the interface for Neck/Waist |
| YAML write-back | Save individual landmark weights on button press | User controls when to persist; avoids accidental overwrites |
| YAML library | PyYAML (not ruamel.yaml) | Already in FastIKD env; comments not preserved on write-back is acceptable since only weights change |
| Polyscope point update | `ps.register_point_cloud()` re-register (not in-place update) | Existing codebase pattern; verify < 2ms per-frame is acceptable |
| `mesh.section()` None handling | Raise `ValueError` with landmark name | Fail loud; let caller decide recovery |
