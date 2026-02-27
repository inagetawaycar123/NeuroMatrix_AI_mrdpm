# 卒中智能体落地执行计划（5人新手团队，不破坏现有系统，严格对齐P0）

本文以我作为项目总负责人推动交付为目标，严格对齐既有方案与优先级约束：[`plans/STROKE_AGENT_PROPOSAL.md`](plans/STROKE_AGENT_PROPOSAL.md)、[`plans/STROKE_AGENT_RND_REQUIREMENTS.md`](plans/STROKE_AGENT_RND_REQUIREMENTS.md)、[`plans/STROKE_AGENT_FINAL_BLUEPRINT.md`](plans/STROKE_AGENT_FINAL_BLUEPRINT.md)、[`plans/STROKE_AGENT_ARCHITECTURE_EXECUTABLE.md`](plans/STROKE_AGENT_ARCHITECTURE_EXECUTABLE.md) 与现有能力说明：[`docs/CORE_FUNCTIONS.md`](docs/CORE_FUNCTIONS.md)。本阶段明确不使用 Dify，所有新增能力以“新增 API + 新增产物目录 + 最小改动页面脚本”的方式落地在现有 Flask 工程中（核心编排入口仍在 [`app.py`](app.py)）。

---

## 第一部分：MVP范围与不做清单（严格对齐 P0）

MVP只做 P0 的闭环交付，目标是让老师看到“上传后自动编排→生成结构化结果与预报告→viewer 动态展示证据卡→可保存”的完整链路跑通，并且在四种输入组合里至少保证三种可演示且不崩（NCCT-only、NCCT+mCTA、NCCT+CTA+CTP参数图），同时不破坏现有 mCTA 四件套流程。

MVP范围定义为四个必交付件。第一件是上传链路最小改造，前端上传页不再强制四个文件齐全，而是只强制 NCCT 必选，其余可选，并在上传成功响应里返回 `available_modalities` 与 `qc_summary`，对应改动点位于 [`processFiles()`](static/js/upload.js:72) 与后端上传入口 [`upload_files()`](app.py:2803)。第二件是新增 Orchestrator 三接口 `POST /api/agent/run`、`GET /api/agent/status`、`GET /api/agent/result`，并保证幂等（`file_id + idempotency_key`）与错误码可解释，这部分完全新增在 [`app.py`](app.py) 内部，避免改动现有 viewer 与 report 的 URL 入口。第三件是新增病例产物规范与 `case_manifest.json` 落盘，落盘根目录统一为 `static/processed/<file_id>/`，并在其下生成 `case_manifest.json`、`module_results/`、`report/`、`audit/` 四个必备目录，协议与字段对齐 [`plans/STROKE_AGENT_FINAL_BLUEPRINT.md`](plans/STROKE_AGENT_FINAL_BLUEPRINT.md) 的 `case_manifest` 与模块 envelope。第四件是 viewer 的 P0 融合展示，在现有 viewer 网格不动的前提下新增“证据卡区域”，从 `GET /api/agent/result` 拉取索引并展示 NCCT 与 CTP 的关键结论、证据图片链接、缺失模态提示文案，同时提供“一键生成预报告”按钮触发 `POST /api/agent/run`，对应改动点位于 [`templates/patient/upload/viewer/index.html`](templates/patient/upload/viewer/index.html) 与 [`static/js/viewer.js`](static/js/viewer.js)。

MVP明确不做清单如下。CTA/mCTA 单独分析的 Medgemma 结构化结论、侧支评分、LVO 部位提示属于 P1，不进入本轮 MVP；多模态融合一致性校验与冲突卡属于 P1，不进入 MVP；异步队列、并发控制、A/B 切换与回滚属于 P2，不进入 MVP；RAG patient_id 直读对话属于 P1+（因为牵涉脱敏与权限审计），本轮仅保留接口占位与数据读取 PoC，不进入 MVP 交付验收口径。Medgemma 1.5 的接入在 MVP 中以“可插拔适配层 + 返回可解析 JSON”为准，模型效果不作为验收指标，验收只看结构化输出可解析、证据可追溯、失败可解释。

---

## 第二部分：按周里程碑计划（4周，每周必须有可演示产物）

周期建议为 4 周，因为团队开发经验有限且需要大量联调与兜底；每周必须完成一个可在浏览器演示的闭环点，避免到最后一周才集成。

第1周目标是“跑通最小主干链路”，演示口径为 NCCT-only 的自动编排与 viewer 展示。产物要求是上传页已支持 NCCT-only 成功返回 `file_id` 并可进入 viewer，后台可通过 `POST /api/agent/run` 生成 `case_manifest.json` 与 `module_results/ncct_v1.json` 的占位结构，viewer 能轮询 `GET /api/agent/status` 显示 processing 与 completed 状态，并能在证据卡区域展示一条 NCCT 结论与一张关键切片证据图（即使这条结论暂时为 indeterminate 也可）。

