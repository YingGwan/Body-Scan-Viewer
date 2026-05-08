# Truth Ladder

## 优先级

1. `settled.md` 中冻结的定义：坐标系、单位、landmark schema（含派生规则）、ICP 配准约定、度量公式
2. 当前代码 + tests
3. `ctx_integrity/` 正确性规则
4. `002_Architecture/data_contracts.md` 和各模块 `design.md`
5. `005_AgentMgmt/active/ctx_*` 当前合约
6. `PROJECT.md` / roadmap
7. `001_Inbox/` / `_archive/` / `_historical/`

## 关键裁定

- 代码输出与 settled 的度量公式或 landmark 定义冲突 → 默认怀疑代码有 bug。
- active ctx 与 settled 冲突 → 以 settled 为准。
- settled 中标注 UNSET 的项 → 不做假设，不实现相关代码。
- 测试断言与 settled 不一致 → 修改测试（settled 为准）。
