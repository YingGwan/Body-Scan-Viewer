# Settled Decisions

本文件是项目最重要的真相源。代码输出若与本文件冲突，默认怀疑代码有 bug。
信息未知写 `UNSET`，并在 `roadmap.md` 中列为阻塞项。

## 坐标系

本项目使用唯一坐标系。不做多坐标系管理。

| 属性 | 值 | 来源 |
|------|---|------|
| SizeStream 轴方向 | Y-up（Y=0 在脚部，Y≈1700 在头部） | `render_config.json` → `up_dir: "y_up"` |
| CAESAR 轴方向 | 动态推断（vertex range 最大轴 = up 轴，通常 Z-up） | `data_loader.py:diagnose_coordinate_systems()` |
| 轴对齐方式 | 自动 90 度旋转矩阵，det(R)=+1（proper rotation） | `data_loader.py:build_axis_swap_matrix()` |
| 运行时统一坐标 | 所有几何计算在 mm 下进行 | `unit_utils.py` |
| 原点 | 无全局约定；SizeStream 和 CAESAR 各自原点不同，通过 ICP centroid align 对齐 | `registration.py` |

## 单位

| 属性 | 值 | 来源 |
|------|---|------|
| 运行时单位 | **mm**（毫米） | `unit_utils.py:MeshUnitContext` |
| SizeStream 输入单位 | mm（XLSX 坐标和 OBJ mesh 均为 mm） | 经验观测 + 测试验证 |
| CAESAR 输入单位 | 动态推断：extent < 10.0 → m，否则 → mm | `unit_utils.py:infer_mesh_unit_context()` |
| m → mm 转换因子 | 1000.0 | `unit_utils.py:MeshUnitContext.to_mm_scale` |
| 导出单位 | 恢复为 CAESAR 原始单位（m 或 mm） | `geometry_backend.py:save_registered()` |
| Transform 导出 | 旋转不变，平移除以 `to_mm_scale` | `unit_utils.py:transform_mm_to_original_units()` |

## Landmark Schema

### 原始 Landmarks — SizeStream 来源

| 属性 | 值 |
|------|---|
| 来源文件 | `Extracted SS Measurements and LMs.xlsx`，Sheet1 |
| 格式 | 三行组（name, NaN, NaN）= (X, Y, Z)；单行 = scalar measurement |
| 3D landmark 数量 | ~199 个 |
| Scalar measurement 数量 | ~263 个 |
| Subject 数量 | 4（从 header 行动态发现 `SS_OUT_csr*` 列） |
| 坐标单位 | mm |
| 已验证 landmark | AbdomenBack 等（见 `tests/test_data_loader.py`） |

### 原始 Landmarks — CAESAR 来源

| 属性 | 值 |
|------|---|
| 来源文件 | `csr*.lnd`（每个 subject 一个） |
| 格式 | `idx quality vertex_idx X Y Z value NAME [NAME...]` |
| Landmark 数量 | 73 per subject |
| 多词名称 | 保留（如 `Rt. Infraorbitale`），通过 `' '.join(parts[7:])` |
| 编码 | latin-1 → utf-8 → utf-8-sig fallback |
| 坐标系 | 可能与 PLY mesh 不同轴；通过 24 旋转候选 + ICP 对齐 |
| 对齐方法 | `data_loader.py:align_caesar_landmarks_to_mesh()` — 遍历所有 proper rotation，centroid align + ICP refine，取 mean mesh error 最低者 |

### Derived Landmarks（切片交线计算得出）

| ID | Name | 生成规则 | 依赖的原始 landmarks | 切面定义 |
|---|---|---|---|---|
| — | 尚未定义 | UNSET | UNSET | UNSET |

规则：
- 原始 landmark：只能来自上述两个 schema 表。外部数据的 landmark 必须通过 mapping 表进入。
- Derived landmark：生成规则在本表冻结。修改生成规则 = 新的 landmark ID。
- 不同论文中的同名 landmark 不自动等价。
- SS 和 CAESAR landmark 是两套独立 schema，名称不同，不做自动匹配。

## ICP 配准约定

