# 卒中智能体（NCCT必选、多模态可选）研发需求清单与优先级

基于已定稿方案：[`plans/STROKE_AGENT_PROPOSAL.md`](plans/STROKE_AGENT_PROPOSAL.md)，这里将需求拆解为可执行的研发 Backlog，并按 P0/P1/P2 排序（后端 API / 前端页面 / 算法模块）。

---

## 0. 现有资产可复用清单（锚点）

- 后端编排与路由集中在：[`app.py`](app.py)
  - 上传入口：[`upload_files()`](app.py:2803)
  - viewer 入口：[`viewer_page()`](app.py:2798)
  - 伪彩生成：[`generate_all_pseudocolors_route()`](app.py:895)
  - 卒中分析：[`analyze_stroke()`](app.py:955)
  - 报告页：[`report_page()`](app.py:1633)
- AI 推理框架：[`class MultiModelAISystem`](ai_inference.py:22)
- 病灶分析框架：[`class StrokeAnalysis`](stroke_analysis.py:16) 与 [`analyze_stroke_case()`](stroke_analysis.py:374)
- Web 页面：上传页 [`templates/patient/upload/index.html`](templates/patient/upload/index.html) + 脚本 [`static/js/upload.js`](static/js/upload.js)
- Web 页面：viewer [`templates/patient/upload/viewer/index.html`](templates/patient/upload/viewer/index.html) + 脚本 [`static/js/viewer.js`](static/js/viewer.js)

---

## 1. 需求分层与交付物定义

### 1.1 统一交付物（每个病例 file_id）

- `case_manifest.json`：模态可用性、切片数、关键元数据、QC 总结、各模块状态
- `module_results/*.json`：NCCT/CTA(或mCTA)/CTP 各自结构化输出
- `evidence/`：证据图片（叠加图、关键切片截图、伪彩参数图等）
- `report_draft.md`：自动拼装的“预报告”（可编辑）

### 1.2 模态组合支持（产品约束 → 工程约束）

- NCCT 必选
- 可选组合：
  - NCCT-only
  - NCCT + single-phase CTA
  - NCCT + mCTA（三期）
  - NCCT + CTA + CTP（含参数图输入）

---

## 2. 优先级总览（Backlog 排序）

### P0（MVP：能闭环、可在真实流程跑通）

1. 上传链路改造：NCCT 必选，CTA/CTP 可选；返回可用模态与下一步建议
2. 病例 Manifest 与状态机：统一产物目录与模块状态
3. 智能体编排 API（run/status/result）：按可用模态自动触发模块并产出预报告
4. NCCT 单独分析 MVP：出血排除提示 + 早期缺血征象提示 + QC + 报告段落
5. CTP 单独分析 MVP：
   - 有参数图：直接量化 + 可视化
   - 无参数图且 NCCT+mCTA：复用现有灌注图生成与现有阈值分析（核心/半暗带/不匹配）
6. viewer 融合展示：缺失模态灰态占位 + 证据卡 + 一键生成预报告

### P1（增强：把 CTA/mCTA 与融合逻辑补齐，形成决策支持）

7. CTA/mCTA 单独分析 MVP：LVO 疑似 + 闭塞段提示 +（mCTA）侧支分级
8. 多模态一致性校验与冲突卡：侧别、部位、体积逻辑冲突 → 提示人工复核
9. 报告拼装器增强：模块化段落可选合并、引用证据、结论不确定性与风险提示模板化

### P2（规模化：可信、可审计、可验证）

10. 模型化升级：ASPECTS 学习型、血管分割/闭塞分类、侧支学习型评分
11. 合规与审计：日志、权限、脱敏、模型版本可追溯
12. 临床验证与数据闭环：回顾性指标、失败样本归因、前瞻性暗运行 SOP

---

## 3. 后端 API 需求（按优先级拆解）

> 约定：所有接口以 `file_id` 作为病例主键，与现有 viewer 与产物目录对齐（现有系统已使用 file_id 组织 `static/processed`，参考 [`analyze_stroke_case()`](stroke_analysis.py:374)）。

