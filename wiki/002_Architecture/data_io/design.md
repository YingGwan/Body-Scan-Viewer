# Data IO

## 定位

负责所有文件 I/O：启动时自动扫描数据文件夹构建 catalog，解析 SizeStream XLSX landmark 文件，解析 CAESAR .lnd 文件，导出配准结果。配置文件的加载和验证也属此模块。

## 算法语义

### 文件夹扫描
- 扫描 `SIZE_STREAM/` 中的 `SS_OUT_*.obj`，通过正则提取 subject ID
- 扫描 `CAESAR/` 中的 `csr*.ply` + 匹配的 `.lnd`
- 扫描 `SIZE_STREAM/` 中的 `*.xlsx`
- 检测 subject ID 不匹配（如 csr2019a vs csr2119a）
- 所有错误收集到 `catalog.scan_errors`，不抛异常

### XLSX 解析
- Header 行动态发现 `SS_OUT_csr*` 列（不硬编码列号）
- 三行组格式：第一行有名称 + 后两行 NaN = 3D landmark (X, Y, Z)
- 单行（非三行组）= scalar measurement

### LND 解析
- 格式：`idx quality vertex_idx X Y Z value NAME [NAME...]`
- 编码 fallback：latin-1 → utf-8 → utf-8-sig
- 多词名称通过 `' '.join(parts[7:])` 保留
- len(parts) < 8 的行自动跳过（header 行）

### JSON 配置加载
- 两个 JSON 文件：`project_config.json` + `render_config.json`
- 每个 key 必须有 `key__comment`
- 启动时完整 schema 验证，失败即 raise

### YAML 配置加载（derived landmarks）
- 文件：`config/derived_landmarks.yaml`（version: 1）
- 由 `derived_landmarks.py:load_derived_landmark_config()` 懒加载（首次计算 derived landmarks 时触发）
- 验证：version 字段、landmarks/measurements section 存在性、每个 landmark 的 triangle (len=3)、init_method、family
- 写入：`derived_landmarks.py:save_weights_to_yaml()` — 单 landmark 权重原地更新
- 注意：PyYAML 不保留 YAML 注释（已知限制）
- 与 JSON 配置独立：不经过 `config_loader.py`，无 `key__comment` 要求

## 输入契约

- SS OBJ: trimesh-loadable mesh file
- SS XLSX: Sheet1, header 行含 `SS_OUT_csr*`
- CAESAR PLY: trimesh-loadable mesh file
- CAESAR LND: text file, space-separated, typically latin-1 (with utf-8/utf-8-sig fallback)
- Config JSON: UTF-8, schema version 1
- Config YAML: UTF-8, schema version 1 (`config/derived_landmarks.yaml`)

## 输出契约

- `DataCatalog`: 完整的 subjects dict + errors
- `load_ss_landmarks()`: `{subject_ids, col_indices, scalar_measurements, landmarks_3d}`
- `parse_lnd()`: `{name: np.array([x, y, z])}`, 73 landmarks
- `AppConfig`: frozen dataclass tree, singleton `APP_CONFIG`

## 正确性标准

- scan_data_folders 永不抛异常
- XLSX 动态列发现（不依赖硬编码列号）
- LND 解析保留多词名称完整性
- 配置验证拒绝未知 key、缺失 comment、超范围值

## 已知失败模式

| 失败模式 | 症状 | 防护方式 |
|---|---|---|
| XLSX 被 Excel 占用 | parse 失败 | 错误收集到 scan_errors |
| .lnd 编码非 latin-1 | 读取失败 | 三种编码 fallback |
| Subject ID 拼写不一致 | 部分 subject 不完整 | scan_errors 警告 ID mismatch |
| config JSON 格式错误 | 启动崩溃 | ConfigError with line:col |

## 当前实现

- 代码路径：`data_loader.py`, `config_loader.py`
- 测试路径：`tests/test_data_loader.py`, `tests/test_config_loader.py`

## 状态

- 已完成：文件夹扫描、XLSX 解析、LND 解析、JSON 配置系统、YAML 配置加载/保存
- 待实现：无

上次更新：2026-05-08
