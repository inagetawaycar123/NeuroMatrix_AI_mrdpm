## Week5（EKV + Consensus Lite）细化落地计划（可直接执行）

### 1. Summary
1. Week5 目标是把 Agent 链从 `ICV` 扩展到 `EKV + Consensus Lite`，形成可审计的校验闭环：`tooling -> icv -> ekv -> consensus -> summary -> done`。  
2. 保持非阻断原则：EKV/Consensus 失败不阻断报告生成，但必须留下可追溯证据与风险提示。  
3. 交付边界包含代码、前端可见化、文档签收与验收留痕；不进入 Week6。

### 2. Implementation Changes
1. **后端编排补齐（主链）**  
   - 在 Agent 工具序列中接入 `ekv`，并在满足冲突条件时接入 `consensus_lite`。  
   - 阶段映射固定：普通工具=`tooling`，`icv`=`icv`，`ekv`=`ekv`，`consensus_lite`=`consensus`，报告=`summary`，终态=`done`。  
   - 非阻断策略固定：`ekv/consensus_lite` 失败仅记录 failed 事件与错误合同，主链继续跑报告。

2. **EKV 工具实现（规则版）**  
   - 输入来源固定：`tool_results.icv`、病例结构化分析结果、模态判定结果、报告关键结论草稿。  
   - 用 `query_guideline_kb` 做证据检索（无新路由），对每条关键结论打标签：`supported | partially_supported | not_supported | unavailable`。  
   - 关键结论最小集（先冻结 6 类）：偏侧、核心体积、半暗带体积、不匹配比、是否存在显著不匹配、治疗时窗相关提示。  
   - 规则：NCCT-only 下 CTP 相关结论默认 `not_applicable/unavailable`，不得伪造支持。

3. **Consensus Lite（轻量裁决）**  
   - 触发条件固定（任一满足即触发）：  
     1) EKV 出现 `not_supported`；  
     2) `partially_supported` 数量 >= 2；  
     3) ICV 为 `fail`；  
     4) EKV 不可用但存在高风险结论。  
   - 输出固定：`decision=accept|review_required|escalate`，并返回 `conflicts[]` 与 `next_actions[]`。  
   - 若不触发，返回 `skipped`，并写明“no material conflict”。

4. **契约字段补齐（向后兼容）**  
   - `EKVResult` 补齐：`status`、`finding_count`、`score`、`confidence_delta`、`claims[]`、`findings[]`、`citations[]`。  
   - `claims[]` 每条固定：`claim_id`、`claim_text`、`verdict`、`evidence_refs`、`message`。  
   - `findings[]` 每条固定：`id`、`status`、`message`、`severity`、`suggested_action`（缺失时后端补默认值）。  
   - `ConsensusResult` 固定：`status`、`decision`、`conflict_count`、`summary`、`next_actions`。

5. **前端可见化（Processing + Viewer + Report）**  
   - Processing 右侧摘要新增：`EKV 状态/发现数/支持率`、`Consensus 决策`、`高风险冲突数`。  
   - Viewer ICV 区升级为“校验结果”区：展示 ICV + EKV + Consensus 统一卡片，支持 `pass/warn/fail/unavailable/skipped`。  
   - Report 页面新增“证据校验摘要”段：显示关键结论校验标签与建议动作，不改变原报告主体结构。  
   - 保持 Week3 结构：左侧上传主时间线不变，右侧只展示摘要，不恢复双步骤明细。

6. **文档与签收回写**  
   - 新增 Week5 交付文档与验收记录（真实 run_id/job_id/file_id + 日志片段 + 截图路径）。  
   - 更新主计划与周清单，把 Week5 DoD 改成“关键结论全部有 EKV 标签，冲突有 Consensus 决策”。  
   - Week5 勾选条件：代码、可见化、验收记录三项同时完成。

### 3. Public APIs / Interfaces / Types
1. 不新增路由，继续用现有 `/api/agent/runs*` 与上传链接口。  
2. `run.result` 中新增（或补齐）`ekv` 与 `consensus` 结构；旧字段保持可读。  
3. `ToolResult.structured_output` 扩展支持 `EKVResult/ConsensusResult`；`ToolResult` 外层字段不变。  
4. 状态类型延续：`CanonicalRunStatus`、`CanonicalStepStatus`、`CanonicalStage` 不改。

### 4. Test Plan
1. **主链必测**  
   - `NCCT-only`：EKV 对 CTP 结论标记 `unavailable/not_applicable`，Consensus 通常 `skipped`。  
   - `NCCT+mCTA`：EKV 可对体积/不匹配相关结论给出支持标签；有冲突时触发 Consensus。  
   - `NCCT+mCTA+CTP`：EKV 校验真实 CTP 量化，Viewer/Report 与分析卡一致。  

2. **非阻断必测**  
   - 人为制造 EKV 失败（如 KB 不可用）：run 仍可 `succeeded`，报告可生成，摘要显示 EKV unavailable 原因。  
   - 人为制造 Consensus 失败：同样不阻断，且失败原因可见。

3. **一致性必测**  
   - Processing/Viewer/Report 对同一 `file_id` 的 EKV 状态、发现数、冲突数一致。  
   - 日志、events、run.result 三处阶段一致可见：`icv -> ekv -> consensus/skip -> summary`。

4. **回归必测**  
   - Agent 关闭路径与 Week3/Week4 行为一致。  
   - 上传、处理、查看、报告主链不退化。  

5. **签收留痕**  
   - 每个用例记录：`run_id/job_id/file_id`、关键请求响应摘要、`[AGENT]/[EKV]/[CONSENSUS]` 日志、截图路径、通过结论。

### 5. 执行节奏（建议 1 周）
1. Day1：冻结 EKV/Consensus 契约与触发规则，补文档草案。  
2. Day2：后端接入 EKV 工具与阶段流转。  
3. Day3：实现 Consensus Lite 与非阻断语义。  
4. Day4：前端 Processing/Viewer/Report 摘要接入与联调。  
5. Day5：跑用例、补验收记录、回写清单并签收。

### 6. Assumptions
1. Week5 仅实现 EKV + Consensus Lite，不实现 Week6 的深度知识推理。  
2. 继续使用现有知识库能力，不引入新外部服务。  
3. 以“可观测、可审计、非阻断”为优先级，高于“复杂智能策略”。
