# System Current State

last_updated: 2026-05-08
current_head: fae0c66
env: conda FastIKD (trimesh 4.11, shapely 2.0.7, rtree 1.4, PyYAML, potpourri3d, polyscope 2.5)

## 项目阶段

**Phase 1 完成**：SizeStream/CAESAR 双源查看器，含 ICP 配准、landmark 距离比较、geodesic 测量。
**Phase 2 进行中**：V3 derived landmarks + 测量 + 重心坐标参数化。

## 代码现状

| 模块 | 文件 | 状态 | 说明 |
|------|------|------|------|
| Entry point | `main.py` | stable | |
| Config loader | `config_loader.py` | stable | JSON-only，不管 YAML |
| **Derived landmarks** | **`derived_landmarks.py`** | **active dev** | 通用框架：YAML 加载、重心坐标、init methods、测量 |
| **Derived config** | **`config/derived_landmarks.yaml`** | **active dev** | 14 landmarks (4 Neck + 4 Armhole + 6 Waist) + 32 measurements |
| Geometry backend | `geometry_backend.py` | **modified** | 新增 Panel E 方法：compute_derived_landmarks, compute_shoulder_measurements, export_results_to_excel |
| GUI panel | `gui_panel.py` | **modified** | 新增 Panel E：交互式重心坐标滑块 + visibility checkboxes + Apply/Save/Load/Reset |
| Data loader | `data_loader.py` | stable | |
| Registration | `registration.py` | stable | |
| Geodesic utils | `geodesic_utils.py` | stable | |
| Unit utils | `unit_utils.py` | stable | |
| Color bar | `colorBar.py` | stable | |
| **Face anonymization** | **`face_anonymization.py`** | **done** | Open3D proxy + vertex smoothing + boundary falloff |

## V3 Derived Landmarks — 当前实现状态

### 架构：重心坐标参数化

所有 derived landmarks 统一用同一模式：
1. 选 3 个已有 landmark 构成参考三角形
2. 用 init_method（几何法）计算初始 3D 位置
3. 反算重心坐标 (α, β, γ)，α + β + γ = 1
4. 投影到 mesh 表面
5. 权重保存到 YAML，跨 subject 复用
6. GUI 滑块可实时微调权重

### 已实现的 landmarks (8)

| Name | Family | init_method | 状态 |
|------|--------|-------------|------|
| NeckFrontLeft | Neck | plane_intersection | done |
| NeckFrontRight | Neck | plane_intersection | done |
| NeckBackLeft | Neck | plane_intersection | done |
| NeckBackRight | Neck | plane_intersection | done |
| ArmholeDepthFrontLeft | Armhole | contour_z_extremum | done |
| ArmholeDepthBackLeft | Armhole | contour_z_extremum | done |
| ArmholeDepthFrontRight | Armhole | contour_z_extremum | done |
| ArmholeDepthBackRight | Armhole | contour_z_extremum | done |

### 已实现的 measurements (12 geodesic + 4 Y projection)

- 8 条 Neck 测地线（每个新 Neck landmark → 它的两个源 landmark）
- 4 条 Shoulder 测地线（MidShoulder→Apex, Apex→LowerBust, 左右各一）
- 4 条 Shoulder Y 投影（同上的纯高度差 |y1-y2|）

### 待实现的 landmarks (V3 剩余)

| Name | Family | init_method | 状态 |
|------|--------|-------------|------|
| WaistDartFrontLeft | Waist | three_plane_intersection | done（待跨 subject 数据验证） |
| WaistDartFrontRight | Waist | three_plane_intersection | done（待数据验证） |
| WaistDartBackLeft | Waist | arc_length_ratio | done（待数据验证） |
| WaistDartBackRight | Waist | arc_length_ratio | done（待数据验证） |
| WaistDartUpperBackLeft | Waist | arc_length_ratio | done（待数据验证） |
| WaistDartUpperBackRight | Waist | arc_length_ratio | done（待数据验证） |

### init_method 实现状态

| Method | 状态 | 用于 |
|--------|------|------|
| `contour_z_extremum` | done | Armhole 4 点 |
| `plane_intersection` | done | Neck 4 点 |
| `arc_length_ratio` | done | Waist Dart Back + Upper Back |
| `three_plane_intersection` | done | Waist Dart Front |

