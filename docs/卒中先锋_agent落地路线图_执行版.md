# 卒中先锋 Agent 落地路线图（执行版 v1.0）

文档状态：Execution-Ready  
最后更新：2026-03-13  
关联主文档：`docs/Agent_PLAN.md`  
约束：本阶段只做规划，不改业务代码

## 0. 一眼看懂（8 周白话版）

| 周次 | 本周只做一件事 | 本周交付物 | 通过标准（看这个就行） |
|---|---|---|---|
| 第1周 | 把规则说清楚 | 术语表 + 真值表 + 字段语义 + 偏差清单 | 必须通过“4路径真值表 + 2触发规则”校验 |
| 第2周 | 把能力变成 Tool | Tool 契约文档 + 触发矩阵 | 每个 Tool 都有 `applicability/precondition` 且触发顺序唯一 |
| 第3周 | 先跑通主链 | 主链流程定义 | 病例输入后能得到结构化结果，失败可重试 |
| 第4周 | 加内部自检（ICV） | ICV 规则清单 | 规则集 + 可见化 + 验收记录 |
| 第5周 | 加外部校验（EKV） | EKV 规则清单 + Lite 裁决规则 | 关键结论可标记“支持/部分支持/不支持” |
| 第6周 | 做最终汇总 | FinalReport + EvidenceMap 约束 | 报告里关键结论都能追溯证据来源 |
| 第7周 | 做前端可视化 | Agent Cockpit 基础页 | 能看到步骤、错误、证据入口、结果入口 |
| 第8周 | 做整体验收 | 测试报告 + 上线建议 | 有明确结论：可上线/灰度/需补齐 |

阅读建议：  
1. 先看本节（0）  
2. 再看第 3 节（周计划）  
3. 最后按需看第 4-7 节细节

## 1. 执行总览
本路线图将 Agent 化实施拆为 8 周、6 个阶段（含 Phase -1），目标是在不破坏现有业务链路的前提下，完成“可运行 + 可验证 + 可追溯”的最小可落地版本。

## 2. 分阶段实施（8 周）

| 阶段 | 时间 | 核心目标 | DoD（完成标准） |
|---|---|---|---|
| Phase -1 基线加固 | 第1周 | 梳理现有链路、术语、状态机 | 必须产出“4路径真值表、2触发规则、字段语义冻结、README/代码偏差清单” |
| Phase 0 Tool 化 | 第2周 | 既有能力 Tool 契约化 | 7个Tool全部具备`applicability/precondition`并通过4路径触发矩阵校验 |
| Phase 1 单 Agent 主链 | 第3周 | 跑通 Planner + Tool 主流程 | 病例输入可到结构化结果，失败节点可重试 |
| Phase 2 双重验证 | 第4-5周 | 接入 ICV + EKV | 关键结论均带校验标签，冲突可回传 |
| Phase 3 汇总与审计 | 第6周 | Summary + Evidence/Trace | 报告可引用证据、带置信度与未决问题 |
| Phase 4 前端接入 | 第7周 | Agent 运行态可视化 | 可查看步骤进度、错误原因、证据来源 |
| Phase 5 验收与上线建议 | 第8周 | 回归/性能/临床可用性评估 | 达到阈值并形成上线建议与风险说明 |

## 3. 周计划与任务拆解

### 第 1 周（Phase -1）
1. 固化术语：CTA 期相、CTP 参数、AI 报告、临床问答。
2. 固化状态机：`queued/running/succeeded/failed/cancelled`。
3. 固化阶段枚举：`triage/tooling/icv/ekv/consensus/summary/done`。
4. 产出临床工作流真值表（4路径 + single-phase三子场景）。
5. 固化触发规则：仅 2 路径触发脑卒中分析，仅 1 路径触发 CTP 生成。
6. 固化字段语义：`available_modalities`（模态主字段）、`hemisphere`（偏侧主字段）。
7. 产出 README 与代码偏差表（入口、端口、前端构建路径、历史页面）。

验收：
1. 4 种路径定义唯一且完整。
2. “2触发卒中分析 + 1触发CTP生成”明确写入并可追溯。
3. `available_modalities` 与 `hemisphere` 语义冻结。
4. 偏差清单可逐项追踪。

### 第 2 周（Phase 0）
1. 明确 Tool 输入输出契约与错误返回格式。
2. 完成 V1 Tool 集合优先级（P0/P1/P2/P3）定义。
3. 每个 Tool 增加固定字段：`applicability`、`precondition`。
4. 固化路径判定优先级：
   - `ncct_mcta_ctp -> ncct_mcta -> ncct_single_phase_cta -> ncct_only`
5. 固化关键触发规则：
   - `NCCT + mCTA`: `generate_ctp_maps -> run_stroke_analysis`
   - `NCCT + mCTA + CTP`: `run_stroke_analysis`
   - 其余两路径不触发两类 Tool

验收：
1. 7 个 Tool 全部具有 `applicability/precondition`。
2. 触发矩阵能对 4 路径给出唯一执行顺序。
3. 错误码字典每项都有 `retryable` 与 `suggested_action`。

### 第 3 周（Phase 1）
1. 完成 `Triage Planner Agent` 协议冻结。
2. 固化主链执行序列（诊断路径优先）。
3. 定义失败节点重试策略（次数、幂等、回滚边界）。

验收：
1. 主链从病例输入到结构化输出闭环定义完成。
2. 重试语义可执行、可审计。

