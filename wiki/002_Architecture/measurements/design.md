# Measurements（度量）

## 定位

计算 mesh 上各种物理度量：geodesic distance、landmark Euclidean distance、per-vertex distance heatmap、V3 derived landmark 度量（Neck/Shoulder geodesic、Y-projection、arc length、3D Euclidean）。

## 算法语义

### Geodesic Distance（已实现）
1. 输入两个 3D 点，snap 到 mesh 最近顶点（KDTree）
2. 优先使用 potpourri3d `EdgeFlipGeodesicSolver`（精确连续表面路径）
3. Fallback: Dijkstra on mesh edge graph（边权 = Euclidean 边长）
4. 返回路径长度 (mm) + 路径顶点序列
5. Disconnected components → 返回 `inf`

### Landmark Euclidean Distance（已实现）
- SS landmark → registered CAESAR surface 最近点距离
- 使用 `trimesh.proximity.closest_point()`

### Per-vertex Distance Heatmap（已实现）
- SS mesh 每个顶点 → registered CAESAR surface 最近点距离
- 通过 `colorBar._changeValueToColor(maxValue, minValue, value)` 映射为 RGB
- 颜色映射算法：4 段分段线性插值（blue→cyan→green→yellow→red），将 [minValue, maxValue] 归一化到 [0,1] 后按 0.25 分段
- Color max 由 UI slider 控制

### V3 Neck Geodesic (×8)（已实现）
- 每个 derived Neck landmark → 其两个源 original landmark 之间的 mesh surface 最短路径
- 使用同一 `geodesic_utils.compute_geodesic()` 引擎
- 配置来源：`config/derived_landmarks.yaml` → `measurements` (type: geodesic, family: Neck)

### V3 Shoulder Geodesic (×4)（已实现）
- MidShoulder → Apex, Apex → LowerBust（左右各一）
- 配置来源：`config/derived_landmarks.yaml` → `measurements` (type: geodesic, family: Shoulder)

### V3 Y-Projection Distance (×4)（已实现）
- `|y1 - y2|`：两 landmark 间的纯高度差
- 由 `also_output_y_projection: true` 标志触发，与对应 geodesic 一起计算
- 算法：`abs(pt_a[1] - pt_b[1])` （Y 轴坐标差绝对值）

### V3 Arc Length (Waist ×10 + Thigh ×8)（已实现）
- 横截面环上两点间的弧长
- 算法：`plane_landmark` 定义横截面 → `mesh.section()` → Shapely `ring.project()` / `ring.length` 差
- 配置来源：`config/derived_landmarks.yaml` → `measurements` (type: arc_length)
- 18 条弧长度量：Waist family (WaistArcA L/R + WaistArcB L/R + BustArcC L/R + BustArcD L/R + BustBack L/R = 10) + Thigh family (Left ×4 quadrant + Right ×4 quadrant = 8)

### V3 3D Euclidean (×2)（已实现）
- 两 landmark 的 3D 直线距离：`np.linalg.norm(p1 - p2)`
- 配置来源：`config/derived_landmarks.yaml` → `measurements` (type: euclidean)

### 围度 (Circumference)（规划中）
- 截面轮廓完整周长
- 依赖切片模块产生的截面轮廓
- 公式定义见 `settled.md` → 度量公式（当前 UNSET）

## 输入契约

- Geodesic: mesh edge graph (csr_matrix) + mesh vertices + 两个 3D 点
- Distance: SS landmarks (N,3) + registered CAESAR mesh
- V3 measurements: `config/derived_landmarks.yaml` measurements config + derived landmark positions + geodesic function

## 输出契约

- Geodesic: (length_mm: float, path_vertices: np.ndarray or None)
- Landmark distance: np.ndarray (N,) per-landmark distances in mm
- Per-vertex: colors registered to Polyscope
- V3 measurements: `list[MeasurementRecord]` — each has name, family, value_mm, method, source_landmarks

## 正确性标准

- geodesic distance >= Euclidean distance（三角不等式）
- 同一点 geodesic = 0.0
- Dijkstra 和 exact solver 在 edge-only path 上应一致
- 度量结果必须声明类型：geodesic / euclidean / arc_length / y_projection
- Y-projection distance 与 geodesic 独立计算，不可替代

## 已知失败模式

| 失败模式 | 症状 | 防护方式 |
|---|---|---|
| Non-manifold edges | potpourri3d solver 构建失败 | `_clean_edge_flip_faces()` 自动清理 |
| Mesh holes | geodesic 返回 inf | 显式报告 "No connected path" |
| potpourri3d 未安装 | 精确 solver 不可用 | Dijkstra fallback |
| Color max 设置过低 | 热图全红 | UI slider 可调 (1-100mm) |
| Geodesic 计算延迟 | 滑块拖动时卡顿 (~50ms/条) | GUI 分离：滑块只更新位置+Y投影，geodesic 需手动 Refresh |

## 当前实现

- 代码路径：`geodesic_utils.py`, `geometry_backend.py:compare_landmark_distances()`, `geometry_backend.py:compute_shoulder_measurements()`, `derived_landmarks.py:compute_configured_measurements()`, `colorBar.py`
- 测试路径：`tests/test_geodesic_utils.py`, `tests/test_derived_landmarks.py`, `tests/test_shoulder_behavior.py`

## 状态

- 已完成：geodesic distance、landmark Euclidean distance、per-vertex heatmap、V3 Neck/Shoulder geodesic (12)、Y-projection (4)、arc length (18)、3D Euclidean (2)
- 待定义：围度 (circumference)

上次更新：2026-05-08
