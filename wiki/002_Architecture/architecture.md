# Architecture

## 当前 Pipeline（已实现）

```mermaid
flowchart TD
  A[Input: SS OBJ + XLSX landmarks<br/>CAESAR PLY + LND landmarks] --> B[Data Discovery<br/>data_loader.scan_data_folders]
  B --> C[Unit Inference<br/>unit_utils.infer_mesh_unit_context]
  C --> D[Coordinate Diagnosis<br/>data_loader.diagnose_coordinate_systems]
  D --> E[ICP Registration<br/>registration.run_icp_registration]
  E --> F[Landmark Distance Comparison<br/>geometry_backend.compare_landmark_distances]
  E --> G[Geodesic Measurement<br/>geodesic_utils.compute_geodesic]
  F --> H[Polyscope Visualization<br/>gui_panel.UI_Menu]
  G --> H
```

## 未来 Pipeline（规划中）

```mermaid
flowchart TD
  A[Input: body scan mesh + original landmarks] --> B[Mesh Preprocessing]
  B --> B2[Face Anonymization]
  B2 --> C[Landmark-Based Slicing]
  C --> D[Slice Intersection → Derived Landmarks]
  D --> E[Measurements: geodesic, circumference, etc.]
  E --> F[Rendering + Physical Quantity Visualization]
```

## 代码架构（Model-View pattern）

```
main.py                    Entry point — Polyscope init + wiring
  ├── config_loader.py     Config singleton (APP_CONFIG)
  ├── geometry_backend.py  Model layer (VisContent class)
  │     ├── data_loader.py       Data discovery + parsing
  │     ├── unit_utils.py        Unit inference + conversion
  │     ├── registration.py      ICP pipeline
  │     ├── geodesic_utils.py    Geodesic computation
  │     └── colorBar.py          Distance-to-color mapping
  └── gui_panel.py         View layer (UI_Menu class)
```

## 模块地图

### Data IO
状态：**已实现**
→ [[data_io/design]]

### Landmark Schema
状态：**已实现**（SS XLSX + CAESAR LND 解析和对齐）
→ [[landmark_schema/design]]

### Unit Management
状态：**已实现**
→ [[unit_management/design]]

### Registration（ICP 配准）
状态：**已实现**
→ [[registration/design]]

### Measurements（度量）
状态：**部分实现**（geodesic + Euclidean distance；围度/弧长待实现）
→ [[measurements/design]]

### Rendering（可视化）
状态：**已实现**（Polyscope + ImGui）
→ [[rendering/design]]

### Mesh Processing（mesh 基础处理）
状态：**部分实现**（non-manifold cleaning for geodesic solver）
→ [[mesh_processing/design]]

### Face Anonymization（面部匿名化）
状态：**未实现 — 规划中**
→ [[face_anonymization/design]]

### Mesh Slicing（切片）
状态：**未实现 — 规划中**
→ [[mesh_slicing/design]]

## 数据流

```
Input: SS OBJ mesh + XLSX landmarks
       CAESAR PLY mesh + LND landmarks
  → data_loader (scan folders, parse XLSX three-row-groups, parse LND)
  → unit_utils (infer m/mm, normalize to runtime mm)
  → data_loader (align CAESAR landmarks to mesh via 24-rotation search + ICP)
  → data_loader (diagnose coordinate systems: detect up-axis)
  → registration (axis swap → centroid → coarse ICP → fine ICP; 参数见 settled.md)
  → geometry_backend (landmark distance: trimesh.proximity.closest_point)
  → geodesic_utils (build edge graph + potpourri3d solver; compute path)
  → colorBar (distance → RGB heatmap)
  → gui_panel (Polyscope ImGui rendering)
Output: 3D visualization + registered PLY + transform NPY
```

## 依赖关系

| 模块 | 依赖库 | 版本 |
|------|--------|------|
| 3D viewer + GUI | polyscope | 2.5.0 |
| Mesh I/O | trimesh | 4.11.0 |
| ICP registration | open3d | 0.19.0 |
| Geodesic solver | potpourri3d | 1.3 |
| Landmark data | pandas + openpyxl | 2.3.3 + 3.1.5 |
| Numerical / spatial | numpy + scipy | 1.26.4 + 1.13.1 |
| Color mapping | matplotlib | 3.9.4 |
| Python | | 3.9.x |
