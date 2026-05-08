# Anonymization Integrity Rules

来源：wiki_creation_prompt_software.md（面部匿名化预设规则）
last_verified: 2026-05-08

> 注意：面部匿名化功能尚未实现。这些规则为未来开发预设。

## Rule Index

| ID | Rule | Silent failure prevented |
|---|---|---|
| A1 | 匿名化前检查区域内 landmark | 下游 pipeline landmark 被简化抹除 |
| A2 | 匿名化后拓扑验证 | PyMeshLab 简化引入 non-manifold，下游计算静默出错 |
| A3 | 匿名化不可逆，原始 mesh 保留 | 原始数据丢失 |
| A4 | 匿名化参数来自 settled | 函数内硬编码参数导致不一致 |

## A1 — Pre-Anonymization Landmark Check

**Rule:** 匿名化前必须检查区域内是否包含下游 pipeline 需要的 landmark。若包含，必须先提取并保留其坐标。

**Why silent:** 简化后 landmark 顶点消失，但代码可能用旧坐标继续计算而不报错。

**Typical symptom:** 某些度量值在匿名化后不合理地变化。

**Required checks:** 区域内 landmark → preserved_landmarks list。

**Code anchors:** 无（未实现）。

## A2 — Post-Anonymization Topology Validation

**Rule:** 匿名化后的 mesh 必须通过与原 mesh 相同的拓扑检查（manifold、无 holes 等）。PyMeshLab 简化可能引入 non-manifold edges。

**Why silent:** Non-manifold mesh 可以正常渲染，但 geodesic/切片算法可能静默返回错误值。

**Typical symptom:** Geodesic 路径穿过匿名化区域时返回 inf 或异常值。

**Required checks:** manifold check + edge count check on anonymized mesh。

**Code anchors:** 无（未实现）。参考现有 `geodesic_utils.py:_clean_edge_flip_faces()` 的 manifold 清理逻辑。

## A3 — Irreversibility and Original Preservation

**Rule:** 匿名化是不可逆操作。原始 mesh 必须保留，匿名化 mesh 另存为新 mesh_id。

**Why silent:** 如果覆写原始文件，无法验证匿名化前后的差异。

**Typical symptom:** 无法回溯，debug 时无参考。

**Required checks:** pre/post anonymization mesh_id 不同；原始文件 intact。

**Code anchors:** 无（未实现）。参考 `geometry_backend.py:save_registered()` 的导出模式。

## A4 — Anonymization Parameters From Settled

**Rule:** Fit 圆的 landmark 对和平面参数必须来自 settled.md 匿名化约定表，不得在函数内硬编码。

**Why silent:** 硬编码参数在 settled 更新后不会自动同步，导致匿名化区域定义不一致。

**Typical symptom:** 匿名化区域过大（吞掉身体 landmark）或过小（面部特征残留）。

**Required checks:** 代码审查 — 匿名化参数引用 settled 表。

**Code anchors:** 无（未实现）。
