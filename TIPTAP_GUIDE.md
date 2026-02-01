# TipTap 富文本编辑器集成指南

## 项目结构

```
src/
├── components/
│   ├── RichTextEditor.tsx        # 富文本编辑器组件（TipTap）
│   ├── StructuredReport.tsx      # 主报告页面
│   ├── PatientInfoModule.tsx     # 患者信息模块
│   ├── ImageFindingsModule.tsx   # 影像学发现模块
│   └── DoctorNotesModule.tsx     # 医生备注模块
├── styles/
│   ├── global.css               # 全局样式
│   ├── report.css               # 报告页面样式
│   └── editor.css               # 编辑器样式
└── main.tsx                     # 入口文件
```

## 功能特性

### 富文本编辑器支持

- ✅ **文本格式化**：加粗、斜体、删除线
- ✅ **结构化内容**：标题、段落、引用
- ✅ **列表**：有序列表、无序列表
- ✅ **链接**：插入和编辑超链接
- ✅ **图片**：插入图片引用
- ✅ **撤销/重做**：完整的编辑历史
- ✅ **气泡菜单**：快速格式化工具

### 编辑器工具栏

| 按钮 | 功能 | 快捷键 |
|------|------|--------|
| **B** | 加粗 | Ctrl+B |
| *I* | 斜体 | Ctrl+I |
| ~~S~~ | 删除线 | Ctrl+Shift+X |
| H2 | 标题 2 | Ctrl+Alt+2 |
| • | 无序列表 | Ctrl+Shift+8 |
| 1. | 有序列表 | Ctrl+Shift+7 |
| 🔗 | 链接 | - |
| 🖼️ | 图片 | - |
| ↶ | 撤销 | Ctrl+Z |
| ↷ | 重做 | Ctrl+Shift+Z |

## 开发环境设置

### 1. 安装依赖

```bash
npm install
```

### 2. 启动开发服务器

```bash
# 终端1：启动 Vite 开发服务器（自动热更新）
npm run dev

# 终端2：启动 Flask 后端
FLASK_ENV=development python run.py
```

Vite 开发服务器默认在 `http://localhost:5173`

Flask 后端在 `http://localhost:5000`

### 3. 访问报告页面

```
http://localhost:5000/report/1?file_id=test_file_123
```

其中：
- `1` 是患者 ID
- `test_file_123` 是文件 ID

## 编译生产版本

```bash
npm run build
```

编译后的文件在 `static/dist/` 目录，包括：
- `index.html`
- `assets/` 文件夹（JS、CSS、图片等）

## 生产环境部署

1. **编译前端**
   ```bash
   npm run build
   ```

2. **更新 Flask 配置**
   - 设置 `FLASK_ENV=production`
   - Flask 会自动加载编译后的静态文件

3. **运行服务**
   ```bash
   python run.py
   ```

## API 集成

### 获取患者信息
```
GET /api/get_patient/<int:patient_id>

Response:
{
  "status": "success",
  "data": {
    "id": 1,
    "patient_name": "张三",
    "patient_age": 65,
    "patient_sex": "男",
    "onset_exact_time": "2024-02-01T14:30:00",
    "admission_time": "2024-02-01T15:00:00",
    "admission_nihss": 15,
    "surgery_time": "30分钟"
  }
}
```

### 保存报告
```
POST /api/save_report

Request:
{
  "patient_id": 1,
  "file_id": "test_file_123",
  "patient": { ... },
  "findings": { ... },
  "notes": "...",
  "saved_at": "2024-02-01T16:00:00"
}

Response:
{
  "status": "success",
  "message": "报告保存成功"
}
```

## 自定义编辑器

### 添加新的格式化选项

编辑 `src/components/RichTextEditor.tsx`：

```tsx
// 添加下标
const addSubscript = () => {
  editor.chain().focus().toggleSubscript().run()
}

// 在工具栏中添加按钮
<button onClick={addSubscript} className="format-btn" title="下标">
  H₂O
</button>
```

### 添加自定义扩展

```tsx
import Highlight from '@tiptap/extension-highlight'

const editor = useEditor({
  extensions: [
    StarterKit,
    Highlight.configure({
      multicolor: true
    })
  ]
})
```

## 故障排除

### 问题 1：Vite 开发服务器无法连接

**解决方案**：确保 Vite 运行在 `5173` 端口，检查防火墙设置

### 问题 2：编辑器内容不保存

**解决方案**：检查 `/api/save_report` 是否返回成功响应

### 问题 3：样式不显示

**解决方案**：确保 CSS 文件在 `src/styles/` 目录中，并正确导入到组件中

## 生产构建优化

```bash
# 分析包大小
npm run build -- --analyze

# 预览生产构建
npm run preview
```

## 参考资源

- [TipTap 官方文档](https://tiptap.dev/)
- [Vite 文档](https://vitejs.dev/)
- [React 18 文档](https://react.dev/)

---

**最后更新**：2024年2月1日
**版本**：1.0.0
