# trimesh.intersections Lab Report (Rev.2 — FastIKD env)

> Date: 2026-05-08
> Env: conda FastIKD (trimesh 4.11, shapely 2.0.7, networkx 3.2, rtree 1.4, scipy 1.13, open3d 0.19, pymeshlab, igl)
> Subject mesh: csr0052a (15002 verts, 30000 faces, Y-up, mm)

---

## Rev.1 → Rev.2 核心变更

**Rev.1 自己写了轮廓重建算法（~30 行 KDTree 拼接）。Rev.2 发现不需要：**

- `mesh.section()` 返回 **Path3D** 对象，trimesh **已内置轮廓重建**，直接给出有序的 entity 列表，每个 entity 有 `closed` 属性和 `discrete()` 方法返回有序点序列
- `path3d.to_planar()` 转为 Path2D + 4×4 逆变换矩阵，自动提取 **Shapely Polygon**
- Shapely `ring.project()` / `ring.interpolate()` 直接支持弧长定位和比例插值
- **结论：不需要写任何轮廓重建代码。trimesh + shapely 已覆盖全部轮廓操作。**

---

## API 实测结果

### 1. `mesh.section()` → Path3D（核心 API）

| 切面 | Entities | 最大 entity | closed | 弧长/周长 |
|------|----------|------------|--------|----------|
| **Waist** (Y=959) | 3 | 148 pts | True | 629.2mm |
| **Bust** (Y=1136) | 3 | 186 pts | True | 809.1mm |
| **Thigh** (Y=crotch-50) | 2 | 131 pts | True | 502.7mm / 500.2mm |
| **Neck coronal** (Z=NF.z) | 5 | 705 pts | True | 3609mm |
| **Armhole** (oblique) | 1 | 649 pts | True | 3095mm |

**关键发现：**
- **Transverse 切面稳定返回 3 个 entity**（躯干 + 两臂），全部 closed
- **Thigh 切面返回 2 个 entity**（左右腿），通过 centroid_x 区分（+57 vs -135）
- **所有 entity 都已是有序点序列**，不需要自己拼接

### 2. Path3D → Shapely Polygon（弧长和比例定位）

`path3d.to_planar()` → Path2D，内含 `polygons_full` 列表，每个是 Shapely Polygon。

**Waist 实测：**

| Property | Value |
|----------|-------|
| 最大 Polygon 面积 | 29280.7 mm² |
| 周长 | 629.2 mm |
| WaistFront snap dist | **0.00 mm** |
| WaistBack snap dist | **0.01 mm** |
| WaistLeft snap dist | **0.05 mm** |
| WaistRight snap dist | **0.10 mm** |

Landmark snap 距离 < 0.1mm，说明 landmark 坐标与 transverse plane 完美匹配。

**弧长计算（全部用 Shapely，零自定义代码）：**

```python
ring = largest_polygon.exterior          # Shapely LinearRing
pos = ring.project(Point(pt_2d))         # 弧长位置 (mm)
pt = ring.interpolate(target_pos)        # 按弧长定位 → 2D 点
pt_3d = np.array([pt.x, pt.y, 0, 1]) @ to_3d.T  # 逆变换回 3D
```

| 弧长度量 | 值 | SS XLSX 参考值 |
|---------|-----|---------------|
| 总周长 | 629.2mm | W01c = 627.3mm (tape measure) |
| Arc WaistFront→WaistLeft | 157.2mm | W01fl = 153.4mm |
| Arc WaistFront→WaistBack | 308.3mm | — |
| Arc WaistBack→WaistLeft | 151.1mm | W01bl = 152.2mm |

**弧长与 SS 参考值误差 < 4mm (< 2.5%)**，验证了方法的正确性。

**50% 比例定位（WaistDartBackLeft）：**
- WaistBack 出发沿轮廓走 50% × arc(WaistBack→WaistLeft) = 75.5mm
- 定位点: `[-115.3, 959.1, -89.2]`
- 位于腰部后方偏左位置，符合解剖预期

