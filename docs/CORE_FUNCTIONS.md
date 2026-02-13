# 项目核心功能说明文档

## 1. 项目概览

本项目是一个面向卒中影像诊疗的端到端系统，包含：

- 医学影像上传与处理
- AI 灌注图生成（CBF/CBV/Tmax）与伪彩展示
- 脑卒中病灶分析（半暗带/核心梗死/不匹配）
- AI 影像诊断报告生成与保存
- 影像查看器与交互式报告界面

核心后端基于 Flask；AI 推理与病灶分析模块位于 Python 侧；前端包含传统模板页与独立 React/Next 前端。

---

## 2. 核心功能模块梳理

### 2.1 影像上传与预处理模块

**功能定位**

- 接收 mCTA（动脉/静脉/延迟期）与 NCCT NIfTI 文件
- 触发后端处理链路，生成 RGB 合成、掩码与 AI 灌注图

**关键实现文件**

- 前端上传页模板：[templates/patient/upload/index.html](../templates/patient/upload/index.html)
- 上传逻辑脚本：[static/js/upload.js](../static/js/upload.js)
- 后端上传路由及处理入口：[app.py](../app.py)

**输入/输出**

- 输入：4 个 NIfTI 文件 + 患者 ID + 模型选择
- 输出：文件 ID、切片数量、RGB 切片与 AI 产物索引

---

### 2.2 影像查看与交互模块

**功能定位**

- 切片浏览、多模态图像对照
- 对比度调节与伪彩切换
- 脑卒中分析结果可视化
- 进入 AI 报告与问诊入口

**关键实现文件**

- 查看器模板：[templates/patient/upload/viewer/index.html](../templates/patient/upload/viewer/index.html)
- 查看器逻辑脚本：[static/js/viewer.js](../static/js/viewer.js)
- 相关后端路由：[app.py](../app.py)

**核心数据流**

- 前端从 `viewerData` 获取切片索引 → 请求 `/get_slice`、`/get_image`、`/generate_all_pseudocolors` 等接口 → 渲染图像
- 分析结果存储在 `localStorage`，用于跨切片展示

---

### 2.3 AI 推理与灌注图生成模块

**功能定位**

- 负责 CBF/CBV/Tmax 三模型推理
- 支持多模型状态检查与推理输出
- 将 AI 输出保存为可视化与后续分析的基础数据

**关键实现文件**

- 多模型推理系统：[ai_inference.py](../ai_inference.py)
- 模型底座（MRDPM/Palette）：[mrdpm/](../mrdpm/) 与 [palette/](../palette/)
- 启动与接入路由：[app.py](../app.py)

**核心数据流**

- 输入：RGB 合成图 + 脑组织掩码
- 输出：CBF/CBV/Tmax NPY + PNG 切片

---

### 2.4 脑卒中病灶分析模块

**功能定位**

- 基于 Tmax 切片进行半暗带/核心梗死检测
- 生成病灶叠加图（半暗带/核心/综合）
- 计算体积与不匹配比

**关键实现文件**

- 病灶分析核心算法：[stroke_analysis.py](../stroke_analysis.py)
- 触发与访问路由：[app.py](../app.py)

**核心数据流**

- 输入：Tmax 切片 NPY + mask
- 输出：病灶可视化 PNG、体积与不匹配比指标

---

### 2.5 AI 报告生成与保存模块

**功能定位**

- 调用百川 M3 API 生成卒中影像诊断报告
- 支持 Markdown 与 JSON 报告格式
- 将报告保存至 Supabase

**关键实现文件**

- 报告生成与 API 路由：[app.py](../app.py)

**核心数据流**

- 输入：患者临床信息 + AI 分析指标
- 输出：结构化报告（Markdown/JSON）

---

### 2.6 数据存储与患者信息模块

**功能定位**

- 使用 Supabase 存储患者信息与报告
- 提供插入、查询、更新接口

**关键实现文件**

- Supabase 连接与操作逻辑：[app.py](../app.py)
- 辅助模块：[core/supabase_client.py](../core/supabase_client.py)

---

### 2.7 前端报告编辑器（React/Next）模块

**功能定位**

- 结构化报告编辑与展示
- TipTap 富文本编辑器
- 报告生成、保存与患者信息渲染

