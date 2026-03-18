# 卒中项目 Agent 化架构与规范主文档（v1.0）

文档状态：Draft-Ready  
最后更新：2026-03-13  
适用范围：NeuroMatrix_AI_mrdpm（规划阶段）  
约束：本版本仅做规划，不改业务代码

## 快速阅读入口
如果你只关心“每周具体做什么”，先看：
- `docs/每周任务清单_一页版.md`
- `docs/卒中先锋_agent落地路线图_执行版.md` 的第 0 节《一眼看懂（8 周白话版）》

## 1. 目标与定位

### 1.1 项目目标
在不推翻现有 Flask + 模型流水线的前提下，将当前卒中项目升级为“可审计、可验证、可追踪”的多 Agent 临床决策与报告系统。

### 1.2 设计原则
1. 最大复用现有能力，不做同功能重写。
2. 先跑通最小主链，再补可信化增强。
3. 每条关键结论必须可追溯到证据。
4. 保持对旧页面和旧流程的兼容。

### 1.3 借鉴来源（WSI-Agent 机制映射）
1. `Task Allocation Module` -> `Triage Planner Agent`
2. `Internal Consistency Verification` -> `Logic Reviewer Agent`
3. `External Knowledge Verification` -> `Guideline/Evidence Verifier Agent`
4. `Summary Module` -> `Clinical Summary Agent`

## 2. 架构全景与职责边界

### 2.1 分层架构
1. 编排层（新增）：Agent Orchestrator（LangGraph + LangChain + ReAct）
2. 工具层（复用）：上传、影像处理、卒中分析、报告、问答等既有能力封装为 Tool
3. 模型层（复用）：`mrdpm`、`palette`、`MedGemma_Model`
4. 存储与审计层（增强）：运行态、轨迹、证据、结果、错误记录

### 2.2 模块边界
1. `backend`：API、任务编排入口、工具适配
2. `frontend`：现有 viewer/report/chat + 新增 Agent Cockpit（展示运行态与证据）
3. `mrdpm`/`palette`：CTP 与伪彩相关推理能力
4. `MedGemma_Model`：报告语义生成与影像理解能力
5. `Supabase/PostgreSQL`：病例结构化数据与运行记录

### 2.3 兼容性策略
1. 不直接改变现有上传、报告、聊天主入口语义。
2. Agent 作为上层增强，不替换旧接口。
3. 新增接口统一放在 `/api/agent/*` 命名空间。

## 3. Agent 角色与执行链

### 3.1 Agent 角色
1. `Triage Planner Agent`：选择路径并生成工具调用计划
2. `Logic Reviewer Agent`：执行内部一致性校验（ICV）
3. `Guideline/Evidence Verifier Agent`：执行外部知识校验（EKV）
4. `Consensus Lite Agent`：冲突结论的轻量裁决
5. `Clinical Summary Agent`：结构化总结输出

### 3.2 统一执行链
1. 任务创建
2. 路径判定
3. Tool 调用
4. ICV 校验
5. EKV 校验
6. Consensus（可选）
7. Summary 汇总
8. 结果发布与审计落库

### 3.3 路径策略（V1）
1. `NCCT-only`
2. `NCCT + single-phase-CTA`
3. `NCCT + mCTA`
4. `NCCT + mCTA + CTP`

### 3.4 真实工作流冻结规则（新增）
1. 合法路径只允许 4 类：
`ncct_only|ncct_single_phase_cta|ncct_mcta|ncct_mcta_ctp`。
2. `available_modalities` 是模态识别主字段，路径判定按归一化值执行。
3. `hemisphere` 是偏侧主字段，枚举固定 `right|left|both`。
4. `single-phase-CTA` 原始子场景固定为：
`['ncct','mcat']` / `['ncct','vcat']` / `['ncct','dcta']`。
5. 触发冻结：
- 仅 `NCCT+mCTA`、`NCCT+mCTA+CTP` 触发 `run_stroke_analysis`。
- 仅 `NCCT+mCTA` 触发 `generate_ctp_maps(MRDPM)`。
- `NCCT+mCTA+CTP` 直接使用真实 `cbf/cbv/tmax`。
6. 路径判定优先级固定：
`ncct_mcta_ctp -> ncct_mcta -> ncct_single_phase_cta -> ncct_only`。

