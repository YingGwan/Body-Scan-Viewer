# Mesh Slicing（切片）

> **状态：未实现 — 规划中**
> 等待 `settled.md` 中切面定义约定的冻结。

## 定位

在指定 landmark 处定义切面，用该平面切 mesh，得到截面轮廓（cross-section contour）。两个切片的交线（或交线与 mesh 表面的交点）产生新的 derived landmark。

## 算法语义（草案）

### 切片
1. 从 `settled.md` 读取切面定义约定（过某 landmark 的某方向平面）
2. 用平面切 mesh，得到一组有序截面轮廓点
3. 截面轮廓可能是 closed 或 open

### 切片交线 → Derived Landmarks
1. 给定两个切片的截面轮廓
2. 计算交线或交点
3. 交点坐标 = 新的 derived landmark
4. 生成规则冻结在 `settled.md` Derived Landmarks 表

## 输入契约

- body scan mesh (trimesh.Trimesh, runtime mm)
- landmark position (from settled schema)
- plane definition convention (from settled)

## 输出契约

- CrossSectionContour: ordered 3D points, is_closed flag
- Derived landmark: 3D position + generation rule reference

## 正确性标准（预设）

- 切面定义必须引用 settled 中的约定
- 空截面必须显式报错（不返回空列表）
- Derived landmark 生成规则变更 = 新 ID

## 已知失败模式（预估）

| 失败模式 | 症状 | 防护方式 |
|---|---|---|
| 切面未与 mesh 相交 | 空截面 | 显式 error（不静默返回空） |
| 两个切片不相交 | 无 derived landmark | 显式报告 |
| Mesh 拓扑有洞 | 截面轮廓不闭合 | is_closed flag |

## 当前实现

- 代码路径：无
- 测试路径：无

## 状态

- 已完成：无
- 待实现：全部（需先在 settled.md 冻结切面定义约定和 derived landmark 规则）

## 前置阻塞

→ [[../settled]] 中以下字段需先填写：
- 切面由什么定义
- 切面法向约定
- Derived Landmarks 表

上次更新：2026-05-08
