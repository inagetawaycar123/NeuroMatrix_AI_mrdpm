# 使用 Coze 落地卒中智能体：结论—架构—接口—工作流—提示词与知识—交互—合规—里程碑（Flask + Medgemma 1.5）

## 结论

在你现有卒中影像 Web 系统基础上，Coze 可以用于完成卒中智能体的对话入口、工作流编排、知识检索与报告段落生成，并可作为医生确认与审计留痕的交互层；但 Coze 不适合也不应直接承担影像文件的存储与处理、NIfTI 或 DICOM 解码、切片渲染、伪彩与叠加图生成、体积与阈值量化、跨模态配准、以及任何需要读写 `static/processed/<file_id>/...` 的产物管理。这些必须继续由 Flask 后端完成，并以“工具化 API”暴露给 Coze 调用。

在合规与工程可控的落地形态上，推荐采用“Coze 只拿结构化结论与证据链接，不拿原始影像”的数据最小化策略：Coze 侧只接收 `file_id`、模块结果 JSON、报告草稿 Markdown、以及可访问的证据图片 URL；原始影像与可反推 PHI 的元数据仅保留在你的内网或受控后端。若你必须在纯内网环境运行且无法让任何数据出网，则不建议使用云端 Coze 作为编排层，此时可把 Coze 限定为前台壳（会话式 UI 与模板化报告编辑），而将全部编排与模型调用留在后端。

你现有工程的可复用锚点包括上传与 viewer 入口 [`upload_files()`](app.py:2803) 与 [`viewer_page()`](app.py:2798)，伪彩链路 [`generate_all_pseudocolors_route()`](app.py:895)，病灶分析链路 [`analyze_stroke_case()`](stroke_analysis.py:374)，以及多模型灌注图推理框架 [`class MultiModelAISystem`](ai_inference.py:22)。新增“单独分析”与“汇总报告”应作为新增 API 与新产物目录落在后端，再由 Coze 负责调度与呈现。

## 架构

架构分为事实层、工具层、智能体层三部分。

事实层是 Flask 计算与文件系统层，职责是：维护病例 `file_id` 与产物目录；完成预处理与 QC；完成 CTP 量化与阈值依据记录；生成伪彩与叠加图证据；生成结构化 JSON 结果与 Markdown 报告段落；调用本地 Medgemma 1.5 生成“语言化结论与结构化摘要”；把所有结果落盘并可回写 Supabase。事实层的落盘与 Schema 应对齐你已沉淀的设计稿 [`plans/STROKE_AGENT_ARCHITECTURE_EXECUTABLE.md`](plans/STROKE_AGENT_ARCHITECTURE_EXECUTABLE.md)。

工具层是 Flask 对外 API 层，职责是：把事实层能力“工具化”，提供幂等任务启动、状态轮询、结果索引、证据 URL 获取、报告草稿与定稿保存等接口，并统一错误码与审计字段。工具层既服务你的 Web viewer，也服务 Coze；Coze 不直接读取文件系统。

智能体层是 Coze 侧，职责是：根据病例状态与可用模态自动分流到 NCCT-only、CTA/mCTA-only、CTP-only、综合汇总四条路径；在每条路径中先调用工具层获取事实与证据，再生成医生可直接使用的“结论+证据+不确定性/建议”段落；把 viewer 链接、叠加图与量化表格嵌入对话卡片；引导医生确认与修订，并最终调用后端保存为定稿报告。

本阶段统一使用本地部署 Medgemma 1.5 作为“可插拔模型”，它的职责限定为“将后端产出的证据摘要与规则量化结果转写为可读结论与可解析结构”；任何像素级分割、体积计算、阈值判断、单位校验、跨模态一致性检查均由后端规则/传统算法完成。未来替换自研模型时，上层 Coze 工作流与 API 协议保持不变，只替换后端的模型适配层实现。

## 接口

