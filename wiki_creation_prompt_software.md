# Body Scan Landmark + Mesh 计算框架 — Wiki 创建 Prompt

> 目标：让 AI agent 为一个 body scan landmark 处理与度量计算框架创建 Obsidian wiki。
> 项目不写论文、不做实验对比、不做多坐标系管理。
> 核心 pipeline：mesh + landmarks → 面部匿名化 → 切片 → 切片交线 → derived landmarks → geodesic distance / 度量 → 渲染物理量。

---

## 0. 你是谁

你是一个 wiki 架构创建 agent。你的任务不是写算法代码，而是创建一套能支持后续算法开发、调试和 AI 协作的 Obsidian wiki。

你要创建的 wiki 面向：

- body scan mesh 上的 landmark 定义（原始 landmark + 切片交线派生 landmark）
- 面部匿名化（landmark + 平面 → fit 圆 → 投影到 mesh → PyMeshLab 简化区域三角面片）
- 基于 landmark 的平面切片和切片间交线计算
- landmark 之间的 geodesic distance 和其他物理度量
- mesh 渲染与物理量可视化提取
- mesh 清洗、法向、拓扑等基础处理

你必须遵守：

- **不创建** `003_Experiments/`、`004_Paper/`。本项目无实验对比框架，无论文写作结构。
- 坐标系只有一个，不需要坐标系管理模块或多坐标系 transform 规则。
- 所有会导致静默错误的约定必须优先冻结：landmark 定义（原始+派生）、单位、mesh 拓扑、度量公式定义。
- 如果信息未知，不要编造；写成 `UNSET`，并在 `roadmap.md` 中列为阻塞项。

---

## 1. 项目本质与 wiki 设计逻辑

### 这个项目在做什么

输入是 body scan mesh 和一组已知 landmarks。项目要做的是：

1. **面部匿名化**：给定两个 landmark 和一个平面，fit 一个圆，将圆投影到 mesh 面部区域，用 PyMeshLab 简化该区域内的三角面片，抹去面部特征
2. **切片**：在指定 landmark 处定义切面，用该平面切 mesh，得到截面轮廓（cross-section contour）
3. **交线**：两个切片的交线（或交线与 mesh 表面的交点）产生新的 **derived landmark**
4. **度量**：指定若干 landmarks（原始或派生），计算它们之间的 geodesic distance、围度（circumference）、弧长等物理量
5. **渲染**：将 mesh、landmarks、切片、度量结果可视化，用于验证和提取物理量

### 最危险的错误类型

本项目的最大风险是**静默错误**：pipeline 正常跑完，数字看起来合理，但：

- landmark 定义不对（同名不同义，或 derived landmark 的生成规则改了但下游没更新）
- 匿名化区域定义错误（圆的 fit 用了错误的 landmark 对、投影方向反了、区域过大吞掉身体 landmark）
- 匿名化后 mesh 拓扑破坏（简化引入 non-manifold edges，导致下游切片/geodesic 失败）
- 切片平面的法向或位置参数不一致
- geodesic distance 算法在 mesh 拓扑有洞/非 manifold 时静默返回错误值
- 度量公式在不同地方实现方式不一致
- 渲染时的单位与计算时的单位不匹配

### 由此推导的 wiki 重点

| wiki 部分 | 核心关切 |
|-----------|---------|
| `settled.md` | 冻结：坐标系（唯一）、单位、landmark schema（原始+派生）、mesh 拓扑要求、度量公式 |
| 模块 `design.md` | 每个算法步骤的数学语义和输入输出契约 |
| `ctx_integrity/` | 防护静默错误：landmark 一致性、mesh 拓扑不变量、度量公式唯一性 |
| `005_AgentMgmt/` | agent boot + 冲突裁定 |

---

## 2. 设计原则

### 原则一：单一入口

每次工作从 `wiki/PROJECT.md` 开始。

### 原则二：定义先于实现

Landmark schema（含派生规则）、单位、mesh 要求、度量公式的定义必须先于代码实现。

### 原则三：正确性规则独立成层

`ctx_integrity/` 记录会导致静默错误的规则。

### 原则四：历史保留

被替代的算法和设计进入 `_archive/` 或 `_historical/`，不删除。

---

## 3. 目录结构

