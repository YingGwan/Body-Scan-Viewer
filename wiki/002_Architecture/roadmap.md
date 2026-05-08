# Roadmap

## UNSET Blockers（需要决策才能推进）

| Item | Location | Why it matters |
|---|---|---|
| 切面定义方式 | `settled.md` → 切面定义约定 | 决定切片模块的数学语义 |
| 围度 (circumference) 公式 | `settled.md` → 度量公式 | 定义后才能实现代码 |
| SS 与 CAESAR landmark 名称映射 | `settled.md` → Landmark Schema | 当前两套 schema 独立，跨源比较需要 mapping |

## 已解决的原 Blockers

| Item | 解决方式 |
|---|---|
| Derived landmark 生成规则 | 14 landmarks 定义在 `config/derived_landmarks.yaml`，8 已实现 |
| 面部匿名化方法 | 采用 Open3D quadric decimation proxy + boundary falloff（非 PyMeshLab） |
| 面部匿名化 landmark 对 | Chin + Head Circum Front/Right/Left，见 `face_anonymization.py:select_face_region()` |
| 弧长 (arc length) 公式 | 横截面环 Shapely `ring.project()/interpolate()`，已实现 |

## 已完成功能

| 功能 | 模块 | 测试文件 |
|------|------|---------|
| 数据文件夹自动发现 | `data_loader.py` | `tests/test_data_loader.py` |
| XLSX landmark 解析（三行组） | `data_loader.py` | `tests/test_data_loader.py` |
| CAESAR .lnd 解析 + landmark 对齐 | `data_loader.py` | `tests/test_data_loader.py` |
| 单位推断（m/mm） + 运行时归一化 | `unit_utils.py` | `tests/test_unit_utils.py` |
| 坐标系诊断 + 轴旋转矩阵 | `data_loader.py` | `tests/test_data_loader.py`, `tests/test_registration.py` |
| Coarse-to-fine ICP 配准 + 质量评级 | `registration.py` | `tests/test_registration.py` |
| Landmark 距离比较 + 热图 | `geometry_backend.py` | `tests/test_geometry_backend_behavior.py` |
| Geodesic + Non-manifold 清理 | `geodesic_utils.py` | `tests/test_geodesic_utils.py` |
| Polyscope 可视化 + ImGui UI (A-D) | `gui_panel.py` | `tests/test_gui_panel_behavior.py` |
| 配置系统（严格 JSON schema） | `config_loader.py` | `tests/test_config_loader.py` |
| PLY 顶点颜色渲染 | `geometry_backend.py` | `tests/test_geometry_backend_behavior.py` |
| Viewer 启动行为 | `main.py` | `tests/test_main_behavior.py` |
| 配准结果导出（PLY + NPY） | `geometry_backend.py` | — |
| V3 Derived Landmarks 框架 (8 Neck/Armhole) | `derived_landmarks.py` | `tests/test_derived_landmarks.py` |
| V3 YAML 配置 + 重心坐标参数化 | `derived_landmarks.py` | `tests/test_derived_landmarks.py` |
| V3 Neck/Shoulder geodesic (12) + Y-projection (4) | `derived_landmarks.py`, `geometry_backend.py` | `tests/test_shoulder_behavior.py` |
| V3 GUI Panel E (滑块/Apply/Save/Load/Reset) | `gui_panel.py` | — |
| 面部匿名化 (Open3D proxy) | `face_anonymization.py` | `tests/test_face_anonymization.py` |
| GUI Panel F (face anonymization) | `gui_panel.py` | — |
| Excel 导出 | `geometry_backend.py` | `tests/test_shoulder_behavior.py` |

## 下一步（待用户确认优先级）

1. **跨 subject 验证** — 在 4 个 subject 上验证重心坐标稳定性，Save 权重到 YAML
2. **Waist/Bust dart landmarks (6 个)** — init_methods 已实现，需跨 subject 数据验证 + 权重持久化
3. **Thigh 四段弧长** — 弧长引擎已实现，需 subject 数据中 Thigh landmarks 可用
4. **统一 Excel 导出** — 完善坐标导出规则
5. **切片模块** — 需先定义切面约定
6. **Landmark mapping** — SS 与 CAESAR 之间的 landmark 名称映射表
