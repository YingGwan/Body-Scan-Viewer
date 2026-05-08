# V3 可行性分析报告 — 三向交叉验证审查

**审查日期：** 2026-05-08
**审查对象：** `TODO/1-0508/V3_feasibility_analysis.md`
**交叉验证依据：** V3 docx、当前 codebase（commit 6dfb11d）

---

## A. Requirement Coverage Checklist（需求覆盖核查表）

| V3 Docx 需求 | 覆盖？ | 解读正确？ | 备注 |
|---|---|---|---|
| 颈部 4 个新 landmarks (NeckFrontLeft/Right, NeckBackLeft/Right) | Yes | 基本正确 | 平面定义存在歧义，Plane 2 描述可再精确 |
| 颈部 Z 方向 surface length 输出 | **No** | — | **漏项：** docx 明确要求"Provide surface lengths in Z as value outputs" |
| 颈部 Geodesic curve + straight length 输出 | **No** | — | **漏项：** docx 第 1 节要求"Geodesic curve and straight length" |
| Plane 3 问题（docx 原始提问） | 未显式作答 | — | 技术方案隐含了答案但未明确说明 |
| Fig.1.2 放弃 NKFR-NKBK 轴方案 | 未提及 | — | docx 已决策放弃，报告应标注 |
| 腰部 4 个 Waist Dart landmarks | Yes | 基本正确 | 但 "Bust With Drop Front" 命名映射未明确 |
| 胸围 2 个 Waist Dart Upper Back landmarks | Yes | 正确 | 但命名写成了"Bust Dart Upper Back"，与 docx 不一致 |
| Waist Dart 的 XYZ 输出 | Yes | 正确 | 隐含在 Excel 导出中 |
| 弧长 A, B, C, D 测量值输出 | Yes | 正确 | |
| Apex → WaistDartFront 直线距离 ("if possible") | Yes | 正确 | 列为 Key Decision 但未计入工作量 |
| 大腿横截面四段弧长 | Yes | 基本正确 | "水平 X 方向"含义存在歧义未讨论 |
| Excel 导出（landmarks XYZ + measurements cm） | Yes | 正确 | |
| Armhole Depth 4 个新 landmarks | Yes | 正确 | |
| Mid-Shoulder → Apex 曲线长度 | Yes | 部分正确 | "in vertical" 语义歧义未作答 |
| Apex → Lower Bust Point 曲线长度 | Yes | 部分正确 | 同上 |
| 面部匿名化 (Chin → Head Circum Front) | Yes | 部分正确 | "preserve some feature" 约束被忽略 |
| SS data 复制到 anonymous folder | Yes | 正确 | |
| 坐标系调整 Z(0) = Crotch | Yes | 基本正确 | |

**总体覆盖率：~95%，有 2 项明确漏项，1 项潜在误读。**

---

## B. Code Fact Verification Table（代码事实核查表）

| 报告声明 | 验证 | 证据 | 修正 |
|---|---|---|---|
| SS XLSX ~199 个 3D landmarks | Correct | `settled.md:39` | — |
| Neck Front/Back/Left/Right 存在于 SS landmarks | Correct | XLSX 实测确认 | — |
| Derived Landmarks 表为 UNSET | Correct | `settled.md:59` | — |
| Mesh slicing 模块未实现 | Correct | `mesh_slicing/design.md:3` | — |
| 无平面构建/mesh 相交代码 | Correct | 全项目 grep 确认 | — |
| Geodesic engine 已实现 | Correct | `geodesic_utils.py:116` | — |
| 弧长 arc length 为 UNSET | Correct | `settled.md:117` | — |
| 仅有 PLY + NPY 导出 | Correct | `geometry_backend.py:402-435` | — |
| 无 CSV/Excel 导出 | Correct | 全项目确认 | — |
| openpyxl 已安装 | Correct | `requirements.txt:13` | — |
| pandas 已安装 | Correct | `requirements.txt:6` | — |
| PyMeshLab 未安装 | Correct | `requirements.txt` 无该条目 | — |
| trimesh 已安装 | Correct | `requirements.txt:7` | — |
| `trimesh.mesh_plane()` 返回"有序"线段 | **Inaccurate** | 实际返回**无序**线段集合 | 需额外轮廓重建排序步骤 |
| 无全局原点约定 | Correct | `settled.md:16` | — |
| GUI 有 Panel D 或 E | **Minor error** | `gui_panel.py` 只有 A-D 四个 Panel | 应为"新建 Panel E" |
| Geodesic 曲线渲染为"绿色" | **Wrong** | `render_config.json`: `[0.576, 0.086, 0.086]` = 深红色 | — |
| Mid-Shoulder 需 midpoint 计算 | **Wrong** | SS XLSX 已含 `Mid Shoulder Left`/`Right` | 直接使用已有 landmark |

---

## C. Scoring Table（综合评分表）

| 评估维度 | 分数 | 理由 |
|---|---|---|
| **完整性** | 7.5/10 | 覆盖 ~95% 需求；颈部 surface length 输出和 geodesic/straight length 明确漏项；5.2/5.3 "in vertical" 歧义未解 |
| **准确性** | 8.5/10 | 代码现状声明绝大多数正确；3 处可纠正错误（trimesh 有序性、Mid Shoulder、geodesic 颜色） |
| **技术深度** | 8.5/10 | 各模块技术路线详实，三平面交点公式和弧长比例算法正确；但 trimesh 轮廓重建的工程细节未提及 |
| **风险识别** | 7.0/10 | 识别了 mesh 拓扑风险；但漏掉坐标系冻结的循环依赖、PyMeshLab selective decimation API 的实际复杂度 |
| **执行计划质量** | 7.0/10 | 顺序逻辑合理；总工作量 14 天偏乐观，修正后约 16 天 |
| **Overall** | **7.5/10** | 高质量可行性分析，修正漏项和歧义后可作为实施计划直接使用 |