Coze 落地的关键是把后端整理成少而稳的“工具化 API”。下面给出可直接实现的接口路径、字段定义、错误码与幂等约定，命名风格与现有 [`app.py`](app.py:1) 的 API 保持一致。

### 1）病例与模态清单接口

路径示例为 `GET /api/case/manifest?file_id=...`。响应体必须包含 `file_id`、`patient_id`、`available_modalities`、`qc_level`、以及 viewer 入口链接，便于 Coze 自动分流。

```json
{
  "success": true,
  "file_id": "f_20260214_001",
  "patient_id": 123,
  "available_modalities": {
    "ncct": true,
    "cta_single": false,
    "mcta": true,
    "ctp_maps": false,
    "perfusion_ai": false
  },
  "qc": {
    "level": "warning",
    "warnings": [
      {"code": "QC_ORIENTATION_UNCERTAIN", "message": "影像方向信息不完整，侧别推断可能不稳定"}
    ]
  },
  "viewer": {
    "url": "/viewer?file_id=f_20260214_001",
    "report_url": "/report/123"
  },
  "artifacts_root": "static/processed/f_20260214_001/"
}
```

### 2）智能体任务启动与状态轮询接口

路径示例为 `POST /api/agent/run`、`GET /api/agent/status`、`GET /api/agent/result`。这是 Coze 编排的主调用面。

`POST /api/agent/run` 请求体示例，必须包含幂等键与审计字段，幂等键用于防止 Coze 重试导致重复计算。

```json
{
  "file_id": "f_20260214_001",
  "patient_id": 123,
  "idempotency_key": "7a1c0d8b-9d70-4c0b-9c6b-7b7c1d2d8e80",
  "path": "auto|ncct_only|cta_only|ctp_only|summary",
  "options": {
    "allow_generate_perfusion": true,
    "generate_pseudocolor": true,
    "generate_overlays": true,
    "timeout_seconds": 900
  },
  "audit": {
    "operator": "coze",
    "request_ip": "<server_side>",
    "user_agent": "coze",
    "trace_id": "coze-trace-001"
  }
}
```

成功响应必须返回 `job_id` 与轮询地址。

```json
{
  "success": true,
  "job_id": "job_20260214_093000_4f2a",
  "file_id": "f_20260214_001",
  "status": "queued",
  "poll": "/api/agent/status?file_id=f_20260214_001&job_id=job_20260214_093000_4f2a"
}
```

`GET /api/agent/status` 响应必须同时包含 stage 与模块状态，以便 Coze 呈现状态机。

```json
{
  "success": true,
  "job_id": "job_20260214_093000_4f2a",
  "file_id": "f_20260214_001",
  "stage": "ANALYSIS_CTP_DONE",
  "modules": {
    "ncct": "done",
    "cta": "done",
    "ctp": "done",
    "fusion": "running",
    "report": "pending"
  },
  "progress": {"percent": 80},
  "last_error": null
}
```

`GET /api/agent/result` 返回索引，不直接返回大文件；Coze 再按需拉取 JSON 或展示链接。

```json
{
  "success": true,
  "job_id": "job_20260214_093000_4f2a",
  "file_id": "f_20260214_001",
  "results": {
    "ncct": {"path": "static/processed/f_20260214_001/module_results/ncct_v1.json"},
    "cta": {"path": "static/processed/f_20260214_001/module_results/cta_v1.json"},
    "ctp": {"path": "static/processed/f_20260214_001/module_results/ctp_v1.json"},
    "fusion": {"path": "static/processed/f_20260214_001/module_results/fusion_v1.json"},
    "report": {
      "draft_md": {"path": "static/processed/f_20260214_001/report/report_draft_v1.md"},
      "final_md": {"path": "static/processed/f_20260214_001/report/report_final_v1.md"}
    }
  },
  "viewer": {"url": "/viewer?file_id=f_20260214_001"}
}
```

### 3）证据与可访问 URL 获取接口

