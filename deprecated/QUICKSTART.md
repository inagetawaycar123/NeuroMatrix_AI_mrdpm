# 🚀 NeuroMatrix AI 报告系统 - 快速开始

## 项目现状

✅ **已完成** - TipTap 富文本编辑器全面集成

```
📦 项目结构
├── src/                          # React/TypeScript 源代码
│   ├── components/               # React 组件
│   │   ├── RichTextEditor.tsx    # ⭐ TipTap 富文本编辑器
│   │   ├── StructuredReport.tsx  # 主报告容器
│   │   ├── PatientInfoModule.tsx # 患者信息
│   │   ├── ImageFindingsModule.tsx # 影像学发现
│   │   └── DoctorNotesModule.tsx # 医生备注
│   ├── styles/                   # CSS 样式
│   └── main.tsx                  # React 入口
├── static/dist/                  # 🔨 编译后的生产文件（npm run build）
├── vite.config.ts                # Vite 构建配置
├── tsconfig.json                 # TypeScript 配置
├── package.json                  # npm 依赖
└── start-dev.bat / start-dev.sh  # 一键启动脚本
```

---

## ⚡ 快速启动（3 种方式）

### 方式 1：使用启动脚本（推荐）

#### Windows
```bash
./start-dev.bat
```

#### macOS/Linux
```bash
bash start-dev.sh
```

**自动启动：**
- Vite 开发服务器（http://localhost:5173）
- Flask 后端（http://localhost:5000）

---

### 方式 2：手动启动（两个终端）

#### 终端 1 - Vite 开发服务器
```bash
cd d:\NeuroMatrix_AI_mrdpm
npm run dev
```
输出：`Local: http://localhost:5173`

#### 终端 2 - Flask 后端
```bash
cd d:\NeuroMatrix_AI_mrdpm
set FLASK_ENV=development
python run.py
```
输出：`Running on http://localhost:5000`

---

### 方式 3：生产模式

```bash
# 1. 编译（已预先执行）
npm run build
# → 输出到 static/dist/

# 2. 运行 Flask（自动加载编译文件）
python run.py
```

---

## 📝 访问报告页面

打开浏览器，访问：

```
http://localhost:5000/report/1?file_id=test123
```

**URL 参数说明：**
- `1` = 患者 ID（替换为实际 ID）
- `test123` = 文件 ID（从查看器页面自动传递）

---

## 🎯 主要功能

### 1️⃣ 患者信息模块
- 编辑患者基本信息（姓名、年龄、性别）
- 日期时间选择（发病时间、入院时间）
- NIHSS 评分输入

### 2️⃣ 影像学发现模块（富文本）
- **核心梗死区** - 完整的富文本编辑
- **半暗带** - 支持格式化
- **血管评估** - 可编辑描述
- **灌注分析** - 支持列表格式
- **AI 指标卡** - 显示体积、不匹配比例

### 3️⃣ 医生备注模块（富文本）
- 自由格式的临床备注
- 完整的格式化工具

### 4️⃣ 编辑器功能（TipTap）

| 功能 | 工具栏按钮 | 快捷键 |
|------|----------|--------|
| 加粗 | **B** | Ctrl+B |
| 斜体 | *I* | Ctrl+I |
| 删除线 | ~~S~~ | Ctrl+Shift+X |
| 标题 | H2 | Ctrl+Alt+2 |
| 列表 | • | Ctrl+Shift+8 |
| 编号列表 | 1. | Ctrl+Shift+7 |
| 链接 | 🔗 | - |
| 图片 | 🖼️ | - |
| 撤销 | ↶ | Ctrl+Z |
| 重做 | ↷ | Ctrl+Shift+Z |

---

## 💾 工作流程

### 1. 医生查看患者信息
```
查看器页面 (已有)
  ↓
患者信息 + 影像 + AI 分析结果
```

### 2. 生成报告
```
点击"生成报告"按钮
  ↓
sessionStorage 保存分析数据
  ↓
导航到 /report/{patientId}
```

