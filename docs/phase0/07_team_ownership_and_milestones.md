# Phase 0 Team Ownership and W2-W8 Milestones

## 1. Team ownership (locked)

| Member | Role | Core ownership | Backup alignment |
|---|---|---|---|
| 敬 | Lead/Architecture | architecture decisions, demo narrative, final review gates | all tracks |
| 朱 | Backend orchestration | AgentRun/Step/Event, DAG executor, API contracts | review/runtime |
| 袁 | Model integration | NCCT/vessel models, tool I/O normalization, fallback policy | analysis path |
| 康 | Frontend cockpit | cockpit graph/cards/timeline, interaction quality | imaging linkage |
| 刘 | Report/evidence | structured report, evidence mapping, knowledge-level display | review flow |
| 雷 | QA/demo/docs | E2E checklist, demo scripts, risk tracking, packaging | release readiness |

## 2. W2-W8 milestone board

| Week | Milestone | Primary owner | Exit criteria |
|---|---|---|---|
| W2 | Cockpit visual skeleton + run/event baseline | 康 + 朱 | cockpit can replay one run timeline |
| W3 | DAG rendering + node details + orchestration contracts | 康 + 朱 | node card fields fully mapped |
| W4 | NCCT/vessel nodes connected (real/hybrid fallback) | 袁 + 朱 | two new triage nodes affect path |
| W5 | Decision bundle + report/review linkage | 刘 + 朱 | report sections map to bundle data |
| W6 | Evidence panel + validation summary integration | 刘 + 康 | conclusion-to-evidence navigation works |
| W7 | P1 demo-level knowledge/feedback view | 刘 + 雷 | source levels and feedback flow visible |
| W8 | Freeze, rehearsal, competition package | 敬 + 雷 | A/B/C scripts stable in live rehearsal |

## 3. Weekly operating rhythm
- Monday: planning + dependency sync (30-45 min)
- Wednesday: integration checkpoint (45 min)
- Friday: gate review + demo rehearsal (60 min)

## 4. Escalation rule
- Blockers > 24h must be escalated to 敬 in writing.
- Cross-track contract changes need same-day review by owners.
- No silent field/schema change after gate lock.

## 5. Output ownership checklist
- Every artifact has: owner, reviewer, due date, acceptance criteria.
- Every PR has: affected contract notes + demo impact note.
- Every weekly build has: one-click demo path validation.

