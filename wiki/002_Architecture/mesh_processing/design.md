# Mesh Processing（mesh 基础处理）

## 定位

Mesh 拓扑清洗和预处理。当前主要功能是为 geodesic solver 清理 non-manifold faces；未来扩展 mesh 清洗、法向修复等。

## 算法语义

### Non-manifold Face 清理（已实现）
`geodesic_utils.py:_clean_edge_flip_faces()`

1. 去除 winding-insensitive 重复三角面（`np.sort` + `np.unique`）
2. 迭代清理共享 >2 faces 的 edge：保留前 2 个 face，移除其余
3. 保证每条 undirected edge 最多属于 2 个 face（manifold 条件）
4. 顶点索引不变，仅修剪 face list → KDTree snapping 不受影响

### CAESAR PLY 加载（已实现）
- `process=False`：保留原始顶点，不让 trimesh 自动修复 winding
- 原因：自动修复可能改变顶点顺序，影响 vertex color 和 landmark vertex index

### 单位归一化（已实现）
- 见 [[unit_management/design]]

### Mesh 清洗 / 法向修复（规划中）
- 完整的 manifold 检查和修复
- 法向一致性
- Hole filling

## 输入契约

- faces: np.ndarray (F, 3), int32
- vertices: np.ndarray (N, 3), float64

## 输出契约

- cleaned faces: np.ndarray (F', 3), F' <= F
- 保证：每条 edge ≤ 2 faces, 无 winding-duplicate

## 正确性标准

- 清理后顶点索引不变
- 清理后 edge count per face ≤ 2
- 无 winding-duplicate faces

## 已知失败模式

| 失败模式 | 症状 | 防护方式 |
|---|---|---|
| SizeStream OBJ 含 reversed winding duplicates | potpourri3d solver 构建失败 | _clean_edge_flip_faces() |
| 清理移除过多 faces | mesh 变得不连通 | 仅移除违规 faces，保留最大子集 |

## 当前实现

- 代码路径：`geodesic_utils.py:_clean_edge_flip_faces()`
- 测试路径：`tests/test_geodesic_utils.py::test_build_geodesic_solver_cleans_nonmanifold_faces`

## 状态

- 已完成：non-manifold face 清理（for geodesic solver）
- 待实现：完整 mesh 清洗、法向修复、manifold 验证

上次更新：2026-05-08
