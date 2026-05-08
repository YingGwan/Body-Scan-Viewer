# Measurement Current Contract

last_updated: 2026-05-08

## 当前有效定义

### Phase 1 度量（已实现）
1. **Geodesic distance**: potpourri3d exact / Dijkstra fallback, mm
2. **Landmark Euclidean distance**: trimesh.proximity.closest_point, mm
3. **Per-vertex distance heatmap**: trimesh.proximity.closest_point, mm, color mapped

参考：`settled.md` → 度量公式 → 已实现

### V3 Derived Landmark 度量（已实现 / 部分实现）

配置来源：`config/derived_landmarks.yaml` → `measurements` section (32 条定义)

| 类型 | 数量 | Family | 状态 |
|------|------|--------|------|
| geodesic (Neck) | 8 | Neck | done |
| geodesic (Shoulder) | 4 | Shoulder | done |
| Y-projection (Shoulder) | 4 | Shoulder | done (与 geodesic 一起，由 `also_output_y_projection: true` 触发) |
| arc_length (Waist: WaistArc + BustArc + BustBack) | 10 | Waist | done (引擎已实现，待 subject 数据验证) |
| euclidean (Waist) | 2 | Waist | done (引擎已实现) |
| arc_length (Thigh: Left/Right ×4 quadrant arcs) | 8 | Thigh | done (引擎已实现，待 subject 数据验证) |

参考：`settled.md` → V3 Derived Landmark 度量

### 未实现度量
- Circumference (围度): UNSET

## 变更历史

| 日期 | 变更内容 | 原因 | 影响的下游模块 |
|---|---|---|---|
| 2026-05-08 | 初始记录 | wiki 创建 | — |
| 2026-05-08 | 新增 32 条 V3 度量定义 (所有度量引擎已实现；Waist/Thigh 待跨 subject 数据验证) | V3 phase 2 开发 | geometry_backend, gui_panel, Excel export |

## 待定决策

- [ ] 围度公式定义（依赖切片模块）
- [x] ~~弧长的数学公式定义~~ → Shapely ring.project()/interpolate()