### P0-API-1 上传接口：允许可选模态 + 返回可用性

**改造点**

- 现状：上传页前端要求 4 文件齐全（见 [`processFiles()`](static/js/upload.js:72) 中 `disabled = !(mcta && vcta && dcta && ncct)`）。
- 目标：NCCT 必须；CTA/mCTA/CTP 允许缺失；后端识别并记录 `available_modalities`。

**后端**

- 修改现有上传路由：[`upload_files()`](app.py:2803)
- 响应新增字段：
  - `available_modalities`: `['ncct', 'cta_single', 'mcta', 'ctp']` 的子集
  - `qc_summary`: 初步 QC（是否缺失、文件头读取成功、维度一致性等）
  - `next_recommended_step`: `viewer` / `need_cta` / `need_ctp`

**验收标准**

- 仅上传 NCCT 时可成功返回 `file_id` 并进入 viewer
- 上传 mCTA 三期时仍兼容现有流程

### P0-API-2 智能体编排接口（新增）

**新增接口**

- `POST /api/agent/run`
  - 入参：`file_id`, `patient_id`, `options`（如是否生成伪彩、是否运行 CTP 推理等）
  - 出参：`job_id`, `status`
- `GET /api/agent/status?file_id=...`
  - 出参：各模块状态：`ncct_status/cta_status/ctp_status/fusion_status/report_status`
- `GET /api/agent/result?file_id=...`
  - 出参：`case_manifest.json` + `module_results` + `report_draft.md` 的索引

**实现建议**

- 先做同步执行（P0），后续再引入异步队列
- 产物路径写入 `case_manifest.json`

**验收标准**

- 对任一输入组合（NCCT-only / NCCT+mCTA / NCCT+CTA+CTP）运行后均能返回一致结构的 result 索引

### P0-API-3 预报告生成与保存（复用 + 轻改造）

**复用点**

- 报告生成可参考现有百川调用逻辑：[`generate_report_with_baichuan()`](app.py:217)

**新增/改造点**

- 新增“预报告拼装器”（不依赖大模型）：将 NCCT/CTA/CTP 模块段落拼接为 `report_draft.md`
- `POST /api/report/save_draft`（或复用 [`api_save_report()`](app.py:1276) 并扩展字段）

**验收标准**

- 无 BAICHUAN key 时也能产出 `report_draft.md`
- 有 key 时可生成增强版段落，但必须保留“证据引用与不确定性提示”字段

### P1-API-4 融合一致性与冲突卡接口

- `GET /api/agent/conflicts?file_id=...`
  - 输出：冲突列表（类型、严重度、证据链接、建议复核点）

---

## 4. 前端页面与交互需求（按优先级拆解）

### P0-FE-1 上传页改造：NCCT 必选、其他可选

**涉及文件**

- 模板：[`templates/patient/upload/index.html`](templates/patient/upload/index.html)
- 脚本：[`processFiles()`](static/js/upload.js:72)

**需求**

- 表单校验：仅校验 NCCT 必填；mCTA/CTA/CTP 选择性启用
- 模态识别提示：上传前显示“当前已选择模态组合”
- 上传后：显示系统识别到的 `available_modalities` 与 QC

**验收标准**

- NCCT-only 能走通并进入 viewer
- 旧的 mCTA 四件套仍能走通

### P0-FE-2 viewer 灰态占位 + 证据卡 + 预报告入口

**涉及文件**

- 模板：[`templates/patient/upload/viewer/index.html`](templates/patient/upload/viewer/index.html)
- 逻辑：[`initializeViewer()`](static/js/viewer.js:58) 与 [`loadSlice()`](static/js/viewer.js:127)

**需求**

- 模态缺失：对应格子显示灰态占位与文案（例如：未上传 CTP，无法输出核心/半暗带量化）
- “证据卡区域”：展示每个模块的关键结论 + 链接到证据图片（叠加图/关键切片）
- “一键生成预报告”：调用 `POST /api/agent/run` 或 `POST /api/report/generate_draft`

