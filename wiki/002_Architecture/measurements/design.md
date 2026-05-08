# Measurements（度量）

## 定位

计算 mesh 上各种物理度量：geodesic distance、landmark Euclidean distance、per-vertex distance heatmap。未来扩展围度 (circumference)、弧长 (arc length) 等。

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

### 围度 / 弧长（规划中）
- 依赖切片模块产生的截面轮廓
- 公式定义见 `settled.md` → 度量公式（当前 UNSET）

## 输入契约

- Geodesic: mesh edge graph (csr_matrix) + mesh vertices + 两个 3D 点
- Distance: SS landmarks (N,3) + registered CAESAR mesh

## 输出契约

- Geodesic: (length_mm: float, path_vertices: np.ndarray or None)
- Landmark distance: np.ndarray (N,) per-landmark distances in mm
- Per-vertex: colors registered to Polyscope

## 正确性标准

- geodesic distance >= Euclidean distance（三角不等式）
- 同一点 geodesic = 0.0
- Dijkstra 和 exact solver 在 edge-only path 上应一致
- 度量结果必须声明使用 geodesic 还是 Euclidean

## 已知失败模式

| 失败模式 | 症状 | 防护方式 |
|---|---|---|
| Non-manifold edges | potpourri3d solver 构建失败 | `_clean_edge_flip_faces()` 自动清理 |
| Mesh holes | geodesic 返回 inf | 显式报告 "No connected path" |
| potpourri3d 未安装 | 精确 solver 不可用 | Dijkstra fallback |
| Color max 设置过低 | 热图全红 | UI slider 可调 (1-100mm) |

## 当前实现

- 代码路径：`geodesic_utils.py`, `geometry_backend.py:compare_landmark_distances()`, `colorBar.py`
- 测试路径：`tests/test_geodesic_utils.py`

## 状态

- 已完成：geodesic distance、landmark Euclidean distance、per-vertex heatmap
- 待实现：围度 (circumference)、弧长 (arc length)

上次更新：2026-05-08