| 属性 | 默认值 | 来源 | 可配置 |
|------|-------|------|--------|
| 方向 | CAESAR → SizeStream（SizeStream 为固定参考） | `registration.py` | 否（架构决策） |
| Step 1 | 轴旋转对齐（CAESAR up → SS up） | `build_axis_swap_matrix()` | 否（自动检测） |
| Step 2 | Centroid 平移对齐 | `registration.py:run_icp_registration()` | 否（自动计算） |
| Step 3 — Coarse ICP | 150mm 搜索半径，Point-to-Plane，50 iter | `project_config.json → registration.coarse_icp` | **是** |
| Step 4 — Fine ICP | 25mm 搜索半径，Point-to-Plane，100 iter | `project_config.json → registration.fine_icp` | **是** |
| 采样 | 30000 点随机下采样，seed=42 | `project_config.json → registration.sampling` | **是** |
| Target normals | radius=30mm, max_nn=30 | `project_config.json → registration.target_normals` | **是** |
| 质量评级 | fitness<0.1=Failed; RMSE<5mm=Excellent; <15mm=Acceptable | `project_config.json → registration.quality` | **是** |
| Transform 链 | T_total = T_icp @ T_centroid @ T_swap | `registration.py:run_icp_registration()` | 否（数学定义） |

## 面部匿名化约定（未来功能）

| 属性 | 值 |
|------|---|
| 定义圆的 landmark 对 | UNSET |
| 定义圆的平面 | UNSET |
| 圆的 fit 方式 | UNSET |
| 投影方式 | UNSET |
| 简化方法 | PyMeshLab（具体 filter：UNSET） |
| 简化后拓扑要求 | UNSET |

规则（预设）：
- 匿名化区域不得包含下游 pipeline 需要的 landmark。
- 匿名化后的 mesh 必须通过与原 mesh 相同的拓扑检查。
- 匿名化是不可逆操作。原始 mesh 必须保留。

## 切面定义约定（未来功能）

- 切面由什么定义：UNSET
- 切面法向约定：UNSET

## 度量公式

### 已实现

| 度量名称 | 数学定义 | 输入 | 算法 | 单位 |
|---------|---------|------|------|------|
| Geodesic distance | mesh surface 上两点间的最短路径长度 | 两个 3D 点（snap 到最近顶点） | potpourri3d EdgeFlipGeodesicSolver（精确），Dijkstra fallback（近似） | mm |
| Landmark Euclidean distance | SS landmark 到 registered CAESAR surface 的最近点距离 | SS landmark 位置 + registered CAESAR mesh | `trimesh.proximity.closest_point()` | mm |
| Per-vertex distance | SS mesh 每个顶点到 registered CAESAR surface 的最近点距离（热图） | SS mesh vertices + registered CAESAR mesh | `trimesh.proximity.closest_point()` | mm |

### 待定义（未来）

| 度量名称 | 数学定义 | 输入 landmarks | 算法 | 单位 |
|---------|---------|---------------|------|------|
| 围度 (circumference) | UNSET | UNSET | UNSET | UNSET |
| 弧长 (arc length) | UNSET | UNSET | UNSET | UNSET |

规则：
- 每个度量的计算公式必须先在本表定义，代码再实现。
- 代码中的度量计算方式若与本表不一致，以本表为准（怀疑代码有 bug）。
- geodesic distance 和 Euclidean distance 不可混用；度量结果必须声明使用哪个。

## Mesh 拓扑约定

| 属性 | 值 | 来源 |
|------|---|------|
| 输入格式 | SizeStream: OBJ; CAESAR: PLY | `data_loader.py` |
| CAESAR PLY 加载 | `process=False`（保留原始顶点，不自动修复 winding） | `geometry_backend.py:load_caesar()` |
| CAESAR PLY 顶点颜色 | 支持 uchar RGBA，归一化到 [0,1] float | `geometry_backend.py:_extract_mesh_vertex_colors()` |
| 是否要求 manifold | 不强制要求，但 non-manifold 影响 geodesic | `geodesic_utils.py:_clean_edge_flip_faces()` |
| Non-manifold 处理 | geodesic solver 构建时自动清理 duplicate faces 和 >2 face/edge | `geodesic_utils.py` |
| 是否允许 holes | 允许，但 geodesic 在 disconnected component 间返回 inf | `geodesic_utils.py:compute_geodesic()` |
| Face winding | 不强制统一（CAESAR 用 `process=False`） | |
| Normal direction | 无全局约定 | |

## 配置系统约定

| 属性 | 值 |
|------|---|
| 配置分离 | `project_config.json`（数据/算法参数）+ `render_config.json`（视觉外观） |
| Schema 版本 | 两个文件均为 `version: 1` |
| 注释要求 | 每个 key 必须有对应 `key__comment` | `config_loader.py:_require_commented_object()` |
| 验证方式 | 启动时严格 schema 验证，失败即 raise `ConfigError` |
| 路径解析 | 相对路径相对于 `PROJECT_ROOT`（`config_loader.py` 所在目录） |

## 明确不做的事

- 不做多坐标系管理
- 不做 registration / alignment between multiple subjects（当前只做 SS↔CAESAR per subject）
- 不做实验对比框架
- 不做面部重建（未来的匿名化是简化/抹除，不是重建）
- 不做论文写作结构
