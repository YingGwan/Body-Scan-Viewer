# Landmark Integrity Rules

来源：代码分析 + wiki_creation_prompt_software.md
last_verified: 2026-05-08

## Rule Index

| ID | Rule | Silent failure prevented |
|---|---|---|
| L1 | Landmark 来源必须可追溯到 settled schema | 使用错误 landmark 定义导致度量偏差 |
| L2 | Derived landmark 生成规则变更 = 新 ID | 旧 ID 的下游度量静默使用新定义 |
| L3 | 不同来源的同名 landmark 不自动等价 | SS "Sellion" ≠ CAESAR "Sellion" |
| L4 | CAESAR landmark 坐标系可能与 mesh 不同 | landmark 显示在错误位置，度量全错 |

## L1 — Landmark Source Traceability

**Rule:** 代码中使用的 landmark 必须可追溯到 settled.md 中的 landmark schema 定义。不得在函数内部硬编码 landmark name 或 index。

**Why silent:** 硬编码的 landmark 名称在数据集切换后不会报错，但可能引用到错误的解剖学位置。

**Typical symptom:** 更换数据集后度量结果「看起来合理」但实际偏移。

**Required checks:** 代码审查：搜索硬编码 landmark 字符串。

**Code anchors:** `data_loader.py` — landmark 名称从 XLSX/LND 动态解析，不硬编码。

## L2 — Derived Landmark ID Stability

**Rule:** Derived landmark 的生成规则若变更（切面参数、交线计算方式），必须分配新的 landmark ID。旧 ID 的下游度量不自动继承新定义。

**Why silent:** Pipeline 继续使用旧 ID 名称，但实际坐标已变，所有引用该 ID 的度量静默产生错误值。

**Typical symptom:** 度量值突然变化但无任何 warning。

**Required checks:** settled.md derived landmarks 表的 ID 唯一性 + version tracking。

**Code anchors:** `derived_landmarks.py` — landmark ID 来自 `config/derived_landmarks.yaml`；YAML `landmark_name_map` 提供名称映射；权重变更保留旧 ID（`save_weights_to_yaml()` 仅更新权重字段）。

## L3 — Cross-Source Name Equivalence

**Rule:** SS landmark 和 CAESAR landmark 是两套独立 schema。同名 landmark（如 "Sellion"）不自动等价。跨源比较需要显式 mapping 表。

**Why silent:** 两个来源可能对同名 landmark 有不同的解剖学定义或标注位置。

**Typical symptom:** 跨源 landmark 距离比较出现系统性偏移。

**Required checks:** 跨源比较前检查 mapping 表是否存在。

**Code anchors:** 当前代码不做跨源名称匹配（SS landmarks 和 CAESAR landmarks 独立处理）。

## L4 — CAESAR Landmark Coordinate System

**Rule:** CAESAR `.lnd` 文件的原始 XYZ 坐标系可能与 PLY mesh 不同轴。必须通过对齐算法将 landmark 变换到 mesh 坐标系后才能使用。

**Why silent:** 未对齐的 landmark 仍然是 valid 3D 坐标，不会触发任何 error。但它们在错误的位置上。

**Typical symptom:** CAESAR landmarks 显示在 mesh 外部或穿过 mesh。

**Required checks:** 对齐后检查 mean mesh error（应 <50mm for body landmarks）。

**Code anchors:** `data_loader.py:align_caesar_landmarks_to_mesh()` — 24 旋转候选 + ICP refine，输出 mean/max mesh error 供验证。
