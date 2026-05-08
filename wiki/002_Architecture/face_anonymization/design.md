# Face Anonymization（面部匿名化）

> **状态：已实现**
> 使用 Open3D quadric decimation 生成简化 proxy surface，将面部区域顶点平滑至 proxy，保持 mesh 拓扑不变。

## 定位

给定面部 landmark（Chin, Head Circum Front/Right/Left），选定面部区域，用 Open3D 构建简化 proxy，将选中顶点位置平滑混合到 proxy 表面，边界用 smoothstep falloff 过渡。核心不变量：**原 mesh 的 vertices 和 faces 拓扑保持不变**，仅移动选中顶点位置。

## 算法语义

### 1. 面部区域选择 — `select_face_region()`

- 输入 landmark：`Chin`（必需）、`Head Circum Front`（必需）、`Head Circum Right`（必需）、`Head Circum Left`（可选）
- Chin + HCF 中点定义椭圆中心 (center_x, center_y)
- 椭圆半高 = max(|HCF_y - Chin_y|/2 + 12mm, 35mm)；半宽 = max(半高×0.78, 35mm)
- 如有 HCL：半宽 = min(max(|HCL_x - HCR_x|/2 × 0.92, 35mm), 半宽×1.2)
- Z 深度范围：back_z = min(Chin_z, HCR_z) - 18mm，front_z = max(HCF_z, Chin_z) + 12mm
- 选中条件：dx²+dy² ≤ 1.0 **且** back_z ≤ z ≤ front_z（仅正面部区域，不包括后脑）
- 扩展至 connected faces，标记 boundary vertices

### 2. Proxy 构建 — `_build_decimated_proxy()`

- 从选中 face 区域提取子 mesh
- 用 **Open3D `simplify_quadric_decimation()`** 将面片数降至 `target_ratio`（默认 0.05 = 5%）
- 返回简化后的 proxy vertex 位置

### 3. 顶点平滑 — `anonymize_face_open3d()`

- 对选中顶点：构建 proxy surface KDTree，将每个顶点位移向 proxy 最近点混合
- `proxy_strength=0.72`：proxy 混合权重
- `smoothing_iterations=18`, `smoothing_strength=0.38`：迭代邻域 Laplacian 平滑
- `boundary_falloff_mm=35.0`：边界外 smoothstep 衰减，避免硬边

### 4. 拓扑验证

- 匿名化前后比较 `boundary_edge_counts()` 和 `connected_component_face_counts()`
- 结果存入 `FaceAnonymizationResult` 的 `before/after_boundary_edges` 和 `before/after_components`

## 输入契约

- body scan mesh (`trimesh.Trimesh`)
- landmarks (`dict[str, np.ndarray]`)：至少含 Chin, Head Circum Front, Head Circum Right
- target_ratio: float（默认 0.05）
- smoothing/proxy 参数（均有默认值）

## 输出契约

- `FaceAnonymizationResult` dataclass：
  - `mesh`: 修改后的 trimesh.Trimesh（顶点位置已变，拓扑不变）
  - `selected_face_count`, `selected_vertex_count`, `boundary_vertex_count`
  - `proxy_face_count`: proxy 简化后面片数
  - `max_displacement_mm`, `mean_displacement_mm`: 顶点位移统计
  - `before/after_boundary_edges`: (boundary, nonmanifold) 元组
  - `before/after_components`: 连通分量面片数列表

## 正确性标准

- 匿名化后 mesh 拓扑不变（boundary edges、non-manifold edges、components 数量一致）
- 面部特征不可辨识
- 匿名化是不可逆操作；原始 mesh 必须另存
- 不使用 cut-and-stitch（防止拓扑裂缝）

## 已知失败模式

| 失败模式 | 症状 | 防护方式 |
|---|---|---|
| 必需 landmark 缺失 | `KeyError` | `_landmark()` 显式检查 |
| 匿名化区域过大 | 吞掉身体 landmark | landmark 选择约束于面部 |
| proxy 比例过低 | 面部过度平滑 | 默认 target_ratio=0.05 经验值 |
| boundary falloff 过小 | 匿名化边界可见硬边 | 默认 35mm smoothstep |

## 当前实现

- 代码路径：`face_anonymization.py`
- 测试路径：`tests/test_face_anonymization.py`
- GUI 入口：`gui_panel.py:_panel_face_anon()` (Panel F)
- Backend 入口：`geometry_backend.py:anonymize_face()`

## 状态

- 已完成：区域选择、Open3D proxy 简化、顶点平滑、边界 falloff、拓扑验证、GUI Panel F
- 待实现：无

上次更新：2026-05-08