第2周目标是“接入 CTP 路径与卒中量化证据自动触发”，演示口径为 NCCT+CTA+CTP 参数图输入后自动产出核心/半暗带/不匹配指标与叠加图并在 viewer 展示。产物要求是 `module_results/stroke_v1.json` 生成，叠加图可通过现有 [`get_stroke_analysis_image()`](app.py:1006) 访问，伪彩可通过现有 [`generate_all_pseudocolors_route()`](app.py:895) 触发并落盘，预报告 `report/report_draft_v1.md` 生成并可在 viewer 打开预览。

第3周目标是“打通 NCCT+mCTA 下的灌注生成与 CTP 分析闭环”，演示口径为上传现有 mCTA 四件套依旧可用且自动触发灌注生成与卒中量化。产物要求是复用 [`class MultiModelAISystem`](ai_inference.py:22) 的推理产物被纳入统一目录规范，`available_modalities` 能区分 `mcta` 与 `perfusion_generated`，并且编排器能够在无外部 CTP 参数图的情况下生成 `stroke_v1.json` 与 `ctp_v1.json` 的最小结构化结果，且失败时有明确 `ERR_PERFUSION_GENERATION` 或 `ERR_STROKE_ANALYSIS`。

第4周目标是“收敛质量与可交付”，演示口径为三种组合稳定跑通，所有失败有提示且不影响原有 viewer 浏览与手动卒中分析入口。产物要求是补齐最小测试计划与回归清单，完善审计落盘 `audit/job_v1.json` 与 `audit/errors.jsonl`，完善缺失模态文案与下一步建议，完成一份面向导师验收的演示脚本与数据包说明，并冻结版本准备打包发布。

---

## 第三部分：5人分工表（责任边界清晰，交付物与验收标准可测）

团队成员代号为 A/B/C/D/E，其中我担任 A（负责人）。表中“交付物路径或接口”必须指向仓库内真实文件或真实路由，验收标准必须是可测的“存在文件/可访问接口/可在页面看到”。

