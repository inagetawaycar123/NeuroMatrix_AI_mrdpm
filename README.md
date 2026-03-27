# NeuroMatrix AI — 卒中先锋智能影像诊断平台

## 项目简介

**NeuroMatrix AI** 是一个面向急性缺血性脑卒中的 AI 辅助影像诊断与治疗决策平台。系统通过深度学习模型自动生成 CTP 灌注参数图（CBF/CBV/Tmax），结合大语言模型（百川 M3 / MedGemma）进行影像分析与报告生成，并通过多层校验智能体架构确保结论的可靠性与可追溯性。

## 仓库与体验地址

- **代码仓库地址：** `https://github.com/inagetawaycar123/NeuroMatrix_AI_mrdpm.git`
- **Demo 公网体验地址：** `https://nonmodally-tinkliest-bennie.ngrok-free.dev`
- **项目演示视频（B站）：** 【NeuroMatrix 卒中智能体演示视频-哔哩哔哩】https://b23.tv/J9K5SUK  # 新增B站视频链接

> 说明：若 Demo 公网地址因 ngrok 会话更新而失效，请以最新发布信息或本地部署方式为准。

### 核心功能

| 功能模块 | 说明 |
|---------|------|
| **NCCT + mCTA 上传与解析** | 支持 NIfTI 格式的 NCCT、多相 CTA 影像上传，自动识别模态 |
| **CTP 灌注图生成** | 基于 MRDPM / Palette 扩散模型，从 mCTA 序列生成 CBF、CBV、Tmax 灌注参数图 |
| **脑卒中自动量化分析** | 自动计算核心梗死体积、半暗带体积、不匹配比值（Mismatch Ratio）、受累侧别等关键指标 |
| **AI 影像报告生成** | 调用百川 M3 大语言模型，结合患者数据和量化指标，生成规范的影像学评估与治疗建议报告 |
| **问题驱动结论** | 用户可输入临床问题（如"评估可挽救脑组织"），系统结合数据和 LLM 分析给出针对性回答 |
| **多层校验智能体** | ICV（内部一致性校验）→ EKV（外部知识验证）→ Consensus（共识裁决）三级校验链 |
| **证据追溯** | 每项结论均可追溯到原始数据和指南引用，支持完整的证据链审计 |
| **AI 临床问答** | 基于百川 M3 的流式对话，支持结合患者上下文的实时临床咨询 |

### 技术栈

| 层级 | 技术 |
|------|------|
| **后端框架** | Python 3.14 + Flask |
| **前端框架** | React 18 + TypeScript + Vite |
| **深度学习** | PyTorch（MRDPM 扩散模型、Palette 灌注图生成） |
| **大语言模型** | 百川 M3（报告生成 + 临床问答 + 问题驱动分析）、MedGemma（医学影像理解） |
| **数据库** | Supabase（PostgreSQL，患者信息 + 影像元数据存储） |
| **包管理** | uv（Python）、npm（前端） |
| **构建工具** | Vite（前端打包，输出到 `static/dist/`） |

### 智能体架构