**验收标准**

- viewer 在任何组合下不报错，且 UI 可解释

### P1-FE-3 冲突卡与不确定性呈现

- 在 viewer 增加“冲突/需复核”面板（严重度分级）
- 报告页中以引用形式插入证据链接与提示

---

## 5. 算法与规则模块需求（按优先级拆解）

### P0-ALG-1 QC 与输入识别（必须先做）

**目标**

- 统一做输入读取、维度/切片一致性检查、方向/强度异常提示
- 产出 `qc_summary.json` 写入 `case_manifest.json`

**验收标准**

- 任何读取失败都能返回可解释错误（不允许 silent fail）

### P0-ALG-2 NCCT 单独分析 MVP

**输出**

- `ncct_result.json`：出血排除提示、早期缺血征象提示、QC
- `evidence/ncct/*.png`：关键切片截图/热图
- `report_fragment_ncct.md`

**实现约束**

- 优先规则化与可解释（阈值、形态学、区域先验），后续再替换学习型模型

### P0-ALG-3 CTP 单独分析 MVP（参数图优先）

**输入路径**

- 有 CTP 参数图：直接阈值 + 后处理 + 体积计算
- 无参数图但 NCCT+mCTA：
  - 复用推理框架生成 CBF/CBV/Tmax（参考 [`class MultiModelAISystem`](ai_inference.py:22)）
  - 复用/扩展病灶分析（参考 [`class StrokeAnalysis`](stroke_analysis.py:16)）

**输出**

- `ctp_result.json`：核心/半暗带/不匹配、DEFUSE3 提示（hint）
- `evidence/ctp/*.png`：伪彩与叠加图
- `report_fragment_ctp.md`

### P1-ALG-4 CTA/mCTA 单独分析 MVP（LVO + 侧支）

**输出**

- `cta_result.json`：LVO 疑似、闭塞段、侧支评分（mCTA）
- `evidence/cta/*.png`：MIP/关键层面截图 + 标注
- `report_fragment_cta.md`

### P1-ALG-5 融合一致性校验（规则引擎）

**规则样例**

- 侧别一致性：CTA 闭塞侧与 CTP 缺损侧不一致 → 冲突卡
- 量化逻辑：NCCT 大面积低密度但 CTP 核心近 0 → 需复核

---

## 6. 数据结构建议（供后端/前端对齐）

### 6.1 case_manifest.json（建议字段）

```json
{
  "file_id": "...",
  "patient_id": 123,
  "available_modalities": ["ncct", "mcta"],
  "qc": {"status": "ok", "warnings": []},
  "modules": {
    "ncct": {"status": "done", "result": "module_results/ncct_result.json"},
    "cta": {"status": "skipped"},
    "ctp": {"status": "done", "result": "module_results/ctp_result.json"},
    "fusion": {"status": "done"},
    "report": {"status": "done", "draft": "report/report_draft.md"}
  }
}
```

### 6.2 module_results 的统一约定

- 必须包含：`status`、`confidence_or_quality`（可先用 rule-based 质量标志）、`key_findings[]`、`evidence[]`

---

## 7. 测试与验收（最小集合）

### P0 必测用例

- 用例 U1：NCCT-only → viewer 正常 → 生成预报告
- 用例 U2：NCCT+mCTA → 生成灌注图 → 伪彩 → 病灶量化 → 预报告
- 用例 U3：NCCT+CTA+CTP 参数图 → 直接量化 → 预报告
- 用例 U4：缺失/损坏文件 → QC 明确报错 → 前端提示清晰

---

## 8. 下一步进入实现模式建议

若确认按本清单推进，建议先切换到 `code` 模式做 P0：

1. 改上传前端校验（NCCT 必选）与后端路由入参
2. 增加 `case_manifest.json` 与基础 QC
3. 增加 `/api/agent/run|status|result` 三接口（同步版）
4. viewer 增加“证据卡 + 灰态占位 + 一键预报告”

