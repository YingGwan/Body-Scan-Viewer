# Data Contracts

本文件记录项目中所有关键数据结构的 schema。
标注 `[CODE]` 表示已在代码中实现；`[PLANNED]` 表示规划中。

## SubjectEntry `[CODE]`

来源：`data_loader.py:SubjectEntry`

- subject_id: str (e.g. "csr0052a")
- ss_obj_path: Optional[pathlib.Path]
- caesar_ply_path: Optional[pathlib.Path]
- caesar_lnd_path: Optional[pathlib.Path]
- has_landmarks: bool
- is_complete: property — `ss_obj_path is not None and caesar_ply_path is not None`
- status_label: property — human-readable label for combo dropdown (e.g. "csr0052a  [SS+CAESAR +LM]")

## DataCatalog `[CODE]`

来源：`data_loader.py:DataCatalog`

- subjects: dict[str, SubjectEntry]
- xlsx_path: Optional[pathlib.Path]
- scan_errors: list[str]
- lm_data: Optional[dict] — output of `load_ss_landmarks()`
- all_ids: property — complete pairs first, then partial

## MeshUnitContext `[CODE]`

来源：`unit_utils.py:MeshUnitContext` (frozen dataclass)

- original_unit: str ("m" | "mm")
- to_mm_scale: float (1000.0 for m, 1.0 for mm)

推断规则：mesh vertex extent max < 10.0 → meters; otherwise → mm

## SS Landmark Data (dict) `[CODE]`

来源：`data_loader.py:load_ss_landmarks()` 返回值

```python
{
    'subject_ids':         list[str],              # e.g. ['csr0052a', ...]
    'col_indices':         list[int],              # XLSX column indices
    'scalar_measurements': dict[str, np.ndarray],  # {name: array(n_subjects)}
    'landmarks_3d':        dict[str, np.ndarray],  # {name: array(n_subjects, 3)}
}
```

## CAESAR Landmark Data (dict) `[CODE]`

来源：`data_loader.py:parse_lnd()` 返回值

```python
{landmark_name: np.array([X, Y, Z])}  # 73 landmarks per subject
```

## CAESAR Landmark Alignment Info (dict) `[CODE]`

来源：`data_loader.py:align_caesar_landmarks_to_mesh()` 返回值的第二元素

```python
{
    'rotation_label': str,            # e.g. "Ry(+90 deg)"
    'rotation_matrix': np.ndarray,    # (3, 3)
    'icp_transform': np.ndarray,      # (4, 4)
    'mean_mesh_error_mm': float,
    'median_mesh_error_mm': float,
    'max_mesh_error_mm': float,
    'fitness': float,
    'rmse': float,
}
```

## AppConfig `[CODE]`

来源：`config_loader.py:AppConfig` (frozen dataclass tree)

```
AppConfig
  ├── version: int (must be 1)
  ├── paths: PathsConfig
  │     ├── data_root: Path
  │     ├── size_stream_dir: Path
  │     ├── caesar_dir: Path
  │     └── processed_dir: Path
  ├── viewer: ViewerConfig
  │     ├── up_dir: str (enum)
  │     ├── ground_plane_mode: str (enum)
  │     ├── transparency_mode: str (enum)
  │     └── transparency_render_passes: int
  ├── render: RenderConfig
  │     ├── sizestream_mesh: MeshRenderConfig
  │     ├── sizestream_landmarks: PointRenderConfig
  │     ├── caesar_mesh: MeshRenderConfig
  │     ├── caesar_landmarks: PointRenderConfig
  │     ├── registered_mesh: MeshRenderConfig
  │     ├── registered_landmarks: PointRenderConfig
  │     ├── landmark_errors: CurveRenderConfig
  │     ├── geodesic_path: CurveRenderConfig
  │     └── geodesic_endpoints: GeodesicEndpointsRenderConfig
  ├── distance: DistanceConfig
  │     ├── default_color_max_mm: float
  │     ├── slider_min_mm: float
  │     └── slider_max_mm: float
  └── registration: RegistrationConfig
        ├── sampling: RegistrationSamplingConfig
        ├── target_normals: RegistrationNormalsConfig
        ├── coarse_icp: ICPStageConfig
        ├── fine_icp: ICPStageConfig
        └── quality: RegistrationQualityConfig
```

## MeasurementRecord `[CODE]`

来源：`derived_landmarks.py:MeasurementRecord` (dataclass)

```python
@dataclass
class MeasurementRecord:
    name: str               # e.g. "NeckFrontLeft_to_NeckFront"
    family: str             # e.g. "Neck", "Shoulder", "Waist", "Thigh"
    value_mm: float         # measured value in mm
    method: str             # "geodesic", "arc_length", "euclidean", "y_projection"
    source_landmarks: tuple # (from_name, to_name)
```

## FaceRegion `[CODE]`

来源：`face_anonymization.py:FaceRegion` (dataclass)

```python
@dataclass
class FaceRegion:
    selected_vertices: np.ndarray   # bool mask (n_vertices,)
    selected_faces: np.ndarray      # bool mask (n_faces,)
    boundary_vertices: np.ndarray   # bool mask (n_vertices,)
```

## FaceAnonymizationResult `[CODE]`

来源：`face_anonymization.py:FaceAnonymizationResult` (dataclass)

```python
@dataclass
class FaceAnonymizationResult:
    mesh: trimesh.Trimesh             # modified mesh (topology unchanged, vertices moved)
    selected_vertices: np.ndarray     # bool mask
    selected_face_count: int
    selected_vertex_count: int
    boundary_vertex_count: int
    proxy_face_count: int             # faces in decimated proxy
    max_displacement_mm: float
    mean_displacement_mm: float
    before_boundary_edges: tuple      # (boundary, nonmanifold) before
    after_boundary_edges: tuple       # (boundary, nonmanifold) after
    before_components: list           # component face counts before
    after_components: list            # component face counts after
```

## DerivedLandmarkConfig (YAML dict) `[CODE]`

来源：`config/derived_landmarks.yaml`，由 `derived_landmarks.py:load_derived_landmark_config()` 加载验证

```yaml
version: 1
landmark_name_map:          # canonical → dataset-specific name mapping
  NeckLeft: "Mid Neck Left"
  ...
landmarks:
  NeckFrontLeft:            # landmark ID
    triangle: [A, B, C]    # 3 reference landmarks for barycentric coords
    weights: [α, β, γ]     # null = use init_method; non-null = use saved weights
    init_method: "plane_intersection"  # registered init method name
    init_params: {...}      # method-specific parameters
    family: "Neck"          # grouping for UI and measurement
measurements:
  MeasurementName:
    type: "geodesic"        # "geodesic" | "arc_length" | "euclidean"
    from: LandmarkA         # source landmark (original or derived)
    to: LandmarkB           # target landmark
    family: "Neck"
    also_output_y_projection: false  # if true, also output |y1-y2|
    plane_landmark: ...     # (arc_length only) landmark defining cut plane
```

## SlicePlane `[PLANNED]`

- landmark_id: which landmark defines this plane
- normal: [nx, ny, nz]
- point_on_plane: [x, y, z]
- convention: references settled 切面定义约定

## CrossSectionContour `[PLANNED]`

- source_plane: SlicePlane reference
- contour_points: ordered list of [x, y, z]
- is_closed: bool
- mesh_id
