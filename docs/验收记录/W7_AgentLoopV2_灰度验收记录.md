# W7 Agent Loop V2 Canary Acceptance Record

## 1. Environment
- Date:
- Branch/Commit:
- `AGENT_LOOP_V2_ENABLED`:
- `AGENT_LOOP_V2_CANARY_RATIO`:
- `AGENT_LOOP_V2_PLANNER_MODE`:
- `AGENT_HUMAN_REVIEW_PAUSE`:

## 2. Case Matrix

| Case | patient_id | file_id | run_id | Path | Expected | Result | Notes |
|---|---:|---|---|---|---|---|---|
| S1 |  |  |  | NCCT-only | end-to-end succeeded |  |  |
| S2 |  |  |  | NCCT+mCTA | end-to-end succeeded |  |  |
| S3 |  |  |  | NCCT+mCTA+CTP | end-to-end succeeded |  |  |
| F1 |  |  |  | failure/soft-failure | non-blocking or fallback verified |  |  |

## 3. API Evidence
- `GET /api/agent/runs/{run_id}` summary:
- `GET /api/agent/runs/{run_id}/events` key excerpts:
- `GET /api/agent/runs/{run_id}/result` key excerpts:
- `GET /api/validation/context?run_id=...` key excerpts:

## 4. Log Evidence
- `[AGENT]` excerpts:
- fallback-to-v1 evidence (if any):
- `[SUMMARY]/[EVIDENCE]` excerpts:

## 5. Screenshot Paths
- processing:
- validation:
- report:
- cockpit:

## 6. Gate Checks
- [ ] traceability coverage >= 0.90
- [ ] high-risk findings are mapped or have unavailable reason
- [ ] non-canary runs still use v1
- [ ] canary runs use v2 and remain stable
- [ ] rollback by env switch verified

## 7. Final Decision
- [ ] PASS
- [ ] FAIL
- Risk notes:

