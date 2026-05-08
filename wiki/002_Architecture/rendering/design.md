# Rendering（可视化）

## 定位

基于 Polyscope + ImGui 的交互式 3D 可视化。提供 MVVM 架构的 View 层（`gui_panel.py:UI_Menu`）和 Model 层的 Polyscope 注册（`geometry_backend.py:VisContent`）。

## 算法语义

### UI 面板结构
- **System**: 扫描结果概览、subject 数量、警告
- **A. Import**: subject 下拉框、文件状态、Load 按钮
- **B. Registration**: ICP 按钮、质量指标、Save 按钮
- **C. Distance**: color range slider、Compare 按钮、统计表
- **D. Geodesic**: landmark slider（实时预览）、Compute 按钮、长度显示

### 设计原则
- Progressive unlock：按钮在前置条件满足前 grayed out
- Subject switch detection：下拉框变化时 reset_subject() 清空全部状态
- ASCII-safe markers：[OK] [!!] [ERR]（无 Unicode 问题）
- Status history：最近 3 条消息可见

### Polyscope 注册结构

| Structure name | Type | 来源 |
|---|---|---|
| SizeStream | surface_mesh | load_sizestream() |
| SS_Landmarks | point_cloud | load_sizestream() |
| CAESAR | surface_mesh | load_caesar() |
| CAESAR_Landmarks | point_cloud | load_caesar() |
| CAESAR_Registered | surface_mesh | run_registration() |
| CAESAR_Landmarks_Registered | point_cloud | run_registration() |
| Distance_to_CAESAR | color_quantity on SizeStream | compare_landmark_distances() |
| Landmark_Errors | curve_network | compare_landmark_distances() |
| Geodesic_Path | curve_network | compute_and_show_geodesic() |
| Geo_Endpoints | point_cloud | show_geodesic_endpoints() |

### CAESAR PLY 顶点颜色
- 自动检测 uchar RGB(A) vertex colors
- 归一化到 [0,1] float
- 作为 `PLY_RGB` color quantity 添加到 surface mesh

## 输入契约

- VisContent 实例（dependency injection）
- APP_CONFIG render/viewer 配置

## 输出契约

- Polyscope 3D 渲染
- ImGui 控制面板
- 用户交互回调

## 正确性标准

- reset_subject() 必须清理所有 known structures
- render config 值必须从 APP_CONFIG 读取（不硬编码）
- Geodesic endpoint preview 在 slider 变化时立即更新

## 已知失败模式

| 失败模式 | 症状 | 防护方式 |
|---|---|---|
| 新增 register 但忘记加到 reset 列表 | subject 切换后残留旧结构 | known_structures 列表 + WARNING 注释 |
| PLY 无 vertex colors | add_color_quantity 失败 | graceful fallback (return None) |

## 当前实现

- 代码路径：`gui_panel.py`, `geometry_backend.py` (Polyscope 注册部分), `config/render_config.json`
- 测试路径：`tests/test_gui_panel_behavior.py`, `tests/test_main_behavior.py`, `tests/test_geometry_backend_behavior.py`

## 状态

- 已完成：完整 Polyscope + ImGui 交互界面
- 待实现：未来模块的 UI 面板扩展

上次更新：2026-05-08
