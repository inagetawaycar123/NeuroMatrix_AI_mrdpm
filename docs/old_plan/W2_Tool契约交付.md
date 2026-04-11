# W2 Tool 契约交付（冻结版，按真实工作流）

文档状态：Frozen (Week2 Redo)  
更新日期：2026-03-13  
边界：仅文档冻结，不改业务代码

## 1. Tool 契约字段（统一）

每个 Tool 必须包含以下固定字段：
1. `tool_name`
2. `目的`
3. `现有实现映射`
4. `applicability`（适用路径）
5. `precondition`（触发前置条件）
6. `输入`
7. `输出`
8. `错误码`
9. `超时`
10. `幂等性`
11. `重试策略`

## 2. Tool 总表（7个）

### 2.1 `detect_modalities`
- tool_name：`detect_modalities`
- 目的：识别并归一化模态组合，产出路径判定输入。
- 现有实现映射：`backend/app.py:4465`、`backend/app.py:972`。
- applicability：所有路径必走。
- precondition：存在 `available_modalities` 或上传文件集合。
- 输入：
  - `available_modalities(raw): string[]` 或上传文件集合
- 输出：
  - `raw_modalities: string[]`
  - `canonical_modalities: string[]`
  - `imaging_path: ImagingPath`
- 错误码：`TOOL_INPUT_INVALID`、`TOOL_EXECUTION_FAILED`
- 超时：`30s`
- 幂等性：强幂等
- 重试策略：输入错误不重试，临时IO错误重试 1 次

### 2.2 `load_patient_context`
- tool_name：`load_patient_context`
- 目的：按 `patient_id` 读取病例上下文与偏侧字段。
- 现有实现映射：`backend/app.py:2569`、`backend/app.py:2846`、`backend/app.py:2985`。
- applicability：所有路径必走。
- precondition：`patient_id` 有效。
- 输入：
  - `patient_id: int`
- 输出：
  - `context_struct: object`
  - `hemisphere: right|left|both`
  - `missing_flags: string[]`
- 错误码：`TOOL_INPUT_INVALID`、`TOOL_EXECUTION_FAILED`
- 超时：`15s`
- 幂等性：强幂等
- 重试策略：查询超时重试 2 次；不存在患者不重试

### 2.3 `generate_ctp_maps`
- tool_name：`generate_ctp_maps`
- 目的：在 `NCCT+mCTA` 路径下生成 CTP 灌注图（MRDPM）。
- 现有实现映射：`backend/app.py:1075`、`backend/app.py:1093`。
- applicability：仅 `ncct_mcta`。
- precondition：
  - `imaging_path == ncct_mcta`
  - 存在 `ncct/mcta/vcta/dcta`
  - 不存在真实 `cbf/cbv/tmax`
- 输入：
  - `file_id: string`
  - `patient_id: int`
  - `canonical_modalities: string[]`
- 输出：
  - `ctp_generated: bool`
  - `generated_modalities: [cbf?,cbv?,tmax?]`
  - `artifacts_ref: string[]`
- 错误码：`TOOL_NOT_APPLICABLE`、`TOOL_DEPENDENCY_MISSING`、`TOOL_TIMEOUT`、`TOOL_EXECUTION_FAILED`
- 超时：`1200s`
- 幂等性：弱幂等
- 重试策略：超时/临时失败重试 1 次，依赖缺失不重试

### 2.4 `run_stroke_analysis`
- tool_name：`run_stroke_analysis`
- 目的：执行脑卒中分析并输出量化结果。
- 现有实现映射：`backend/app.py:2024`、`backend/app.py:1760`、`backend/app.py:1095`。
- applicability：仅 `ncct_mcta` 与 `ncct_mcta_ctp`。
- precondition：
  - `imaging_path in {ncct_mcta, ncct_mcta_ctp}`
  - `hemisphere in {right,left,both}`
- 输入：
  - `file_id: string`
  - `patient_id: int`
  - `hemisphere: right|left|both`
- 输出：
  - `core_infarct_volume?: number`
  - `penumbra_volume?: number`
  - `mismatch_ratio?: number`
  - `analysis_status: string`
- 错误码：`TOOL_NOT_APPLICABLE`、`TOOL_TIMEOUT`、`TOOL_EXECUTION_FAILED`
- 超时：`900s`
- 幂等性：弱幂等
- 重试策略：执行失败重试 1 次，前置不满足不重试

### 2.5 `generate_medgemma_report`
- tool_name：`generate_medgemma_report`
- 目的：基于病例+影像上下文生成 AI 报告。
- 现有实现映射：`backend/app.py:1871`、`backend/app.py:2079`。
- applicability：所有路径可走。
- precondition：
  - `patient_id`、`file_id` 有效
  - 前序必需数据可读取
- 输入：
  - `patient_id: int`
  - `file_id: string`
  - `format: markdown|json`
- 输出：
  - `report: string|object`
  - `report_payload: object`
  - `json_path?: string`
