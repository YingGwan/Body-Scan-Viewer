# ADE Polyscope Viewer V3 — Implementation Plan (Rev.3)

> Date: 2026-05-08 | Source: ADE Polyscope Viewer Development V3.docx
> Baseline: commit **d797570** (main branch)
> Env: **conda FastIKD** (trimesh 4.11, shapely 2.0.7, rtree 1.4, scipy 1.13, open3d 0.19, pymeshlab, potpourri3d)
> Rev.3: 引入重心坐标参数化 + trimesh/Shapely 库原生能力，替代自定义轮廓重建和弧长引擎

---

## Executive Summary

### 架构核心变更 (Rev.2 → Rev.3)

**Rev.2** 的思路是"先做切片引擎、再算弧长、再定位 landmark"——每个模块都有自定义算法。

**Rev.3** 引入两个关键简化：

1. **Derived Landmark 统一表示：重心坐标参数化。** 所有 14 个新 landmark 都用同一模式：选 3 个已有 landmark 构成参考三角形 → 用重心坐标 (α, β, γ) 表达相对位置 → 投影到 mesh 表面。初始权重由 V3 几何法/弧长法计算，之后可微调。权重保存在 YAML 配置中，跨 subject 自适应。

2. **库覆盖替代自定义代码。** `mesh.section()` 返回已重建的 Path3D（不用自己拼接线段），`shapely.ring.project()/interpolate()` 直接算弧长和比例定位（不用自己写弧长引擎）。自定义代码从 Rev.2 预估的几百行降到约 60 行。

**工作量：15–20 个工作日**（Rev.2 估计 20–27 天；库覆盖省 ~5 天，重心坐标统一表示省 ~2 天）。

---

## 架构设计：Derived Landmark 的两层表示

### Layer 1: 几何初始化（一次性运行）

对每个新 landmark，用 V3 定义的几何方法计算初始 3D 位置 P₀：

| 方法 | 适用的 landmark |
|------|----------------|
| 两平面交线 + ray casting | Neck 4 点 |
| 三平面交叉 + snap | Waist Dart Front 2 点 |
| 截面弧长 50% 定位 | Waist Dart Back 2 点 + Upper Back 2 点 |
| 截面轮廓 Z 极值 | Armhole 4 点 |

### Layer 2: 重心坐标参数化（持久保存 + 跨 subject 复用）

```
输入: P₀ (初始 3D 位置) + △(A, B, C) (参考三角形, 由 3 个已有 landmark 构成)
  │
  ├── 1. 反算重心坐标: P₀ = α·A + β·B + γ·C  (α + β + γ = 1)
  │
  ├── 2. 可选微调: 修改 (α, β, γ) → P₁
  │
  ├── 3. 投影到 mesh 表面: P_final = closest_point(mesh, P₁)
  │
  └── 4. 保存 (α, β, γ) 到 YAML
```

**新 subject 使用流程：**
```
读取 YAML 中的 (α, β, γ) + 三角形定义
  → 从该 subject 的 landmark 中取 A, B, C
  → 计算 P = α·A + β·B + γ·C
  → 投影到该 subject 的 mesh 表面
  → 得到该 subject 的 derived landmark
```

### 为什么这样做

| 优势 | 说明 |
|------|------|
| **体型自适应** | 重心坐标是相对比例，不是绝对坐标。胖人和瘦人用同一组权重，解剖位置自动对应。 |
| **可微调** | 改 3 个数字就能调整位置，不需要改算法逻辑。 |
| **统一表示** | 14 个 landmark 全部用 `(triangle, weights)` 描述，代码只需一个通用函数。 |
| **可追溯** | YAML 中记录了每个 landmark 的参考三角形和初始化方法，便于审计。 |
| **失败安全** | 即使几何初始化法在某个异常 mesh 上失败，也可以用手动权重 fallback。 |

---

## YAML 配置 Schema