### 第 4-5 周（Phase 2）
1. 接入 `Logic Reviewer Agent`（ICV）。
2. 接入 `Guideline/Evidence Verifier Agent`（EKV）。
3. 定义冲突分类与处理策略（直接失败、降级、待人工复核）。
4. 定义 `Consensus Lite Agent` 启动条件与输出格式。

验收：
1. 每条关键结论可标记“支持/部分支持/不支持”。
2. 冲突结论可形成结构化回传。

### 第 6 周（Phase 3）
1. 接入 `Clinical Summary Agent`。
2. 冻结结果对象：`FinalReport`、`EvidenceItem`、`AgentEvent`。
3. 落实 Evidence Map 与 Agent Trace 对应关系。

验收：
1. 关键结论至少映射 1 条可追溯证据。
2. 可按 `run_id` 重放执行轨迹。

### 第 7 周（Phase 4）
1. 增加基础版 Agent Cockpit 展示。
2. 展示项：阶段进度、Tool 调用、错误原因、证据入口、结果入口。
3. 保持 viewer/report/chat 原入口可用。

验收：
1. 前端可查看一次完整运行轨迹。
2. 不影响原有核心页面可用性。

### 第 8 周（Phase 5）
1. 执行回归、性能、稳定性、可解释性测试。
2. 输出上线建议（可上线/灰度/需补齐项）。
3. 形成 M2 待办（可信化增强深化）。

验收：
1. 完成测试记录与结果归档。
2. 输出风险清单和回退策略。

## 4. 关键接口与对象（执行侧冻结）

### 4.1 API
1. `POST /api/agent/runs`
2. `GET /api/agent/runs/{run_id}`
3. `GET /api/agent/runs/{run_id}/events`
4. `GET /api/agent/runs/{run_id}/result`
5. `POST /api/agent/runs/{run_id}/retry`

### 4.2 对象
1. `RunState`
2. `AgentEvent`
3. `EvidenceItem`
4. `FinalReport`
5. `ErrorContract`

执行约束：
1. 任一新增字段必须附兼容策略（默认值/可空性/版本号）。
2. 任一状态枚举变更必须同步更新主文档状态机。

## 5. 风险与回退策略

### 5.1 主要风险
1. 旧流程与新流程状态不一致。
2. Tool 结果不稳定导致链式失败。
3. ICV/EKV 增加时延，影响端到端体验。
4. 证据链不完整导致“结论不可解释”。

### 5.2 控制措施
1. 所有关键节点写入 `AgentEvent`，统一错误码。
2. 重试只允许在标记为 `retryable=true` 的节点触发。
3. 设置性能预算并持续记录 `latency_ms`。
4. 结果未满足证据要求时强制加“待人工复核”标记。

### 5.3 回退策略
1. 保留旧流程入口，支持按开关回退。
2. Agent 失败时，允许降级到现有报告链路。
3. 验证模块异常时，主流程可切换到“仅结果+人工复核”模式。

## 6. 测试与验收矩阵

### 6.1 功能链路
1. 标准病例：全链路成功。
2. 边界病例：缺模态或低质量输入可降级。
3. 异常病例：工具失败可重试并保留轨迹。

### 6.2 一致性与可解释性
1. ICV 能识别至少 1 类逻辑冲突。
2. EKV 能识别至少 1 类证据不足场景。
3. FinalReport 的每条关键结论可追溯证据来源。

### 6.3 回归与性能
1. 现有非 Agent 功能回归通过率 100%。
2. 端到端时延增幅在预算范围内。
3. 并发场景下无重复消费与死锁。

### 6.4 安全与合规
1. 日志脱敏检查通过。
2. 运行创建/结果访问/轨迹访问权限校验通过。
3. 审计日志可按 `run_id` 完整回放。

## 7. 协作与文档治理
1. 本文档用于执行排期和任务管理，不承载架构决策细节。
2. 架构与契约变更先更新 `docs/Agent_PLAN.md`，再更新本文档。
3. 每次里程碑结束必须更新“实际完成 vs 计划差异”。
4. 所有重大调整都要记录 ADR 编号并互链到主文档。

## 8. Week3 完成回写（2026-03-13）
1. 完成项：
   - `Triage Planner` 协议冻结并落地。
   - 主链执行序列固定并可运行。
   - 失败节点重试机制（含 retryable 与上限）落地。
2. DoD 对照：
   - 病例输入 -> 结构化结果：已实现。
   - 失败节点可重试且可追踪：已实现（事件含 attempt 与 error_code）。
3. 本周交付物：
   - [W3_主链跑通交付.md](./W3_主链跑通交付.md)
   - [W3_主链验收记录.md](./验收记录/W3_主链验收记录.md)

## Week6 Update (2026-03-23)
1. Implemented summary and evidence-chain output in report_payload.
2. Added final_report, evidence_items, evidence_map, and traceability contracts.
3. Validation and report pages can display traceability metrics.
4. Runtime sign-off with real run_id/job_id/file_id remains mandatory.

## Week7 Update (2026-03-23)
1. Added independent Cockpit page (`/cockpit`) for run-level trajectory playback.
2. Cockpit shows run overview, step timeline, event timeline, validation summary, and result links.
3. Added Cockpit entries from processing / validation / viewer / report pages.
4. Reused existing APIs only (`/api/agent/runs*`, `/api/validation/context`), no new data protocol.
5. Week7 docs delivered:
   - [W7_Cockpit交付.md](./W7_Cockpit交付.md)
   - [W7_Cockpit验收记录.md](./验收记录/W7_Cockpit验收记录.md)
6. Runtime sign-off evidence with real cases remains mandatory before final week sign-off.
