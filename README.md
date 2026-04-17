# NeuroMatrix AI — 卒中先锋智能影像诊断平台

## 项目简介
**NeuroMatrix AI** 是一个面向急性缺血性脑卒中的临床辅助系统。  
系统将多模态影像处理、智能体编排、证据核验与结构化报告整合为可追踪闭环：

- 输入：NCCT / CTA / CTP（按可用模态自动路由）
- 过程：Agent 分阶段执行（分析、校验、共识、总结）
- 输出：结构化报告 + 证据追溯 + 分段人工确认

本项目目标不是“替代医生诊断”，而是提供**可解释、可校验、可复核**的决策支持流程。

## 一、临床价值（面向评委）
### 1) 场景价值
- 基层/夜间场景常见“有影像、缺CTP、缺专科”问题。
- 系统可在模态不完整时自动选择可执行路径，优先给出可用结论与风险提示。

### 2) 安全价值
- 通过 `ICV + EKV + Consensus` 三段质控，避免“单模型直接给结论”。
- 对高风险或冲突结果触发人工复核节点，形成“发现风险 → 人工确认 → 最终归档”闭环。

### 3) 边界声明
- 系统结论仅用于辅助临床决策。
- 最终诊断与治疗方案必须由具备资质的临床医生确认。

### 4) 可读临床指标
- 核心梗死体积（core infarct volume）
- 半暗带体积（penumbra volume）
- 不匹配比值（mismatch ratio）

上述指标与治疗建议、风险提示在报告中一一对应，支持追溯。

## 二、核心能力概览
| 模块 | 说明 |
|---|---|
| 模态识别与路径决策 | 自动识别 `ncct/mcta/vcta/dcta/cbf/cbv/tmax`，按规则选择分析路径 |
| CTP 生成 | 基于 MRDPM / Palette 从 mCTA 生成 CBF/CBV/Tmax（当真实 CTP 缺失时） |
| 脑卒中量化 | 输出 core/penumbra/mismatch/侧别等关键量化结果 |
| 报告生成 | `generate_medgemma_report` 负责结构化报告草案生成与组装 |
| 质控链 | ICV（内部一致性）+ EKV（外部证据）+ Consensus（冲突裁决） |
| 证据追溯 | 结论映射证据项，支持 traceability 覆盖率检查 |
| 人机协同 | `/processing` 中分段确认，未确认完成不可进入 `/viewer` |
| 临床问答增强 | Baichuan 模型用于问答与交互增强能力（非主报告链路） |

## 三、智能体架构/底层价值
### 1) 架构组成
- Planner：任务规划与重规划
- Loop Controller：循环调度、超时控制、重试与终止
- Tool Registry：工具契约与调度
- Context Manager：上下文状态累积
- Reporter / Summary Assembler：结果汇总与最终包组装

关键实现参考：
- `backend/agent/loop_controller.py`
- `backend/app.py`

### 2) 运行机制（非黑盒）
- 启动后先规划，再按 tool sequence 顺序执行。
- 支持 replan（重规划）与边执行边修正。
- 默认约束：`max_steps`、`max_duration_ms`。

### 3) 可观测性
`GET /api/agent/runs/{run_id}` 返回运行态核心字段：
- `plan_frames`
- `replan_count`
- `termination_reason`
- `status / stage / error / result`

`GET /api/agent/runs/{run_id}/events` 提供事件流，并附带可读字段：
- `input_summary`
- `result_summary`
- `clinical_impact`
- `risk_level`
- `risk_items`
- `action_required / action_log`
- `narrative_hint`

### 4) 可靠性策略
- `icv / ekv / consensus_lite` 失败采用 soft-fail（非阻断）策略，流程可继续。
- 非可容错关键节点失败则终止 run 并记录 error contract。
- 可配置高风险暂停（`paused_review_required`），等待人工介入。

### 5) 人机门禁
- 主链路：`/upload -> /processing(分段确认) -> /viewer`
- `review_state.all_confirmed != true` 时，不允许进入 viewer 作为最终报告展示。

## 四、算法价值（输入→决策→指标→解释）
### 1) 模态路径决策规则
系统按固定优先级选择路径（见 `backend/app.py::_build_path_decision`）：

1. `ncct_mcta_ctp`
2. `ncct_mcta`
3. `ncct_single_phase_cta`
4. `ncct_only`

对应行为：
- `ncct_mcta`：触发 CTP 生成 + 卒中分析
- `ncct_mcta_ctp`：直接进入卒中分析（已有真实 CTP）
- 其他路径：按可用模态降级执行

### 2) 关键量化指标
- `core_infarct_volume`：核心梗死体积
- `penumbra_volume`：半暗带体积
- `mismatch_ratio`：不匹配比值

这些指标进入报告正文、问题驱动结论与风险段，形成“指标-结论-建议”链路。

