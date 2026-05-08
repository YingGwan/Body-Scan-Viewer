# Glossary

| Term | Definition | Common confusion |
|---|---|---|
| SizeStream (SS) | 参考 body scan 来源，OBJ 格式，mm 单位，Y-up | 固定参考坐标系，ICP 的 target |
| CAESAR | 待配准 body scan 来源，PLY 格式，m 或 mm，动态 up-axis | ICP 的 source，配准到 SS 空间 |
| Original landmark | 输入数据中已有的 landmark（SizeStream XLSX 或 CAESAR LND） | 与 derived landmark 区分 |
| Derived landmark | 由 init_method（几何法）计算得出的 landmark，以重心坐标参数化 | 生成规则在 settled.md 冻结；当前 14 个已定义（8 Neck/Armhole + 6 Waist），4 个 init_method 全部已实现；Waist 待跨 subject 数据验证 |
| Barycentric coordinates | α + β + γ = 1 的参考三角形权重，描述 derived landmark 在 3 个 reference landmark 张成空间中的位置 | 不限于三角形内部（权重可 >1 或 <0） |
| init_method | 计算 derived landmark 初始位置的几何算法（如 `contour_z_extremum`, `plane_intersection`） | init_method 只在首次计算时使用，之后由 saved weights 接管 |
| landmark_name_map | YAML 中规范名到数据集实际名的映射（如 NeckLeft → "Mid Neck Left"） | 由 `resolve_landmark_name()` 解析 |
| Runtime mm | 所有运行时几何计算使用的统一单位（毫米） | 导出时恢复为原始单位 |
| ICP | Iterative Closest Point，刚体配准算法 | 本项目用 Point-to-Plane ICP |
| Coarse ICP | 大搜索半径的第一阶段 ICP（参数见 settled.md） | 粗定位 |
| Fine ICP | 小搜索半径的第二阶段 ICP（参数见 settled.md） | 精细对齐 |
| Fitness | ICP inlier correspondence 占比 (0-1) | 阈值见 settled.md |
| RMSE | Root Mean Square Error of inlier correspondences (mm) | 阈值见 settled.md |
| Slice / cross-section | 用平面切 mesh 得到的截面轮廓 | 不是 mesh 的 face 子集；用于 contour_z_extremum 和 arc_length |
| Face anonymization | Open3D quadric decimation proxy → vertex smoothing + boundary falloff，抹去面部特征 | 不切割拓扑；不用 PyMeshLab |
| Geodesic distance | 沿 mesh surface 的最短路径距离 | 不是 Euclidean distance |
| Euclidean distance | 3D 空间中的直线距离 | 不同于 geodesic |
| Y-projection distance | `\|y1-y2\|`，两 landmark 间的纯高度差 | V3 测量类型，不是 geodesic 也不是 Euclidean |
| Arc length | 横截面环上两点间的弧线长度 | 不是完整围度（circumference） |
| Circumference | 截面轮廓的周长 | 不是 bounding circle；当前未实现 |
| Mesh | 带 vertices + faces 的 surface | Point cloud 不是 mesh |
| Manifold | 每条 edge 恰好属于两个 face 的 mesh | non-manifold 影响 geodesic 计算 |
| MeshUnitContext | frozen dataclass 描述 mesh 原始单位和 mm 转换因子 | `unit_utils.py` |
| AppConfig | frozen dataclass tree 描述完整应用配置（JSON only） | `config_loader.py` |
| MeasurementRecord | dataclass 描述单条 V3 度量结果（name, family, value_mm, method, source_landmarks） | `derived_landmarks.py` |
| Panel E | GUI 面板：derived landmarks 的交互式重心坐标滑块 + Apply/Save/Load/Reset + measurements | `gui_panel.py:_panel_derived()` |
| Panel F | GUI 面板：face anonymization 的参数滑块 + 执行按钮 | `gui_panel.py:_panel_face_anon()` |
| Polyscope | 本项目使用的 3D 可视化库 | 不支持 headless 运行 |
| potpourri3d | 精确 geodesic solver 库 (EdgeFlipGeodesicSolver) | 可选依赖，有 Dijkstra fallback |
| FastIKD | conda 环境名，包含所有运行时依赖 | 所有 Python/pip 命令必须用此环境 |
