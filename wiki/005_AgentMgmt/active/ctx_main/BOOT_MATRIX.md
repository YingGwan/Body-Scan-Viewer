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
| V3 Derived Landmarks 开发 | `ctx_system_current`; `config/derived_landmarks.yaml`; `derived_landmarks.py` | `TODO/1-0508/V3_requirements_guide.md`; `TODO/1-0508/V3_feasibility_analysis.md` |
| 新增 Derived Landmark | `derived_landmarks.py` INIT_METHODS; `config/derived_landmarks.yaml` | `docs/superpowers/specs/2026-05-08-shoulder-derived-landmarks-design.md` |
| 新增 init_method | `derived_landmarks.py` 现有 init methods 签名 | `TODO/1-0508/trimesh_intersections_lab_report.md` |
| Waist/Bust dart 开发 | `ctx_system_current` 待实现表; `settled.md` 度量公式 | `TODO/1-0508/V3_requirements_guide.md` Section 2 |
| 重心坐标微调 | `gui_panel.py` Panel E; `config/derived_landmarks.yaml` | `derived_landmarks.py` from_barycentric/to_barycentric |
| Docs audit | `TRUTH_LADDER` | all active ctx + architecture docs |
