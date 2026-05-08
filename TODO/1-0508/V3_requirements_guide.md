# ADE Polyscope Viewer V3 — Requirements Guide

> For: Simeon (collaborator) & development reference
> Source: ADE Polyscope Viewer Development V3.docx
> Date: 2026-05-08

---

## Why V3

V3 的目标是从 3D 人体扫描中自动提取**服装版型所需的关键尺寸**。当前的 Viewer 能加载扫描数据、对齐 landmark、计算两点间的 geodesic 距离，但还不能做服装设计最核心的事：**沿身体横截面量围度、定位省道（dart）位置、输出版型表**。

V3 要补上这条链路：3D 扫描 → 截面轮廓 → 弧长测量 → 省道定位点 → Excel 输出。

---

## 需要什么：6 组新测量

### 1. 颈部 4 个新 landmark — 领口形状

**为什么需要：** 领口（neckline）不是一个简单的圆。它在前面较低（锁骨上缘），后面较高（颈根），左右各有一个拐点。服装版型需要知道这 4 个拐点的精确位置，才能画出合体的领口线。

**需要什么：**
- 4 个新点：NeckFrontLeft, NeckFrontRight, NeckBackLeft, NeckBackRight
- 它们是前颈线和侧颈线的交叉点
- 配套测量：相邻颈部 landmark 之间的表面弧长 + 直线距离

**V3 的定位方法：**
- 在 NeckFront 处做一个 Coronal plane（冠状面，把人分成前后两半）
- 在 NeckLeft 处做一个 Sagittal plane（矢状面，把人分成左右两半）
- 两平面交线与颈部表面的交点就是 NeckFrontLeft

```
           NeckBack (Y=1334)
              ╱    ╲
    NeckLeft ●      ● NeckRight (Y=1335)
    (Y=1337)  ╲    ╱
        NeckBackLeft ◆  ◆ NeckBackRight    ← 新
              │    │
        NeckFrontLeft ◆  ◆ NeckFrontRight  ← 新
              ╲    ╱
           NeckFront (Y=1291)

    ◆ = 新 landmark    ● = 已有 landmark
```

**实测发现的问题：** NeckFront 比其他三个点低了约 46mm（锁骨 vs 颈根）。用 V3 方法定位 NeckFrontLeft 时，两平面交线穿过的是上胸部表面（Y≈1283），不在颈部范围内。NeckBack 系列则定位正常（Y≈1323）。**需要确认 NeckFrontLeft 应在哪个高度。**

---

### 2. 腰部和胸部 6 个省道定位点 — 衣身贴合

**为什么需要：** 省道（dart）是服装中的楔形褶缝，让平面布料贴合人体曲面。省道的位置和大小直接决定衣服是否合体。V3 需要在腰围和胸围的截面上精确定位 6 个省道锚点。

**需要什么：**

腰围层面（4 个新点）：

| 新 Landmark | 定位方法 |
|------------|---------|
| Waist Dart Front Left | 三平面交叉：Bust 层的辅助平面投射到腰围截面 |
| Waist Dart Front Right | 对称 |
| Waist Dart Back Left | 从 WaistBack 沿轮廓走 **50%** × arc(WaistBack→WaistLeft) |
| Waist Dart Back Right | 对称 |

胸围层面（2 个新点）：

| 新 Landmark | 定位方法 |
|------------|---------|
| Waist Dart Upper Back Left | 从 BustBack 沿轮廓走 **50%** × arc(BustBack→BustLeft) |
| Waist Dart Upper Back Right | 对称 |

```
    俯视图（Bust + Waist 截面叠加）

                Apex Left
                   ●
                  ╱
    Bust Left ●  ╱  ● Bust Front (Bust With Drop Front)
              │ ╱   │
              │╱    │
    ─ ─ ─ ─ ─◆─ ─ ─│─ ─ ─ ─   ← Waist Dart Front Left (三平面交叉)
              │     │
    Waist Left ●    ● Waist Front
              │     │
    ─ ─ ─ ─ ─◆─ ─ ─ ─ ─ ─ ─   ← Waist Dart Back Left (50% 弧长)
              │
    Bust Back ●     ● Waist Back
              │
    ─ ─ ─ ─ ─◆─ ─ ─ ─ ─ ─ ─   ← Waist Dart Upper Back Left (Bust 层 50% 弧长)
```

配套弧长测量（V3 docx 中的 A/B/C/D）：

