# Reader Boot — 快速入门

## 这个项目是什么

一个 Polyscope 桌面 3D 查看器，用于对比分析两个来源的人体扫描数据（SizeStream 和 CAESAR）。

## 核心能力（已实现）

1. **自动数据发现**：扫描文件夹，匹配 subject ID
2. **ICP 配准**：将 CAESAR 扫描刚体配准到 SizeStream 参考空间
3. **距离热图**：每个 SS landmark 到 registered CAESAR 的距离可视化
4. **Geodesic 测量**：mesh 表面上任意两个 landmark 间的最短路径
5. **V3 Derived Landmarks（开发中）**：重心坐标参数化的 derived landmark 框架
   - 8 个已实现：4 Neck（两平面交线法）+ 4 Armhole（截面 Z 极值法）
   - 交互式 GUI 滑块微调 + YAML 持久化
   - 12 条 geodesic 测量 + 4 条 Y 投影

## 5 分钟理解代码

```
python main.py
```

1. `main.py` → 初始化 Polyscope，创建 VisContent（backend）和 UI_Menu（frontend）
2. Backend 自动扫描 `TODO/SORO MADE Garments/` 下的数据文件
3. 用户在 UI 选择 subject → Load SS → Load CAESAR → Run ICP → Compare / Geodesic
4. 所有状态在 `VisContent` 中，切换 subject 时 `reset_subject()` 清空

## 关键设计决策

- **运行时 mm**：所有计算在 mm 下进行（`unit_utils.py`）
- **双配置文件**：`project_config.json`（数据/算法）+ `render_config.json`（视觉）+ `derived_landmarks.yaml`（V3 derived landmarks）
- **CAESAR landmark 自动对齐**：24 旋转候选 + ICP（`align_caesar_landmarks_to_mesh()`）
- **Geodesic 双引擎**：potpourri3d 精确 solver + Dijkstra fallback
- **V3 Derived Landmarks 用重心坐标参数化**：每个 derived landmark = 参考三角形 + (α,β,γ) 权重 + mesh 表面投影。权重在 YAML 持久化，跨 subject 自适应
- **Conda FastIKD 环境**：trimesh + shapely + rtree + PyYAML。所有 Python 命令必须 `conda run -n FastIKD python ...`

## 如何修改

→ 查 `BOOT_MATRIX.md` 确定你的任务需要先读什么文件
→ 查 `settled.md` 了解哪些定义已冻结
→ 查 `ctx_integrity/` 了解哪些规则不能违反