```text
wiki/
│
├── PROJECT.md
│
├── 001_Inbox/
│   └── .gitkeep
│
├── 002_Architecture/
│   ├── architecture.md              ← pipeline + 模块地图
│   ├── settled.md                   ← 冻结定义：坐标系、单位、landmarks、mesh、度量
│   ├── roadmap.md                   ← 缺口 + 阻塞 + 下一步
│   ├── data_contracts.md            ← 数据对象 schema
│   │
│   ├── discussion/
│   │   └── .gitkeep
│   │
│   ├── landmark_schema/             ← 原始 + 派生 landmark 定义
│   │   ├── design.md
│   │   └── discussion/
│   │       └── .gitkeep
│   │
│   ├── face_anonymization/          ← landmark+平面→fit圆→投影→PyMeshLab简化
│   │   ├── design.md
│   │   └── discussion/
│   │       └── .gitkeep
│   │
│   ├── mesh_slicing/                ← 平面切片 + 切片交线 → derived landmark
│   │   ├── design.md
│   │   └── discussion/
│   │       └── .gitkeep
│   │
│   ├── measurements/                ← geodesic distance、围度、弧长等度量
│   │   ├── design.md
│   │   └── discussion/
│   │       └── .gitkeep
│   │
│   ├── rendering/                   ← 可视化 + 物理量渲染提取
│   │   ├── design.md
│   │   └── discussion/
│   │       └── .gitkeep
│   │
│   ├── mesh_processing/             ← mesh 清洗、法向、拓扑基础处理
│   │   ├── design.md
│   │   └── discussion/
│   │       └── .gitkeep
│   │
│   ├── data_io/                     ← 输入输出格式
│   │   ├── design.md
│   │   └── discussion/
│   │       └── .gitkeep
│   │
│   └── _archive/
│       └── README.md
│
├── 005_AgentMgmt/
│   ├── INDEX.md
│   ├── _how_to_use.md
│   │
│   ├── active/
│   │   ├── ctx_main/
│   │   │   ├── README.md
│   │   │   ├── ctx_system_current.md
│   │   │   ├── ctx_runtime_architecture.md
│   │   │   ├── BOOT_MATRIX.md
│   │   │   ├── TRUTH_LADDER.md
│   │   │   ├── GLOSSARY.md
│   │   │   └── readerBoot.md
│   │   │
│   │   ├── ctx_integrity/
│   │   │   ├── README.md
│   │   │   ├── landmarkIntegrityRule.md
│   │   │   ├── anonymizationIntegrityRule.md
│   │   │   ├── meshTopologyIntegrityRule.md
│   │   │   └── measurementIntegrityRule.md
│   │   │
│   │   ├── ctx_landmark/
│   │   │   ├── README.md
│   │   │   └── landmarkCurrent.md
│   │   │
│   │   ├── ctx_measurement/
│   │   │   ├── README.md
│   │   │   └── measurementCurrent.md
│   │   │
│   │   └── ctx_completed/
│   │       └── README.md
│   │
│   └── _historical/
│       └── README.md
│
└── _templates/
    ├── discussion.md
    ├── module_design.md
    ├── integrity_rule.md
    └── current_contract.md
```

不要创建：

```text
wiki/003_Experiments/
wiki/004_Paper/
wiki/002_Architecture/coordinate_systems/
wiki/002_Architecture/registration/
wiki/002_Architecture/evaluation/
```

---

## 4. 文件职责与初始内容

### 4.1 `PROJECT.md`

```markdown
# Project: Body Scan Landmark + Measurement Framework

## 一句话
在 body scan mesh 上定义/派生 landmarks，执行切片与交线计算，
求 geodesic distance 等物理度量，渲染可视化验证结果。

## 当前状态
- 已完成：UNSET
- 进行中：UNSET
- 阻塞：landmark schema 是否已冻结、度量公式是否已定义
- 下一步：[[002_Architecture/roadmap]]

## Pipeline

→ [[002_Architecture/architecture]]

​```mermaid
flowchart LR
  A[Body scan mesh + landmarks] --> B[Mesh preprocessing]
  B --> B2[Face anonymization]
  B2 --> C[Landmark-based slicing]
  C --> D[Slice intersection → derived landmarks]
  D --> E[Geodesic distance / measurements]
  E --> F[Rendering + physical quantity extraction]
