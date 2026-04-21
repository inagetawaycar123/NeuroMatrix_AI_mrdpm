# Phase 0 Demo Scripts (A/B/C)

## 1. General demo structure
Each scenario follows:
1. Create/upload case
2. Enter cockpit
3. Explain DAG progression
4. Open imaging page and show evidence relation
5. Open report page and show structured output + review
6. Open evidence panel and trace critical conclusions

All scenarios must explicitly mention `source_tag`.

---

## 2. Scenario A: NCCT + mCTA (no real CTP)

### Expected path
`detect_modalities -> ncct_triage -> vessel_classification -> generate_ctp_maps -> run_stroke_analysis -> validation -> report -> review`

### Judge-facing highlights
- "System dynamically selected pseudo-CTP generation because real CTP is absent."
- "The chain remains explainable with evidence references."

### Must-show UI moments
- Cockpit node transitions through pseudo-CTP generation.
- Imaging page: Tmax/CBF/CBV overlays.
- Report page: mismatch-related recommendation.

### Fallback policy
- If model step fails, use `hybrid` fallback and continue timeline.

---

## 3. Scenario B: NCCT + CTA + CTP

### Expected path
`detect_modalities -> ncct_triage -> vessel_classification -> run_stroke_analysis -> validation -> report -> review`

### Judge-facing highlights
- "System skipped MRDPM path because real CTP is available."
- "Workflow adapts to input conditions (DAG behavior, not fixed pipeline)."

### Must-show UI moments
- Cockpit branch skipping pseudo-CTP node.
- Imaging page with real CTP evidence.
- Evidence panel showing guideline-linked suggestion.

---

## 4. Scenario C: Conflict/high-risk requiring human review

### Expected path
normal analysis path + `consensus/consistency conflict` -> `human_review_required`

### Judge-facing highlights
- "System does not auto-finalize risky conclusions."
- "Doctor has final authority and full traceability."

### Must-show UI moments
- Cockpit risk escalation and review_required state.
- Report section review actions (confirm/edit/reject).
- Review completion gate before viewer/report finalization.

---

## 5. Live demo timing (recommended)
- Scenario A: 6-7 min
- Scenario B: 4-5 min
- Scenario C: 5-6 min
- Total core demo: 15-18 min

## 6. Narration checkpoints (fixed wording cues)
- "This is planned execution, not a one-shot model call."
- "Each conclusion is linked to evidence and source level."
- "When conflict appears, the system pauses for human review."
- "The final output is a ClinicalDecisionBundle, not plain text only."

## 7. Demo failure contingency
- If backend latency spikes: switch to preloaded hybrid run and continue.
- If a model endpoint fails: show `source_tag=mock` badge and explain fallback.
- If a page fails to load: reopen from cockpit using persisted run context.

## 8. Ownership
- Demo script owner: 雷
- Clinical narrative owner: 敬
- UI flow owner: 康