| 成员代号 | 角色定位 | 负责模块（边界到文件/接口/页面） | 本周任务 | 下周任务 | 交付物路径或接口 | 验收标准 |
| --- | --- | --- | --- | --- | --- | --- |
| A | 架构与集成负责人 | 统一协议与集成，维护 `case_manifest`、产物目录规范、错误码，主持联调与发布；主改 [`app.py`](app.py) 的新 API 与编排主入口 | 第1周内制定并冻结 `case_manifest.json` 与模块 envelope v1，落地 `/api/agent/run|status|result` 的最小可用版本（同步） | 第2周补齐 `report/report_draft_v1.md` 拼装器与 `audit/*` 落盘规范；第3周完成 mCTA 生成路径联调；第4周做收敛与发布 | 新增路由：[`/api/agent/run`](app.py:1)、[`/api/agent/status`](app.py:1)、[`/api/agent/result`](app.py:1)；文档：[`plans/STROKE_AGENT_FINAL_BLUEPRINT.md`](plans/STROKE_AGENT_FINAL_BLUEPRINT.md) 的字段落地对齐 | `POST /api/agent/run` 输入合法时返回 `job_id`，`GET /api/agent/status` 能从 running 到 done，`GET /api/agent/result` 返回索引且索引指向的文件存在 |
| B | 后端数据与落盘负责人 | `static/processed/<file_id>/` 目录创建、输入识别、QC、hash 与幂等复用；主要改动集中在 [`upload_files()`](app.py:2803) 及新增的 manifest 生成函数 | 第1周改造上传链路支持 NCCT-only，返回 `available_modalities` 与 `qc_summary`，落盘 `case_manifest.json` | 第2周将外部 CTP 参数图输入落盘到 `inputs/ctp_maps/` 并在 manifest 记录；第3周将 MRDPM 生成产物纳入 `perfusion/` 规范 | 上传入口：[`upload_files()`](app.py:2803)；落盘：`static/processed/<file_id>/case_manifest.json` | NCCT-only 上传成功可进入 viewer；manifest 包含 `available_modalities` 且 QC 至少包含 `level` 与 `warnings`；重复上传或重复 run 不会破坏已有产物 |
| C | AI/算法管线负责人 | 卒中量化与可视化证据自动触发，复用 [`analyze_stroke_case()`](stroke_analysis.py:374) 与伪彩链路；必要时补齐外部 CTP 参数图到切片/掩膜的转换桥接 | 第1周输出 stroke 模块的结果 JSON 结构草案并与 A 冻结字段；完成最小调用链的函数入口占位 | 第2周实现外部 CTP 参数图的量化触发与叠加图落盘；第3周联调 `class MultiModelAISystem` 生成灌注→量化闭环 | 复用入口：[`analyze_stroke()`](app.py:955) 或被编排器调用的封装函数；结果：`static/processed/<file_id>/module_results/stroke_v1.json` | 在 NCCT+CTA+CTP 参数图输入用例中，自动生成 `stroke_v1.json` 且包含 `core_volume_ml/penumbra_volume_ml/mismatch_ratio` 三字段，并且叠加图至少一张可通过 [`get_stroke_analysis_image()`](app.py:1006) 访问 |
| D | 前端viewer与报告展示负责人 | 改动 [`templates/patient/upload/viewer/index.html`](templates/patient/upload/viewer/index.html) 与 [`static/js/viewer.js`](static/js/viewer.js)，新增证据卡与状态条，缺失模态文案与下一步建议；增加一键触发编排按钮 | 第1周在 viewer 增加状态条与 NCCT 证据卡占位，从 `/api/agent/status` 轮询并展示状态 | 第2周展示 CTP 量化卡与证据图链接，支持打开 `report_draft_v1.md` 预览；第3周完成 mCTA 路径下的动态展示兼容 | 页面：[`templates/patient/upload/viewer/index.html`](templates/patient/upload/viewer/index.html)；脚本：[`static/js/viewer.js`](static/js/viewer.js) | 任一组合进入 viewer 不报错；processing 时有可见提示；done 后卡片显示结构化字段与证据图链接；缺失模态显示固定解释文案 |
| E | 测试与交付负责人 | 测试数据整理、回归用例、导师验收脚本与录屏；同时负责合规最低要求（脱敏规则草案、审计字段检查）与文档同步 | 第1周建立四组合测试用例模板与最小数据包目录说明，写出“验收检查表 v1”并跟进每周 Demo | 第2周补齐外部 CTP 用例；第3周补齐 mCTA 生成用例；第4周收敛并输出最终验收脚本与风险说明 | 文档：`docs/` 或 `plans/` 下的验收检查表；Issue 模板与测试记录 | 每周 Demo 前能提供可复现步骤与预期结果；最终能覆盖三组合稳定演示并记录失败原因码与截图；审计文件 `audit/job_v1.json` 存在且包含 `trace_id` |

---

## 第四部分：关键任务依赖关系与接口约定（由谁维护）

项目成功的关键在于“统一协议先冻结，再并行开发”，否则新手团队会在联调阶段因字段不一致返工。核心依赖有三条：第一条是 `file_id` 与病例目录规范，所有模块都必须把产物写入同一个 `static/processed/<file_id>/` 目录；第二条是结构化 JSON 的 envelope 与必填字段，viewer 不读取 Python 内存对象，只读取 `GET /api/agent/result` 返回的索引再加载 JSON；第三条是缺失模态与降级策略，所有 `skipped|failed` 必须有 `ERR_*` 码与可展示文案来源。

我作为 A 负责制定与维护以下“冻结件”，并在第1周末形成一次不可随意变更的接口契约，后续任何变更必须走 PR 评审并更新文档：其一是 `case_manifest.json` 字段集合与路径规则，定义在 [`plans/STROKE_AGENT_FINAL_BLUEPRINT.md`](plans/STROKE_AGENT_FINAL_BLUEPRINT.md) 并以代码常量实现；其二是模块结果 envelope v1，字段包含 `schema_version/module/file_id/patient_id/job_id/qc/evidence/findings/model/status/audit`，并要求 `evidence.path` 必须可映射到现有图像读取路由 [`get_image()`](app.py:2934) 或 [`get_stroke_analysis_image()`](app.py:1006)；其三是编排器 API 的请求响应字段与错误码集合，具体对齐 [`POST /api/agent/run`](plans/STROKE_AGENT_FINAL_BLUEPRINT.md) 的字段定义。

成员 B 负责维护“输入识别与 QC 约定”，包含 `available_modalities` 的判定规则与 `qc_summary` 的生成，输出必须写入 manifest 并通过上传响应返回；成员 C 负责维护“stroke_v1.json 的数值字段口径”，特别是单位、阈值依据、体积计算的 basis 文本（与现有 [`calculate_volumes()`](stroke_analysis.py:336) 的输出对齐）；成员 D 负责维护“前端展示字段映射表”，即卡片展示哪些字段、缺失模态文案如何由模块状态生成，并将映射表写入一个固定的前端配置对象；成员 E 负责维护“端到端验收用例与可复现数据说明”，并把每次接口/字段变更同步到验收脚本中。

