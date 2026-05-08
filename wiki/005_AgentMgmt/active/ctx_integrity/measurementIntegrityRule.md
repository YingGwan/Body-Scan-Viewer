# Measurement Integrity Rules

来源：代码分析 + wiki_creation_prompt_software.md
last_verified: 2026-05-08

## Rule Index

| ID | Rule | Silent failure prevented |
|---|---|---|
| E1 | 度量公式必须先在 settled.md 定义 | 代码中的度量无定义参考，难以验证正确性 |
| E2 | Geodesic 和 Euclidean 不可混用 | 度量类型混淆导致数值差异 |
| E3 | 渲染标注单位与计算单位一致 | 用户看到的单位与实际不符 |

## E1 — Formula Before Code

**Rule:** 每个度量的计算公式必须先在 `settled.md` 度量公式表中定义，然后才能在代码中实现。代码中的度量计算方式若与 settled 不一致，以 settled 为准（怀疑代码有 bug）。

**Why silent:** 没有参考定义时，代码中的「合理」实现可能不是用户期望的定义。不同实现可能给出略有差异的结果，都看起来「对」。

**Typical symptom:** 两个开发者对同一度量有不同理解，各自实现通过测试但数值不同。

**Required checks:** 代码中每个度量函数注释引用 settled.md 中的公式 ID。

**Code anchors:** 
- `geodesic_utils.py:compute_geodesic()` — 对应 settled 中 "Geodesic distance" 定义
- `geometry_backend.py:compare_landmark_distances()` — 对应 settled 中 "Landmark Euclidean distance" 和 "Per-vertex distance" 定义

## E2 — Geodesic vs Euclidean Disambiguation

**Rule:** Geodesic distance 和 Euclidean distance 不可混用。度量结果必须声明使用哪个。在 mesh surface 上两点之间，geodesic ≥ Euclidean（三角不等式）。

**Why silent:** 两者量纲相同（mm），数值可能接近（平坦区域），混用在小范围内难以发现。

**Typical symptom:** 度量在弯曲区域（如腋下）明显偏小；或在平坦区域数值相似而让人误以为两者等价。

**Required checks:** 
- 函数名或返回值声明 distance type
- UI 标注区分 geodesic 和 Euclidean

**Code anchors:**
- `geodesic_utils.py` — 明确是 geodesic（surface path）
- `geometry_backend.py:compare_landmark_distances()` — 使用 `trimesh.proximity.closest_point()`，这是 Euclidean 最近点距离
- `gui_panel.py` — Panel D 标注为 "Geodesic"，Panel C 标注为 "Distance"（nearest-point Euclidean）

## E3 — Rendering Unit Consistency

**Rule:** 渲染标注的单位必须与计算单位一致。当前运行时单位为 mm，UI 显示的所有数值应为 mm（或显式标注为 cm 并做转换）。

**Why silent:** 单位标错不会导致程序 error，但用户基于错误单位做出错误判断。

**Typical symptom:** 度量值「差 1000 倍」（m vs mm 混淆）或「差 10 倍」（cm vs mm）。

**Required checks:** UI 中所有数值标注带单位；转换公式显式写出。

**Code anchors:**
- `gui_panel.py` — geodesic 显示 `mm` 和 `cm`（`length/10`）
- `gui_panel.py` — distance 显示 `mm`
- `geometry_backend.py:save_registered()` — 导出时明确 print export_unit
