# Validation UI Refactor Acceptance Record

Date: 2026-03-21
Scope: ICV/EKV visualization refactor (no Week6 features)

## 1. Structural Checks

- Viewer sidebar no longer shows dedicated ICV blocks (icvPlaceholder, icvStaticPanel removed at runtime).
- Report page no longer renders Evidence Validation Summary module.
- New page /validation is available with two tabs (ICV, EKV).

## 2. Navigation Checks

- Viewer: top toolbar can open Validation Center (ICV/EKV entry).
- Report: header action Validation opens /validation?...&tab=ekv.

## 3. Data Chain Checks

- API: GET /api/validation/context
- Source priority:
  1) agent run result
  2) report_payload (case level)
  3) local fallback on frontend only

## 4. Runtime Evidence (to fill with real runs)

- Case A:
  - patient_id: TODO
  - file_id: TODO
  - run_id: TODO
  - status consistency (Processing vs Validation Center): TODO
  - screenshot paths: TODO

- Case B:
  - patient_id: TODO
  - file_id: TODO
  - run_id: TODO
  - status consistency (Viewer/Report/Validation): TODO
  - screenshot paths: TODO

## 5. Command-Level Checks

- python -m py_compile backend/app.py
- node --check static/js/viewer.js
- node --check static/js/validation.js
- cmd /c npm run build (frontend)

## 6. Conclusion

- Refactor goal achieved at UI level: ICV and EKV details are decoupled from crowded original locations and centralized in Validation Center.
- Core Week5 algorithms/semantics are unchanged.
