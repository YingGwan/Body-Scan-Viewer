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

## AnonymizationRegion `[PLANNED]`

- landmark_pair: [landmark_id_1, landmark_id_2]
- plane_normal: [nx, ny, nz]
- fitted_circle_center: [x, y, z]
- fitted_circle_radius
- projection_method: references settled
- pymeshlab_filter: references settled
- pre_anonymization_mesh_id
- post_anonymization_mesh_id
- preserved_landmarks: list of landmark IDs extracted before simplification

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

## MeasurementResult `[PLANNED]`

- measurement_name: references settled 度量公式
- value
- unit
- input_landmarks: list of landmark IDs
- algorithm: references settled
- mesh_id