| 标签 | 测量内容 |
|------|---------|
| A | WaistFront → WaistDartFrontLeft 弧长 |
| B | WaistBack → WaistDartBackLeft 弧长 |
| C | BustFront → BustLeft 弧长 |
| D | BustFront → ApexLeft 弧长 |
| 可选 | ApexLeft → WaistDartFrontLeft 直线距离 |

---

### 3. 大腿横截面 4 段弧长 — 裤装贴合

**为什么需要：** 裤腿版型需要知道大腿截面的前后左右分布。同样的大腿围，有人前侧肌肉发达、有人后侧更厚——4 段弧长反映了这种不对称性。

**需要什么：**
- 在大腿上部横截面上，用 Front/Back/Left/Right 四个 landmark 把轮廓分为 4 段
- 分别量出每段弧长
- 左右腿各一组

```
    大腿横截面俯视

         Front
          ●
         ╱ ╲
    Left ●   ● Right
         ╲ ╱
          ●
         Back

    → 4 段弧长: Front→Left, Left→Back, Back→Right, Right→Front
```

---

### 4. 臂孔和肩-胸曲线 — 袖笼设计

**为什么需要：** 袖笼（armhole）的深度和形状决定了手臂活动范围和肩部舒适度。从肩点到胸部最高点的体表曲线长度是前衣身长度的关键尺寸。

**需要什么：**

(a) **4 个新 Armhole Depth landmark：**
- 在肩点（ShoulderLeft）和腋下点（ArmpitLeft）之间做一个平面
- 在该平面与 mesh 的截面轮廓上，找 Z 最大点（Front Depth）和 Z 最小点（Back Depth）
- 左右各一组

```
    Armhole 截面（从侧面看）

    Shoulder ●─────────── ●  Armhole Depth Front
              ╲         ╱
               ╲       ╱
                ╲     ╱
                 ● Armpit
                ╱
               ╱
    Armhole Depth Back ●
```

(b) **4 条体表曲线长度：**

| 曲线 | 起点 | 终点 | 方法 |
|------|------|------|------|
| 肩→胸（左） | Mid Shoulder Left | Apex Left | Geodesic（体表最短路径） |
| 肩→胸（右） | Mid Shoulder Right | Apex Right | Geodesic |
| 胸→下胸（左） | Apex Left | Lower Bust Left | Geodesic |
| 胸→下胸（右） | Apex Right | Lower Bust Right | Geodesic |

> V3 docx 对这 4 条曲线写的是 "in vertical as value outputs"。这可能指 geodesic 体表路径，也可能只要 Y 方向投影（高度差）。需要确认。

---

### 5. 坐标系和 Excel 输出 — 数据交付

**为什么需要：** 上述所有测量最终要交付给版型师使用，需要统一的坐标约定和标准化的输出格式。

**需要什么：**
- 所有 landmark 的 XYZ 坐标输出到 Excel
- 所有弧长/距离测量值以 **cm** 输出到 Excel，并标注 measurement family（Neck / Waist / Bust / Thigh / Armhole）
- 坐标约定：Z(0) = Crotch Point 的 Z 坐标（V3 docx 定义）

---

### 6. 面部匿名化 — 数据隐私

**为什么需要：** 3D 人体扫描包含面部信息，在共享数据时需要去除面部特征以保护隐私。

**需要什么：**
- 从 Chin（下巴）到 Head Circum Front（前额）区域降低多边形密度
- 使用 PyMeshLab 进行区域性 mesh decimation
- V3 docx 提到 "preserve some feature"——可能需要保留某些面部结构轮廓

---

## 技术路线

### 核心发现：库已覆盖几乎所有计算

在 FastIKD conda 环境中实测，发现不需要自己写轮廓重建和弧长引擎：

```
mesh.section(origin, normal)        → Path3D（有序轮廓，trimesh 内置）
path3d.to_planar()                  → Path2D + Shapely Polygon
polygon.exterior.project(Point)     → 弧长位置（Shapely 一行）
polygon.exterior.interpolate(pos)   → 按弧长比例定位（Shapely 一行）
```

实测 Waist 截面弧长与 SS tape measure 参考值误差 < 2.5%，验证了方法的正确性。

### 执行顺序

```
Phase 0  冻结规则 + 确认歧义        ← 不写代码
Phase 1  切片验证（Waist/Bust/Thigh）← 最稳定的场景先做
Phase 2  Neck landmarks             ← 取决于歧义确认结果
Phase 3  弧长引擎 + Waist/Bust dart
Phase 4  Thigh 分段 + Armhole + Geodesic 曲线
Phase 5  统一结果收集 + Excel 导出
Phase 6  坐标导出规则
Phase 7  面部匿名化（独立研究任务）
```

