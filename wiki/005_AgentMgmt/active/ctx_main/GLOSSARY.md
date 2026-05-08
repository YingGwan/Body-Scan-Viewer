# Glossary

| Term | Definition | Common confusion |
|---|---|---|
| SizeStream (SS) | 参考 body scan 来源，OBJ 格式，mm 单位，Y-up | 固定参考坐标系，ICP 的 target |
| CAESAR | 待配准 body scan 来源，PLY 格式，m 或 mm，动态 up-axis | ICP 的 source，配准到 SS 空间 |
| Original landmark | 输入数据中已有的 landmark（SizeStream XLSX 或 CAESAR LND） | 与 derived landmark 区分 |
| Derived landmark | 由两个切片交线（或其他几何操作）计算得出的 landmark | 生成规则在 settled.md 冻结；当前尚未实现 |
| Runtime mm | 所有运行时几何计算使用的统一单位（毫米） | 导出时恢复为原始单位 |
| ICP | Iterative Closest Point，刚体配准算法 | 本项目用 Point-to-Plane ICP |
| Coarse ICP | 大搜索半径的第一阶段 ICP（参数见 settled.md） | 粗定位 |
| Fine ICP | 小搜索半径的第二阶段 ICP（参数见 settled.md） | 精细对齐 |
| Fitness | ICP inlier correspondence 占比 (0-1) | 阈值见 settled.md |
| RMSE | Root Mean Square Error of inlier correspondences (mm) | 阈值见 settled.md |
| Slice / cross-section | 用平面切 mesh 得到的截面轮廓 | 不是 mesh 的 face 子集；当前未实现 |
| Slice intersection | 两个切片截面轮廓的交线或交点 | 可能产生 0 个或多个交点；当前未实现 |
| Face anonymization | 用 landmark+平面 fit 圆→投影→简化区域三角面片，抹去面部特征 | 不是面部重建；当前未实现 |
| Geodesic distance | 沿 mesh surface 的最短路径距离 | 不是 Euclidean distance |
| Euclidean distance | 3D 空间中的直线距离 | 不同于 geodesic |
| Circumference | 截面轮廓的周长 | 不是 bounding circle；当前未实现 |
| Mesh | 带 vertices + faces 的 surface | Point cloud 不是 mesh |
| Manifold | 每条 edge 恰好属于两个 face 的 mesh | non-manifold 影响 geodesic 计算 |
| MeshUnitContext | frozen dataclass 描述 mesh 原始单位和 mm 转换因子 | `unit_utils.py` |
| AppConfig | frozen dataclass tree 描述完整应用配置 | `config_loader.py` |
| Polyscope | 本项目使用的 3D 可视化库 | 不支持 headless 运行 |
| potpourri3d | 精确 geodesic solver 库 (EdgeFlipGeodesicSolver) | 可选依赖，有 Dijkstra fallback |
