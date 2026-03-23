# W5 EKV + Consensus Acceptance Record

Date: `2026-03-20`  
Owner: `Codex`

## 1. Scope

- Week5 implementation acceptance for:
  - EKV document-driven verification
  - Consensus Lite conflict decision
  - Processing/Viewer/Report visibility
  - Non-blocking pipeline behavior

## 2. Code-Level Checks (Completed)

1. Python syntax check  
Command:
```bash
python -m py_compile backend/app.py backend/ekv.py backend/ekv_retrieval.py
```
Result: `PASS`

2. Frontend JS syntax checks  
Commands:
```bash
node --check static/js/processing.js
node --check static/js/viewer.js
```
Result: `PASS`

3. React report build  
Command:
```bash
cd frontend
cmd /c npm run build
```
Result: `PASS` (assets emitted to `static/dist/`)

4. EKV retrieval smoke (local PDF evidence)  
Command: inline Python smoke  
Result:
- `EKV_docs` found
- retrieval hit count: `3`
- sample citation: `中国脑卒中防治指导规范（2021 年版）.pdf#page=249`

5. EKV/Consensus rule smoke  
Command: inline Python smoke  
Result:
- NCCT-only -> CTP-related claims `unavailable`
- conflict case -> consensus `decision=escalate`
- output marker: `week5_smoke_ok`

## 3. Manual E2E Case Records (To be filled by runtime verification)

> Fill the following after running real upload cases in your environment.

### Case A: NCCT-only

- run_id: `TBD`
- job_id: `TBD`
- file_id: `TBD`
- Expected:
  - EKV marks CTP claims `unavailable/not_applicable`
  - Consensus usually `skipped`
  - Report still generated
- Evidence:
  - Processing screenshot path: `TBD`
  - Viewer screenshot path: `TBD`
  - Logs snippet `[AGENT]/[EKV]/[CONSENSUS]`: `TBD`
- Result: `TBD`

### Case B: NCCT+mCTA

- run_id: `TBD`
- job_id: `TBD`
- file_id: `TBD`
- Expected:
  - EKV outputs claims + citations
  - Consensus triggers when conflict conditions are met
- Evidence:
  - Processing screenshot path: `TBD`
  - Viewer screenshot path: `TBD`
  - Report screenshot path: `TBD`
  - Logs snippet `[AGENT]/[EKV]/[CONSENSUS]`: `TBD`
- Result: `TBD`

### Case C: NCCT+mCTA+CTP

- run_id: `TBD`
- job_id: `TBD`
- file_id: `TBD`
- Expected:
  - EKV validates quantitative claims against CTP context
  - Processing/Viewer/Report values remain consistent
- Evidence:
  - Processing screenshot path: `TBD`
  - Viewer screenshot path: `TBD`
  - Report screenshot path: `TBD`
  - Logs snippet `[AGENT]/[EKV]/[CONSENSUS]`: `TBD`
- Result: `TBD`

## 4. Non-Blocking Verification Scenarios

### EKV failure (forced)

- Setup: `FORCE_EKV_FAIL=1`
- Expected:
  - run can still complete (report generated)
  - EKV shown as `unavailable` with reason
- Record:
  - run_id/job_id/file_id: `TBD`
  - logs/screenshot: `TBD`

### Consensus failure (forced)

- Setup: `FORCE_CONSENSUS_FAIL=1`
- Expected:
  - run can still complete (report generated)
  - consensus shown as `unavailable` with reason
- Record:
  - run_id/job_id/file_id: `TBD`
  - logs/screenshot: `TBD`

## 5. Acceptance Conclusion

- Code-level Week5 implementation: `PASS`
- Local build/syntax/retrieval smokes: `PASS`
- Manual E2E sign-off: `PENDING` (fill Case A/B/C and forced-failure records)

---

## 6. Semantic Consistency Patch (2026-03-23)

### 6.1 Fixed items

- Validation context linkage improved with `run_id` propagation and fallback chain clarity.
- EKV unavailable KPI semantics corrected:
  - unavailable + no findings => `finding_count` renders `-`
  - unavailable => `support_rate` renders `-`, not `0%`
- Consensus unavailable fallback aligned:
  - decision becomes `unavailable`
  - conflict KPI is nullable in fallback path.

### 6.2 Verification checklist

- [x] Frontend summary mapping updated (`processing.js`, `validation.js`)
- [x] Backend fallback semantics updated (`backend/app.py`)
- [x] Viewer/report jump links now keep run context for validation
- [ ] Real-case acceptance evidence appended (A/B/C + forced-failure records)

### 6.3 Current status

- Week5 engineering closure: **completed**
- Week5 final manual sign-off: **pending real-case evidence**
