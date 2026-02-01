# 📋 快速操作指南 - CSS 404 修复

## 问题已解决 ✅

你遇到的错误：
```
index-C-3TA9pv.css:1  Failed to load resource: the server responded with a status of 404 (NOT FOUND)
```

已通过在 Flask 后端添加**动态路径重写**解决。

## 立即使用

### 1️⃣ 启动应用

```bash
# 使用 conda 环境
conda activate NeuroMatrix_AI_mrdpm
python run.py
```

### 2️⃣ 访问报告页面

在浏览器中访问：
```
http://localhost:5000/report/55?file_id=397ecb0d
```

### 3️⃣ 验证修复

打开浏览器开发者工具 (F12)：
- **Network** 标签
- 查看资源加载状态
- CSS 和 JS 文件应显示 **200 OK**

## 修复原理

| 发生位置 | 状态 | 说明 |
|---------|------|------|
| HTML 编译 | `/assets/index-*.js` | Vite 生成的相对路径 |
| Flask 路由 | 动态替换 | `/static/dist/assets/index-*.js` |
| 浏览器请求 | 正确 URL | Flask 正确服务文件 |

## 技术细节

**修改文件**: `app.py`  
**修改位置**: `/report/<patient_id>` 路由 (第 671-697 行)  
**修改方式**: 使用正则表达式重写 HTML 中的资源路径

```python
# 修改前的路径
src="/assets/index-CKfC5faa.js"
href="/assets/index-C-3TA9pv.css"

# 修改后的路径（自动完成）
src="/static/dist/assets/index-CKfC5faa.js"
href="/static/dist/assets/index-C-3TA9pv.css"
```

## 常见问题

### Q: 还是 404？
A: 确保：
1. Flask 应用已重启
2. `static/dist/` 目录存在
3. 使用正确的 URL: `http://localhost:5000/report/55?file_id=397ecb0d`

### Q: 开发环境如何处理？
A: 如果 `static/dist/` 不存在，系统自动使用 Vite 开发服务器。

### Q: 生产环境如何部署？
A: 
1. 运行 `npm run build` 生成 `static/dist/`
2. 部署应用
3. Flask 自动使用预编译的文件

## 验证命令

```bash
# 测试路径替换逻辑
python test_path_logic.py

# 测试 HTML 文件是否存在
ls -la static/dist/index.html
```

## 下一步

✅ 修复完成  
✅ 无需进一步操作  
✅ 正常访问报告页面  

---

**更多信息**: 查看 `CSS_404_FIX.md` 了解完整的技术细节