Coze 不应直接访问文件系统；后端提供 `GET /api/artifacts/list?file_id=...&type=visuals` 或者为每个模块结果 JSON 中的 `evidence[].url` 直接给可访问 URL。建议沿用你现有图像读取路由风格，例如 [`get_image()`](app.py:2933) 与 [`get_stroke_analysis_image()`](app.py:1005)。

### 4）报告草稿与定稿保存接口

Coze 的“报告生成”只生成草稿文本，最终由医生确认；保存定稿必须回写后端与 Supabase，且保留审计。

路径示例为 `POST /api/report/save`，请求体必须包含 `file_id`、`patient_id`、`report_md`、`source`、`audit`。

```json
{
  "file_id": "f_20260214_001",
  "patient_id": 123,
  "report_version": "v1",
  "status": "draft|final",
  "report_md": "## 影像诊断报告\n...",
  "source": "coze",
  "audit": {"operator": "doctor_a", "trace_id": "coze-trace-002"}
}
```

### 5）错误码、重试与幂等约定

错误码必须可解释并可驱动 Coze 的降级话术，建议采用分层前缀：`ERR_INPUT_*`、`ERR_QC_*`、`ERR_MODEL_*`、`ERR_TIMEOUT_*`、`ERR_IO_*`。当错误可重试时返回 `retryable=true`，并在 `status` 与 `last_error` 中给出建议等待或改用降级路径。幂等键以 `idempotency_key + file_id + path` 为主键，重复调用必须返回同一 `job_id` 或直接复用既有结果。

## 工作流

Coze 侧必须拆成四条可执行路径，并用同一套“缺失识别与降级”逻辑自动分流。分流依据来自后端 `case_manifest` 与各模块 `status`。

### 1）NCCT-only 路径

该路径触发条件是 `available_modalities.ncct=true` 且 `mcta=false` 且 `cta_single=false` 且 `ctp_maps=false`。Coze 在会话中先调用 `GET /api/case/manifest` 确认模态与 QC，再调用 `POST /api/agent/run` 以 `path=ncct_only` 启动任务。后端需要产出 `ncct_v1.json` 与最少一张关键切片证据图，并生成 `report_draft_v1.md` 的 NCCT 段落。Coze 仅负责将后端 JSON 的 findings 组织成医生可读的段落，并明确输出边界为“初筛提示”。

### 2）CTA 或 mCTA-only 路径

该路径并非真正无 NCCT，而是“血管评估优先”的对话路径，触发条件是 `ncct=true` 且 `cta_single=true` 或 `mcta=true`，但 CTP 不可用或用户选择不做灌注量化。Coze 在开场明确当前只做血管闭塞与侧支提示，不输出核心/半暗带量化。后端产出 `cta_v1.json`、关键证据图与对应段落；Coze 将其与 NCCT 段落一起拼接成“NCCT+CTA 血管评估报告草稿”，并引导医生选择是否进一步补充 CTP。

### 3）CTP-only 路径

该路径同样默认包含 NCCT，但对话目标是优先输出灌注量化；触发条件是 `ncct=true` 且 `ctp_maps=true`，或者 `mcta=true` 且允许后端生成灌注图。后端必须保证体积与阈值依据由规则算法生成，并把 Medgemma 限定为“语言化解释与不确定性提示”。Coze 将核心/半暗带/不匹配与 DEFUSE3 hint 以表格卡片形式展示，并在文本段落中引用证据图链接。

### 4）综合汇总路径

该路径触发条件是 `ncct=true` 且至少一项 `cta_single|mcta|ctp_maps|perfusion_ai` 为真。Coze 启动 `path=summary`，后端执行融合一致性校验与冲突卡生成，并给出模块化段落的汇总报告草稿。Coze 的任务是把冲突点显式呈现为“需复核事项”，并将报告送医生编辑确认。