**关键实现文件**

- 结构化报告页面入口：[frontend/src/app/page.tsx](../frontend/src/app/page.tsx)
- 组件集合：[frontend/src/components/](../frontend/src/components/)
- API 代理层：[frontend/src/app/api/](../frontend/src/app/api/)

---

## 3. 模块间依赖关系与数据流向

```text
影像上传 (templates/static)
  ↓
Flask 接收与存储 (app.py)
  ↓
AI 推理 (ai_inference.py → mrdpm/palette)
  ↓
生成 CBF/CBV/Tmax 切片与可视化
  ↓
病灶分析 (stroke_analysis.py)
  ↓
产出体积/不匹配 + 可视化叠加图
  ↓
报告生成 (app.py → Baichuan API)
  ↓
报告保存 (Supabase)
  ↓
前端查看/编辑 (viewer.js + React 报告编辑器)
```

**关键依赖关系**

- [app.py](../app.py) 是主路由与服务编排中心
- [ai_inference.py](../ai_inference.py) 依赖 [mrdpm/](../mrdpm/) 和 [palette/](../palette/) 的模型实现
- [stroke_analysis.py](../stroke_analysis.py) 依赖 AI 生成的 Tmax 切片数据
- 前端查看器依赖后端图像 API 与分析结果缓存
- 报告生成依赖患者信息与分析指标（核心梗死/半暗带/不匹配）

---

## 4. 关键功能点分类整理

### 4.1 影像处理类

- 上传校验与文件组织
- RGB 合成与切片处理
- 对比度调节与伪彩生成

### 4.2 AI 推理类

- 三模型推理（CBF/CBV/Tmax）
- 多模型加载与状态管理
- 推理输出持久化

### 4.3 病灶分析类

- 半暗带/核心梗死阈值化
- 后处理与连通域筛选
- 体积计算与不匹配评估

### 4.4 报告生成类

- Prompt 驱动报告生成
- Markdown / JSON 双格式输出
- Supabase 报告存储

### 4.5 前端交互类

- 多切片联动查看
- 对比度调节
- 病灶结果可视化与 AI 报告展示

---

## 5. 核心业务流程说明

### 5.1 影像上传 → AI 推理 → 结果展示

1. 用户在上传页选择 mCTA + NCCT 文件并提交
2. 后端接收文件，生成 RGB 合成与掩码
3. AI 推理生成 CBF/CBV/Tmax 切片
4. 前端查看器加载切片并展示

### 5.2 病灶分析与量化指标

1. 用户在查看器触发脑卒中分析
2. 后端基于 Tmax 切片执行阈值化与后处理
3. 生成半暗带/核心/综合叠加图
4. 计算半暗带体积、核心体积与不匹配比

### 5.3 AI 报告生成与保存

1. 组织患者信息与分析指标
2. 调用百川 M3 生成影像报告
3. 报告保存至 Supabase
4. 前端报告页加载并允许编辑

---

## 6. 模块索引表

| 模块 | 功能描述 | 关键实现文件 |
| --- | --- | --- |
| 影像上传与预处理 | 接收 NIfTI 文件、触发处理链路 | [templates/patient/upload/index.html](../templates/patient/upload/index.html)、[static/js/upload.js](../static/js/upload.js)、[app.py](../app.py) |
| 影像查看与交互 | 多切片浏览、对比度/伪彩/分析展示 | [templates/patient/upload/viewer/index.html](../templates/patient/upload/viewer/index.html)、[static/js/viewer.js](../static/js/viewer.js) |
| AI 推理 | 三模型推理输出灌注图 | [ai_inference.py](../ai_inference.py)、[mrdpm/](../mrdpm/)、[palette/](../palette/) |
| 病灶分析 | 半暗带/核心梗死分析与量化 | [stroke_analysis.py](../stroke_analysis.py) |
| AI 报告生成 | 调用百川 M3 生成诊断报告 | [app.py](../app.py) |
| 数据存储 | 患者信息/报告存储 | [app.py](../app.py)、[core/supabase_client.py](../core/supabase_client.py) |
| 报告编辑器 | 结构化报告编辑与展示 | [frontend/src/app/page.tsx](../frontend/src/app/page.tsx)、[frontend/src/components/](../frontend/src/components/) |

