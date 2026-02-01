# 项目文件结构详解

## 完整的项目树

```
d:\NeuroMatrix_AI_mrdpm\
│
├── 📄 核心配置文件
│   ├── vite.config.ts                 # Vite 构建配置
│   ├── tsconfig.json                  # TypeScript 编译配置
│   ├── tsconfig.node.json             # Node TypeScript 配置
│   ├── package.json                   # npm 依赖和脚本
│   ├── index.html                     # React 应用入口 HTML
│   └── .env.example                   # 环境变量模板
│
├── 📁 src/                            # ⭐ React 源代码目录
│   ├── 📄 main.tsx                    # React 应用入口
│   │   └── 作用: 解析 URL 参数 → 获取患者数据 → 挂载 React 应用
│   │
│   ├── 📂 components/                 # React 组件
│   │   ├── RichTextEditor.tsx         # ⭐ TipTap 富文本编辑器
│   │   │   ├── 功能: 加粗、斜体、删除线
│   │   │   ├── 功能: 标题、列表、链接、图片
│   │   │   ├── 功能: 撤销/重做
│   │   │   └── 输出: HTML 格式的编辑内容
│   │   │
│   │   ├── StructuredReport.tsx       # 主报告容器
│   │   │   ├── 功能: 管理编辑/查看状态
│   │   │   ├── 功能: 获取患者信息 (API)
│   │   │   ├── 功能: 生成 AI 影像描述
│   │   │   └── 功能: 保存报告 (API)
│   │   │
│   │   ├── PatientInfoModule.tsx      # 患者信息模块
│   │   │   ├── 字段: 姓名、年龄、性别
│   │   │   ├── 字段: 发病时间、入院时间
│   │   │   ├── 字段: NIHSS 评分
│   │   │   └── 支持: 编辑/查看模式切换
│   │   │
│   │   ├── ImageFindingsModule.tsx    # 影像学发现模块
│   │   │   ├── 核心梗死区 → RichTextEditor
│   │   │   ├── 半暗带区域 → RichTextEditor
│   │   │   ├── 血管评估 → RichTextEditor
│   │   │   ├── 灌注参数 → RichTextEditor (支持列表)
│   │   │   └── AI 指标卡 (只读)
│   │   │       ├── 体积、不匹配比例
│   │   │       └── 颜色标记状态
│   │   │
│   │   └── DoctorNotesModule.tsx      # 医生备注模块
│   │       ├── 字段: 自由文本备注
│   │       ├── 编辑: 完整的富文本支持
│   │        └── 查看: 保留所有格式化
│   │
│   └── 📂 styles/                    # CSS 样式文件
│       ├── global.css                # 全局样式
│       │   ├── 深色主题配置
│       │   ├── 字体和基础样式
│       │   └── 响应式设计
│       │
│       ├── report.css                # 报告页面布局
│       │   ├── 报告容器和头部
│       │   ├── 模块、字段样式
│       │   ├── AI 指标卡样式
│       │   └── 响应式布局
│       │
│       └── editor.css                # TipTap 编辑器样式
│           ├── 工具栏布局和按钮
│           ├── 编辑器内容区域
│           ├── 文本和列表样式
│           └── 链接、图片、代码样式
│
├── 📁 static/                         # 静态资源
│   ├── dist/                          # 🔨 编译后的生产文件 (npm run build)
│   │   ├── index.html                # 生产版本 HTML
│   │   ├── assets/
│   │   │   ├── index-*.js            # 打包的 React + TipTap (580+ KB)
│   │   │   └── index-*.css           # 打包的样式 (5.66 KB)
│   │   └── (其他资源文件)
│   │
│   ├── css/                           # 旧版本样式 (可以删除)
│   │   ├── main.css
│   │   ├── report.css
│   │   └── contrast_control.js
│   │
│   ├── js/                            # 旧版本 JavaScript (可以删除)
│   │   ├── common.js
│   │   ├── patient.js
│   │   ├── upload.js
│   │   ├── viewer.js
│   │   └── report.js                 # 旧的纯 JS 版本
│   │
│   ├── uploads/                       # 用户上传的文件
│   └── processed/                     # 处理后的文件
│
├── 📁 templates/                      # Flask HTML 模板
│   ├── base.html                      # 基础模板
│   ├── patient.html                   # 患者信息表单
│   ├── patient/
│   │   └── upload/
│   │       ├── index.html             # 文件上传页
│   │       └── viewer/
│   │           ├── index.html         # 图像查看器
│   │           └── report/
│   │               ├── index.html     # 旧版本报告页 (不用)
│   │               └── vite.html      # 新版本报告页 (开发模式)
│   │
│   └── (其他模板)
│
├── 📁 mrdpm/                          # AI 模型
│   ├── models/
│   ├── weights/
│   └── config/
│
├── 📁 palette/                        # 灌注图 AI 模型
│   ├── models/
│   ├── weights/
│   └── config/
│
├── 📁 core/                           # 核心模块
│   ├── supabase_client.py             # 数据库连接
│   ├── base_model.py
│   └── (其他核心文件)
│
├── 🔧 启动脚本
│   ├── start-dev.bat                  # Windows 一键启动
│   ├── start-dev.sh                   # Linux/macOS 一键启动
│   ├── run.bat                        # Windows 运行
│   ├── run.py                         # Python 运行脚本
│   └── run.sh                         # Shell 运行脚本
│
├── 🐍 主应用
│   ├── app.py                         # Flask 后端应用
│   │   ├── 路由: /report/<patient_id> → 加载报告页面
│   │   ├── API: GET /api/get_patient/<id>
│   │   ├── API: POST /api/save_report
│   │   └── (其他 API 路由)
│   │
│   ├── stroke_analysis.py             # 卒中分析模块
│   ├── ai_inference.py                # AI 推理
│   ├── cuda.py                        # GPU 配置
│   └── extensions.py                  # Flask 扩展
│
├── 📚 文档
│   ├── QUICKSTART.md                  # ⭐ 快速开始
│   ├── TIPTAP_GUIDE.md                # 🔍 TipTap 详细指南
│   ├── IMPLEMENTATION_SUMMARY.md      # 📝 实现总结
│   ├── COMPLETION_CHECKLIST.md        # ✅ 完成清单
│   ├── README.md                      # 项目 README
│   ├── IMPLEMENTATION_GUIDE.md        # 其他指南
│   └── (其他文档)
│
├── 📋 配置
│   ├── requirements.txt               # Python 依赖
│   ├── .gitignore
│   └── (其他配置)
│
└── 🗂️ 其他
    ├── node_modules/                  # npm 包 (包含 TipTap)
    │   ├── react/
    │   ├── @tiptap/
    │   │   ├── react/
    │   │   ├── starter-kit/
    │   │   ├── extension-image/
    │   │   ├── extension-link/
    │   │   └── (其他 TipTap 包)
    │   └── (其他依赖)
    │
    ├── __pycache__/
    └── .env
```

