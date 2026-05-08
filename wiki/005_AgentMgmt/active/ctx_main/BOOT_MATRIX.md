# Boot Matrix

| Task | Must read first | Then read |
|---|---|---|
| Onboarding | `GLOSSARY`; `settled.md`; `ctx_system_current` | `architecture.md`; `readerBoot` |
| Landmark 定义 / 解析 | `landmarkIntegrityRule`; `settled.md` Landmark Schema | `landmark_schema/design` |
| ICP 配准开发 | `settled.md` ICP 配准约定; `meshTopologyIntegrityRule` | `registration/design`; `unit_management/design` |
| 单位管理 | `settled.md` 单位; `measurementIntegrityRule` | `unit_management/design` |
| 面部匿名化开发 | `anonymizationIntegrityRule`; `meshTopologyIntegrityRule`; `settled.md` 匿名化约定 | `face_anonymization/design`; `landmark_schema/design` |
| 切片算法开发 | `landmarkIntegrityRule`; `meshTopologyIntegrityRule` | `mesh_slicing/design`; `landmark_schema/design` |
| 度量算法开发 | `measurementIntegrityRule`; `settled.md` 度量公式 | `measurements/design`; `data_contracts.md` |
| 渲染开发 | `measurementIntegrityRule`; `rendering/design` | `data_contracts.md` |
| Mesh 处理 | `meshTopologyIntegrityRule` | `mesh_processing/design` |
| 数据 IO | `data_io/design`; `data_contracts.md` | `settled.md` 格式约定 |
| 添加 Config 参数 | `_how_to_use.md` "添加 Config 参数" 章节 | `config_loader.py`; `data_contracts.md` |
| 添加 UI 面板 | `rendering/design.md` Polyscope 结构表 | `gui_panel.py`; `geometry_backend.py` |
| 添加新 Polyscope 结构 | `rendering/design.md` 结构表; `geometry_backend.py:reset_subject()` known list | `gui_panel.py` |
| 添加新测试 | `tests/` 目录现有测试参考 | 对应模块的 `design.md` |
| 修改 Color 映射 | `measurements/design.md`; `colorBar.py` | `geometry_backend.py` |
| Docs audit | `TRUTH_LADDER` | all active ctx + architecture docs |