```yaml
# config/derived_landmarks.yaml

version: 1

# 重心坐标反算和投影所需的函数:
#   P = alpha * A + beta * B + gamma * C   (alpha + beta + gamma = 1)
#   P_surface = closest_point(mesh, P)

landmarks:

  # ── Neck ──────────────────────────────────────────
  NeckFrontLeft:
    triangle: [NeckFront, NeckLeft, NeckBack]
    weights: [1.15, 0.42, -0.57]       # 初始值由 V3 两平面交线法反算
    init_method: plane_intersection     # 几何初始化方法
    init_note: >
      Coronal plane (z=NeckFront.z) ∩ Sagittal plane (x=NeckLeft.x).
      Ray hit at Y≈1283 (肩-胸交界). Option A accepted.
    family: Neck

  NeckFrontRight:
    triangle: [NeckFront, NeckRight, NeckBack]
    weights: [1.15, 0.42, -0.57]
    init_method: plane_intersection
    family: Neck

  NeckBackLeft:
    triangle: [NeckBack, NeckLeft, NeckFront]
    weights: [0.60, 0.55, -0.15]
    init_method: plane_intersection
    init_note: "Ray hit at Y≈1323, within neck region. No adjustment needed."
    family: Neck

  NeckBackRight:
    triangle: [NeckBack, NeckRight, NeckFront]
    weights: [0.60, 0.55, -0.15]
    init_method: plane_intersection
    family: Neck

  # ── Waist Dart ────────────────────────────────────
  WaistDartFrontLeft:
    triangle: [WaistFront, WaistLeft, "Bust With Drop Front"]
    weights: [0.35, 0.40, 0.25]
    init_method: three_plane_intersection
    init_note: >
      Plane1(BustWithDropFront + BustLeft) ∩ Plane2(ApexLeft) ∩ Plane3(Waist transverse).
      Snap to waist contour.
    family: Waist

  WaistDartFrontRight:
    triangle: [WaistFront, WaistRight, "Bust With Drop Front"]
    weights: [0.35, 0.40, 0.25]
    init_method: three_plane_intersection
    family: Waist

  WaistDartBackLeft:
    triangle: [WaistBack, WaistLeft, WaistFront]
    weights: [0.50, 0.50, 0.00]        # 50% arc midpoint ≈ midpoint of edge
    init_method: arc_length_ratio
    init_note: "50% of arc(WaistBack → WaistLeft) on waist contour."
    family: Waist

  WaistDartBackRight:
    triangle: [WaistBack, WaistRight, WaistFront]
    weights: [0.50, 0.50, 0.00]
    init_method: arc_length_ratio
    family: Waist

  WaistDartUpperBackLeft:
    triangle: [BustBack, BustLeft, BustFront]
    weights: [0.50, 0.50, 0.00]
    init_method: arc_length_ratio
    init_note: "50% of arc(BustBack → BustLeft) on bust contour. At bust height, not waist."
    family: Waist

  WaistDartUpperBackRight:
    triangle: [BustBack, BustRight, BustFront]
    weights: [0.50, 0.50, 0.00]
    init_method: arc_length_ratio
    family: Waist

  # ── Armhole ───────────────────────────────────────
  ArmholeDepthFrontLeft:
    triangle: [ShoulderLeft, ArmpitLeft, NeckLeft]
    weights: [0.35, 0.55, 0.10]
    init_method: contour_z_extremum
    init_note: "Max-Z point on armhole cross-section (Shoulder-Armpit plane)."
    family: Armhole

  ArmholeDepthBackLeft:
    triangle: [ShoulderLeft, ArmpitLeft, NeckBack]
    weights: [0.35, 0.55, 0.10]
    init_method: contour_z_extremum
    init_note: "Min-Z point on armhole cross-section."
    family: Armhole

  ArmholeDepthFrontRight:
    triangle: [ShoulderRight, ArmpitRight, NeckRight]
    weights: [0.35, 0.55, 0.10]
    init_method: contour_z_extremum
    family: Armhole

  ArmholeDepthBackRight:
    triangle: [ShoulderRight, ArmpitRight, NeckBack]
    weights: [0.35, 0.55, 0.10]
    init_method: contour_z_extremum
    family: Armhole
```

> 注：以上 weights 为示意值。实际值需在 Phase 1 中对 4 个 subject 运行几何初始化后反算。

---

## Execution Phases (Rev.3)

### Phase 0: Rule Freezing + YAML Schema

> 不写功能代码。冻结规则，设计 YAML schema，确认歧义。

**0.1 冻结到 `settled.md`：**
- 14 个 derived landmark 的名称、参考三角形选择、init_method
- 弧长公式：沿截面轮廓，Shapely `ring.project()` / `ring.interpolate()`
- 坐标系：内部保持 Y-up mm，导出时 Z(0)=Crotch

**0.2 创建 `config/derived_landmarks.yaml`：** 初始版本，weights 用占位值

**0.3 向协作者确认：**

| # | 问题 | 建议答案 |
|---|------|---------|
| Q1 | NeckFrontLeft 高度 | **选项 A 已确认** — 接受 Y≈1283 的数学结果，通过重心坐标微调 |
| Q2 | 5.2/5.3 "in vertical" | Geodesic? Y 投影? |
| Q3 | Face anonymization "preserve some feature" | 纯 decimation? 保留结构? |

