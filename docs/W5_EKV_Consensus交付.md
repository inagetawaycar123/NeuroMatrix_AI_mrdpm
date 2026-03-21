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
  - Example source ref: `中国脑卒中防治指导规范（2021 年版）.pdf#page=249`

## 5. Notes

- This delivery does not add new HTTP routes.
- Existing `/api/upload/*` and `/api/agent/runs*` contracts remain compatible.
- Clinical sign-off still requires manual case-based validation records (run IDs/screenshots).