​```

## 已定论
→ [[002_Architecture/settled]]

## Agent Boot
→ [[005_AgentMgmt/INDEX]]
```

### 4.2 `002_Architecture/settled.md`

项目最重要的文件。信息未知写 `UNSET`。

```markdown
# Settled Decisions

## 坐标系
本项目使用唯一坐标系。不做多坐标系管理。

| 属性 | 值 |
|------|---|
| 轴方向 | UNSET |
| 原点 | UNSET |
| 单位 | UNSET（mm / m） |
| 法向约定 | UNSET（朝外 / 朝内） |

## Landmark Schema

### 原始 Landmarks（来自输入数据）

| ID | Name | Side | Anatomical definition | Source |
|---|---|---|---|---|
| UNSET | UNSET | L/R/Midline | UNSET | UNSET |

### Derived Landmarks（切片交线计算得出）

| ID | Name | 生成规则 | 依赖的原始 landmarks | 切面定义 |
|---|---|---|---|---|
| UNSET | UNSET | UNSET | UNSET | UNSET |

规则：
- 原始 landmark：只能来自本表。外部数据的 landmark 必须通过 mapping 表进入。
- Derived landmark：生成规则在本表冻结。修改生成规则 = 新的 landmark ID。
- 不同论文中的同名 landmark 不自动等价。

## 面部匿名化约定

| 属性 | 值 |
|------|---|
| 定义圆的 landmark 对 | UNSET（哪两个 landmark） |
| 定义圆的平面 | UNSET（过哪些点 / 法向如何确定） |
| 圆的 fit 方式 | UNSET（最小二乘 / 经过两点+平面约束 / ...） |
| 投影方式 | UNSET（沿法向投影到 mesh / 最近点投影 / ...） |
| 简化方法 | PyMeshLab（具体 filter：UNSET） |
| 简化后拓扑要求 | UNSET（必须 manifold / 允许 boundary edges / ...） |

规则：
- 匿名化区域不得包含下游 pipeline 需要的 landmark。若某个 landmark 落在匿名化区域内，必须在匿名化前提取并保留其坐标。
- 匿名化后的 mesh 必须通过与原 mesh 相同的拓扑检查（manifold、无 holes 等）。
- 匿名化是不可逆操作。原始 mesh 必须保留，匿名化 mesh 另存。

## 切面定义约定
- 切面由什么定义：UNSET（过某 landmark 的某方向平面 / 两点连线的垂直平面 / ...）
- 切面法向约定：UNSET

## 度量公式

| 度量名称 | 数学定义 | 输入 landmarks | 算法 | 单位 |
|---------|---------|---------------|------|------|
| UNSET | UNSET | UNSET | UNSET | UNSET |

规则：
- 每个度量的计算公式必须先在本表定义，代码再实现。
- 代码中的度量计算方式若与本表不一致，以本表为准（怀疑代码有 bug）。

## Mesh 拓扑约定
- 格式：UNSET
- 是否要求 manifold：UNSET
- 是否允许 holes：UNSET
- 是否允许 disconnected components：UNSET
- Face winding：UNSET
- Normal direction：UNSET

## 明确不做的事
- 不做多坐标系管理
- 不做 registration / alignment
- 不做实验对比框架
- 不做面部重建（匿名化是简化/抹除，不是重建）
```

### 4.3 `002_Architecture/architecture.md`

```markdown
# Architecture

## Pipeline

​```mermaid
flowchart TD
  A[Input: body scan mesh + original landmarks] --> B[Mesh Preprocessing]
  B --> B2[Face Anonymization]
  B2 --> C[Landmark-Based Slicing]
  C --> D[Slice Intersection → Derived Landmarks]
  D --> E[Measurements: geodesic, circumference, etc.]
  E --> F[Rendering + Physical Quantity Visualization]
