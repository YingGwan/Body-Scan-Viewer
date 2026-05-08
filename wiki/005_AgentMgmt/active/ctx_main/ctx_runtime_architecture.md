# Runtime Architecture

## Model-View pattern

VisContent (Model) 持有全部可变状态并提供计算方法；UI_Menu (View) 直接调用 Model 方法并渲染 ImGui 面板。无 ViewModel 中间层。

```
main.py (Entry)
  │
  ├── config_loader.py → APP_CONFIG singleton (frozen dataclass tree)
  │     Loads: config/project_config.json + config/render_config.json
  │
  ├── geometry_backend.py → VisContent class (Model)
  │     │  Holds all mutable state
  │     │  Public methods:
  │     │    load_sizestream, load_caesar, run_registration,
  │     │    save_registered, compare_landmark_distances,
  │     │    compute_and_show_geodesic, show_geodesic_endpoints,
  │     │    reset_subject
  │     │
  │     ├── data_loader.py → scan_data_folders, parse XLSX/LND, coordinate diagnosis
  │     ├── unit_utils.py → MeshUnitContext, m↔mm conversion
  │     ├── registration.py → ICP pipeline (uses open3d, Point-to-Plane)
  │     ├── geodesic_utils.py → edge graph, potpourri3d solver, Dijkstra fallback
  │     └── colorBar.py → distance → RGB mapping (piecewise linear: blue→cyan→green→yellow→red)
  │
  └── gui_panel.py → UI_Menu class (View)
        ImGui panels A-D, per-frame callback
```

## 运行时单位

所有内部几何计算在 **mm** 下进行。
CAESAR mesh 在 `load_caesar()` 时立即归一化到 mm。
导出时通过 `from_runtime_mm_vertices()` 还原到原始单位。

## 状态生命周期

1. `VisContent.__init__()`: 扫描文件夹 → DataCatalog
2. `load_sizestream()`: mesh + landmarks + geodesic structures
3. `load_caesar()`: mesh + landmarks (aligned) + unit context
4. `run_registration()`: ICP → registered mesh + transform
5. `compare_landmark_distances()`: distance heatmap
6. `compute_and_show_geodesic()`: surface path
7. `reset_subject()`: 清空全部状态，回到步骤 2

## 配置系统

- `project_config.json`: 数据路径、ICP 参数、距离设置（per dataset）
- `render_config.json`: 视觉外观（shared across datasets）
- 每个 key 必须有 `key__comment`
- 启动时严格 schema 验证
