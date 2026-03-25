# W7_Cockpit交付

## 1. 目标
Week7 交付独立 `Cockpit` 页面，用于集中查看一次 Agent 运行的完整轨迹与结果入口，避免信息分散在 processing/validation。

本周边界：
- 仅做前端可视化与入口治理。
- 不改 ICV/EKV/Consensus 算法。
- 不新增业务 API 协议。

## 2. 页面与入口
### 2.1 新页面
- 新增路由：`GET /cockpit`
- 页面模板：`backend/templates/patient/upload/cockpit/index.html`
- 页面脚本：`static/js/cockpit.js`
- 页面样式：`static/css/cockpit.css`

### 2.2 入口打通
- processing：Agent 摘要卡新增 `打开 Cockpit` 按钮（脚本动态注入）。
- validation：页头新增 `Cockpit` 按钮。
- viewer：工具栏新增 `Cockpit` 按钮。
- report：动作栏新增 `Cockpit` 按钮。

统一透传上下文：
- `run_id`（优先）
- `file_id`
- `patient_id`

## 3. Cockpit 信息架构
页面固定三段：
1. 运行总览  
`run_id/patient_id/file_id/status/stage/current_tool/event_count/updated_at`
2. 轨迹区  
- 步骤轨迹：`run.steps`
- 事件轨迹：`events(event_seq/stage/tool/status/attempt/latency/error_code)`
3. 结果区  
- 运行摘要（最后错误、可重试步骤、结果状态、来源）
- 校验摘要（ICV/EKV/Consensus）
- 证据追溯摘要（traceability）
- 结果入口（Viewer/Report/Validation）

## 4. 数据链路
复用现有接口：
- `GET /api/agent/runs/{run_id}`
- `GET /api/agent/runs/{run_id}/events`
- `GET /api/agent/runs/{run_id}/result`
- `GET /api/validation/context?run_id=&file_id=&patient_id=`

刷新策略：
- `run.status in {queued, running}`：持续轮询
- 终态 `succeeded/failed/cancelled`：停止轮询

空态策略：
- URL 无 `run_id` 时，先尝试 `latest_agent_run_{file_id}`。
- 仍无可用 run 时，显示引导文案（从 processing/viewer/report 进入或手动提供 run_id）。

## 5. 状态语义
- 页面显示统一中文文案（机器值保留原值，不改后端枚举）。
- `最后错误`：
  - 运行中/成功且无失败：显示 `无`
  - 失败：优先 `run.error`，其次最近失败步骤 message。
- 可重试步骤：展示最后一个 `failed && retryable=true` 的步骤；无则显示 `无`。

## 6. 兼容性
- 不改 `/api/upload/*`、`/api/agent/runs*`、`/api/validation/context` 返回结构。
- viewer/report/chat 原流程保持不变。
- processing 原 6 步主时间线保持不变。

## 7. 本周交付清单
- [x] 独立 Cockpit 页（模板+JS+CSS）
- [x] processing/validation/viewer/report 四入口打通
- [x] 轨迹筛选（stage/status/tool）
- [x] run_id 复制与轨迹导出（前端文本）
- [ ] 真实病例签收留痕（见验收记录）


## 8. Agent Loop V2 Canary Notes (2026-03-24)
- Cockpit remains API-compatible with `/api/agent/runs*`.
- Runs now expose loop metadata:
  - `loop_version`
  - `loop_canary_hit`
- V2 result payload may include:
  - `report_payload.tool_metrics`
  - `report_payload.decision_trace`