​```

## 模块地图

### Mesh Preprocessing
状态：UNSET
→ [[mesh_processing/design]]

### Landmark Schema
状态：UNSET
→ [[landmark_schema/design]]

### Face Anonymization
状态：UNSET
→ [[face_anonymization/design]]

### Mesh Slicing
状态：UNSET
→ [[mesh_slicing/design]]

### Measurements
状态：UNSET
→ [[measurements/design]]

### Rendering
状态：UNSET
→ [[rendering/design]]

### Data IO
状态：UNSET
→ [[data_io/design]]

## 数据流

Input mesh + landmarks
  → mesh_processing (清洗、法向修复)
  → landmark_schema (验证 + 查表)
  → face_anonymization (landmark+平面→fit圆→投影→PyMeshLab简化面部区域)
  → mesh_slicing (在 landmark 处定义平面、切 mesh、得截面轮廓)
  → mesh_slicing (两个截面的交线 → derived landmark 坐标)
  → measurements (geodesic distance / 围度 / 弧长)
  → rendering (3D 可视化 + 度量标注 + 物理量提取)
```

### 4.4 `002_Architecture/data_contracts.md`

```markdown
# Data Contracts

## MeshRecord
- mesh_id
- source
- file_path
- vertex_unit
- vertex_count
- face_count
- is_manifold
- has_holes
- preprocessing_applied

## LandmarkSet
- landmarks: list[Landmark]
  - id: settled schema ID
  - name
  - position_3d: [x, y, z]
  - type: original / derived
  - generation_rule: (only for derived, references settled table)
  - confidence / status

## AnonymizationRegion
- landmark_pair: [landmark_id_1, landmark_id_2]
- plane_normal: [nx, ny, nz]
- fitted_circle_center: [x, y, z]
- fitted_circle_radius
- projection_method: references settled
- pymeshlab_filter: references settled
- pre_anonymization_mesh_id
- post_anonymization_mesh_id
- preserved_landmarks: list of landmark IDs extracted before simplification

## SlicePlane
- landmark_id: which landmark defines this plane
- normal: [nx, ny, nz]
- point_on_plane: [x, y, z]
- convention: references settled 切面定义约定

## CrossSectionContour
- source_plane: SlicePlane reference
- contour_points: ordered list of [x, y, z]
- is_closed: bool
- mesh_id

## MeasurementResult
- measurement_name: references settled 度量公式
- value
- unit
- input_landmarks: list of landmark IDs
- algorithm: references settled
- mesh_id
```

### 4.5 模块 `design.md` 模板

用于 `landmark_schema/`、`face_anonymization/`、`mesh_slicing/`、`measurements/`、`rendering/`、`mesh_processing/`、`data_io/`。

```markdown
# [Module Name]

## 定位
[模块在 pipeline 中处理什么数据，解决什么问题]

## 算法语义
[数学定义或精确语义]

## 输入契约
- 数据类型：
- 单位：
- 前置条件：

## 输出契约
- 数据类型：
- 单位：
- 保证：

## 正确性标准
- 不变量：
- 可测试断言：

## 已知失败模式
| 失败模式 | 症状 | 防护方式 |
|---|---|---|

## 当前实现
- 代码路径：UNSET
- 测试路径：UNSET

## 状态
- 已完成：UNSET
- 待实现：UNSET

上次更新：YYYY-MM-DD
```

---

## 5. `005_AgentMgmt/` 设计

### 5.1 `INDEX.md`

```markdown
# Agent Boot Protocol

## Step 0 — 术语对齐
读 `active/ctx_main/GLOSSARY.md`。

## Step 1 — 正确性规则
读 `active/ctx_integrity/README.md`，按任务读对应 integrity rules。

## Step 2 — 已定论定义
读 `../002_Architecture/settled.md`。

## Step 3 — 系统现状
读 `active/ctx_main/ctx_system_current.md`。

## Step 4 — 任务路由
查 `active/ctx_main/BOOT_MATRIX.md`。

## Historical
`_historical/` 仅供考古，不作为当前实现依据。
```

### 5.2 `TRUTH_LADDER.md`

```markdown
# Truth Ladder

## 优先级

1. `settled.md` 中冻结的定义：坐标系、单位、landmark schema（含派生规则）、度量公式
2. 当前代码 + tests
3. `ctx_integrity/` 正确性规则
4. `002_Architecture/data_contracts.md` 和各模块 `design.md`
5. `005_AgentMgmt/active/ctx_*` 当前合约
6. `PROJECT.md` / roadmap
7. `001_Inbox/` / `_archive/` / `_historical/`

## 关键裁定

- 代码输出与 settled 的度量公式或 landmark 定义冲突 → 默认怀疑代码有 bug。
- active ctx 与 settled 冲突 → 以 settled 为准。
```