## 4. Public API 规范

### 4.1 接口清单
1. `POST /api/agent/runs`：创建运行
2. `GET /api/agent/runs/{run_id}`：查询状态
3. `GET /api/agent/runs/{run_id}/events`：查询执行轨迹
4. `GET /api/agent/runs/{run_id}/result`：查询最终结果
5. `POST /api/agent/runs/{run_id}/retry`：失败节点重试

### 4.2 状态语义（建议）
1. `status`: `queued | running | succeeded | failed | cancelled`
2. `stage`: `triage | tooling | icv | ekv | consensus | summary | done`
3. `retryable`: `true | false`

### 4.3 错误契约（最小）
1. `error_code`
2. `error_message`
3. `retryable`
4. `suggested_action`

## 5. 统一类型约束（最小必需字段）

### 5.1 `RunState`
- `run_id`
- `patient_id`
- `status`
- `stage`
- `created_at`
- `updated_at`

### 5.2 `AgentEvent`
- `event_id`
- `run_id`
- `agent_name`
- `tool_name`
- `input_ref`
- `output_ref`
- `latency_ms`
- `status`
- `error_code`

### 5.3 `EvidenceItem`
- `evidence_id`
- `source_type`
- `source_ref`
- `claim`
- `support_level`
- `timestamp`

### 5.4 `FinalReport`
- `summary`
- `key_findings`
- `risk_level`
- `confidence`
- `citations`
- `uncertainties`
- `next_actions`

### 5.5 `ErrorContract`
- `error_code`
- `error_message`
- `retryable`
- `suggested_action`

## 6. Tool 契约（V1 最小集合）
1. `detect_modalities`
2. `load_patient_context`
3. `generate_ctp_maps`
4. `run_stroke_analysis`
5. `generate_medgemma_report`
6. `query_guideline_kb`
7. `save_notes`

### 6.1 ICV Tool（内部一致性检查）

角色定位：

- 归属于 `Logic Reviewer Agent`，用于对同一次 Agent Run 内部的“路径/量化/报告文本”做一致性检查。

输入契约（由 `_tool_icv` 组装）：

- `planner_output`: 包含 `path_decision.imaging_path`、`path_decision.canonical_modalities`、`tool_sequence`。
- `tool_results`: 当次运行中已完成的 Tool 结果列表，重点消费：
   - `generate_ctp_maps`（是否生成 CTP、生成的模态和切片数等）
   - `run_stroke_analysis`（核心/半暗带体积、不匹配比例等）
   - `generate_medgemma_report`（结构化报告 payload）
- `patient_context`: 患者基础信息及 `available_modalities/hemisphere`（来自 Supabase）。
- `analysis_result`: 影像分析结果与（可选）报告 payload 快照。

输出契约（`evaluate_icv`）：

- 顶层：
   - `success: bool` — 仅表示规则引擎自身是否跑通。
   - `icv: { status: "pass|warn|fail", findings: Finding[] }`。
- `findings[i]` 结构：
   - `id: str` — 规则编号（如 `R2_mismatch_consistency`）。
   - `status: "pass|warn|fail|not_applicable"`。
   - `message: str` — 中文可读解释（已与前端字段对齐）。
   - `details: dict`（可选）— 数值细节，如预期/实际不匹配比等。
   - `suggested_action: str`（可选）— 建议动作，供前端展示。

落地方式：

- Tool 层：`tool_name = "icv"`，由 `_tool_icv` 负责装配输入并调用 `evaluate_icv`。
- 报告层：`_tool_generate_medgemma_report` 在生成结构化报告后，将 ICV 结果挂载到 `report_payload.icv`，供前端 viewer 直接消费。

