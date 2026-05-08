# Integrity Rules Index

这些规则防止静默错误：pipeline 能跑完，但结果是错的。

| File | Rule IDs | Topic |
|---|---|---|
| landmarkIntegrityRule.md | L1-L4 | landmark 定义一致性、对齐、同名不同义 |
| anonymizationIntegrityRule.md | A1-A4 | 匿名化区域边界、landmark 保留、拓扑完整性 |
| meshTopologyIntegrityRule.md | M1-M3 | mesh 拓扑对切片/geodesic 的影响 |
| measurementIntegrityRule.md | E1-E3 | 度量公式唯一性、单位一致性 |

## 使用规则

- 涉及 landmark、切片、度量的任务，必须先读对应 integrity rule。
- active ctx 不得覆盖 integrity rule。
- integrity rule 标注 `[CODE ANCHOR]` 的项在代码中有对应实现。