### 5.3 `BOOT_MATRIX.md`

```markdown
# Boot Matrix

| Task | Must read first | Then read |
|---|---|---|
| Onboarding | `GLOSSARY`; `settled.md`; `ctx_system_current` | `architecture.md`; `readerBoot` |
| Landmark 定义 / 派生规则 | `landmarkIntegrityRule`; `settled.md` | `landmark_schema/design` |
| 面部匿名化开发 | `anonymizationIntegrityRule`; `meshTopologyIntegrityRule`; `settled.md` 匿名化约定 | `face_anonymization/design`; `landmark_schema/design` |
| 切片算法开发 | `landmarkIntegrityRule`; `meshTopologyIntegrityRule` | `mesh_slicing/design`; `landmark_schema/design` |
| 度量算法开发 | `measurementIntegrityRule`; `settled.md` 度量公式 | `measurements/design`; `data_contracts.md` |
| 渲染开发 | `measurementIntegrityRule`; `rendering/design` | `data_contracts.md` |
| Mesh 处理 | `meshTopologyIntegrityRule` | `mesh_processing/design` |
| 数据 IO | `data_io/design`; `data_contracts.md` | `settled.md` 格式约定 |
| Docs audit | `TRUTH_LADDER` | all active ctx + architecture docs |
```

### 5.4 `ctx_integrity/README.md`

```markdown
# Integrity Rules Index

这些规则防止静默错误：pipeline 能跑完，但结果是错的。

| File | Rule IDs | Topic |
|---|---|---|
| landmarkIntegrityRule.md | L1-L4 | landmark 定义一致性、派生规则、同名不同义 |
| anonymizationIntegrityRule.md | A1-A4 | 匿名化区域边界、landmark 保留、拓扑完整性 |
| meshTopologyIntegrityRule.md | M1-M3 | mesh 拓扑对切片/geodesic 的影响 |
| measurementIntegrityRule.md | E1-E3 | 度量公式唯一性、单位一致性 |

## 使用规则

- 涉及 landmark、切片、度量的任务，必须先读对应 integrity rule。
- active ctx 不得覆盖 integrity rule。
```

### 5.5 integrity rule 模板

```markdown
# [Topic] Integrity Rules

来源：UNSET
last_verified: null

## Rule Index

| ID | Rule | Silent failure prevented |
|---|---|---|
| L1 | UNSET | UNSET |

## L1 — [Rule Name]

**Rule:** [精确规则]

**Why silent:** [为什么不会报错但结果会错]

**Typical symptom:** [结果或可视化上的症状]

**Required checks:** [assertion / test / visualization]

**Code anchors:** UNSET
```

### 5.6 首批 integrity rules 建议

| ID | Rule |
|---|---|
| L1 | landmark ID 只能来自 settled schema；代码中不得硬编码 landmark name 或 index |
| L2 | derived landmark 的生成规则若变更，必须分配新 ID；旧 ID 的下游度量不自动继承 |
| L3 | 外部数据的 landmark 必须通过 mapping 表进入本项目 schema |
| L4 | 切面定义必须引用 settled 中的切面约定，不得在函数内部自行定义法向 |
| A1 | 匿名化前必须检查区域内是否包含下游 pipeline 需要的 landmark；若包含，必须先提取保留 |
| A2 | 匿名化后的 mesh 必须通过与原 mesh 相同的拓扑检查；PyMeshLab 简化可能引入 non-manifold |
| A3 | 匿名化是不可逆操作；原始 mesh 必须保留，匿名化结果另存为新 mesh_id |
| A4 | fit 圆的 landmark 对和平面参数必须来自 settled 匿名化约定表，不得在函数内硬编码 |
| M1 | mesh 有 holes 或 non-manifold edges 时，geodesic distance 算法可能静默返回错误值；必须在计算前验证 |
| M2 | 切片产生空截面时必须显式报错，不得返回空列表 |
| M3 | mesh decimation / remesh 不得改变 landmark 附近的 surface topology |
| E1 | 度量公式必须在 settled.md 定义后才能在代码中实现 |
| E2 | geodesic distance 和 Euclidean distance 不可混用；度量结果必须声明使用哪个 |
| E3 | 渲染标注的单位必须与计算单位一致 |

