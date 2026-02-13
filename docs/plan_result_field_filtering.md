# 工具结果智能裁剪方案（Result Field Filtering）

## 问题描述

多步骤计划中，步骤1/2返回大量列表数据（如20+水库×25字段），executor 的 `_format_execution_results` 用 `str(output)[:500]` 硬截断到500字符，导致后续 LLM 步骤只看到第一个水库的部分数据，最终结果错误。

即使不截断，把全量数据塞给合成 LLM 也会导致响应慢、结果不准确。

## 根因

1. 工具的 `get_prompt_description()` 不输出返回值字段信息，LLM 规划时不知道工具返回什么字段
2. executor 对 dict 类型结果一律 `str()[:500]` 硬截断，无法按需裁剪
3. 没有机制让 LLM 在计划阶段声明"后续步骤只需要哪些字段"

## 改动清单

### 改动1：base.py — 新增 OutputField + output_fields 属性 + get_prompt_description 输出返回字段

- 新增 `OutputField` 模型（name + description）
- `BaseTool` 新增 `output_fields` 属性（默认空列表，向后兼容）
- `get_prompt_description()` 末尾追加返回字段信息

### 改动2：工具文件 — 从接口文档提取 output_fields

按优先级分批补充，接口文档在 `开发资料/api接口清单/` 下：

**P0（必须，高频被多步骤引用）**：
- basin_info.py: `get_reservoir_flood_list`, `get_river_flood_list`, `get_station_list`, `get_reservoir_info`, `get_sluice_info`, `get_flood_dam_info`, `get_flood_storage_area`
- hydro_monitor.py: `query_reservoir_last`, `query_river_last`, `query_rain_sum`, `query_reservoir_process`, `query_river_process`, `query_rain_process`
- flood_otherbusiness.py: `monitor_rsvr_now`, `monitor_rsvr_track`, `mike_rsvr_info`, `mike_gate_all`

**P1（建议，中频使用）**：
- rain_control.py 中的降雨相关工具
- hydromodel_resultget.py 中的模型结果工具
- damage_assess.py 中的避险安置工具

**P2（后续按需补充）**：其余工具

### 改动3：planner.py — 计划 JSON 格式增加 result_fields 字段

- 步骤 JSON 增加 `"result_fields": ["stcd", "stnm", "ttcp"]`
- 增加提示词说明：从工具"返回字段"中选择，对大列表工具务必只选所需字段
- 步骤解析处增加 `result_fields` 的提取

### 改动4：executor.py — 字段裁剪替换硬截断

- `_format_execution_results` 增加 `plan_steps` 参数，按 `result_fields` 裁剪
- 新增 `_filter_result_fields` 方法（支持 dict/list 数据结构）
- 安全兜底截断从 500 提升到 8000
- `_execute_with_llm` 调用处传入 plan

### 改动5：controller.py — 同步适配

- `_format_execution_results` 增加同样的字段裁剪逻辑

## 效果预期

以"统计各水库库容"为例：
- 改动前：20水库×25字段 ≈ 15000字符 → str()[:500] → LLM只看到1个水库 → 错误
- 改动后：20水库×4字段(裁剪后) ≈ 1200字符 → LLM看到全部水库关键数据 → 正确