缺失模态与质量差数据的降级必须通过 Coze 统一话术呈现，但话术的事实依据只能来自后端 `qc` 与 `status.error`，不得凭空推断；当 `qc.level=fail` 时，Coze 必须强制进入“仅提示质量与缺失，不输出诊断性结论”的模式。

## 提示词与知识

Coze 的知识与提示词工程应围绕“仅依据事实与证据，输出可解析结构，并显式不确定性”三条约束。

知识库建设方面，应将你的四份文档作为 Coze 知识库核心来源：[`docs/CORE_FUNCTIONS.md`](docs/CORE_FUNCTIONS.md)、[`plans/STROKE_AGENT_PROPOSAL.md`](plans/STROKE_AGENT_PROPOSAL.md)、[`plans/STROKE_AGENT_RND_REQUIREMENTS.md`](plans/STROKE_AGENT_RND_REQUIREMENTS.md)、[`plans/STROKE_AGENT_ARCHITECTURE_EXECUTABLE.md`](plans/STROKE_AGENT_ARCHITECTURE_EXECUTABLE.md)。索引策略应按“工作流/模块/API/字段/错误码/降级话术”切分，便于 Coze 在生成对话与报告时引用一致口径。

提示词策略需要在 Coze 侧和后端 Medgemma 侧分别控制。Coze 侧只做“基于后端结构化 JSON 与证据列表的报告组织”，不做影像读片推理；后端 Medgemma 侧可用于将证据摘要生成严格 JSON 或严格段落文本。为避免医疗幻觉，Coze 侧系统提示必须硬性声明：只能使用工具返回字段，不允许生成工具未返回的影像征象；凡缺失证据或 QC 警告时，结论必须输出为不确定并给出复核建议。

为了让输出可解析并可回填数据库，建议 Coze 侧在报告生成时先产出一个严格 JSON 的“报告结构体”，再渲染为 Markdown；该 JSON 至少包含 `sections[]`、每段 `evidence_urls[]`、每段 `uncertainty_level`。若 Coze 平台不支持严格 JSON，则改为让后端 Medgemma 生成严格 JSON，Coze 仅做渲染与交互。

下面给出 Coze 用的报告段落生成约束示例，输入仅包含后端返回的 findings 与 evidence：

```text
你是一名卒中影像报告助手。你只能依据工具返回的结构化字段生成报告。对于任何工具未提供的信息，你必须写明不确定或未提供。你不得给出具体治疗决策，只能给出复核建议与进一步检查建议。输出必须为Markdown，必须包含 结论 证据 不确定性 三个子句。
```

## 交互

对话与界面交互必须与现有 Web viewer 形成闭环。推荐的状态机是“上传完成→可用模态识别→任务运行→证据卡片展示→草稿报告生成→医生编辑确认→定稿保存”。Coze 会话中应展示三类卡片：病例卡片（展示 `file_id`、可用模态、QC 级别、viewer 链接）；模块卡片（NCCT/CTA/CTP 各自的关键结论、证据图缩略与置信度或质量标记）；冲突与需复核卡片（来自融合模块的冲突列表）。

关键文案必须由后端状态驱动，例如当 `ctp` 模块为 `skipped` 时，Coze 自动展示“未提供 CTP 参数图且当前数据无法生成可靠灌注量化，本部分不输出”的固定句式，并提供按钮引导用户补充上传或选择 mCTA 生成。

为了与现有 viewer 对接，Coze 卡片中应直接提供 `viewer.url`，并在证据卡片中提供可点击的 `evidence.url`，这些 URL 应由后端生成并通过现有静态路由访问，例如复用 [`get_image()`](app.py:2933) 与 [`get_stroke_analysis_image()`](app.py:1005)。医生在 viewer 中检查叠加图后回到 Coze 会话点击“确认/修订”，Coze 再把修订后的 Markdown 调用 `POST /api/report/save` 保存为 final。

## 合规

