# Phase 0 Scope and Boundaries

## 1. Phase 0 goal
Phase 0 is a **decision-freeze phase**, not a feature implementation phase.

Primary outcomes:
- Shared architecture language across the team.
- Shared contract language across backend/frontend/model/demo tracks.
- Shared execution cadence for Week 2 onward.

## 2. In-scope (must finish in Week 1)
- Freeze competition narrative and demo flow.
- Freeze core object models.
- Freeze minimum API contracts and payload fields.
- Freeze frontend page IA and Definition of Done (DoD).
- Freeze ownership boundaries for 6 members.
- Freeze risk register and change control process.

## 3. Out-of-scope (must NOT be done in Phase 0)
- Large code refactors.
- Model retraining or heavy data migration.
- Full production-level observability deployment.
- New feature implementation beyond tiny placeholders for planning validation.

## 4. Competition-first defaults
- Frontend impact first: Cockpit must be the main stage.
- Backend can run in `real/mock/hybrid` modes.
- Every displayed result must carry `source_tag`.
- Demo continuity has higher priority than full backend completeness.

## 5. Required decision locks
- Lock A: Core objects and ownership of each object.
- Lock B: API endpoint surfaces and response payload keys.
- Lock C: Page sequence in competition demo.
- Lock D: Which items are real now vs mock now.
- Lock E: Acceptance gates for entering Phase 1.

## 6. Phase 0 outputs acceptance
Phase 0 is accepted only when:
1. All files in this folder are reviewed and signed by owners.
2. No unresolved field/API argument remains.
3. A/B/C demo scripts are usable for rehearsal.
4. Week 2 owners have explicit deliverables and dependencies.