**估计工作量：1–2 天**

---

### Phase 1: Geometric Initialization（在 4 个 subject 上算初始位置）

> 目标：对 4 个 subject 运行 V3 几何法，得到每个 derived landmark 的初始 3D 位置，反算重心坐标，验证跨 subject 稳定性。

**1.1 切片引擎（库调用，不自己写）：**

```python
path3d = mesh.section(plane_origin=origin, plane_normal=normal)  # trimesh Path3D
path2d, to_3d = path3d.to_planar()                               # → Shapely Polygon
ring = max(path2d.polygons_full, key=lambda p: p.area).exterior   # 主轮廓
```

实测验证（Rev.2 lab report）：
- Waist: 3 entities, 主轮廓 148 pts / 629mm, landmark snap < 0.1mm
- Bust: 3 entities, 主轮廓 186 pts / 809mm
- Thigh: 2 entities (左右腿), 均闭合
- 弧长 vs SS tape measure: 误差 < 2.5%

**1.2 四种 init_method 实现：**

| Method | 实现 | 库依赖 |
|--------|------|--------|
| `plane_intersection` | 两平面交线 + `mesh.ray.intersects_location()` | trimesh.ray + rtree |
| `three_plane_intersection` | 三平面交点公式 + snap 到截面轮廓 | numpy + shapely |
| `arc_length_ratio` | `ring.project()` + `ring.interpolate()` | shapely |
| `contour_z_extremum` | `mesh.section()` → contour → `argmax/argmin` Z | trimesh + numpy |

**1.3 反算重心坐标：**

```python
def to_barycentric(P, A, B, C):
    """P = α·A + β·B + γ·C, α+β+γ=1 → solve 3×3 linear system."""
    M = np.column_stack([A - C, B - C])  # (3, 2)
    rhs = P - C                          # (3,)
    # Least-squares solve (over-determined: 3 equations, 2 unknowns)
    ab, _, _, _ = np.linalg.lstsq(M, rhs, rcond=None)
    alpha, beta = ab
    gamma = 1.0 - alpha - beta
    return alpha, beta, gamma
```

**1.4 跨 subject 稳定性验证：**

对 4 个 subject (csr0052a, csr0283a, csr1921a, csr2119a) 的每个 derived landmark：
- 分别运行 init_method → 得到 P₀
- 反算 (α, β, γ)
- 计算 4 组权重的方差
- 若方差 < 0.05 → 取均值作为 YAML 默认权重
- 若方差 > 0.05 → 需要检查原因（体型差异大? 算法不稳定?）

**1.5 投影验证：**

```python
P_bary = alpha * A + beta * B + gamma * C
P_surface, _, _ = trimesh.proximity.closest_point(mesh, [P_bary])
projection_dist = np.linalg.norm(P_bary - P_surface)
# 期望 < 10mm (颈部/腰部三角形离体表近)
```

**估计工作量：3–4 天**（4 个 init_method + 4 subjects × 14 landmarks + 稳定性分析）

---

### Phase 2: Measurement Engine（弧长 + Geodesic + Euclidean）

> 目标：实现所有配套测量，全部用库。

**2.1 截面弧长（Shapely，零自定义代码）：**

```python
# 弧长 = ring 上两点间的弧线长度
pos_a = ring.project(Point(pt_a_2d))
pos_b = ring.project(Point(pt_b_2d))
arc = abs(pos_b - pos_a)
if arc > ring.length / 2:
    arc = ring.length - arc  # 取短弧
```

| 测量 | 起点 → 终点 | 切面 |
|------|------------|------|
| Neck surface length Z | NeckFrontLeft → NeckFrontRight | Neck transverse or coronal |
| Waist arc A | WaistFront → WaistDartFrontLeft | Waist transverse |
| Waist arc B | WaistBack → WaistDartBackLeft | Waist transverse |
| Bust arc C | BustFront → BustLeft | Bust transverse |
| Bust arc D | BustFront → ApexLeft | Bust transverse |
| Thigh 4 segments | Front→Left→Back→Right→Front | Thigh transverse |
| (所有对称右侧) | | |

**2.2 Geodesic 曲线（已有引擎）：**

| 曲线 | 起点 | 终点 |
|------|------|------|
| Mid Shoulder Left → ApexBustLeft | SS 已有 | SS 已有 |
| Mid Shoulder Right → ApexBustRight | SS 已有 | SS 已有 |
| ApexBustLeft → LowerBustLeft | SS 已有 | SS 已有 |
| ApexBustRight → LowerBustRight | SS 已有 | SS 已有 |

