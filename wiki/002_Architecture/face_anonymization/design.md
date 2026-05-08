# Face Anonymization（面部匿名化）

> **状态：未实现 — 规划中**
> 等待 `settled.md` 中匿名化约定的冻结。

## 定位

给定两个 landmark 和一个平面，fit 一个圆，将圆投影到 mesh 面部区域，用 PyMeshLab 简化该区域内的三角面片，抹去面部特征。

## 算法语义（草案）

1. 从 `settled.md` 读取定义圆的 landmark 对和平面参数
2. 在指定平面上 fit 一个圆（方式 UNSET）
3. 将圆投影到 mesh 面部表面（投影方式 UNSET）
4. 用 PyMeshLab filter 简化投影区域内的三角面片（具体 filter UNSET）
5. 验证简化后 mesh 拓扑完整性

## 输入契约

- body scan mesh (trimesh.Trimesh)
- landmark pair (两个 settled landmark ID)
- plane definition (from settled)

## 输出契约

- anonymized mesh (新 mesh_id，原 mesh 保留)
- preserved landmark list (匿名化前从区域内提取的 landmark 坐标)

## 正确性标准（预设）

- 匿名化区域不得包含下游 pipeline 需要的 landmark（或已提取保留）
- 匿名化后 mesh 通过与原 mesh 相同的拓扑检查
- 匿名化是不可逆操作；原始 mesh 必须另存

## 已知失败模式（预估）

| 失败模式 | 症状 | 防护方式 |
|---|---|---|
| PyMeshLab 简化引入 non-manifold edges | 下游切片/geodesic 失败 | 简化后拓扑验证 |
| 匿名化区域过大 | 吞掉身体 landmark | 区域内 landmark 检查 |
| 投影方向反了 | 简化了背部而非面部 | 法向约定 + visualization 验证 |

## 当前实现

- 代码路径：无
- 测试路径：无

## 状态

- 已完成：无
- 待实现：全部（需先在 settled.md 冻结匿名化约定）

## 前置阻塞

→ [[../settled]] 中以下字段需先填写：
- 定义圆的 landmark 对
- 定义圆的平面
- 圆的 fit 方式
- 投影方式
- PyMeshLab 具体 filter
- 简化后拓扑要求

上次更新：2026-05-08