系统采用 **Agent Loop V2** 架构，由多个专业智能体协同完成从影像上传到报告生成的全流程：

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent Loop Controller                     │
│  (loop_controller.py — 循环调度、超时控制、重试策略)           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │ Triage        │    │ Clinical     │    │ Verification │   │
│  │ Planner Agent │───▶│ Tool Agent   │───▶│ Agent        │   │
│  └──────────────┘    └──────────────┘    └──────────────┘   │
│        │                    │                    │            │
│   detect_modalities    generate_ctp_maps    ICV 校验         │
│   load_patient_context run_stroke_analysis  EKV 验证         │
│                        generate_report      Consensus 裁决   │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│  Planner (planner.py)     — 规则+LLM混合规划                 │
│  Context Manager          — 上下文状态管理                    │
│  Tool Registry            — 工具注册与契约校验                │
│  Reporter (reporter.py)   — 结果汇总与证据链组装              │
│  Summary Assembler        — 问题驱动结论 + 证据追溯生成       │
└─────────────────────────────────────────────────────────────┘
```

**工具链执行顺序：**
1. `detect_modalities` — 识别上传影像的模态类型
2. `load_patient_context` — 加载患者基本信息和影像元数据
3. `generate_ctp_maps` — 基于 mCTA 生成 CTP 灌注参数图（CBF/CBV/Tmax）
4. `run_stroke_analysis` — 执行脑卒中自动量化分析
5. `icv` — 内部一致性校验（Internal Consistency Verification）
6. `ekv` — 外部知识验证（External Knowledge Verification）
7. `consensus_lite` — 共识裁决（综合 ICV + EKV 结果）
8. `generate_medgemma_report` — 生成最终报告 + 问题驱动结论

### 示例数据

> 示例 NCCT + mCTA 影像数据（NIfTI 格式）：
>
> **百度网盘：** [example_NCCT_mCTA](https://pan.baidu.com/s/1n4ufFqn7TsQUrGORSX1CAg)
> **提取码：** `98tu`

---

## 开发指南

## 一、环境变量配置（`.env`）

请在项目根目录（与 `run.py` 同级）创建 `.env` 文件。

可直接复制模板：

```bash
cp .env.example .env
```

建议配置项如下：

```env
# Flask 后端
FLASK_ENV=development
FLASK_DEBUG=1

# 前端开发时可用（可选）
VITE_API_URL=http://localhost:5011

# 百川 API（若功能依赖该服务）
BAICHUAN_API_URL=https://api.baichuan-ai.com/v1/chat/completions
BAICHUAN_API_KEY=请替换为你自己的真实Key
BAICHUAN_MODEL=Baichuan-M3
```

注意事项：

- 不要把真实 `API_KEY` 提交到 Git。
- 如果历史中出现过泄露的 Key，请立刻去服务端轮换（重置）密钥。

## 二、使用 `uv` 同步 Python 依赖

本项目使用 `pyproject.toml` + `uv.lock` 管理 Python 依赖。

在项目根目录执行：

```bash
uv sync
```

常用命令：

```bash
# 直接在 uv 环境运行后端
uv run python run.py
```

Python 版本说明：

- 项目 `.python-version` 为 `3.14`。
- 如果本机 Python 版本不一致，请先切换/安装对应版本，再执行 `uv sync`。

## 三、启动后端

在项目根目录执行：

```bash
uv run python run.py
```

启动后访问：

- `http://127.0.0.1:5011`

## 四、构建前端（React + Vite）

前端源码位于 `frontend/`，构建产物输出到 `static/dist/`。

```bash
cd frontend
npm install
npm run build
```

构建结果：

- `static/dist/index.html`
- `static/dist/assets/*`

构建完成后可刷新：

- `http://127.0.0.1:5011/report/<patient_id>?file_id=<file_id>`

前端开发模式（可选）：

```bash
cd frontend
npm run dev
```

## 五、模型权重配置（重点）

本仓库默认不提交大模型权重文件，`.gitignore` 已忽略：

- `MedGemma_Model/*.safetensors`
- `*.safetensors`
- `**/weights/`

这意味着你拉取代码后，通常需要手动补齐模型文件，否则会出现报告生成慢、失败或模型加载报错。

### 1) MedGemma 权重（`safetensors`）

请将 MedGemma 的本地模型文件放到 `MedGemma_Model/` 目录。

**下载地址（百度网盘）：**

