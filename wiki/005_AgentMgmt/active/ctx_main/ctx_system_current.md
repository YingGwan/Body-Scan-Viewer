# System Current State

last_updated: 2026-05-08

## 项目阶段

**Phase 1 完成**：SizeStream/CAESAR 双源查看器，含 ICP 配准、landmark 距离比较、geodesic 测量。
**Phase 2 规划中**：面部匿名化、切片、derived landmarks、扩展度量。

## 代码现状

| 模块 | 文件 | 状态 |
|------|------|------|
| Entry point | `main.py` | stable |
| Config loader | `config_loader.py` | stable |
| Geometry backend | `geometry_backend.py` | stable |
| GUI panel | `gui_panel.py` | stable |
| Data loader | `data_loader.py` | stable |
| Registration | `registration.py` | stable |
| Geodesic utils | `geodesic_utils.py` | stable |
| Unit utils | `unit_utils.py` | stable |
| Color bar | `colorBar.py` | stable (legacy style) |

## 测试现状

测试文件在 `tests/` 目录下，覆盖所有核心模块。运行方式：`pytest tests/`

## 数据现状

- 3 个完整 subject pairs (csr0052a, csr0283a, csr1921a)
- 1 个 ID 不匹配 (csr2019a SS vs csr2119a CAESAR)
- SizeStream: ~199 3D landmarks, ~263 scalar measurements
- CAESAR: 73 landmarks per subject (.lnd)

## 当前阻塞

无代码阻塞。Phase 2 需先在 `settled.md` 做决策。
