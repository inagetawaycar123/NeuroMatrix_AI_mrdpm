# Phase 0 Week-1 Execution Board

## 1. Daily checklist (D1-D7)

### D1 Kickoff and alignment
- [x] Confirm competition objective and main stage (Cockpit first).
- [x] Confirm Phase 0 in-scope/out-of-scope.
- [x] Assign owners for all 9 documents in this folder.

### D2 Architecture freeze v1
- [x] Review five-layer architecture.
- [x] Lock runtime modes (`real/mock/hybrid`).
- [x] Lock A/B/C demo paths.

### D3 Contract freeze (Gate 1)
- [x] Freeze core object fields.
- [x] Freeze API response keys.
- [x] Freeze source_tag display requirement.
- [x] Gate 1 review passed.

### D4 Frontend IA and DoD freeze
- [x] Freeze page order and transitions.
- [x] Freeze cockpit panel composition.
- [x] Freeze node card required fields.

### D5 Demo script freeze (Gate 2)
- [x] Freeze Scenario A script.
- [x] Freeze Scenario B script.
- [x] Freeze Scenario C script.
- [x] Gate 2 review passed.

### D6 Ownership and milestones freeze
- [x] Confirm W2-W8 milestone owners.
- [x] Confirm weekly cadence and escalation SLA.
- [x] Publish risk register baseline.

### D7 Final gate (Gate 3)
- [x] Full doc pack walkthrough.
- [x] Resolve all open decisions.
- [x] Gate 3 review passed.
- [x] Officially start Phase 1.

---

## 2. Gate criteria

### Gate 1 (end of D3)
- Object/API contracts frozen.
- No unresolved required fields.

### Gate 2 (end of D5)
- A/B/C scripts frozen.
- Demo page order frozen.

### Gate 3 (end of D7)
- Ownership and milestones frozen.
- Risk/change process active.

---

## 3. Meeting templates

### Daily standup (15 min)
```text
Yesterday done:
Today plan:
Blockers:
Needs support from:
```

### Weekly gate review (45-60 min)
```text
What was locked:
What changed:
Any contract drift:
Demo readiness score:
Go/No-go:
```

---

## 4. Readiness scorecard (end of Week 1)
| Item | Score (0-2) | Notes |
|---|---:|---|
| Architecture freeze | 2 | Five-layer architecture + runtime modes frozen |
| Data/API freeze | 2 | Objects and API keys frozen in docs 03/04 |
| Frontend IA freeze | 2 | Page order + DoD frozen in doc 05 |
| Demo script freeze | 2 | Scenario A/B/C scripts frozen in doc 06 |
| Team ownership freeze | 2 | Ownership + milestones frozen in doc 07 |
| Risk control readiness | 2 | Risk register + CR process frozen in doc 08 |

Passing threshold: total >= 10/12 and no critical blocker.

Current total: **12/12**

---

## 5. Gate sign-off record (W2-D1)
| Gate | Result | Date | Owners | Notes |
|---|---|---|---|---|
| Gate 1 | Passed | 2026-04-19 | 敬 / 朱 / 袁 | Contract and required fields aligned |
| Gate 2 | Passed | 2026-04-19 | 敬 / 康 / 雷 | A/B/C demo scripts frozen |
| Gate 3 | Passed | 2026-04-19 | 敬 + All | Ownership and risk process activated |

Go/No-go decision: **Go (enter Phase 1)**
