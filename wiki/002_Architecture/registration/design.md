# Registration（ICP 配准）

## 定位

将 CAESAR body scan 刚体配准到 SizeStream 参考坐标系。这是当前 pipeline 的核心步骤，所有下游的距离比较和度量都依赖配准质量。

## 算法语义

### Pipeline
1. **轴旋转对齐**：检测 CAESAR up-axis（vertex range 最大轴），构造 90 度 proper rotation（det=+1）对齐到 SS 的 Y-up
2. **Centroid 平移**：将 CAESAR centroid 移动到 SS centroid
3. **Coarse ICP**：Point-to-Plane，大搜索半径（具体参数 → `settled.md` ICP 配准约定）
4. **Fine ICP**：Point-to-Plane，小搜索半径（具体参数 → `settled.md` ICP 配准约定）
5. **质量评估**：基于 fitness + RMSE 分级（阈值 → `settled.md` ICP 配准约定）

### 坐标诊断
- `diagnose_coordinate_systems()`: 对两个 mesh 分别计算 vertex range，最大轴 = up-axis
- Sellion landmark 作为 soft cross-check（不 override mesh-based diagnosis）

### 轴旋转矩阵
- `build_axis_swap_matrix()`: 6 种 axis pair 的 proper 90 度旋转
- 验证：det(R)=+1, R^T@R=I, 目标轴映射正确, roundtrip = identity

### Transform 链
```
T_total = T_icp @ T_centroid @ T_swap
```
应用顺序：raw CAESAR → axis swap → centroid align → ICP refine

## 输入契约

- mesh_ss: trimesh.Trimesh (SizeStream reference, mm)
- mesh_caesar: trimesh.Trimesh (CAESAR, runtime mm)
- coord_diag: dict from `diagnose_coordinate_systems()`, or None
- 两个 mesh 均需 >0 vertices

## 输出契约

- mesh_registered: trimesh.Trimesh (CAESAR after registration, mm)
- T_total: np.ndarray (4, 4), complete transform chain
- rmse: float (mm)
- fitness: float (0-1, fraction of inlier correspondences)
- quality: str ("Excellent"/"Acceptable"/"Needs review"/"Failed")

## 正确性标准

- T_total 的旋转部分 det > 0（proper transform）
- 应用 T_total 到 raw CAESAR vertices 应等于 step-by-step 应用
- Coarse ICP 结果作为 Fine ICP 初始值（init）
- Target normals 在 SizeStream 上估计（Point-to-Plane 需要 target normals）

## 已知失败模式

| 失败模式 | 症状 | 防护方式 |
|---|---|---|
| ICP 收敛到局部最优 | RMSE 偏高，visual misalignment | Coarse→Fine 两阶段 |
| fitness 极低（<0.1） | 几乎没有 correspondence | quality 标记为 Failed |
| 两个 mesh up-axis 相同但误诊 | 错误旋转 90 度 | vertex range 最大轴检测 |
| 点云过大导致 ICP 慢 | 耗时 >10s | 30000 点随机下采样 |

## 当前实现

- 代码路径：`registration.py`, `data_loader.py` (diagnose + axis swap)
- 测试路径：`tests/test_registration.py` (TestAxisSwapMatrix, TestTransformChain, TestRegistrationQuality, TestICPIntegration)

## 状态

- 已完成：完整 ICP pipeline + 质量评级 + 导出
- 待实现：无

上次更新：2026-05-08