### GUI Panel E 功能

- Compute / Initialize 按钮（一键计算所有 derived landmarks + 测量）
- 3 个 visibility checkbox（全局 landmarks / Neck / Armhole）
- 按 family 折叠的 landmark 列表，每个展开有 α/β/γ 滑块
- 每个 landmark 独立的 [Apply] [Save] [Load] [Reset] 按钮
- 全局 [Apply Weights] [Save to YAML] [Load from YAML] [Reset to Default] [Refresh Geodesics] [Export Excel]
- Measurements 折叠区域显示 geodesic + dY 值

### YAML landmark_name_map

用于跨数据集兼容。当前映射：
```yaml
NeckLeft: "Mid Neck Left"
NeckRight: "Mid Neck Right"
NeckFront: NeckFront
NeckBack: NeckBack
BustWithDropFront: "Bust With Drop Front"
```
config 中使用规范名（如 `NeckLeft`），运行时通过 `resolve_landmark_name()` 映射到数据集实际名称。

## 测试现状

23 个测试，全部通过。运行方式：
```
conda run -n FastIKD python -m pytest tests/test_derived_landmarks.py tests/test_shoulder_behavior.py tests/test_face_anonymization.py -v
```

| 测试文件 | 测试数 | 覆盖 |
|---------|--------|------|
| `tests/test_derived_landmarks.py` | 19 | 重心坐标、YAML I/O、4 init methods、compute_all、measurements、arc_length、three_plane |
| `tests/test_shoulder_behavior.py` | 3 | VisContent 集成、geodesic 测量、Excel 导出 |
| `tests/test_face_anonymization.py` | 1 | Open3D proxy 面部匿名化拓扑保持验证 |

## 数据现状

- 4 个 subject (csr0052a, csr0283a, csr1921a, csr2119a)
- SizeStream: ~199 3D landmarks, ~263 scalar measurements
- CAESAR: 73 landmarks per subject (.lnd)
- 重心坐标在 csr0052a 上已验证，其他 3 个 subject 的 cross-subject 稳定性待验证

## 关键文件路径

| 用途 | 路径 |
|------|------|
| V3 需求文档 | `TODO/1-0508/V3_requirements_guide.md` |
| V3 实施计划 (Rev.3) | `TODO/1-0508/V3_feasibility_analysis.md` |
| Trimesh 实测报告 | `TODO/1-0508/trimesh_intersections_lab_report.md` |
| Shoulder 设计 spec | `docs/superpowers/specs/2026-05-08-shoulder-derived-landmarks-design.md` |
| Shoulder 实施 plan | `docs/superpowers/plans/2026-05-08-shoulder-derived-landmarks.md` |
| Derived landmarks YAML | `config/derived_landmarks.yaml` |
| settled decisions | `wiki/002_Architecture/settled.md` |

## 下一步开发任务

按优先级排序：

1. **跨 subject 验证**：在 4 个 subject 上跑 derived landmarks，检查重心坐标方差，如果稳定则 Save 权重到 YAML
2. **Waist/Bust dart landmarks (6 个)**：init_methods 已实现，需在 4 个 subject 上跑数据验证 + 权重持久化
3. **Thigh 四段弧长**：复用弧长引擎
4. **统一 Excel 导出**：完善 `export_results_to_excel()` 加坐标导出规则（Z(0)=Crotch，仅导出时变换）
5. **统一 Excel 导出**：完善 `export_results_to_excel()` 加坐标导出规则（Z(0)=Crotch，仅导出时变换）

## 已知 bug / 注意事项

- 生产代码使用 `mesh.section()` 而非 `slice_mesh_plane(cap=True)`（后者在 FastIKD 环境中需 `triangle`/`mapbox-earcut`，仅在实验代码 `TODO/` 中出现）
- Polyscope `ps.register_point_cloud()` 是重注册而非 in-place 更新，per-frame 性能 ~2ms，可接受
- `save_weights_to_yaml` 用 PyYAML，不保留 YAML 注释（PyYAML 限制）
- geodesic 计算 ~50ms/条，滑块拖动时只更新位置和 Y 投影，geodesic 需手动点 Refresh