PHI 处理策略必须围绕数据最小化与可追溯。Coze 侧不应接触原始影像文件、DICOM header、姓名证件号等；Coze 只使用 `file_id`、脱敏后的患者标签字段（例如年龄段、性别、NIHSS 等必要字段）与证据图片 URL。若必须展示患者姓名，则要求 Coze 部署在内网或通过反向代理与权限控制保证不出网。

日志脱敏要求是：后端的 `audit` 字段记录操作人、时间戳、trace_id、工具调用链路与结果版本号，但不得记录原始影像路径的外网可访问地址；Coze 的会话日志中不得回显任何可识别身份信息。权限与审计建议在后端统一：所有 `/api/agent/*` 与 `/api/report/*` 调用必须携带 `trace_id`，并在后端落盘 `audit/job_v1.json`，便于事后追溯。

模型调用隔离要求是：Medgemma 1.5 的调用仅发生在后端内部，Coze 不直接调用模型服务；Coze 只调用后端工具 API。若后端模型服务需要 GPU 与较高权限，应与 Web 服务做进程隔离并设置超时与并发限制，避免影响现有功能。

## 里程碑

路线图按 P0/P1/P2 给出，目标是每阶段都能在 Web 端看到明确新增能力，并且可回滚。

P0 的最小可用版本必须实现：Coze 能根据 `file_id` 拉取病例模态与 QC；能启动并轮询 `ncct_only` 路径；能拿到 `ncct_v1.json` 与证据图 URL；能生成包含“结论+证据+不确定性”的 NCCT 报告草稿；医生可点击 viewer 链接复核并在 Coze 内确认保存草稿。P0 的验收指标是：结构化 JSON 可解析率为 100%，任何失败都有明确 `ERR_*` 错误码与可执行建议；Coze 不产生工具未返回的影像结论。

P1 需要实现：CTA/mCTA 路径与 CTP 路径可用；后端可生成伪彩与叠加图证据；Coze 在会话中展示量化表格与证据图卡片；综合汇总路径能输出冲突与需复核事项；报告可拆段编辑并保存为 final 回写后端。P1 的验收指标是：四条路径均能跑通；缺失模态时话术与报告段落严格一致且不越界；重复触发同一任务不会重复生成产物，幂等键生效。

P2 需要实现：引入异步队列与并发控制；增加 A/B 版本记录与回滚；完善合规审计与脱敏；将你的文档与错误码、字段规范纳入 Coze 知识库并形成可追溯的提示词版本管理；增加离线回放评测入口用于 Medgemma 与自研模型对比。P2 的验收指标是：高并发下服务不阻塞现有 viewer；模型输出不可解析时可自愈降级；审计链路可追溯到每次生成的 `job_id` 与 `schema_version`。

为保证回滚能力，每个阶段的后端改动必须是新增 API 与新增产物目录，不修改现有 viewer 的关键路径；若 Coze 侧出现异常，用户仍可用原有 Web 流程完成上传、查看、伪彩与病灶分析。

## 示例结构化 JSON 与示例报告片段

### 示例 1：NCCT-only 的结构化输出 JSON（模块结果）

