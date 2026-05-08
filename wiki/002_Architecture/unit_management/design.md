# Unit Management

## 定位

处理 SizeStream (mm) 和 CAESAR (m 或 mm) 之间的单位差异。所有运行时几何计算统一在 mm 下进行；导出时恢复为原始单位。

## 算法语义

### 单位推断
```python
extent = max(ptp(vertices, axis=0))
if extent < 10.0:
    original_unit = "m", to_mm_scale = 1000.0
else:
    original_unit = "mm", to_mm_scale = 1.0
```

依据：人体扫描的两个稳定桶
- ~1-3 units tall → meters
- ~1000-3000 units tall → millimeters

### 转换
- `to_runtime_mm_vertices()`: vertices * to_mm_scale
- `from_runtime_mm_vertices()`: vertices_mm / to_mm_scale
- `transform_mm_to_original_units()`: 旋转不变，平移 /= to_mm_scale

## 输入契约

- vertices: np.ndarray (N, 3), raw mesh vertices
- MeshUnitContext: frozen dataclass (original_unit, to_mm_scale)

## 输出契约

- `infer_mesh_unit_context()` → `MeshUnitContext`
- `to_runtime_mm_vertices()` → np.ndarray in mm
- `from_runtime_mm_vertices()` → np.ndarray in original unit
- `transform_mm_to_original_units()` → 4x4 transform in original unit

## 正确性标准

- roundtrip: `from_runtime(to_runtime(v, ctx), ctx) == v`
- transform export: 旋转矩阵不变，仅平移缩放
- 阈值 10.0 对人体扫描有效（人体不会 <10mm 也不会 >10m）

## 已知失败模式

| 失败模式 | 症状 | 防护方式 |
|---|---|---|
| 非人体 mesh（如小零件）| 错误推断为 meters | 阈值仅对 body scan 有效 |
| mesh 单位为 cm | 可能误判为 mm 或 m | 当前不支持 cm（不在已知数据集中） |

## 当前实现

- 代码路径：`unit_utils.py`
- 测试路径：`tests/test_unit_utils.py`

## 状态

- 已完成：m/mm 推断 + runtime 归一化 + 导出还原
- 待实现：无

上次更新：2026-05-08
