# W5 EKV + Consensus Lite Delivery

Version: `v1`  
Cycle: `Week5`  
Scope: `EKV (evidence verification) + Consensus Lite (conflict decision), non-blocking`

## 1. Objectives

- Upgrade Week4 ICV-only validation to a complete verification chain:
  - `tooling -> icv -> ekv -> consensus -> summary -> done`
- Keep the upload/report main path non-blocking:
  - `ekv` or `consensus_lite` failure does not stop report generation.
- Make EKV/Consensus visible in Processing, Viewer, and structured report payload.

## 2. Core Implementation

### 2.1 Agent pipeline and stage mapping

- Added `ekv` and `consensus_lite` into tool sequences:
  - `AGENT_TOOL_SEQUENCE_MAP`
  - `POST_UPLOAD_SUMMARY_TOOL_SEQUENCE`
- Added stage mapping:
  - `ekv -> ekv`
  - `consensus_lite -> consensus`
  - `generate_medgemma_report -> summary`
- Added retry limits:
  - `ekv: 1`
  - `consensus_lite: 1`

### 2.2 EKV implementation (document-driven)

- New module: `backend/ekv.py`
  - `evaluate_ekv(...)`
  - `evaluate_consensus_lite(...)`
- New module: `backend/ekv_retrieval.py`
  - Local PDF index + chunk retrieval from `EKV_docs/`
  - Lightweight scoring (TF-IDF/BM25-like)
  - Citation output includes `doc_name + page + snippet`
- `_query_guideline_kb(...)` upgraded:
  - Prefer local retrieval results from `EKV_docs`
  - Keep fallback to stub when no evidence can be retrieved

### 2.3 Contracts

- `EKVResult` (via `tool_results.structured_output` and `run.result`):
  - `status`
  - `finding_count`
  - `score`
  - `confidence_delta`
  - `support_rate`
  - `claims[]`
  - `findings[]`
  - `citations[]`
- `ConsensusResult`:
  - `status`
  - `decision`
  - `conflict_count`
  - `summary`
  - `conflicts[]`
  - `next_actions[]`

### 2.4 Non-blocking behavior

- In `_run_agent_pipeline(...)`:
  - Soft-fail and continue for `icv`, `ekv`, `consensus_lite`
  - Hard-fail only for non-verification tools
- `_tool_generate_medgemma_report(...)` now merges:
  - `report_payload.icv`
  - `report_payload.ekv`
  - `report_payload.consensus`
  - Includes `unavailable` fallback payload on verification tool failure

### 2.5 Frontend visibility

- Processing page (`static/js/processing.js`)
  - Added resolvers:
    - `resolveEkvFromRun(...)`
    - `resolveConsensusFromRun(...)`
  - Added summary bindings:
    - `EKV status / findings / support_rate`
    - `Consensus decision / conflict_count`
  - Source priority:
    - `tool_results(completed)` > `report_payload` > `tool_results(failed)`
- Viewer page (`static/js/viewer.js`)
  - Added payload extractors:
    - `extractEkvPayload(...)`
    - `extractConsensusPayload(...)`
  - Upgraded static validation panel renderer to display:
    - ICV + EKV + Consensus summary in one place
- Report (React, `frontend/src/components/StructuredReport.tsx`)
  - Added `Evidence Validation Summary` section
  - Displays EKV status/findings/support_rate, consensus decision/conflict count,
    claim verdicts and citations

## 3. Files Changed

- `backend/app.py`
- `backend/ekv.py` (new)
- `backend/ekv_retrieval.py` (new)
- `static/js/processing.js`
- `static/js/viewer.js`
- `backend/templates/patient/upload/processing/index.html`
- `frontend/src/components/StructuredReport.tsx`
- `tests/test_ekv.py` (new)
- `static/dist/*` (rebuilt frontend assets)

## 4. Local Validation

- `python -m py_compile backend/app.py backend/ekv.py backend/ekv_retrieval.py` -> passed
- `node --check static/js/processing.js` -> passed
- `node --check static/js/viewer.js` -> passed
- `cmd /c npm run build` (under `frontend/`) -> passed
- EKV retrieval smoke:
  - `search_guideline_evidence(...)` returns citations from local PDFs in `EKV_docs`
  - Example source ref: `涓浗鑴戝崚涓槻娌绘寚瀵艰鑼冿紙2021 骞寸増锛?pdf#page=249`

## 5. Notes

- This delivery does not add new HTTP routes.
- Existing `/api/upload/*` and `/api/agent/runs*` contracts remain compatible.
- Clinical sign-off still requires manual case-based validation records (run IDs/screenshots).

## Validation Center Refactor (UI only)

- EKV/Consensus details are removed from report page body to reduce cognitive load.
- A dedicated Validation Center page is introduced:
  - route: `/validation`
  - tabs: `ICV`, `EKV`
  - data source priority: `agent run result` > `report_payload` > `local fallback`
- Report page now provides a Validation action button (default tab: `ekv`).
- Algorithm contracts and verdict semantics are unchanged.

## Week5 Sign-off Supplement (2026-03-23)

### A. Source and Context Alignment

- Validation page now resolves run context with explicit priority:
  1. URL `run_id`
  2. `latest_agent_run_<file_id>` local context
  3. case fallback when run context is missing.
- This reduces false `unavailable` caused by missing run linkage.

### B. Unavailable KPI Semantics

- EKV unavailable state no longer displays misleading valid-looking KPIs.
- UI behavior:
  - `finding_count` shows `-` (not `0`) when unavailable and no details
  - `support_rate` shows `-` (not `0%`) in unavailable state
- Backend fallback behavior:
  - `finding_count: null`
  - `support_rate: null`
  - no fake calculated numbers under unavailable.

### C. Consensus Consistency

- `consensus` unavailable now uses `decision=unavailable` and nullable conflict KPI in fallback semantics.
- This avoids contradictory display such as unavailable status with effective decision values.

### D. Sign-off Note

- Week5 semantic consistency patch: **implemented**.
- Manual runtime evidence attachment in acceptance record is still needed for full sign-off.
