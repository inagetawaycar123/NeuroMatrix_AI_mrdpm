# W4 ICV 交付说明

> 版本：V1
> 周期：Week4（内部一致性 ICV 落地）

## 1. 范围与目标

- 覆盖对象：卒中主链（NCCT/mCTA/CTP 路径）下的内部一致性检查。
- 目标：
- 完成一套可运行的 ICV 规则集，用于检查“路径 / 量化 / 文本”之间的一致性；
- 将 ICV 结果接入 Agent 主链，并在前端 Processing / Viewer 中可视化；
- 提供可回看、可验收的文档与示例病例。

## 2. 角色与职责

- ICV 归属于 `Logic Reviewer Agent`：
- 对同一次 Agent Run 内的 imaging path、tool_results、analysis_result、report_payload 做内部一致性校验；
- 不直接生成新结论，只对现有结果打标签（pass / warn / fail）。

## 3. 输入输出契约

### 3.1 输入（由 `_tool_icv` 组装）

- `planner_output`：
- `path_decision.imaging_path`
- `path_decision.canonical_modalities`
- `tool_sequence`
- `tool_results`：
- `generate_ctp_maps`（是否成功、生成的模态/切片等）
- `run_stroke_analysis`（核心/半暗带体积、不匹配比等）
- `generate_medgemma_report`（结构化报告 payload，如章节、量化字段）
- `patient_context`：
- 患者基础信息
- `available_modalities` / `hemisphere`
- `analysis_result`：
- 影像分析结果（volume、mismatch 等）
- 可选的报告 payload 快照

### 3.2 输出（`evaluate_icv`）

```jsonc
{
  "success": true,
  "icv": {
    "status": "pass | warn | fail",
    "findings": [
      {
        "id": "R2_mismatch_consistency",
        "status": "pass | warn | fail | not_applicable",
        "message": "中文说明……",
        "details": { "expected_ratio": 1.8, "reported_ratio": 1.1 },
        "suggested_action": "示例：建议人工复核 CTP 量化结果与报告文本。"
      }
    ]
  }
}
```

- 工具层：`_tool_icv` 将 `icv` 部分作为 `tool_results[].structured_output` 返回。
- 报告层：`_tool_generate_medgemma_report` 在生成结构化报告时，将 ICV 写入：

```jsonc
{
  "report_payload": {
    "icv": {
      "status": "warn",
      "findings": [ /* 同上 */ ]
    },
    "...": "其他字段"
  }
}
```

## 4. 规则集概览

> 详细规则清单与中文 message 以 `backend/icv.py` 为准，这里列出分组。

- CTP 相关：
- CTP 可用性与触发链路一致性（是否应有 CTP 却没有 / 不应有却出现）；
- mismatch 比例与核心/半暗带体积的一致性；
- CTP 覆盖与层数合理性。
- 体积与量化：
- 核心体积是否在阈值内（过小 / 过大）；
- 半暗带/核心比是否在合理范围内。
- 模态与章节：
- 仅有 NCCT 时，不应出现 CTA/CTP 章节；
- 存在 CTA/CTP 检查时，报告中不应完全缺失对应章节。
- 路径与 Tool：
- `imaging_path` 与实际执行的 Tool（例如 `generate_ctp_maps`）是否一致。
- 侧别与语气：
- 分析侧别与报告文字中的侧别是否一致；
- 分析 status 与报告措辞（如“无大血管闭塞” vs 分析发现 LVO）是否冲突。

## 5. 前端集成与可视化

### 5.1 Processing 页

- 数据来源：`/api/agent/runs/{run_id}` 的 `tool_results` 与最终 `result.report_result.report_payload.icv`。
- 存储：
- 通过 `static/js/processing.js` 将 `report_payload`（含 `icv`）落盘到 `localStorage["ai_report_payload_<fileId>"]`。
- 展示：
- Agent 面板显示：ICV 总状态 + findings 数量；
- 当 ICV 结果可用时，提前写入 localStorage，供 Viewer 使用。

### 5.2 Viewer 页

- 数据来源：`localStorage["ai_report_payload_<fileId>"]` 中的 `icv`。
- 展示位置：
- 报告区域顶部：插入 ICV 概览块（状态 + 非 pass 的问题列表）；
- 侧边栏固定面板：`#icvStaticPanel` 显示：
- `#icvStaticStatus`：PASS/WARN/FAIL（颜色区分）；
- `#icvStaticIssues`：列出每条非 pass 的 finding（id + message + 建议）。

## 6. 非阻断策略

- ICV 属于质控增强模块，不阻断主链：
- ICV 工具失败（异常 / 输入缺失）不会阻止报告生成，只在日志和 `tool_results` 中标记失败；
- 单条规则 `status = fail/warn` 仅作为提示，由医生结合上下文判断是否需要改写报告。
- 任何“基于 ICV 自动拦截报告”的行为，都需要：
- 完成单独的临床验收；
- 在本文件或新增文档中显式记录规则与触发条件。

## 7. 示例病例（占位）

> 建议在验收时补充至少 2–3 个代表性样例。

- 病例 A：完整 NCCT + mCTA + CTP，存在 mismatch 不一致问题（应触发 `R2_mismatch_consistency`）。
- 病例 B：仅有 NCCT，报告中却出现“CTA 见...”章节（应触发模态/章节不一致规则）。
- 病例 C：分析结果提示 LVO，但报告写“未见明显大血管闭塞”（应触发状态语气不一致规则）。

## 8. 与路线图和周任务的对齐

- 对应 `docs/卒中先锋_agent落地路线图_执行版.md` 中 Week4：
- 通过标准：**规则集 + 可见化 + 验收记录**。
- 对应 `docs/每周任务清单_一页版.md` 中 Week4：
- 已拆解为“规则集设计 / Tool 接入 / 前端展示 / 文档与验收记录”四个子任务。