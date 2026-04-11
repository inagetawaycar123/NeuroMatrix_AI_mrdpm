# W7 Agent Loop V2 Canary Delivery

## 1. Scope
- Refactor runtime shape to `Agent = Loop(LLM + Context + Tools)` without replacing existing business tools.
- Keep existing APIs and pages compatible.
- Add canary rollout controls for safe migration.

## 2. Delivered Changes
- Added modular runtime package under `backend/agent/`:
  - `planner.py`
  - `context_manager.py`
  - `tool_registry.py`
  - `executor.py`
  - `loop_controller.py`
  - `reporter.py`
- Added v1/v2 dispatcher in backend runtime:
  - v2 selected by canary switch
  - automatic fallback to v1 if v2 runtime exception happens
- Extended run input contracts:
  - optional `question`
  - optional `max_steps`
  - optional `max_duration_ms`
  - optional `execution_mode`, `trigger_source`
- Added run metadata:
  - `loop_version` (`v1` / `v2`)
  - `loop_canary_hit` (bool)
- Added report payload enrichment in v2 finalization:
  - `tool_metrics`
  - `decision_trace`
  - keeps existing `final_report/evidence_items/evidence_map/traceability` unchanged

## 3. Canary Controls
Environment variables:
- `AGENT_LOOP_V2_ENABLED=0|1`
- `AGENT_LOOP_V2_CANARY_RATIO=0.0..1.0`
- `AGENT_LOOP_V2_PLANNER_MODE=guarded_hybrid|rule_only|llm_first`
- `AGENT_HUMAN_REVIEW_PAUSE=0|1`
- `AGENT_LOOP_MAX_STEPS`
- `AGENT_LOOP_MAX_DURATION_MS`

Selection rule:
- if disabled: always v1
- if enabled: deterministic hash bucket on `run_id` compared with canary ratio

## 4. Runtime Semantics
- Non-blocking remains for verification tools: `icv`, `ekv`, `consensus_lite`.
- Optional high-risk pause:
  - high-risk not-supported claim without evidence, or
  - consensus decision is `escalate`.
- Resume support:
  - `/api/agent/runs/{run_id}/retry` accepts paused run with `step_key=resume` (mapped to summary/report continuation).

## 5. Compatibility
- No breaking changes to:
  - `/api/agent/runs*`
  - `/api/upload/*`
  - `/api/validation/context`
- Existing pages keep current behavior; new fields are additive.

## 6. Validation Notes
- `py_compile` passed for `backend/app.py` and all new `backend/agent/*` modules.
- `pytest` is unavailable in the current Python runtime (`No module named pytest`).
- Smoke script passed:
  - `python tests/run_icv_smoke.py`

## 7. Next Acceptance Actions
- Run 3 real successful cases + 1 failure/soft-failure case with canary enabled.
- Record evidence in `docs/验收记录/W7_AgentLoopV2_灰度验收记录.md`.