```json
{
  "schema_version": "1.0.0",
  "module": "ncct",
  "file_id": "f_20260214_010",
  "patient_id": 123,
  "job_id": "job_20260214_100000_abcd",
  "idempotency_key": "0d0c2c46-6ad6-4f0c-9a1a-3d76e0f3a7c1",
  "timestamp_utc": "2026-02-14T10:00:05Z",
  "inputs": {
    "modalities": ["ncct"],
    "files": [{"role": "ncct", "path": "static/processed/f_20260214_010/inputs/ncct.nii.gz", "sha256": "<sha256>"}]
  },
  "qc": {
    "level": "ok",
    "warnings": [],
    "fatal": []
  },
  "evidence": [
    {
      "type": "image",
      "title": "NCCT关键切片",
      "path": "static/processed/f_20260214_010/visuals/key_slices/ncct_key_slice_012.png",
      "slice_index": 12,
      "notes": "用于出血排除与早期缺血征象复核"
    }
  ],
  "findings": [
    {
      "id": "F001",
      "category": "hemorrhage",
      "evidence_refs": ["E001"],
      "conclusion": "indeterminate",
      "confidence": {"value": 0.35, "calibration": "hybrid"},
      "uncertainty": {"level": "high", "reasons": [{"code": "UNC_SIGNAL_NOISE", "message": "伪影或噪声导致密度判断不稳定"}]},
      "recommendations": [{"type": "manual_review", "message": "建议人工复核关键切片，必要时补充薄层重建"}],
      "structured": {"hemorrhage_ruleout": "indeterminate"}
    },
    {
      "id": "F002",
      "category": "ischemia",
      "evidence_refs": ["E001"],
      "conclusion": "indeterminate",
      "confidence": {"value": 0.40, "calibration": "hybrid"},
      "uncertainty": {"level": "high", "reasons": [{"code": "UNC_EARLY_SIGN_LIMITED", "message": "仅NCCT条件下早期缺血征象敏感性有限"}]},
      "recommendations": [{"type": "acquire_cta", "message": "如临床怀疑缺血性卒中，建议结合CTA或CTP进一步评估"}],
      "structured": {"early_ischemic_signs": "indeterminate"}
    }
  ],
  "numerics": {"units": "", "values": []},
  "rules_and_thresholds": [],
  "model": {
    "engine": "medgemma-1.5",
    "adapter_version": "1.0.0",
    "prompt_version": "ncct.v1",
    "raw_output_path": "static/processed/f_20260214_010/audit/medgemma_raw_ncct.json",
    "parse_status": "ok"
  },
  "status": {"state": "done", "error": null},
  "audit": {"operator": "coze", "trace_id": "coze-trace-010"}
}
```

对应的 NCCT-only 示例报告片段如下。

```md
## NCCT影像表现
结论: 未见明确颅内出血证据或结论不确定; 早期缺血征象提示不确定
证据: NCCT关键切片 slice 12, 证据图 static/processed/f_20260214_010/visuals/key_slices/ncct_key_slice_012.png
不确定性与建议: 受噪声或伪影影响且仅NCCT条件下敏感性有限, 建议人工复核关键切片并结合CTA或CTP进一步评估
```

### 示例 2：NCCT+CTA+CTP 的结构化输出 JSON（汇总结果）