### 3. `slice_mesh_plane()` — cap=False 可用，cap=True 需要 triangle 引擎

- `cap=False`: Upper 9255v/17679f, Lower 6847v/12871f。可用于面部匿名化区域提取。
- `cap=True`: 失败 — "No available triangulation engine"。需要 `pip install triangle` 或 `mapbox-earcut`。FastIKD 有 mapbox_earcut 但未被 trimesh 自动识别。

### 4. `ray.intersects_location()` — 可用（FastIKD 有 rtree）

在 FastIKD 环境下 rtree 可用，ray casting 正常工作。

---

## Neck Landmark 定位方案终测

### 4 个颈部 Landmark 的 Y 坐标差异

```
NeckFront: Y = 1291    ← 比其他三个低 ~46mm！
NeckBack:  Y = 1334
NeckLeft:  Y = 1337
NeckRight: Y = 1335
```

NeckFront 在锁骨前方（较低），NeckBack/Left/Right 在颈根部（较高）。**四点不在同一水平面上。**

### V3 原方法实测（两平面交线 + ray casting）

| 新 Landmark | 交线定义 | Ray hit Y | 结果 |
|------------|---------|-----------|------|
| NeckFrontLeft | x=NL.x(15.6), z=NF.z(-12.7) | **1283.1** | 在肩-胸交界处，不在颈部 |
| NeckFrontRight | x=NR.x(-111.8), z=NF.z(-12.7) | **1283.8** | 同上 |
| NeckBackLeft | x=NL.x(15.6), z=NB.z(-94.8) | **1323.5** | 在颈部！合理位置 |

**关键发现：**
- **NeckBack 系列的交点合理**（Y=1323，在颈部范围内）
- **NeckFront 系列的交点太低**（Y=1283，在锁骨下方）——因为 NeckFront 本身就比其他点低 46mm，两平面交线在 z=-12.7 处穿过的是胸部上方，不是颈部

### 判断：V3 docx 的颈部 landmark 方案存在几何歧义

这不是实现问题，而是**需求定义本身的歧义**。V3 docx 中 Plane 1 的 coronal plane 经过 NeckFront，但 NeckFront 比 NeckLeft/Right 低 46mm，导致交线在"颈部正面"穿过的不是颈部表面而是上胸部表面。

**需要向协作者确认的核心问题：** NeckFrontLeft 应该在哪个高度？
- 选项 A: NeckFront 的 Y 高度（1291）→ 交点在上胸部
- 选项 B: NeckLeft 的 Y 高度（1337）→ 交点在颈部但远离 NeckFront
- 选项 C: 用其他方式定义（如颈部截面轮廓上的特定位置）

---

## V3 需求 ↔ 库能力覆盖表

| V3 需求 | 技术方案 | 用到的库 | 自定义代码量 |
|---------|---------|---------|------------|
| Waist/Bust 截面轮廓 | `mesh.section()` → Path3D | trimesh | 0 |
| 轮廓重建 + 有序化 | Path3D 内置 | trimesh | 0 |
| 弧长计算 | `ring.project()` | shapely | 0 |
| 50% 弧长比例定位 | `ring.interpolate()` | shapely | 0 |
| 2D↔3D 转换 | `path.to_planar()` + inv(to_3d) | trimesh | ~5 行 |
| Landmark snap 到轮廓 | `ring.project(Point(...))` | shapely | ~3 行 |
| 主轮廓选择 | `max(polygons_full, key=area)` | shapely | 1 行 |
| Thigh 左右腿区分 | centroid_x 比较 | numpy | 1 行 |
| Neck landmarks | ray casting 沿交线 | trimesh.ray | ~10 行 |
| Armhole Z 极值 | `argmax/argmin` on contour Z | numpy | 2 行 |
| Geodesic curves | 已有 `geodesic_utils.py` | potpourri3d | 0 |
| Mesh boolean cut | `slice_mesh_plane(cap=False)` | trimesh | 0 |
| Face region extraction | 两次 `slice_mesh_plane` | trimesh | ~5 行 |
| Excel export | `openpyxl.Workbook` | openpyxl | ~30 行 |