---

## 第五部分：质量保障与风险清单（每项给出缓解动作与负责人）

以下风险按对交付影响排序，缓解动作必须是可执行的工程动作而不是口号。

| 风险 | 具体表现 | 缓解动作（必须可执行） | 负责人 |
| --- | --- | --- | --- |
| 模型效果不稳定或输出不可解析 | Medgemma 输出 JSON 解析失败或字段缺失，导致 viewer 无法展示 | 在编排器中实现严格 parse+validate+最多2次 repair 重试，仍失败则写入 `status.error.code=ERR_MEDGEMMA_PARSE` 并输出降级 findings；同时落盘 `audit/medgemma_raw_*.json` 便于复盘 | A |
| 输入数据不一致与模态缺失 | 前端上传组合多样，后端识别错误或路径混乱 | 上传响应必须回传 `available_modalities`；manifest 作为唯一事实源；viewer 只信 manifest 与模块状态；缺失时必须展示固定文案与建议补采 | B 与 D |
| NIfTI 与可能的 DICOM 差异 | 医生可能上传非 NIfTI 或维度/方向异常 | P0 只支持 NIfTI 并在上传时严格校验扩展名与可读性；QC 发现异常则 `qc.level=fail` 并输出可操作提示；E 在验收脚本中明确“仅支持 NIfTI”边界 | B 与 E |
| 前后端联调失败 | viewer 找不到 JSON 或证据路径不可访问 | `GET /api/agent/result` 必须返回可访问 URL 或可映射路径，D 在前端封装统一 fetch 与错误提示；E 提供联调检查脚本，包含路径存在性检查 | A 与 D 与 E |
| 性能与超时 | 灌注生成或卒中分析耗时长导致请求卡死 | P0 先同步但加入模块级超时与清晰错误码；第4周前在 run 接口中加入 `timeout_seconds` 兜底并允许部分完成落盘；避免阻塞原有 viewer 浏览路由 | A 与 C |
| 合规与脱敏不足 | 日志或报告包含姓名等直接标识符 | P0 仅要求审计文件不写明文姓名；patient context 写入时提供脱敏版本；RAG 功能后置到 P1+；E 负责检查审计落盘内容是否含敏感字段 | E |
| 导师验收口径不清 | 老师关注点偏临床而团队实现偏工程 | 第1周末由 E 输出“导师验收脚本 v1”，每周 demo 前按脚本走一遍并记录风险点；我作为 A 每周同步一次验收口径并锁定本周只改可演示点 | A 与 E |

---

## 第六部分：团队工作机制（新手可照做的交付流程）

我会把工作机制设计成“每天有进展、每周有可演示产物、每次改动可回滚”。代码分支采用单主干与短分支策略，主分支为 main，所有人只能从 main 拉 `feature/<name>` 分支开发，禁止直接 push main。每个 PR 必须包含三个内容：变更说明、如何本地验证、对应的验收截图或接口返回示例，并且至少由两个人 review 才能合并，其中一位必须是我（A）或对应模块 owner（例如前端改动必须 D review）。

Issue 管理采用最小模板，我会在仓库中统一要求每个 Issue 写清楚“目标接口或文件、输入输出字段、验收标准、影响面”，并绑定到每周里程碑。每日节奏我会组织 10 分钟站会，只同步三件事：昨天完成了什么、今天要完成什么、遇到的阻塞是什么；每周固定一次 40 分钟里程碑评审，按第二部分每周演示口径验收，未达标的内容不允许合并到 main。

文档更新要求是“协议先于代码”。任何涉及接口字段、目录命名、错误码的变更，必须同步更新至少一份文档并在 PR 中附链接，优先更新本计划与 [`plans/STROKE_AGENT_FINAL_BLUEPRINT.md`](plans/STROKE_AGENT_FINAL_BLUEPRINT.md)。Demo 验收流程固定为：E 按测试脚本跑一遍并录屏，D 在 viewer 端验证 UI 展示与缺失文案，C 验证量化指标与叠加图路径存在性，B 验证 manifest 与落盘结构完整性，我最后做端到端走查并在 `audit/job_v1.json` 检查 trace_id 与错误码是否齐全。

为确保不破坏现有系统，每次合并到 main 前必须跑一次回归演示，即仍能走通原有 mCTA 四件套上传与 viewer 浏览，并能手动触发现有卒中分析入口 [`analyze_stroke()`](app.py:955) 与伪彩入口 [`generate_all_pseudocolors_route()`](app.py:895)。任何破坏现有功能的 PR 必须回滚并在 Issue 中记录原因。