### 3) 质控链价值
- ICV：检查内部逻辑一致性（是否自相矛盾）
- EKV：对照外部指南/知识证据进行核验
- Consensus：在冲突时给出裁决结论

### 4) 证据追溯价值
- 支持 evidence map 与 traceability 信息输出
- 可对结论进行反查，评估覆盖率与证据完整度

## 五、主流程与工具链
典型 Agent 工具链：
1. `detect_modalities`
2. `load_patient_context`
3. `generate_ctp_maps`（按路径触发）
4. `run_stroke_analysis`
5. `icv`
6. `ekv`
7. `consensus_lite`
8. `generate_medgemma_report`

## 六、已落地 API（工程评委重点）
### Run 与事件
- `POST /api/agent/runs`
- `GET /api/agent/runs/{run_id}`
- `GET /api/agent/runs/{run_id}/events`
- `GET /api/agent/runs/{run_id}/result`

### 计划预览
- `POST /api/agent/plans/preview`

### 报告分段审阅
- `GET /api/agent/runs/{run_id}/review`
- `POST /api/agent/runs/{run_id}/review`

`POST /review` 支持 action：
- `init_review`
- `rewrite_section`
- `save_section`
- `confirm_section`
- `finalize_review`

## 七、仓库与演示
- 代码仓库：`https://github.com/inagetawaycar123/NeuroMatrix_AI_mrdpm.git`
- Demo：`https://nonmodally-tinkliest-bennie.ngrok-free.dev`
- 演示视频（B站）：`https://b23.tv/J9K5SUK`

> 若 Demo 因 ngrok 会话变更失效，请以本地部署结果为准。

## 八、快速启动
### 1) 环境要求
- Python：建议与 `.python-version` 对齐
- Node.js + npm
- Windows / Linux 均可（命令示例以常见 shell 为准）

### 2) 配置 `.env`
```bash
cp .env.example .env
```

最小示例：
```env
FLASK_ENV=development
FLASK_DEBUG=1
VITE_API_URL=http://localhost:5011

BAICHUAN_API_URL=https://api.baichuan-ai.com/v1/chat/completions
BAICHUAN_API_KEY=your_key
BAICHUAN_MODEL=Baichuan-M3
```

### 3) 安装依赖并启动后端
```bash
uv sync
uv run python run.py
```

访问：
- `http://127.0.0.1:5011`

### 4) 构建前端
```bash
cd frontend
npm install
npm run build
cd ..
```

构建输出：
- `static/dist/index.html`
- `static/dist/assets/*`

## 九、模型权重配置（关键）
默认 `.gitignore` 不包含大权重文件，请手动补齐：

- `MedGemma_Model/*.safetensors`
- `palette/weights/*`
- `mrdpm/weights/*`

### MedGemma 权重（百度网盘）
| 文件 | 链接 | 提取码 |
|---|---|---|
| `model-00001-of-00002.safetensors` | https://pan.baidu.com/s/1G6Ru1CaU3OiqDt5W7OrOUQ | `31k4` |
| `model-00002-of-00002.safetensors` | https://pan.baidu.com/s/1xtl-r96R0f_dvJSFLwUDmw | `vqj8` |

### Palette 权重
- 下载：`https://pan.baidu.com/s/1QzYK6Fx-wKtBSB-iVkhXBg`
- 提取码：`ynua`
- 放置到：`palette/weights/cbf|cbv|tmax`

### MRDPM 权重
- 下载：`https://pan.baidu.com/s/1hLgUh_lVA6RDWm4SaMZedg`
- 提取码：`ixqm`
- 放置到：`mrdpm/weights/cbf|cbv|tmax`

## 十、工程复现与最小测试
### 1) 最小复现
```bash
uv sync
cd frontend && npm install && npm run build && cd ..
uv run python run.py
```

### 2) 最小测试（工程评委建议执行）
```bash
pytest tests/test_agent_loop_modules.py tests/test_icv.py tests/test_ekv.py
```

## 十一、验收清单（建议答辩前自检）
1. API 可用：可成功创建 run 并查询 `/runs` 与 `/events`
2. 事件可见：可看到节点推进与状态变化（含风险事件）
3. 审阅门禁：`/processing` 报告分段未全部确认时不能进入 `/viewer`
4. 结果可读：报告包含 core/penumbra/mismatch 及对应临床解释
5. 证据可追溯：关键结论可映射至证据项/traceability

## 十二、项目结构（简）
```text
backend/                 Flask 后端、Agent 编排、API
backend/agent/           planner/loop/reporter/context/tool registry
backend/workers/         异步任务 worker
frontend/                React + TypeScript 前端源码
static/dist/             前端构建产物
tests/                   核心模块测试（loop/icv/ekv）
```

## 十三、合规与使用声明
- 本系统用于教学、科研和工程验证场景。
- 不可替代执业医师诊疗行为。
- 生产落地前需结合本地法规、院内流程与伦理规范进行合规审查。