---

## D. Issues Found（发现的具体问题）

### Issue #1 [中]：颈部 surface length 输出需求漏项

报告 Module 1 仅讨论了 4 个新 landmark 的坐标生成，完全未提及 docx 第 1 节的配套输出要求：
- "Provide surface lengths in Z as value outputs."
- "Geodesic curve and straight length."

**建议：** Module 1 补充 Step 5：计算颈部 landmark 间截面弧长和 geodesic/Euclidean 距离。额外 +0.5 天。

### Issue #2 [低]：Plane 3 问题未显式作答

Docx 对 4 个颈部新点都提问"Do we need Plane 3 for anchoring it at neck surface?"。报告的技术方案（两平面交线与 mesh 表面交点）隐含了答案，但未显式说明。

**建议：** 在 Module 1 中写明："Plane 3 由 mesh 表面约束替代——两平面交线与 mesh 的交点天然位于表面上。"

### Issue #3 [高]：执行顺序循环依赖

报告建议 M6（坐标系）最先做，但 Module 1/2/5 的技术路线中已写死了平面法向（如"normal = Z-axis 前后方向"）。若 M6 改变了轴约定，所有平面描述都需修改。

**建议：** M6 完成前，所有模块的法向描述应标注"待 M6 冻结后确认"。并在依赖图中补充 M6 → M1/M2/M5 的依赖线。

### Issue #4 [中]：trimesh.mesh_plane() 返回无序线段

报告写"返回有序截面线段"，实际返回**无序线段集合**。需额外实现轮廓重建排序（端点 KDTree 匹配拼接），这是弧长引擎正确性的前提。

**建议：** 切片引擎工作量从 2 天修正为 2.5-3 天。

### Issue #5 [中]：面部匿名化"preserve some feature"被忽略

Docx Notes 1.1 写 "preserve some feature"，这可能意味着不能做纯 uniform decimation，需要保留某些面部特征轮廓。报告仅描述了 quadric edge collapse。

**建议：** 增加 clarification 任务，向 docx 作者确认含义。

### Issue #6 [中]：PyMeshLab selective decimation API 被过度简化

`meshing_decimation_quadric_edge_collapse()` 默认对整个 mesh 操作。需先通过 `compute_selection_by_condition_per_face()` 建立 selection mask 再设 `selected=True`。

**建议：** Module 7 增加 0.5 天 spike 验证 API 链。

### Issue #7 [低]：命名不一致

报告将 "Waist Dart Upper Back Left/Right" 写成 "Bust Dart Upper Back"，与 docx 命名不符。

### Issue #8 [低]：Mid Shoulder landmark 无需插值

SS XLSX 已含 `Mid Shoulder Left`/`Mid Shoulder Right`，不需要从两点中点计算。

---

## E. Recommendations（改进建议）

### E.1 补充颈部测量输出

Module 1 增加子任务：NeckFront→NeckFrontLeft/Right 截面弧长（Z 方向）+ geodesic/Euclidean 距离。+0.5 天。

### E.2 M6 优先冻结轴约定，后续模块引用 settled.md

在 `settled.md` 中写入:
```
| 轴约定 | X=左右 Y=up Z=前后 | 原点 | CrotchPoint 的坐标映射 |
```
M1/M2/M5 的平面法向描述改为"参见 settled.md 轴约定"。

### E.3 切片引擎补充轮廓重建步骤

分解为: (1) `mesh_plane()` 获取无序线段 → (2) 端点拼接/轮廓重建排序 → (3) is_closed 判定。工作量 2→3 天。

### E.4 向 docx 作者确认 3 个歧义

1. Plane 3：是否接受 mesh 表面约束作为替代？
2. 5.2/5.3 "in vertical"：geodesic surface distance 还是 Y 方向投影？
3. Face anonymization "preserve some feature"：具体指什么？

### E.5 PyMeshLab API spike

Module 7 前增加 0.5 天 spike，验证 selective decimation filter 链。

### E.6 更新依赖图

```
M6: 坐标系约定
    ├── M1: Neck Landmarks（法向依赖）
    ├── M2: Waist/Bust Darts（transverse Y 值依赖）
    └── M5.1: Armhole Plane（轴定义依赖）

Mesh Slicing Engine
    ├── M1  ├── M2  ├── M3  └── M5.1
```

### E.7 修正工作量

| 模块 | 原估 | 建议 | 原因 |
|---|---|---|---|
| Mesh Slicing Engine | 2d | 3d | 轮廓重建 |
| M2: Waist/Bust Darts | 4d | 5d | 弧长边界条件 |
| M7: Face Anon | 2d | 3d | PyMeshLab API 复杂度 |
| **总计** | **14d** | **~16d** | |

---

**审查结论：** 报告技术判断可信、架构思路清晰，是合格的 V3 开发路线图基础。核心改进：(1) 补充颈部输出测量漏项；(2) 修正 trimesh 切片"有序"的不准确描述；(3) 将 M6 坐标系约定显式化为 M1/M2/M5 的前置依赖；(4) 对 Face Anonymization 和 "in vertical" 含义向作者确认。修正后可作为实施计划直接使用。
