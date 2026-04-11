# W0 API 契约表（增量）

## 1. GET `/api/agent/runs/{run_id}`（增量字段）
| 字段 | 类型 | 可空 | 说明 | W0 策略 |
|---|---|---|---|---|
| `plan_frames` | array<object> | 否 | 计划帧列表 | 缺失时后端补 `[]` |
| `replan_count` | int | 否 | 重规划次数 | 缺失时按 `plan_frames` 推导 |
| `termination_reason` | string | 否 | 终止原因 | 运行中可为 `running` |
| `human_checkpoint` | object/null | 是 | 人工复核上下文 | W0 默认 `null` |
| `finalization` | object/null | 是 | 归档/回写状态 | 成功时给占位对象 |

### `plan_frames[]` 推荐结构
```json
{
  "revision": 1,
  "source": "triage_planner",
  "objective": "StrokeClaw W0 orchestration (ncct_mcta)",
  "reasoning_summary": "Rule-based plan derived from modality path",
  "next_tools": ["detect_modalities", "load_patient_context"],
  "confidence": 1.0
}
```

## 2. GET `/api/agent/runs/{run_id}/events`（增量字段）
| 字段 | 类型 | 可空 | 说明 |
|---|---|---|---|
| `event_type` | string | 否 | 统一事件类型 token |
| `phase` | string | 否 | 事件阶段（可回退 `stage`） |
| `node_name` | string | 否 | 节点名（可回退 `tool_name`） |

## 3. POST `/api/agent/runs/{run_id}/review`（W0 冻结协议）
- W0 目标：冻结协议，不实现业务动作。
- W0 行为：返回 `501 NOT_IMPLEMENTED_IN_W0`。

### 请求（冻结）
```json
{
  "action": "accept",
  "patch": {},
  "signature": {},
  "note": "optional",
  "actor_id": "optional"
}
```

### 响应（W0）
```json
{
  "success": false,
  "run_id": "xxx",
  "error": "W0 contract frozen: review action will be implemented in W1",
  "error_code": "NOT_IMPLEMENTED_IN_W0",
  "contract": {
    "allowed_actions": ["accept", "edit", "reject", "sign", "handoff"],
    "required_fields": ["action"],
    "optional_fields": ["patch", "signature", "note", "actor_id"]
  }
}
```

## 4. 兼容策略
- 新字段均为增量，不影响旧调用方。
- 前端必须对缺失字段有回退渲染：
  - `plan_frames` 缺失 -> 读 `planner_output.tool_sequence`
  - `event_type` 缺失 -> 前端按 `status/tool_name` 推导
