# Phase 0 Architecture Freeze

## 1. Target architecture (competition version)
Five-layer architecture:

1. Presentation and Interaction Layer  
2. Service and Orchestration Layer  
3. Agent Collaboration Layer  
4. Model and Tool Layer  
5. Data and Audit Layer

## 2. Runtime modes
- `real`: all supported steps run with real backend/model output.
- `mock`: steps run with scripted outputs for stable demo.
- `hybrid`: partial real + fallback mock by step.

Rule:
- UI must render `source_tag` for each node and conclusion.

## 3. Core runtime flow
```text
Case intake
 -> Modality detect
 -> DAG plan
 -> Node execution
 -> Evidence/consistency checks
 -> Structured report
 -> Human review
 -> Decision bundle output
```

## 4. Input path variants (must be supported by planner)
1. `NCCT only`
2. `NCCT + CTA/mCTA`
3. `NCCT + CTA/mCTA + CTP`

Optional branches:
- suspected hemorrhage branch
- conflict/manual-review branch

## 5. Frontend storytelling flow (locked)
```text
Upload page
 -> Cockpit main stage
 -> Imaging page
 -> Report page
 -> Evidence trace panel
```

## 6. Phase 0 architecture constraints
- Keep existing runnable chain in parallel (no hard cut-over in Week 1).
- Introduce contracts first, then incremental migration.
- No hidden logic in UI: node-level status must come from explicit payload fields.

## 7. Architecture ownership
- Global architecture owner: 敬
- Orchestration owner: 朱
- Model integration owner: 袁
- Frontend architecture owner: 康
- Report/evidence owner: 刘
- Validation/demo stability owner: 雷