直接调用 `compute_geodesic()` (geodesic_utils.py)。

**2.3 Euclidean 距离：**

| 测量 | 说明 |
|------|------|
| ApexBustLeft → WaistDartFrontLeft | "if possible" — `np.linalg.norm(A - B)` |
| Neck straight distances | NeckFront → NeckFrontLeft etc. |

**估计工作量：2–3 天**

---

### Phase 3: Results + Excel Export

**3.1 统一结果表：**

```python
@dataclass
class MeasurementRecord:
    name: str
    family: str          # "Neck" | "Waist" | "Bust" | "Thigh" | "Armhole"
    value_mm: float
    method: str          # "arc_length" | "geodesic" | "euclidean"
    source_landmarks: tuple[str, ...]
```

**3.2 Excel 导出：**
- Sheet "Landmarks": [Name, X_mm, Y_mm, Z_mm, Type(original/derived), Family]
- Sheet "Measurements": [Family, Name, Value_cm, Method, Source Landmarks]
- GUI 新建 **Panel E: Export**

**3.3 坐标导出规则：**
- 内部不变（Y-up, mm）
- 导出时 Z -= CrotchPoint.z
- X(0), Y(0) 待确认

**估计工作量：2–3 天**

---

### Phase 4: Face Anonymization（独立任务）

不变，与 Rev.2 相同。独立于主链路。

**估计工作量：3–4 天**

---

## Dependency Graph (Rev.3)

```
Phase 0: Rule Freezing + YAML Schema Design
    │
    ├── settled.md 冻结
    ├── derived_landmarks.yaml 模板
    └── Q1(已确认)/Q2/Q3 向协作者确认
         │
         v
Phase 1: Geometric Initialization
    │
    ├── 4 种 init_method 实现 (库调用)
    ├── 4 subjects × 14 landmarks → 初始 P₀
    ├── 反算重心坐标 (α, β, γ)
    ├── 跨 subject 稳定性检查
    ├── 微调 + 写入 YAML
    └── 投影验证 (trimesh.proximity.closest_point)
         │
         v
Phase 2: Measurement Engine
    │
    ├── 截面弧长 (Shapely ring.project)
    ├── Geodesic 曲线 (已有引擎)
    └── Euclidean 距离 (numpy)
         │
         v
Phase 3: Results + Excel Export
    │
    ├── 统一结果表
    ├── Excel 导出 (openpyxl)
    └── 坐标导出规则
         │
         v
Phase 4: Face Anonymization (独立)
```

---

## Execution Plan Summary (Rev.3)

| Phase | 内容 | Est. Days | 累计 |
|-------|------|-----------|------|
| **0** | 规则冻结 + YAML schema + 确认 | 1–2 | 1–2 |
| **1** | 几何初始化 + 重心反算 + 稳定性验证 | 3–4 | 4–6 |
| **2** | 弧长/Geodesic/Euclidean 测量 | 2–3 | 6–9 |
| **3** | 统一结果 + Excel 导出 + 坐标规则 | 2–3 | 8–12 |
| **4** | Face anonymization (独立) | 3–4 | 11–16 |
| | **Total（不含 Phase 4）** | **8–12** | |
| | **Total（含 Phase 4）** | **11–16** | |

---

## Rev.2 → Rev.3 Change Log

| Item | Rev.2 | Rev.3 | Reason |
|------|-------|-------|--------|
| Derived landmark 表示 | 每个模块独立的几何方法 | **统一重心坐标参数化 + YAML** | 体型自适应、可微调、统一实现 |
| 轮廓重建 | 自定义 KDTree 拼接 (~30 行) | **`mesh.section()` → Path3D（库内置）** | FastIKD 环境实测确认 |
| 弧长引擎 | 自定义 `arc_length.py` (~50 行) | **Shapely `ring.project()`/`ring.interpolate()`** | 零自定义代码 |
| 主轮廓选择 | 自定义算法 | **`max(polygons_full, key=area)`** | 一行 Shapely |
| Neck landmark Q1 | 选项待确认 | **选项 A 已确认 + 重心坐标微调** | 用户决策 |
| 配置持久化 | 无 | **`config/derived_landmarks.yaml`** | 跨 subject 复用 + 可微调 |
| 工作量 | 20–27 天 | **11–16 天** | 库覆盖 + 统一表示 |
| Phase 结构 | 7 phases (按 V3 模块划分) | **4 phases (按技术层划分)** | 统一表示消除了模块间边界 |
| 环境 | 系统 Python (缺依赖) | **conda FastIKD** | shapely/rtree/networkx 全部可用 |