### 各需求的技术实现

| 需求 | 做什么 | 用什么库 | 自定义代码 |
|------|--------|---------|-----------|
| 截面轮廓 | `mesh.section()` | trimesh | 0 行 |
| 弧长 | `ring.project()` | Shapely | 0 行 |
| 比例定位 | `ring.interpolate()` | Shapely | 0 行 |
| 主轮廓选择 | `max(polygons, key=area)` | Shapely | 1 行 |
| 左右腿区分 | centroid X 比较 | numpy | 1 行 |
| Neck 定位 | ray casting 沿交线 | trimesh.ray | ~10 行 |
| Armhole 极值 | contour 上 argmax/argmin Z | numpy | 2 行 |
| Geodesic 曲线 | 已有引擎 | potpourri3d | 0 行 |
| Mesh 切割 | `slice_mesh_plane()` | trimesh | 0 行 |
| Excel 导出 | `openpyxl.Workbook` | openpyxl | ~30 行 |

自定义代码总量约 60 行。绝大部分工作是**业务规则配置**（哪个 landmark 做什么平面、哪段弧长对应什么测量名称），不是算法实现。

---

## Questions for Simeon

在开始实现之前，需要确认以下问题。这些都是 V3 docx 中的开放项或实测中发现的歧义。

### Q1. NeckFrontLeft 应该在哪个高度？

**背景：** NeckFront 比 NeckLeft/NeckRight 低约 46mm（锁骨 vs 颈根）。用 V3 描述的两平面交线法定位 NeckFrontLeft 时，交点落在上胸部（Y≈1283），而不是颈部（Y≈1330）。NeckBackLeft 则能正确定位在颈部。

**选项：**
- A: 接受 Y≈1283（上胸部）的定位——这是 V3 方法的数学结果
- B: 改为在 NeckLeft 的 Y 高度做 transverse 切片，在截面轮廓上找最接近 NeckFront Z 坐标的点
- C: 其他方法

### Q2. Plane 3 是否需要？

**背景：** V3 docx 对 NeckFrontLeft 的定位提问 "Do we need Plane 3 for anchoring it at neck surface?" 我们实测发现两平面交线只有 1 个 mesh 表面交点，不需要第三平面来消歧。

**建议答案：** 不需要——mesh 表面几何约束已替代 Plane 3 的功能。

### Q3. 5.2/5.3 的 "in vertical" 是什么意思？

**背景：** V3 docx 对 Mid Shoulder → Apex 和 Apex → Lower Bust 曲线写的是 "in vertical as value outputs"。

**选项：**
- A: Geodesic surface distance（沿体表的最短路径长度）
- B: Y 方向投影（纯高度差 |y₁ - y₂|）
- C: 沿体表的垂直方向曲线长度（不是最短路径，而是尽量沿 Y 方向走）

### Q4. 面部匿名化 "preserve some feature" 的含义？

**背景：** V3 docx Notes 1.1 写 "Identify the Chain point of face, preserve some feature"。

**选项：**
- A: 纯 uniform decimation（降低多边形数量，不保留特定结构）
- B: 保留眼眶/鼻梁等骨骼轮廓，只抹平软组织细节
- C: 其他

### Q5. Waist Dart Front 使用的是 "Bust With Drop Front" 还是 "BustFront"？

**背景：** V3 docx 写 "Bust Front (Bust with Drop Front)"。SS XLSX 中两者是不同的 landmark（位置不同）。

**确认：** 是否使用 `Bust With Drop Front`（Y=1133, Z=58）而非 `BustFront`（Y=1136, Z=57）？

### Q6. 坐标系 X(0) 和 Y(0) 如何定义？

**背景：** V3 docx 定义了 Z(0) = Crotch Point，但对 X(0) 和 Y(0) 写的是 "remine the X, Y (0)"，未明确。

**选项：**
- A: Y(0) = 地面（保持当前 SizeStream 约定），X(0) = 人体中心线
- B: 其他

### Q7. 大腿弧长 "in horizon (X)" 的含义？

**背景：** V3 docx 对大腿四段弧长写 "surface lengths of four segments in horizon (X) as value outputs"。

**选项：**
- A: 在 transverse plane 横截面上的弧长（最可能的理解）
- B: 仅 X 方向的投影长度