### 5.7 `GLOSSARY.md` 初始术语

```markdown
# Glossary

| Term | Definition | Common confusion |
|---|---|---|
| Original landmark | 输入数据中已有的 landmark（解剖学标注） | 与 derived landmark 区分 |
| Derived landmark | 由两个切片交线（或其他几何操作）计算得出的 landmark | 生成规则在 settled.md 冻结 |
| Slice / cross-section | 用平面切 mesh 得到的截面轮廓 | 不是 mesh 的 face 子集 |
| Slice intersection | 两个切片截面轮廓的交线或交点 | 可能产生 0 个或多个交点 |
| Face anonymization | 用 landmark+平面 fit 圆→投影→简化区域三角面片，抹去面部特征 | 不是面部重建；是降分辨率 |
| Geodesic distance | 沿 mesh surface 的最短路径距离 | 不是 Euclidean distance |
| Circumference | 截面轮廓的周长 | 不是 bounding circle |
| Mesh | 带 vertices + faces 的 surface | Point cloud 不是 mesh |
| Manifold | 每条 edge 恰好属于两个 face 的 mesh | non-manifold 影响 geodesic 计算 |
```

---

## 6. 创建步骤

1. 创建 `wiki/` 目录，将 `wiki/.obsidian/` 加入 `.gitignore`。
2. 创建第 3 节中的全部目录和 `.gitkeep`。
3. 创建 `_templates/` 中 4 个模板文件（discussion, module_design, integrity_rule, current_contract）。
4. 创建 `PROJECT.md`。
5. 创建 `002_Architecture/architecture.md`、`settled.md`、`roadmap.md`、`data_contracts.md`。
6. 为 7 个模块创建 `design.md`（landmark_schema, face_anonymization, mesh_slicing, measurements, rendering, mesh_processing, data_io）。
7. 创建 `005_AgentMgmt/INDEX.md`、`_how_to_use.md`、`active/ctx_main/*` 全部文件。
8. 创建 `ctx_integrity/` README + 4 个 rule 文件（landmark, anonymization, mesh topology, measurement）。
9. 创建 `ctx_landmark/`、`ctx_measurement/` 的 README 和 current contract。
10. 创建 `ctx_completed/README.md`、`_historical/README.md`、`_archive/README.md`。
11. 输出文件树和 UNSET 决策清单。

---

## 7. 成功标准

创建完成后 wiki 必须满足：

- 没有 `003_Experiments/`、`004_Paper/`、`coordinate_systems/`、`registration/`、`evaluation/`。
- `PROJECT.md` 能把新 agent 导航到 boot 入口。
- `settled.md` 明确列出：唯一坐标系、单位、原始 landmark schema、derived landmark 生成规则、面部匿名化约定、切面定义约定、度量公式。
- `ctx_integrity/` 覆盖四类静默错误：landmark 一致性、匿名化区域/拓扑、mesh 拓扑、度量公式。
- `BOOT_MATRIX` 能按任务类型给出必读文件。
- 所有未知项写 `UNSET`，集中列到 `roadmap.md`。

---

## 8. 最终输出格式

Agent 完成创建后必须输出：

```markdown
# Wiki Created

## Created tree
[文件树]

## Required first decisions
| Decision | File | Why it matters |
|---|---|---|

## UNSET blockers
| Item | Location |
|---|---|

## Recommended first work session
1. 填 settled.md 坐标系 + 单位
2. 填 settled.md 原始 landmark schema
3. 定义第一批 derived landmark 生成规则
4. 定义第一批度量公式
5. 填 settled.md mesh 拓扑要求
```

---

## 9. 不要做的事

- 不要创建 experiment / paper 目录。
- 不要创建 coordinate_systems 模块（只有一个坐标系，记在 settled.md 就够了）。
- 不要创建 registration / evaluation 模块。
- 不要让 `PROJECT.md` 承载细节。
- 不要把 landmark 名称相同当作定义相同。
- 不要在没有 settled 度量公式定义的情况下写度量代码。
- 不要在 mesh 未通过拓扑检查时静默运行 geodesic 计算。
- 不要在匿名化后跳过拓扑验证（PyMeshLab 简化可能引入 non-manifold edges）。
- 不要在匿名化区域内包含下游需要的 landmark 而不先提取保留。
