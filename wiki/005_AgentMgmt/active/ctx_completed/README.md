# ctx_completed — Completed Tasks

已完成的任务和决策记录。新条目追加到此目录。

## Phase 1（完成）

- SizeStream/CAESAR 双源查看器 — ICP 配准、landmark 距离比较、geodesic 测量
- 配置系统（project_config.json + render_config.json，严格 JSON schema 验证）
- Polyscope + ImGui 交互界面（Panels A-D）
- 测试覆盖：test_data_loader, test_registration, test_geodesic_utils, test_unit_utils, test_config_loader, test_gui_panel_behavior, test_main_behavior, test_geometry_backend_behavior

## Phase 2（进行中）

### 已完成
- V3 derived landmark 框架：重心坐标参数化 + YAML 配置 + 4 init_methods（全部 done）
- 14 derived landmarks（8 Neck/Armhole done + 6 Waist init_method done，待跨 subject 数据验证）
- 32 条度量定义：12 geodesic + 4 Y-projection + 18 arc_length + 2 euclidean（引擎均已实现）
- GUI Panel E：交互式重心坐标滑块 + Apply/Save/Load/Reset + measurements 显示
- 面部匿名化（Open3D proxy + vertex smoothing + boundary falloff）+ GUI Panel F
- Excel 导出 (`export_results_to_excel`)
- 23 个测试通过（test_derived_landmarks: 19, test_shoulder_behavior: 3, test_face_anonymization: 1）

### 待完成
- 跨 subject 重心坐标稳定性验证
- Waist/Bust dart landmarks 跨 subject 数据验证 + 权重持久化
- Thigh 四段弧长度量
- 统一 Excel 导出规则
