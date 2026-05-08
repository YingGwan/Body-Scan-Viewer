# Anonymization Integrity Rules

来源：wiki_creation_prompt_software.md（面部匿名化预设规则）+ 已实现代码
last_verified: 2026-05-08

> 面部匿名化已实现，使用 Open3D quadric decimation proxy + boundary falloff vertex smoothing。

## Rule Index

| ID | Rule | Silent failure prevented |
|---|---|---|
| A1 | 匿名化前检查区域内 landmark | 下游 pipeline landmark 被简化抹除 |
| A2 | 匿名化后拓扑验证 | 简化引入 non-manifold，下游计算静默出错 |
| A3 | 匿名化不可逆，原始 mesh 保留 | 原始数据丢失 |
| A4 | 匿名化参数来自 settled | 函数内硬编码参数导致不一致 |

## A1 — Pre-Anonymization Landmark Check

**Rule:** 匿名化前必须检查区域内是否包含下游 pipeline 需要的 landmark。若包含，必须先提取并保留其坐标。

**Why silent:** 简化后 landmark 顶点消失，但代码可能用旧坐标继续计算而不报错。

**Typical symptom:** 某些度量值在匿名化后不合理地变化。

**Required checks:** 区域内 landmark → preserved_landmarks list。

**Code anchors:** `face_anonymization.py:select_face_region()` — 基于 Chin + Head Circum 定义的区域仅覆盖面部，身体 landmark 不在区域内。

## A2 — Post-Anonymization Topology Validation

**Rule:** 匿名化后的 mesh 必须通过与原 mesh 相同的拓扑检查（boundary edges、non-manifold edges、connected components 数量一致）。

**Why silent:** Non-manifold mesh 可以正常渲染，但 geodesic/切片算法可能静默返回错误值。

**Typical symptom:** Geodesic 路径穿过匿名化区域时返回 inf 或异常值。

**Required checks:** boundary edge count + non-manifold edge count + component count 匿名化前后一致。

**Code anchors:** `face_anonymization.py:boundary_edge_counts()` — 返回 (boundary, nonmanifold) 计数；`face_anonymization.py:connected_component_face_counts()` — 返回分量面片数；`FaceAnonymizationResult.before/after_boundary_edges` 和 `before/after_components` 保存验证结果。

## A3 — Irreversibility and Original Preservation

**Rule:** 匿名化是不可逆操作。原始 mesh 必须保留，匿名化 mesh 另存为新 mesh_id。

**Why silent:** 如果覆写原始文件，无法验证匿名化前后的差异。

**Typical symptom:** 无法回溯，debug 时无参考。

**Required checks:** pre/post anonymization mesh_id 不同；原始文件 intact。

**Code anchors:** `face_anonymization.py:anonymize_face_open3d()` — 返回 `FaceAnonymizationResult` 包含修改后的 mesh 副本，不覆写输入 mesh。`geometry_backend.py:anonymize_face()` — 调用后将结果存入 `face_anonymization_stats`，原始 `mesh_ss` 不变。

## A4 — Anonymization Parameters From Settled

**Rule:** 匿名化区域定义的 landmark 和参数必须来自 settled.md 匿名化约定表，不得在函数内硬编码。

**Why silent:** 硬编码参数在 settled 更新后不会自动同步，导致匿名化区域定义不一致。

**Typical symptom:** 匿名化区域过大（吞掉身体 landmark）或过小（面部特征残留）。

**Required checks:** 代码审查 — 匿名化参数引用 settled 表。

**Code anchors:** `face_anonymization.py:select_face_region()` — landmark 名称（"Chin", "Head Circum Front", "Head Circum Right"）当前硬编码在函数中，对应 settled.md 面部匿名化约定表。算法参数（target_ratio, smoothing_iterations 等）通过函数参数传入，默认值与 settled 一致。