```json
{
  "schema_version": "1.0.0",
  "module": "fusion",
  "file_id": "f_20260214_020",
  "patient_id": 456,
  "job_id": "job_20260214_103000_efgh",
  "idempotency_key": "2e6a7c2d-5c20-4c13-a3e0-6f1c2b9a4a2c",
  "timestamp_utc": "2026-02-14T10:30:40Z",
  "inputs": {
    "modalities": ["ncct", "cta_single", "ctp_maps"],
    "files": [
      {"role": "ncct", "path": "static/processed/f_20260214_020/inputs/ncct.nii.gz", "sha256": "<sha256>"},
      {"role": "cta_single", "path": "static/processed/f_20260214_020/inputs/cta_single.nii.gz", "sha256": "<sha256>"},
      {"role": "tmax", "path": "static/processed/f_20260214_020/inputs/ctp_maps/tmax.nii.gz", "sha256": "<sha256>"}
    ]
  },
  "qc": {"level": "ok", "warnings": [], "fatal": []},
  "evidence": [
    {"type": "image", "title": "CTA关键证据", "path": "static/processed/f_20260214_020/visuals/key_slices/cta_key_slice_034.png", "slice_index": 34, "notes": "疑似闭塞证据"},
    {"type": "image", "title": "Tmax伪彩", "path": "static/processed/f_20260214_020/visuals/pseudocolor/slice_010_tmax_pseudocolor.png", "slice_index": 10, "notes": "灌注延迟证据"},
    {"type": "image", "title": "病灶叠加综合", "path": "static/processed/f_20260214_020/visuals/overlays/slice_010_combined_overlay.png", "slice_index": 10, "notes": "核心与半暗带叠加"}
  ],
  "findings": [
    {
      "id": "F101",
      "category": "lvo",
      "evidence_refs": ["E001"],
      "conclusion": "positive",
      "confidence": {"value": 0.65, "calibration": "hybrid"},
      "uncertainty": {"level": "medium", "reasons": [{"code": "UNC_SINGLE_PHASE", "message": "单期CTA侧支与时相信息有限"}]},
      "recommendations": [{"type": "manual_review", "message": "建议结合临床与必要时补充mCTA或DSA复核闭塞段"}],
      "structured": {"lvo_suspect": true, "occlusion_site": "M1"}
    },
    {
      "id": "F201",
      "category": "perfusion",
      "evidence_refs": ["E002", "E003"],
      "conclusion": "positive",
      "confidence": {"value": 0.75, "calibration": "rule"},
      "uncertainty": {"level": "low", "reasons": []},
      "recommendations": [{"type": "manual_review", "message": "请复核叠加图与阈值依据, 并结合临床时间窗"}],
      "structured": {
        "core_volume_ml": 18.2,
        "penumbra_volume_ml": 52.6,
        "mismatch_ratio": 2.89,
        "defuse3_eligibility_hint": "eligible_hint",
        "threshold_basis": "penumbra: tmax>6s; core: rcbf<30%"
      }
    }
  ],
  "numerics": {
    "units": "ml",
    "values": [
      {"name": "core_volume_ml", "value": 18.2, "unit": "ml", "basis": "rcbf<30%"},
      {"name": "penumbra_volume_ml", "value": 52.6, "unit": "ml", "basis": "tmax>6s"},
      {"name": "mismatch_ratio", "value": 2.89, "unit": "ratio", "basis": "penumbra/core"}
    ]
  },
  "rules_and_thresholds": [{"name": "defuse3", "details": "mismatch_ratio>=1.8 and mismatch_volume>=15ml"}],
  "model": {"engine": "medgemma-1.5", "adapter_version": "1.0.0", "prompt_version": "fusion.v1", "raw_output_path": "static/processed/f_20260214_020/audit/medgemma_raw_fusion.json", "parse_status": "ok"},
  "status": {"state": "done", "error": null},
  "audit": {"operator": "coze", "trace_id": "coze-trace-020"}
}
```

对应的综合示例报告片段如下。

```md
## 血管评估
结论: 提示大血管闭塞可能性较高, 闭塞段提示M1
证据: CTA关键证据 slice 34, 证据图 static/processed/f_20260214_020/visuals/key_slices/cta_key_slice_034.png
不确定性与建议: 单期CTA时相与侧支信息有限, 建议人工复核并必要时补充mCTA或DSA

## 灌注与量化
结论: 核心梗死体积约18.2ml, 半暗带体积约52.6ml, 不匹配比约2.89, DEFUSE3提示满足入选条件
证据: Tmax伪彩 slice 10 与病灶叠加综合 slice 10, 证据图 static/processed/f_20260214_020/visuals/overlays/slice_010_combined_overlay.png
不确定性与建议: 量化结论基于阈值 rcbf<30% 与 tmax>6s, 请结合临床时间窗与NIHSS, 对关键切片进行人工复核
```

## 需要你确认的关键不确定项

你是否计划让 Coze 部署在内网并可直接访问你的 Web 系统域名，还是必须使用云端 Coze 且严格禁止任何影像或患者信息出网；你希望 Coze 在会话中展示的证据图片是以可访问 URL 形式呈现还是以卡片内嵌的缩略图形式呈现；你当前 Medgemma 1.5 的本地部署形态是 HTTP 服务还是 Python 进程内调用，这将决定后端工具化 API 中 `timeout`、`retry` 与并发控制的默认配置。

