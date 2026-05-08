# Landmark Schema

## 定位

管理两套独立的 landmark 来源（SizeStream XLSX、CAESAR LND），提供 CAESAR landmark 到 mesh 坐标系的自动对齐，以及未来 derived landmark 的定义框架。

## 算法语义

### SizeStream Landmarks
- 从 XLSX 三行组格式解析 ~199 个 3D landmarks + ~263 个 scalar measurements
- 坐标单位：mm，Y-up
- 每个 landmark 有 4 个 subject 的坐标（shape: `(n_subjects, 3)`）

### CAESAR Landmarks
- 从 `.lnd` 解析 73 个 landmarks per subject
- 原始 XYZ 坐标系可能与 PLY mesh 不同轴
- 对齐算法：`align_caesar_landmarks_to_mesh()`
  1. 遍历所有 24 个 proper axis-aligned 旋转（det=+1）
  2. 每个候选：旋转 → centroid 对齐到 mesh center → **Point-to-Point** ICP refine（400mm 搜索半径，80 iter）
  3. 计算 landmark-to-mesh nearest-neighbor 距离
  4. 选择 (mean_error, max_error, rmse) 最小的候选
- 注意：此处使用 **Point-to-Point** ICP（轻量级，仅用于 landmark 对齐），不同于 `registration.py` 中的 **Point-to-Plane** ICP（两阶段，用于 mesh 配准）
- 对齐后 **不** 投影到 mesh 表面（保留真实偏移）

### Derived Landmarks（部分实现）
- 使用统一的重心坐标参数化模式：3 个 reference landmark → init_method → barycentric coords → mesh surface projection
- 配置来源：`config/derived_landmarks.yaml`（14 landmarks: 8 Neck/Armhole done + 6 Waist init_method done，待跨 subject 数据验证）
- 名称映射：`landmark_name_map` 解析规范名到数据集实际名（`derived_landmarks.py:resolve_landmark_name()`）
- 4 个 init_method：`contour_z_extremum`（done）、`plane_intersection`（done）、`arc_length_ratio`（done）、`three_plane_intersection`（done）
- 权重持久化：saved weights 优先于 init_method 重新计算
- 生成规则冻结在 `settled.md`

## 输入契约

- XLSX: `Sheet1`, header 行有 `SS_OUT_csr*` 列
- LND: text file, `idx quality vertex_idx X Y Z value NAME [NAME...]`
- Mesh vertices: np.ndarray (N, 3) for alignment target

## 输出契约

- SS landmarks: `{name: np.ndarray(n_subjects, 3)}`
- CAESAR landmarks: `{name: np.array([x, y, z])}` (aligned to mesh frame)
- Alignment info: rotation_label, rotation_matrix, mean/max mesh error

## 正确性标准

- SS 和 CAESAR landmark 是两套独立 schema，不做自动名称匹配
- CAESAR 对齐使用 proper rotation（det=+1），不使用 reflection
- 对齐后保留真实偏移，不投影到表面
- 多词 landmark 名称完整保留

## 已知失败模式

| 失败模式 | 症状 | 防护方式 |
|---|---|---|
| CAESAR .lnd 轴与 mesh 不同 | landmarks 显示在错误位置 | 24 旋转候选搜索 |
| .lnd 名称截断（空格分割） | "Rt." 单独作为 key | `' '.join(parts[7:])` |
| XLSX 列号变化 | 解析到错误的 subject | 动态列发现（不硬编码） |

## 当前实现

- 代码路径：`data_loader.py` (`load_ss_landmarks`, `parse_lnd`, `align_caesar_landmarks_to_mesh`)
- 测试路径：`tests/test_data_loader.py` (TestLoadSSLandmarks, TestParseLnd)

## 状态

- 已完成：SS XLSX 解析、CAESAR LND 解析、CAESAR landmark 对齐、derived landmark 重心坐标框架（8 Neck/Armhole done + 6 Waist init_method done）
- 待实现：6 Waist landmarks 跨 subject 数据验证 + 权重持久化、SS↔CAESAR 名称映射表

上次更新：2026-05-08
