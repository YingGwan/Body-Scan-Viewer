# Mesh Topology Integrity Rules

来源：代码分析 + wiki_creation_prompt_software.md
last_verified: 2026-05-08

## Rule Index

| ID | Rule | Silent failure prevented |
|---|---|---|
| M1 | Non-manifold mesh 影响 geodesic 和切片 | geodesic 静默返回错误值 |
| M2 | 空截面必须显式报错 | 空列表被下游当作无 landmark |
| M3 | Mesh 简化/remesh 不得改变 landmark 附近拓扑 | landmark snap 到被修改的顶点 |

## M1 — Non-Manifold Impact on Algorithms

**Rule:** Mesh 有 holes 或 non-manifold edges 时，geodesic distance 算法可能静默返回错误值。切片算法在 non-manifold 区域也可能产生不连续轮廓。必须在计算前验证或清理。

**Why silent:** Dijkstra/potpourri3d 不会对 non-manifold 报错，只是路径可能绕行或截断。

**Typical symptom:** Geodesic 距离异常偏大或返回 inf；切片轮廓有断点。

**Required checks:** 
- Geodesic 计算前：`_clean_edge_flip_faces()` 自动清理
- 未来切片：需类似的拓扑预检

**Code anchors:** `geodesic_utils.py:_clean_edge_flip_faces()` — 移除 duplicate faces 和 >2 face/edge 的情况。测试：`test_geodesic_utils.py::test_build_geodesic_solver_cleans_nonmanifold_faces`。

## M2 — Empty Cross-Section Must Error

**Rule:** 切片产生空截面时必须显式报错，不得返回空列表。空列表被下游代码当作「该位置无 landmark」而不是「切片失败」。

**Why silent:** 空列表是 valid Python 对象，downstream code 不会 crash，只是 skip。

**Typical symptom:** 某个 derived landmark 被静默跳过，度量结果缺少该项。

**Required checks:** 切片函数返回前检查 contour 非空。

**Code anchors:** 无（切片尚未实现）。

## M3 — Mesh Modification Near Landmarks

**Rule:** 任何 mesh decimation / remesh / 匿名化操作不得改变 landmark 附近的 surface topology。如果 landmark 通过 vertex index snap 到 mesh，修改 topology 会使 snap 失效。

**Why silent:** Vertex index 仍然 valid（在范围内），但指向不同的物理位置。

**Typical symptom:** Landmark 位置在 mesh 修改后「跳」到不相关位置。

**Required checks:** 
- Mesh 修改前保存 landmark 坐标（而非 vertex index）
- 修改后重新 snap

**Code anchors:** `data_loader.py:parse_lnd()` — 支持 `mesh_vertices` 参数通过 vertex_idx resolve 坐标。`align_caesar_landmarks_to_mesh()` 使用坐标而非 index。
