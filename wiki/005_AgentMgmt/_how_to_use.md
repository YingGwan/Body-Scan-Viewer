# How to Use This Wiki

## 开始工作

1. 打开 `PROJECT.md` → 了解项目当前状态
2. 按 `005_AgentMgmt/INDEX.md` 的 Boot Protocol 初始化 context
3. 查 `BOOT_MATRIX.md` 确定你的任务需要先读什么
4. 开始工作

## 修改规则

### 修改已定论 (settled.md)
- 必须先在 `002_Architecture/discussion/` 创建讨论记录
- 讨论达成结论后更新 `settled.md`
- 旧定义不删除，标记为 `[SUPERSEDED by ...]`

### 修改 integrity rule
- 不可随意修改，需要明确理由
- active ctx 不得覆盖 integrity rule
- 若规则确实错误，需在 discussion 中记录修改原因

### 修改模块 design.md
- 随时可更新
- 代码实现若与 design 不一致，优先修改代码（除非 design 明确错误）
- 更新后同步更新 `上次更新` 日期

## 添加 Config 参数

`config_loader.py` 有严格 schema 验证，添加新 config key 需要同步修改三处：

1. **JSON 文件**：在 `config/project_config.json` 或 `config/render_config.json` 中添加 key + 对应的 `key__comment`
2. **Python 验证**：在 `config_loader.py` 中：
   - 在对应的 `_require_commented_object()` 调用中添加 key 名称到 keys tuple
   - 添加对应的 `_require_*()` 验证调用
   - 如果是新的 section，创建新的 frozen dataclass
3. **Wiki**：更新 `002_Architecture/data_contracts.md` 中的 AppConfig tree

注意：遗漏任何一步都会导致启动时 `ConfigError`。`_require_commented_object()` 会拒绝 JSON 中的未知 key，也会拒绝缺少 `__comment` 的 key。

## 添加 Derived Landmark / Measurement

`config/derived_landmarks.yaml` 使用独立的 YAML 配置路径（不经过 `config_loader.py`）：

1. **YAML 文件**：在 `config/derived_landmarks.yaml` → `landmarks` section 添加新 landmark（需含 `triangle`, `init_method`, `init_params`, `family`, `weights: null`）；在 `measurements` section 添加对应度量
2. **如需名称映射**：在 `landmark_name_map` 中添加规范名 → 数据集实际名映射
3. **如需新 init_method**：在 `derived_landmarks.py` 中用 `@_register_init("method_name")` 装饰器注册新函数
4. **Wiki**：更新 `settled.md` Derived Landmarks 表 + `data_contracts.md` YAML schema 说明

注意：PyYAML 写入时不保留 YAML 注释。无 `key__comment` 要求。

## 添加新模块

1. 在 `002_Architecture/` 下创建 `new_module/design.md` + `discussion/.gitkeep`
2. 在 `architecture.md` 的模块地图中添加条目
3. 如涉及正确性风险，在 `ctx_integrity/` 添加对应 rule

## 归档

- 被替代的设计 → `002_Architecture/_archive/`
- 历史 agent context → `005_AgentMgmt/_historical/`
- 不删除，只移动
