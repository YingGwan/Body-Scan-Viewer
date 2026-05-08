# Landmark Current Contract

last_updated: 2026-05-08

## 当前有效定义

### SizeStream Landmarks
- 来源：XLSX 动态解析，~199 个 3D landmarks
- 冻结状态：schema 由 XLSX 文件本身定义（动态发现，非 settled 冻结）
- 参考：`settled.md` → 原始 Landmarks — SizeStream 来源

### CAESAR Landmarks
- 来源：`.lnd` 文件解析，73 个 per subject
- 对齐方式：24 旋转 + ICP（`align_caesar_landmarks_to_mesh`）
- 冻结状态：schema 由 `.lnd` 文件本身定义（动态发现，非 settled 冻结）
- 参考：`settled.md` → 原始 Landmarks — CAESAR 来源

### Derived Landmarks
- 当前状态：**尚未定义**
- 需先在 `settled.md` 填写 Derived Landmarks 表

## 变更历史

| 日期 | 变更内容 | 原因 | 影响的下游模块 |
|---|---|---|---|
| 2026-05-08 | 初始记录 | wiki 创建 | — |

## 待定决策

- [ ] 是否需要冻结 SS landmark schema（当前靠 XLSX 动态发现）
- [ ] 是否需要 SS↔CAESAR landmark 名称映射表
- [ ] Derived landmark 生成规则定义
