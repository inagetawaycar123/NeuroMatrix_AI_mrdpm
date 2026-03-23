# W4 ICV 验收记录

> 版本：V1（草案）
> 周期：Week4（内部一致性 ICV 落地）

## 1. 基本信息

- 验收日期：____-__-__
- 验收人：________
- 代码版本 / Commit：`________`
- 测试环境：本地 / 测试服 / 生产影子环境（圈选其一）

## 2. 验收范围

- ICV 规则引擎是否按设计运行（见 `backend/icv.py`）；
- ICV 与 Agent 主链集成是否正确（`_tool_icv` / `_tool_generate_medgemma_report`）；
- 前端 Processing / Viewer 能否正确显示 ICV 状态和具体问题；
- ICV 是否为非阻断：主链在 ICV 失败或触发 fail 时仍可完成报告。

## 3. 用例列表

> 建议至少覆盖下列场景，可按实际病例增减。

### 用例 1：CTP mismatch 不一致

- 条件：
- 病例具有 NCCT + mCTA + CTP，存在核心 / 半暗带体积与报告中 mismatch 比例不一致的情况；
- 路径：`ncct_mcta_ctp`。
- 预期：
- ICV 运行成功，`icv.status = warn` 或 `fail`；
- `findings` 中包含 `R2_mismatch_consistency`，中文 message 能清楚说明“不匹配比值与体积推算不一致”；
- Processing 页 Agent 面板与 Viewer ICV 面板均能看到该问题。
- 实际结果：
- [ ] 通过   [ ] 未通过
- 说明：
- 

### 用例 2：仅 NCCT 却出现 CTA 章节

- 条件：
- 病例仅有 NCCT 影像，`canonical_modalities = ["ncct"]`；
- 报告中出现“CTA 见...”等章节或描述。
- 预期：
- ICV 运行成功，`icv.status = warn` 或 `fail`；
- 触发模态/章节不一致相关规则（ID 以实际实现为准）；
- Viewer ICV 面板中能看到对应中文问题描述和建议动作。
- 实际结果：
- [ ] 通过   [ ] 未通过
- 说明：
- 

### 用例 3：分析提示 LVO，但报告写“未见大血管闭塞”

- 条件：
- 分析结果提示存在大血管闭塞（如 `has_lvo = true` 或类似字段）；
- 报告文本中写“未见明显大血管闭塞”或语义等价表述。
- 预期：
- ICV 运行成功，`icv.status = warn` 或 `fail`；
- 触发“状态/语气不一致”相关规则；
- 前端能清楚标出该问题，便于医生人工复核。
- 实际结果：
- [ ] 通过   [ ] 未通过
- 说明：
- 

### 用例 4：ICV 输入缺失 / 工具异常

- 条件：
- 人为构造或遇到 ICV 输入缺失、内部异常的情况（例如某关键字段为 `null`）。
- 预期：
- ICV 工具在 `tool_results` 中标记为 `status = failed`，日志中有明确错误信息；
- 主链仍然能够生成分析结果与报告；
- Viewer 中 ICV 面板可显示“结果暂不可用”或空状态（具体文案以前端实现为准）。
- 实际结果：
- [ ] 通过   [ ] 未通过
- 说明：
- 

## 4. 终端与日志检查

- [ ] Agent 工具执行日志中能看到 ICV 起止、状态与 findings 统计；
- [ ] 异常场景下有足够的错误信息定位问题；
- [ ] 日志内容不包含患者隐私信息（或已做脱敏处理）。

## 5. 结论

- 本轮验收结论：
- [ ] 通过   [ ] 有待修复
- 剩余问题与 TODO：
- 

> 备注：本记录建议与 `docs/W4_ICV交付.md` 一起维护，后续如对 ICV 规则或策略做重大调整，应补充新的验收轮次记录。

---

## 6. Engineering Closure Notes（2026-03-18）

### 6.1 Code-level completion

- [x] ICV soft-fail behavior implemented in agent pipeline
- [x] stage mapping aligned to `tooling -> icv -> summary -> done`
- [x] ICV output contract extended:
  - `finding_count`
  - `score`
  - `confidence_delta`
  - normalized finding fields with `severity/suggested_action`
- [x] Processing and Viewer ICV rendering paths aligned

### 6.2 Local verification logs

- `python -m py_compile backend/app.py backend/icv.py` -> passed
- `node --check static/js/processing.js` -> passed
- `node --check static/js/viewer.js` -> passed
- `python -c "...evaluate_icv(...)"` smoke check -> returned extended ICV fields

### 6.3 Pending runtime evidence (manual)

- [ ] `run_id/job_id/file_id` from real cases
- [ ] API response snapshots for `/api/agent/runs*`
- [ ] terminal log snippets with `[AGENT]` + `[ICV]`
- [ ] Processing/Viewer screenshots

### 6.4 Current sign-off status

- Engineering sign-off: **ready**
- Clinical runtime sign-off: **pending evidence attachment**

---

## 7. Semantic Consistency Patch (2026-03-23)

### 7.1 Fixed items

- `run_id` context continuity has been enforced across processing/viewer/report/validation entry.
- Unavailable ICV KPI semantics are corrected:
  - unavailable with empty findings => display `-` (not `0`)
  - backend unavailable payload now uses nullable KPI values.

### 7.2 Verification checklist

- [x] Frontend mapping logic updated (`processing.js`, `validation.js`)
- [x] Backend fallback payload updated (`backend/app.py`)
- [x] Validation summary defaults updated (template)
- [ ] Real-case runtime evidence appended (`run_id/job_id/file_id + screenshots + logs`)

### 7.3 Current status

- Week4 engineering closure: **completed**
- Week4 final clinical sign-off: **pending runtime evidence**
