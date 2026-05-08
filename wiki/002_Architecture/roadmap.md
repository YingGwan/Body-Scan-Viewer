# Roadmap

## UNSET Blockers（需要决策才能推进）

| Item | Location | Why it matters |
|---|---|---|
| Derived landmark 生成规则 | `settled.md` → Derived Landmarks 表 | 切片交线模块的输入契约依赖此定义 |
| 面部匿名化 landmark 对 | `settled.md` → 面部匿名化约定 | 决定哪两个 landmark 用于 fit 圆 |
| 面部匿名化平面定义 | `settled.md` → 面部匿名化约定 | 圆的 fit 方式和投影方式 |
| PyMeshLab 具体 filter | `settled.md` → 面部匿名化约定 | 简化算法选择 |
| 切面定义方式 | `settled.md` → 切面定义约定 | 决定切片模块的数学语义 |
| 围度 (circumference) 公式 | `settled.md` → 度量公式 | 定义后才能实现代码 |
| 弧长 (arc length) 公式 | `settled.md` → 度量公式 | 定义后才能实现代码 |
| SS 与 CAESAR landmark 名称映射 | `settled.md` → Landmark Schema | 当前两套 schema 独立，跨源比较需要 mapping |

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
| Polyscope 可视化 + ImGui UI | `gui_panel.py` | `tests/test_gui_panel_behavior.py` |
| 配置系统（严格 JSON schema） | `config_loader.py` | `tests/test_config_loader.py` |
| PLY 顶点颜色渲染 | `geometry_backend.py` | `tests/test_geometry_backend_behavior.py` |
| Viewer 启动行为 | `main.py` | `tests/test_main_behavior.py` |
| 配准结果导出（PLY + NPY） | `geometry_backend.py` | — |

## 下一步（待用户确认优先级）

1. **面部匿名化** — 需先冻结 `settled.md` 中的匿名化约定
2. **切片** — 需先定义切面约定和 derived landmark 生成规则
3. **扩展度量** — 围度、弧长等物理度量
4. **Landmark mapping** — SS 与 CAESAR 之间的 landmark 名称映射表