### 3. 编辑报告（新功能 ⭐）
```
点击"编辑报告"
  ↓
进入编辑模式（所有字段可编辑）
  ↓
使用富文本编辑器编辑影像描述
  ↓
点击"保存报告"
  ↓
POST /api/save_report
  ↓
保存到 Supabase
```

### 4. 查看报告
```
查看模式
  ↓
所有内容已格式化显示
  ↓
支持 PDF 导出（开发中）
```

---

## 🔧 常见操作

### 编辑器快速技巧

#### 插入链接
1. 选中文本
2. 点击 🔗 按钮或 Ctrl+K
3. 输入 URL

#### 插入图片
1. 点击 🖼️ 按钮
2. 输入图片 URL（支持 http/https）
3. 图片显示在编辑器中

#### 创建列表
```
点击 • 按钮创建无序列表
点击 1. 按钮创建编号列表
按 Enter 添加新项
按 Backspace 删除列表
```

#### 格式化文本
```
选中文本
点击工具栏按钮或使用快捷键
例：Ctrl+B 加粗，Ctrl+I 斜体
```

---

## 🐛 调试

### 查看浏览器控制台

```javascript
// 检查患者数据
console.log(sessionStorage.getItem('analysis_data'))

// 检查 API 响应
fetch('/api/get_patient/1').then(r => r.json()).then(console.log)

// 测试编辑器 HTML
// (在编辑器失焦后查看)
document.querySelector('.editor-content p').innerHTML
```

### 网络请求

F12 → Network 标签 → 点击"保存报告"观察：
- 请求：`POST /api/save_report`
- 响应：`{"status": "success", "message": "报告保存成功"}`

---

## 📦 构建和部署

### 开发模式
- Vite 热更新
- 快速构建
- 完整 DevTools

### 生产模式
```bash
# 优化编译
npm run build

# 生成文件
static/dist/
├── index.html        # 入口
├── assets/
│   ├── index-*.js    # 打包 JS（580+ KB）
│   └── index-*.css   # 打包 CSS
```

### 部署服务器
```bash
# 设置环境
FLASK_ENV=production

# 运行
python run.py

# Flask 自动从 static/dist/ 加载前端文件
```

---

## 🚀 性能优化

当前编译结果：
- **JS**: 584 KB (186 KB gzipped)
- **CSS**: 5.66 KB (1.58 KB gzipped)

优化建议：
- 使用 `npm run build` 后的文件（已压缩）
- Gzip 传输（Web 服务器自动启用）
- CDN 加速静态资源

---

## ✨ 已实现的功能

- ✅ 完整的 React + TypeScript 框架
- ✅ TipTap 富文本编辑器集成
- ✅ 所有模块都支持编辑和查看
- ✅ HTML 格式化内容保存
- ✅ 编辑历史（撤销/重做）
- ✅ 响应式设计（桌面/平板/手机）
- ✅ 深色主题（医疗专业外观）
- ✅ 生产编译和优化

---

## 🎯 后续功能（可选）

- 📄 PDF 导出（需要 pdf-lib）
- 📝 Word 导出（需要 docx）
- 📸 本地图片上传
- 👥 多用户协作编辑
- 📊 版本历史对比
- 🔐 权限管理

---

## 📞 遇到问题？

### 问题：报告页面显示空白

**解决：**
1. 检查浏览器控制台错误
2. 确保 Flask 运行在 5000 端口
3. 验证患者 ID 在数据库中存在

### 问题：编辑器不显示

**解决：**
1. 检查 CSS 文件是否加载
2. 在浏览器 DevTools 中查看样式
3. 刷新页面

### 问题：保存失败

**解决：**
1. 检查 `/api/save_report` 是否有错误
2. 查看 Flask 后端日志
3. 确保 Supabase 连接正常

---

## 📚 参考资源

- [TipTap 文档](https://tiptap.dev/)
- [Vite 文档](https://vitejs.dev/)
- [React 18 文档](https://react.dev/)
- [项目详细文档](./TIPTAP_GUIDE.md)
- [实现总结](./IMPLEMENTATION_SUMMARY.md)

---

**开始编辑你的第一份报告吧！** 🎉

访问：`http://localhost:5000/report/1?file_id=test123`