关键触发规则：
1. `NCCT + mCTA`：先 `generate_ctp_maps`，后 `run_stroke_analysis`
2. `NCCT + mCTA + CTP`：直接 `run_stroke_analysis`
3. `NCCT-only`、`NCCT + single-phase-CTA`：不触发 `generate_ctp_maps` / `run_stroke_analysis`

字段语义冻结：
1. `available_modalities`：判定主字段（先归一化再判定）。
2. `hemisphere`：偏侧主字段（`right|left|both`）。
3. 允许保留 `raw_modalities` 追溯历史写法。

## 7. 质量门禁与验收标准

### 7.1 M1（可运行）
1. 四条模态路径可走通。
2. Agent 运行状态可查询。
3. 可输出结构化结果对象。
4. 不破坏旧功能：viewer/report/chat。

### 7.2 M2（可信化）

1. 关键结论具备证据映射。
2. ICV/EKV 均有可见校验标记。
3. 冲突场景可触发 Consensus Lite。
4. 审计日志可按 `run_id` 回放。

### 7.3 ICV 非阻断策略（Week4 要求）

1. ICV 作为“内部一致性增强模块”，不阻断主链（上传 -> 分析 -> 报告）正常完成：
   - 规则评估失败（如输入缺失、异常）仅在 `tool_results` 中标记 `status=failed` 并写入 error，不中断既有报告链路。
   - 单条规则 `status=fail/warn` 仅作为质控信号，由前端以高亮/告警形式展示，不自动否决整份报告。
2. 前端可见化要求：
   - Processing 页：在 Agent 面板中展示 ICV 总状态与 findings 数量。
   - Viewer 页：在报告侧边栏固定位置展示：
     - ICV 总状态（PASS/WARN/FAIL）。
     - 具体问题列表：规则 ID + 中文 message + 建议动作。
3. 验收前禁止将 ICV 结果接入“硬门禁”（例如直接拒绝返回报告），所有拦截必须经过临床验收并在文档中写明。

## 8. README 与代码一致性校验清单（执行前必须完成）
1. 启动入口与端口是否一致。
2. 前端构建产物路径是否一致。
3. 模型权重与依赖描述是否一致。
4. 历史页面是否保留及路由是否可达。
5. 文档中的 API 与真实路由是否一致。

## 9. 变更治理（双文档机制）
1. 本文档是“架构与规范主文档”。
2. 排期任务仅写在《卒中先锋 Agent 落地路线图》。
3. 架构变更必须先更新本文档，再更新路线图。
4. 每次关键变更都需要 ADR 编号（格式：`ADR-YYYYMMDD-XX`）。

## 10. 本版本默认技术选型
1. 主编排：`LangGraph + LangChain`
2. 推理范式：`ReAct + Tool Calling`
3. 机制借鉴：`AutoGen`（仅借鉴多 Agent 协作思想，不作为强依赖）
4. 后端基础：现有 Flask 服务
5. 数据与存储：Supabase/PostgreSQL（按现有工程为准）

## 11. Week3 实施回写（2026-03-13）
1. 已实现规则版 `Triage Planner`：输入 `patient_id/file_id/available_modalities/hemisphere`，输出 `imaging_path/tool_sequence/trigger_flags`。
2. 已实现 Week3 主链执行：`detect_modalities -> load_patient_context -> [generate_ctp_maps] -> [run_stroke_analysis] -> generate_medgemma_report`。
3. 已实现失败重试语义：仅 `retryable=true` 节点允许重试，默认上限 `generate_ctp_maps=1`、`run_stroke_analysis=1`、`generate_medgemma_report=1`。
4. 已实现 API：
   - `POST /api/agent/runs`
   - `GET /api/agent/runs/{run_id}`
   - `GET /api/agent/runs/{run_id}/events`
   - `GET /api/agent/runs/{run_id}/result`
   - `POST /api/agent/runs/{run_id}/retry`
5. 已保持上传链路兼容：`/api/upload/start`、`/api/upload/progress/{job_id}` 不变，并支持可选返回 `agent_run_id`。
6. Week3 运行态目前为进程内存态，后续阶段再迁移持久化。