- 错误码：`TOOL_INPUT_INVALID`、`TOOL_EXTERNAL_API_FAILED`、`TOOL_TIMEOUT`、`TOOL_EXECUTION_FAILED`
- 超时：`120s`
- 幂等性：弱幂等
- 重试策略：外部API失败重试 1 次，参数错误不重试

### 2.6 `query_guideline_kb`
- tool_name：`query_guideline_kb`
- 目的：用于 EKV/问答的知识库增强查询。
- 现有实现映射：`backend/app.py:2846`、`backend/app.py:2985`、`backend/app.py:3083`。
- applicability：EKV场景可选、问答场景可选。
- precondition：
  - `question` 非空
  - 会话上下文有效
- 输入：
  - `question: string`
  - `session_id: string`
- 输出：
  - `answer: string`
  - `kb_fallback_used: bool`
- 错误码：`TOOL_INPUT_INVALID`、`TOOL_EXTERNAL_API_FAILED`、`TOOL_TIMEOUT`
- 超时：`60s`
- 幂等性：非幂等
- 重试策略：网络失败重试 1 次

### 2.7 `save_notes`
- tool_name：`save_notes`
- 目的：保存报告备注并回写结果JSON。
- 现有实现映射：`backend/app.py:330`、`backend/app.py:2226`、`backend/app.py:5156`。
- applicability：报告编辑场景可选。
- precondition：
  - `patient_id`、`file_id` 有效
  - `notes` 非空
- 输入：
  - `patient_id: int`
  - `file_id: string`
  - `notes: string`
- 输出：
  - `saved_targets: object`
  - `json_sync: object`
  - `warnings: string[]`
- 错误码：`TOOL_INPUT_INVALID`、`TOOL_EXECUTION_FAILED`、`TOOL_EXTERNAL_API_FAILED`
- 超时：`15s`
- 幂等性：幂等写入
- 重试策略：数据库短暂失败重试 2 次

## 3. 触发矩阵（冻结版）

### 3.1 路径判定优先级（避免二义性）
1. 先判定 `ncct_mcta_ctp`（完整7模态）
2. 再判定 `ncct_mcta`（4模态）
3. 再判定 `ncct_single_phase_cta`（3个单期子场景）
4. 最后判定 `ncct_only`

### 3.2 路径到 Tool 顺序（唯一）
| ImagingPath | 固定顺序 |
|---|---|
| `ncct_only` | `detect_modalities -> load_patient_context -> generate_medgemma_report` |
| `ncct_single_phase_cta` | `detect_modalities -> load_patient_context -> generate_medgemma_report` |
| `ncct_mcta` | `detect_modalities -> load_patient_context -> generate_ctp_maps -> run_stroke_analysis -> generate_medgemma_report` |
| `ncct_mcta_ctp` | `detect_modalities -> load_patient_context -> run_stroke_analysis -> generate_medgemma_report` |

可选跨路径 Tool：
1. `query_guideline_kb`
2. `save_notes`

## 4. 错误码字典（Week2 统一）

| 错误码 | 触发条件 | retryable | suggested_action |
|---|---|---|---|
| `TOOL_INPUT_INVALID` | 输入缺失/类型非法/枚举非法 | false | 修正输入再执行 |
| `TOOL_NOT_APPLICABLE` | 当前路径不适用该 Tool | false | 按触发矩阵切换路径 |
| `TOOL_DEPENDENCY_MISSING` | 权重/文件/依赖缺失 | false | 补齐依赖后重试 |
| `TOOL_TIMEOUT` | 超时未完成 | true | 按策略重试或降级 |
| `TOOL_EXECUTION_FAILED` | 本地执行异常 | true | 记录日志并重试 |
| `TOOL_EXTERNAL_API_FAILED` | 外部API不可达/失败 | true | 退避重试后降级 |

统一约束：
1. Tool 错误输出必须包含：`error_code/error_message/retryable/suggested_action`。
2. `retryable` 值必须与本表一致。

## 5. 文档级类型冻结（供 Week3 实现）

### 5.1 新增/改写类型
1. `ImagingPath`: `ncct_only|ncct_single_phase_cta|ncct_mcta|ncct_mcta_ctp`
2. `Hemisphere`: `right|left|both`
3. `AvailableModalitiesRaw`: `string[]`
4. `AvailableModalitiesCanonical`: `ncct|mcta|vcta|dcta|cbf|cbv|tmax`
5. `PathDecision`: `{raw_modalities, canonical_modalities, imaging_path, should_generate_ctp, should_run_stroke_analysis}`

### 5.2 延续类型
1. `CanonicalRunStatus`: `queued|running|succeeded|failed|cancelled`
2. `CanonicalStepStatus`: `pending|running|completed|failed|skipped`
3. `CanonicalStage`: `triage|tooling|icv|ekv|consensus|summary|done`
4. `ToolResult`: `tool_name/status/error_code/retryable/structured_output/raw_ref/latency_ms`

## 6. 范围声明
1. 本轮不新增后端路由。
2. `/api/agent/*` 在 Week3 后进入实现阶段。
3. 任何路径判定实现必须严格遵循本文件。
