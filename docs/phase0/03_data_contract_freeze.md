# Phase 0 Data Contract Freeze

## 1. Core entities (minimum required fields)

### 1.1 AgentRun
```json
{
  "run_id": "run_xxx",
  "case_id": "case_xxx",
  "patient_id": 1001,
  "status": "queued|running|paused_review_required|succeeded|failed|cancelled",
  "stage": "triage|tooling|icv|ekv|consensus|summary|done",
  "current_step": "run_stroke_analysis",
  "source_tag": "real|mock|hybrid",
  "created_at": "2026-04-19T10:00:00Z",
  "updated_at": "2026-04-19T10:05:00Z"
}
```

### 1.2 AgentStep
```json
{
  "step_id": "step_xxx",
  "run_id": "run_xxx",
  "step_key": "run_stroke_analysis",
  "tool_name": "run_stroke_analysis",
  "status": "pending|running|completed|failed|skipped",
  "confidence": 0.91,
  "latency_ms": 1834,
  "needs_human_review": false,
  "source_tag": "real"
}
```

### 1.3 ToolCall
```json
{
  "call_id": "call_xxx",
  "run_id": "run_xxx",
  "step_id": "step_xxx",
  "tool_name": "run_stroke_analysis",
  "input_ref": {"file_id": "f001"},
  "output_ref": {"core_infarct_volume": 24.8},
  "error_code": null,
  "retryable": false
}
```

### 1.4 TraceEvent
```json
{
  "event_id": "evt_xxx",
  "run_id": "run_xxx",
  "step_id": "step_xxx",
  "event_type": "plan_created|step_started|step_completed|issue_found|human_review_required|human_review_completed|writeback_completed",
  "actor": "system|agent|doctor",
  "timestamp": "2026-04-19T10:05:10Z",
  "message": "run_stroke_analysis completed",
  "metadata": {"latency_ms": 1834}
}
```

### 1.5 ClinicalDecisionBundle
```json
{
  "run_id": "run_xxx",
  "input_modalities": ["ncct", "mcta"],
  "triage_result": {},
  "vessel_result": {},
  "perfusion_result": {},
  "stroke_analysis": {},
  "consistency_check": {},
  "report_payload": {},
  "evidence_items": [],
  "human_review": {}
}
```

## 2. Node card payload contract (frontend required)
```json
{
  "node_name": "NCCT triage",
  "skill_name": "run_ncct_classification",
  "input_summary": "NCCT volume + patient context",
  "output_summary": "ischemia suspected",
  "confidence": 0.87,
  "risk_level": "medium_high",
  "evidence_refs": ["ev_101", "ev_102"],
  "latency_ms": 728,
  "need_human_review": true,
  "source_tag": "real"
}
```

## 3. Required enums (frozen)
- `source_tag`: `real`, `mock`, `hybrid`
- `run_status`: `queued`, `running`, `paused_review_required`, `succeeded`, `failed`, `cancelled`
- `step_status`: `pending`, `running`, `completed`, `failed`, `skipped`

## 4. Contract ownership
- Primary owner: 朱
- Co-owners: 袁（模型字段）, 刘（报告/证据字段）, 康（前端读取需求）

