# Phase 0 Frontend IA and DoD Freeze

## 1. IA goal
Make judges immediately understand:
- This is an agent system, not a single-model tool.
- The system is traceable and clinically controllable.
- Human review is explicit and mandatory where needed.

## 2. Competition page order (locked)
1. Upload / Case create
2. Agent Cockpit (main stage)
3. Imaging view
4. Structured report + review
5. Evidence trace panel

## 3. Cockpit layout (must-have)
- Left: case profile, input modalities, risk badges
- Center: DAG execution graph
- Right: current conclusion + evidence summary + warnings
- Bottom: timeline/event stream

Must show on first screen:
- current stage
- current node
- node statuses
- source tag (real/mock/hybrid)

## 4. Page-level DoD checklist

### 4.1 Upload page DoD
- [ ] modality recognition feedback visible
- [ ] recommended path preview visible
- [ ] run launch status visible

### 4.2 Cockpit page DoD
- [ ] DAG nodes rendered with status colors
- [ ] clicking node opens detail card
- [ ] detail card includes confidence/latency/risk/source_tag
- [ ] timeline updates by polling or stream
- [ ] fallback banner when in mock/hybrid mode

### 4.3 Imaging page DoD
- [ ] original + derived maps toggle available
- [ ] at least 3 overlays supported
- [ ] each key conclusion links to image evidence hint

### 4.4 Report page DoD
- [ ] report in structured sections
- [ ] section-level confirm/edit/reject actions
- [ ] review completion gate before final sign-off
- [ ] citation/evidence mapping visible

### 4.5 Evidence panel DoD
- [ ] conclusion-to-evidence mapping list
- [ ] evidence source level shown (S/A/B/C/D)
- [ ] source reference/snippet visible

## 5. Visual language freeze
- Status color map:
  - completed: green
  - running: blue
  - pending: gray
  - failed: red
  - review_required: amber
- Source badge:
  - real: solid green badge
  - hybrid: blue/amber split badge
  - mock: amber outline badge

## 6. "Amazing demo" interaction requirements
- DAG node reveal animation on run start
- Smooth status transitions in timeline
- Cross-page context persistence (`run_id`, `patient_id`, `file_id`)
- One-click jump from cockpit node to imaging/report context

## 7. Frontend ownership
- Primary owner: 康
- Co-owners: 敬（report/evidence sections）, 万（demo script alignment）