| 文件 | 链接 | 提取码 |
|------|------|--------|
| `model-00001-of-00002.safetensors` | [下载](https://pan.baidu.com/s/1G6Ru1CaU3OiqDt5W7OrOUQ) | `31k4` |
| `model-00002-of-00002.safetensors` | [下载](https://pan.baidu.com/s/1xtl-r96R0f_dvJSFLwUDmw) | `vqj8` |

> 将以上两个权重文件直接放入 `MedGemma_Model/` 文件夹即可。

目录中还应包含以下配置文件（已随代码提交）：

- `model.safetensors.index.json`
- `config.json`、`generation_config.json`
- `preprocessor_config.json`、`processor_config.json`
- `tokenizer.json`、`tokenizer_config.json`、`tokenizer.model`
- `special_tokens_map.json`


### 2) Palette 灌注模型权重

Palette 模型用于从 mCTA 生成 CBF/CBV/Tmax 灌注参数图。

**下载地址（百度网盘）：**

> [palette/weights](https://pan.baidu.com/s/1QzYK6Fx-wKtBSB-iVkhXBg) — 提取码：`ynua`

将下载的 `weights` 文件夹直接放入 `palette/` 目录，最终结构：

- `palette/weights/cbf/`
- `palette/weights/cbv/`
- `palette/weights/tmax/`

### 3) MRDPM 权重（务必配置）

MRDPM 模型包含 BRAN 权重文件。

**下载地址（百度网盘）：**

> [mrdpm/weights](https://pan.baidu.com/s/1hLgUh_lVA6RDWm4SaMZedg) — 提取码：`ixqm`

将下载的 `weights` 文件夹直接放入 `mrdpm/` 目录，最终结构：

- `mrdpm/weights/cbf/`
- `mrdpm/weights/cbv/`
- `mrdpm/weights/tmax/`

调用示例（测试脚本）：

```bash
cd mrdpm
python test_predictor.py \
  --config <你的配置文件.json> \
  --model <你的权重文件.pth> \
  --output ./test_output
```

若权重路径错误，常见报错是 `模型文件不存在` 或加载 checkpoint 失败。

### 4) 推荐配置步骤（从零开始）

```bash
# 1) 拉代码后先同步 Python 依赖
uv sync

# 2) 准备 MedGemma 权重到 MedGemma_Model/
#    （手动拷贝或用你自己的下载方式）

# 3) 准备灌注模型权重到 palette/weights/*

# 4) 准备 MRDPM 权重（如需运行 mrdpm 训练/测试）

# 5) 构建前端
cd frontend && npm install && npm run build && cd ..

# 6) 启动后端
uv run python run.py
```

### 5) 快速自检（启动前）

```bash
# 检查 MedGemma safetensors 是否在位
ls -lh MedGemma_Model/*.safetensors

# 检查灌注权重目录
ls -lh palette/weights/cbf
ls -lh palette/weights/cbv
ls -lh palette/weights/tmax

# 检查 MRDPM 权重目录（如有）
ls -lh mrdpm/weights/cbf
ls -lh mrdpm/weights/cbv
ls -lh mrdpm/weights/tmax
```

若 `ls` 提示 `No such file or directory`，说明权重尚未配置完成。

## 六、后续开发规范（重要）

后续页面功能请尽量在 React 前端框架内继续开发，不再修改模板页面逻辑。

推荐开发位置：

- `frontend/src/main.tsx`
- `frontend/src/components/StructuredReport.tsx`
- `frontend/src/components/*`
- `frontend/src/styles/*`

请尽量避免继续在以下目录新增业务 UI 逻辑：

- `backend/templates/**`

当前约定：

- `backend/templates` 仅作为页面壳与路由入口。
- 新功能、交互、展示逻辑优先在 `frontend/src` 实现。

### 目录结构约定补充

- 项目根目录只放启动与工程配置：`run.py`、`.env*`、`pyproject.toml`、锁文件等。
- 后端业务逻辑统一放在 `backend/*`。
- 异步/队列 Worker 入口统一放在 `backend/workers/*`。

`report_worker.py` 已归位到：

- `backend/workers/report_worker.py`

根目录 `report_worker.py` 保留为兼容转发（deprecated），后续版本将移除。

## 七、推荐最小启动流程

```bash
# 1) 同步 Python 依赖
uv sync

# 2) 构建前端
cd frontend && npm install && npm run build && cd ..

# 3) 启动后端
uv run python run.py
```
