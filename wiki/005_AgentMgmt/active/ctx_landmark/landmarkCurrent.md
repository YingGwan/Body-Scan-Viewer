# Landmark Current Contract

last_updated: 2026-05-08

## 当前有效定义

### SizeStream Landmarks
- 来源：XLSX 动态解析，~199 个 3D landmarks
- 冻结状态：schema 由 XLSX 文件本身定义（动态发现，非 settled 冻结）
- 参考：`settled.md` → 原始 Landmarks — SizeStream 来源

### CAESAR Landmarks
- 来源：`.lnd` 文件解析，73 个 per subject
- 对齐方式：24 旋转 + ICP（`align_caesar_landmarks_to_mesh`）
- 冻结状态：schema 由 `.lnd` 文件本身定义（动态发现，非 settled 冻结）
- 参考：`settled.md` → 原始 Landmarks — CAESAR 来源

### Derived Landmarks
- 当前状态：**14 个已定义**（8 个已实现，6 个 init_method stub）
- 配置来源：`config/derived_landmarks.yaml`
- 参数化方式：重心坐标（3 reference landmarks → init_method → α,β,γ → mesh surface projection）
- 名称映射：`landmark_name_map`（规范名 → 数据集实际名），由 `derived_landmarks.py:resolve_landmark_name()` 解析
- 代码路径：`derived_landmarks.py`

#### 已实现 (8)

| Name | Family | init_method |
|------|--------|-------------|
| NeckFrontLeft | Neck | plane_intersection |
| NeckFrontRight | Neck | plane_intersection |
| NeckBackLeft | Neck | plane_intersection |
| NeckBackRight | Neck | plane_intersection |
| ArmholeDepthFrontLeft | Armhole | contour_z_extremum |
| ArmholeDepthBackLeft | Armhole | contour_z_extremum |
| ArmholeDepthFrontRight | Armhole | contour_z_extremum |
| ArmholeDepthBackRight | Armhole | contour_z_extremum |

#### 已定义 / init_method done，待跨 subject 数据验证 (6)

| Name | Family | init_method |
|------|--------|-------------|
| WaistDartFrontLeft | Waist | three_plane_intersection |
| WaistDartFrontRight | Waist | three_plane_intersection |
| WaistDartBackLeft | Waist | arc_length_ratio |
| WaistDartBackRight | Waist | arc_length_ratio |
| WaistDartUpperBackLeft | Waist | arc_length_ratio |
| WaistDartUpperBackRight | Waist | arc_length_ratio |

## 变更历史

| 日期 | 变更内容 | 原因 | 影响的下游模块 |
|---|---|---|---|
| 2026-05-08 | 初始记录 | wiki 创建 | — |
| 2026-05-08 | 新增 14 derived landmarks (8 done + 6 init_method done 待数据验证) | V3 phase 2 开发 | geometry_backend, gui_panel, measurements |

## 待定决策

- [ ] 是否需要冻结 SS landmark schema（当前靠 XLSX 动态发现）
- [ ] 是否需要 SS↔CAESAR landmark 名称映射表
- [x] ~~Derived landmark 生成规则定义~~ → 14 landmarks 在 YAML 中定义
