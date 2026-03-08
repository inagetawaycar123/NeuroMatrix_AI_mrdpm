# 重构版项目说明-开发前请阅读


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

请将 MedGemma 的本地模型文件放到：

- `MedGemma_Model/`

至少应包含类似文件：

- `model-00001-of-00002.safetensors`
- `model-00002-of-00002.safetensors`
- `model.safetensors.index.json`
- `config.json`
- `generation_config.json`
- `preprocessor_config.json`
- `processor_config.json`
- `tokenizer.json`
- `tokenizer_config.json`
- `tokenizer.model`
- `special_tokens_map.json`


### 2) 灌注模型权重（`weights` 目录）

如果需要 CBF/CBV/TMAX 的相关推理，请确认以下目录存在对应权重文件（通常是 `.pth`）：

- `palette/weights/cbf/`
- `palette/weights/cbv/`
- `palette/weights/tmax/`

项目中 `mrdpm/weights/` 也被忽略，请按你的训练/部署流程补齐。

### 3) MRDPM 权重（务必配置）


目录：

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

## 七、推荐最小启动流程

```bash
# 1) 同步 Python 依赖
uv sync

# 2) 构建前端
cd frontend && npm install && npm run build && cd ..

# 3) 启动后端
uv run python run.py
```
