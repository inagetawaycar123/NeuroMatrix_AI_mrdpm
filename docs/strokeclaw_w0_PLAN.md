## StrokeClaw W0 计划安排表（范围冻结与契约对齐周）

### Summary
- 周期：`2026-04-13 ~ 2026-04-15`（3天）
- 目标：把 W0 做成“可执行起跑线”，完成范围冻结、交互骨架冻结、接口契约冻结。
- 结果：W1 可以直接进入开发，不再反复改需求和字段。

### W0 日程表（细化到半天）
| 时间 | 工作包 | 具体任务 | 交付物 | 完成标准 |
|---|---|---|---|---|
| 4/13 上午 | 目标与边界冻结 | 明确 W0/W1/W2 边界；列出不做项（算法升级、模型替换、全站重构） | 《W0范围冻结清单》 | 所有人对“做什么/不做什么”签字确认 |
| 4/13 下午 | 页面信息架构冻结 | 冻结 4 个核心页面：任务工作台、Runtime、Human Review、Finalization 的区块结构与主文案 | 《W0页面IA与文案清单》 | 页面结构不再变更，仅允许微调文案 |
| 4/14 上午 | 状态机与事件字典冻结 | 冻结 run 状态、阶段状态、事件类型、状态颜色与标签映射 | 《W0状态机与事件字典》 | 前后端使用同一套 token，不再各自定义 |
| 4/14 下午 | API 契约冻结 | 冻结 `/api/agent/runs/{id}`、`/events` 的增量字段；定义 `review` 动作请求/响应 | 《W0 API契约表（增量）》 | 字段名、类型、可空性、兼容策略全部明确 |
| 4/15 上午 | 骨架联调验证 | 前端接入最小骨架（任务入口+计划面板+运行态占位）；后端返回最小可用 run/events mock/真实数据 | 可跑通骨架联调版本 | 可从入口启动并看到计划与状态更新 |
| 4/15 下午 | W0 验收与风险清零 | 走查 checklist、确认阻塞项、输出 W1 开发任务拆分与优先级 | 《W0验收记录》+《W1任务分解》 | W1 任务可直接排期，不存在未决关键问题 |

### W0 对外接口与类型冻结（Public Changes）
- `GET /api/agent/runs/{run_id}` 增量字段：
  - `plan_frames[]`
  - `replan_count`
  - `termination_reason`
  - `human_checkpoint`（可空）
  - `finalization`（可空）
- `GET /api/agent/runs/{run_id}/events` 统一事件类型：
  - `plan_created`, `step_started`, `step_completed`, `issue_found`, `human_review_required`, `human_review_completed`, `writeback_completed`
- `POST /api/agent/runs/{run_id}/review`（W0 冻结协议，W1 实装）

### W0 验收用例（必须通过）
1. 能从“任务入口”创建 run，并看到 `Stroke Orchestration` 计划面板。
2. Runtime 页可显示 run 基本状态、当前阶段、当前节点占位信息。
3. 事件流可按时间顺序渲染，状态标签与颜色一致。
4. 后端缺失增量字段时，前端有兼容回退，不白屏。
5. 输出完整 W1 backlog（按 P0/P1/P2）。

### Assumptions
- W0 只做“冻结与打样联调”，不做大规模功能开发。
- 前后端并行各 1 名主责，产品/架构 1 名主责。
- W0 完成标志是“规范冻结 + 骨架可跑”，不是“功能完备”。
