# Measurement Current Contract

last_updated: 2026-05-08

## 当前有效定义

### 已实现度量
1. **Geodesic distance**: potpourri3d exact / Dijkstra fallback, mm
2. **Landmark Euclidean distance**: trimesh.proximity.closest_point, mm
3. **Per-vertex distance heatmap**: trimesh.proximity.closest_point, mm, color mapped

参考：`settled.md` → 度量公式 → 已实现

### 未实现度量
- Circumference (围度): UNSET
- Arc length (弧长): UNSET

## 变更历史

| 日期 | 变更内容 | 原因 | 影响的下游模块 |
|---|---|---|---|
| 2026-05-08 | 初始记录 | wiki 创建 | — |

## 待定决策

- [ ] 围度 / 弧长的数学公式定义
- [ ] 是否需要更多度量类型
