# Phase 0 Risk Register and Change Control

## 1. Risk register (initial)

| ID | Risk | Probability | Impact | Trigger | Mitigation | Owner |
|---|---|---|---|---|---|---|
| R1 | Cockpit visual target not reached by W3 | Medium | High | DAG/card/timeline incomplete | lock scope to must-have visuals first | 康 |
| R2 | API fields drift between FE/BE | High | High | frontend cannot render node details | enforce frozen contract + gate checks | 朱 |
| R3 | NCCT/vessel model integration instability | Medium | High | model timeout/error > threshold | hybrid fallback + source_tag exposure | 袁 |
| R4 | Demo breaks under unstable backend | Medium | High | live scenario cannot proceed | scripted scenario endpoint + cached runs | 雷 |
| R5 | Too many late requirement changes | High | Medium | weekly goals slip repeatedly | formal change request process | 敬 |
| R6 | Report/review UX too complex for judges | Medium | Medium | explanations exceed time slot | tighten storyline and fixed script cues | 刘 |
| R7 | Medical credibility challenge in Q&A | Medium | High | judge questions mock validity | always disclose source_tag and fallback logic | 敬 |

## 2. Risk response SLA
- Critical risk: same day owner action + lead notification.
- High risk: mitigation plan within 24h.
- Medium risk: mitigation plan within 48h.

## 3. Change control process (frozen)
Any change affecting contracts, page order, or milestone ownership must follow:
1. Submit change request (CR) with reason and impact.
2. Identify affected owners and acceptance criteria.
3. Lead approval required before merge.
4. Update impacted docs in this folder on same day.

## 4. CR template
```text
CR_ID:
Requester:
Date:
Change summary:
Reason:
Affected files/contracts/pages:
Impact on milestones:
Rollback strategy:
Decision: approved/rejected
Approver:
```

## 5. Gate protection rules
- After Gate 1: no object/API semantic changes without CR.
- After Gate 2: no demo page order changes without CR.
- After Gate 3: no ownership changes without CR.

