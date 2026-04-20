# Phase 0 API Contract Freeze

## 1. API design principles for competition version
- Keep existing endpoints backward-compatible.
- Add minimum new endpoints only for demo-critical visualization.
- Return explicit fields for frontend; avoid inferred state.
- Include `source_tag` where user-visible result may be mock/hybrid.

## 2. Contract table

| Endpoint | Method | Purpose | Required response keys |
|---|---|---|---|
| `/api/agent/runs/{run_id}` | GET | Get run summary | `run_id,status,stage,current_step,source_tag,updated_at` |
| `/api/agent/runs/{run_id}/events` | GET | Timeline events | `events[].event_type,events[].step_id,events[].timestamp,events[].message` |
| `/api/agent/runs/{run_id}/result` | GET | Final run result | `status,result,stage,run_id` |
| `/api/agent/runs/{run_id}/review` | GET/POST | Human review state/actions | `review_state,all_confirmed,current_section_id,can_enter_viewer` |
| `/api/validation/context` | GET | Validation aggregate | `icv,ekv,consensus,traceability,meta` |
| `/api/agent/runs/{run_id}/graph` | GET | DAG graph data (new) | `nodes,edges,run_meta` |
| `/api/agent/runs/{run_id}/decision-bundle` | GET | Unified decision package (new) | `decision_bundle,report_payload,evidence_items,source_tag` |
| `/api/demo/scenarios/{scenario_id}/start` | POST | Start scripted demo run (new) | `run_id,scenario_id,mode,status_urls` |

## 3. New endpoint payload sketches

### 3.1 `GET /api/agent/runs/{run_id}/graph`
```json
{
  "success": true,
  "run_id": "run_xxx",
  "nodes": [
    {
      "step_key": "run_ncct_classification",
      "title": "NCCT三分类",
      "status": "completed",
      "source_tag": "real",
      "confidence": 0.87
    }
  ],
  "edges": [
    {"from": "detect_modalities", "to": "run_ncct_classification"}
  ],
  "run_meta": {
    "status": "running",
    "stage": "tooling",
    "updated_at": "2026-04-19T12:00:00Z"
  }
}
```

### 3.2 `GET /api/agent/runs/{run_id}/decision-bundle`
```json
{
  "success": true,
  "run_id": "run_xxx",
  "source_tag": "hybrid",
  "decision_bundle": {},
  "report_payload": {},
  "evidence_items": []
}
```

### 3.3 `POST /api/demo/scenarios/{scenario_id}/start`
Request:
```json
{
  "mode": "real|mock|hybrid",
  "patient_id": 1001,
  "file_id": "f001"
}
```

Response:
```json
{
  "success": true,
  "scenario_id": "A_ncct_mcta_no_ctp",
  "run_id": "run_demo_xxx",
  "mode": "hybrid",
  "status_url": "/api/agent/runs/run_demo_xxx",
  "events_url": "/api/agent/runs/run_demo_xxx/events",
  "graph_url": "/api/agent/runs/run_demo_xxx/graph"
}
```

## 4. Backward compatibility rules
- Existing routes stay valid for current frontend.
- New frontend should prefer new graph/decision-bundle endpoints when present.
- Fallback strategy: if new endpoint unavailable, derive from `runs + events + result`.

## 5. API ownership and review
- Owner: 朱
- Reviewers: 康（frontend contract usage）, 敬（demo narrative alignment）, 雷（test coverage）