**自定义代码总量：~60 行业务逻辑 + 配置。** 轮廓重建、弧长计算、比例定位、polygon 提取全部由库完成。

---

## 对 V3 Implementation Plan 的技术路线修正

### 修正 1: 不需要写轮廓重建算法

Rev.1 plan 的 Phase 1 估计 3-4 天用于"切片与轮廓原型"。实测发现 `mesh.section()` 已内置轮廓重建，核心操作是：
```python
path3d = mesh.section(plane_origin=origin, plane_normal=normal)
path2d, to_3d = path3d.to_planar()
polygon = max(path2d.polygons_full, key=lambda p: p.area)
ring = polygon.exterior
```
4 行代码替代了 30+ 行自定义轮廓重建。Phase 1 **可缩短至 1-2 天**（主要时间在验证各切面的 edge case）。

### 修正 2: 弧长和比例定位是 Shapely 一行代码

Rev.1 plan 的 Phase 3 估计 2-3 天用于"弧长引擎"。实测用 Shapely：
```python
arc_position = ring.project(Point(pt_2d))       # 弧长位置
target_point = ring.interpolate(target_pos)      # 比例定位
```
弧长引擎不需要自己写。Phase 3 **可缩短 1-2 天**。

### 修正 3: Neck landmark 需要额外确认

两平面交线法在 NeckFront 系列上产生了不在颈部的交点。需要与协作者确认方案后再实现。**这是一个需求问题，不是技术问题。**

### 修正 4: 工作量重估

| Phase | Rev.1 估计 | Rev.2 (FastIKD) | 原因 |
|-------|-----------|-----------------|------|
| 0 规则冻结 | 1-2d | **2-3d** | 颈部方案需要额外确认 |
| 1 切片原型 | 3-4d | **1-2d** | trimesh Path3D 内置轮廓重建 |
| 2 Neck | 2-3d | **1-2d** | 取决于确认结果 |
| 3 Arc + Waist/Bust | 5-6d | **3-4d** | Shapely 弧长零代码 |
| 4 Thigh + Armhole | 3-4d | **2-3d** | 库覆盖 |
| 5 Results + Excel | 2-3d | **2d** | |
| 6 Coord export | 1d | **1d** | |
| 7 Face anon | 3-4d | **3-4d** | 不变 |
| **Total** | **20-27d** | **15-21d** | 库减少了 ~5d 自定义工作 |

---

## 额外发现：弧长验证

| 弧长 | mesh.section 计算 | SS XLSX 参考值 | 误差 |
|------|-------------------|---------------|------|
| Waist 周长 | 629.2mm | 627.3mm (W01c tape) | +1.9mm (0.3%) |
| Waist Front→Left arc | 157.2mm | 153.4mm (W01fl) | +3.8mm (2.5%) |
| Waist Back→Left arc | 151.1mm | 152.2mm (W01bl) | -1.1mm (0.7%) |

**误差 < 2.5%**。SS 的 tape measure 是软尺贴合体表，mesh.section 是平面切割后的轮廓——两者语义略有不同（软尺贴合曲面 vs 平面截面），1-4mm 差异是正常的。

---

## 结论

**FastIKD 环境下的 trimesh + shapely 已经覆盖了 V3 全部切片和弧长需求。** 核心技术路线从"自己造轮子"变成了"组装库 API"，大幅降低了实现风险和工作量。唯一需要注意的是：
1. Neck landmark 定位的几何歧义需要与协作者确认
2. `slice_mesh_plane(cap=True)` 需要安装 `triangle` 或 `mapbox-earcut` 并让 trimesh 识别
3. 所有计算应在 FastIKD conda env 下运行，不要用系统 Python（缺少 rtree/shapely/networkx）