---

## 关键文件说明

### 1. 配置文件

| 文件 | 用途 | 重要性 |
|------|------|--------|
| `vite.config.ts` | Vite 构建配置、代理设置 | 🔴 必须 |
| `tsconfig.json` | TypeScript 编译选项 | 🔴 必须 |
| `package.json` | npm 依赖和脚本 | 🔴 必须 |
| `index.html` | React 应用入口 | 🔴 必须 |
| `.env.example` | 环境变量模板 | 🟡 可选 |

### 2. React 源代码

| 文件 | 行数 | 功能 |
|------|------|------|
| `src/main.tsx` | ~40 | 应用入口和初始化 |
| `RichTextEditor.tsx` | ~160 | TipTap 编辑器组件 |
| `StructuredReport.tsx` | ~180 | 主报告容器 |
| `PatientInfoModule.tsx` | ~100 | 患者信息编辑 |
| `ImageFindingsModule.tsx` | ~100 | 影像学发现编辑 |
| `DoctorNotesModule.tsx` | ~35 | 医生备注编辑 |

### 3. 样式文件

| 文件 | 大小 | 功能 |
|------|------|------|
| `global.css` | ~100 行 | 深色主题 + 响应式基础 |
| `report.css` | ~200 行 | 报告页面完整布局 |
| `editor.css` | ~250 行 | TipTap 编辑器和工具栏 |

### 4. Flask 后端

| 文件 | 关键路由/函数 | 功能 |
|------|----------------|------|
| `app.py` | `@app.route('/report/<patient_id>')` | 报告页面路由 |
| | `GET /api/get_patient/<id>` | 获取患者信息 |
| | `POST /api/save_report` | 保存报告到数据库 |

---

## 编译后的文件结构

编译后 (`npm run build` → `static/dist/`)：

```
static/dist/
├── index.html                         # HTML 入口 (0.43 KB)
└── assets/
    ├── index-C-3TA9pv.css            # 样式包 (5.66 KB, 1.58 KB gzip)
    └── index-CKfC5faa.js             # JavaScript 包 (584.66 KB, 186.11 KB gzip)
                                       # 包含: React 18 + TipTap + 所有组件
```

---

## 数据流和交互

### 页面加载流程

```
1. 用户访问 /report/1?file_id=abc
   ↓
2. Flask 检查 static/dist/index.html 是否存在
   ↓
3. 返回编译后的 index.html
   ↓
4. 浏览器加载 assets/index-*.js 和 assets/index-*.css
   ↓
5. React 应用初始化 (src/main.tsx)
   ├── 解析 URL 获取 patientId 和 fileId
   ├── 从 sessionStorage 获取 analysis_data
   └── 渲染 StructuredReport 组件
   ↓
6. StructuredReport 调用 API
   ├── GET /api/get_patient/1
   └── 获取患者信息，自动生成影像描述
   ↓
7. 页面显示报告
   ├── PatientInfoModule (患者信息)
   ├── ImageFindingsModule (影像学发现 + TipTap)
   └── DoctorNotesModule (医生备注 + TipTap)
```

### 编辑流程

```
用户点击"编辑报告"
   ↓
setIsEditing(true)
   ↓
所有字段进入编辑模式
├── PatientInfoModule: input 字段显示
├── ImageFindingsModule: RichTextEditor 显示
└── DoctorNotesModule: RichTextEditor 显示
   ↓
用户编辑内容 (使用 TipTap 工具栏)
   ↓
内容自动保存到 React state
   ↓
用户点击"保存报告"
   ↓
POST /api/save_report (发送 HTML 格式内容)
   ↓
Flask 保存到 Supabase
   ↓
显示"保存成功"提示
   ↓
setIsEditing(false) 返回查看模式
```

---

## 文件大小统计

### 源代码
```
src/
├── components/        ~600 行
├── styles/           ~550 行
└── main.tsx          ~40 行
总计: 约 1,200 行代码
```

### 编译后
```
dist/
├── index.html        0.43 KB
├── index-*.css       5.66 KB (1.58 KB gzip)
└── index-*.js        584.66 KB (186.11 KB gzip)
总计: ~590 KB (187 KB gzip)

包含:
- React 18
- React DOM
- TipTap React
- TipTap Starter Kit
- Prosemirror (编辑器核心)
- 所有自定义组件和样式
```

---

## 部署检查清单

部署到生产环境前：

- [ ] 编译源代码: `npm run build`
- [ ] 检查 `static/dist/` 目录是否生成
- [ ] 验证 `app.py` 中的报告路由正确
- [ ] 设置 `FLASK_ENV=production`
- [ ] 验证 Supabase 连接
- [ ] 测试 `/api/save_report` 端点
- [ ] 检查浏览器控制台是否有错误
- [ ] 验证 CSS 样式正确应用
- [ ] 测试编辑器的所有功能

---

## 开发工作流

### 修改源代码

1. 编辑 `src/components/*.tsx` 或 `src/styles/*.css`
2. 保存文件
3. Vite 自动热更新浏览器
4. 查看修改效果

### 构建生产版本

```bash
npm run build
# 生成 static/dist/ 目录
# Flask 自动加载生产文件
```

### 调试

```bash
# 打开浏览器 DevTools
F12

# Network 标签: 查看 API 请求和响应
# Console 标签: 查看 JavaScript 错误
# Styles 标签: 调试 CSS
```

---

**祝你开发愉快！** 🎉
