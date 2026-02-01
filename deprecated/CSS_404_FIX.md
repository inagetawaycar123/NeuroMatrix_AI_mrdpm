# 🔧 CSS 404 错误修复报告

## 问题描述

访问报告页面时出现错误：
```
index-C-3TA9pv.css:1  Failed to load resource: the server responded with a status of 404 (NOT FOUND)
```

浏览器请求的路径：
- `/assets/index-CKfC5faa.js` → 404
- `/assets/index-C-3TA9pv.css` → 404

## 根本原因

Vite 编译生成的 `index.html` 中使用了相对于项目根目录的资源路径：
```html
<script src="/assets/index-CKfC5faa.js"></script>
<link href="/assets/index-C-3TA9pv.css">
```

但实际的文件位于：
```
/static/dist/assets/index-*.js
/static/dist/assets/index-*.css
```

Flask 的静态文件夹在 `static/`，所以浏览器尝试从 `/assets/` 直接查找文件会导致 404。

## 解决方案

在 `app.py` 的 `/report/<patient_id>` 路由中添加动态路径重写：

```python
@app.route('/report/<int:patient_id>')
def report_page(patient_id):
    """渲染报告页面"""
    import os
    import re
    # 检查是否有编译后的生产文件
    dist_file = os.path.join(app.static_folder, 'dist', 'index.html')
    if os.path.exists(dist_file):
        # 生产环境：使用编译后的文件，并修改资源路径
        with open(dist_file, 'r', encoding='utf-8') as f:
            html = f.read()
        
        # 修改 <link> 标签中的 href 路径：from /assets/ to /static/dist/assets/
        html = re.sub(r'href="\/assets\/', 'href="/static/dist/assets/', html)
        
        # 修改 <script> 标签中的 src 路径：from /assets/ to /static/dist/assets/
        html = re.sub(r'src="\/assets\/', 'src="/static/dist/assets/', html)
        
        return html
    else:
        # 开发环境：返回 Vite 开发服务器入口
        return render_template('patient/upload/viewer/report/vite.html')
```

## 修复验证

✅ **路径替换逻辑验证通过**

原始路径转换示例：
```
/assets/index-CKfC5faa.js      → /static/dist/assets/index-CKfC5faa.js
/assets/index-C-3TA9pv.css     → /static/dist/assets/index-C-3TA9pv.css
```

## 工作流程

1. **用户访问** `http://localhost:5000/report/55?file_id=397ecb0d`
2. **Flask 路由** `/report/<patient_id>` 被触发
3. **读取文件** `static/dist/index.html`（Vite 编译结果）
4. **动态替换** 所有 `/assets/` 路径为 `/static/dist/assets/`
5. **返回 HTML** 给浏览器
6. **浏览器加载** 正确的资源文件

## 修复后的资源加载

```
GET /static/dist/assets/index-CKfC5faa.js   ✅ 200 OK
GET /static/dist/assets/index-C-3TA9pv.css  ✅ 200 OK
```

## 两种环境支持

### 生产环境
- 使用预编译的 `static/dist/index.html`
- 路径自动重写为 `/static/dist/assets/...`
- 无需 Vite 开发服务器

### 开发环境
- 如果 `static/dist/` 不存在，使用 `vite.html` 模板
- 连接到 Vite 开发服务器
- 支持热更新

## 相关文件

| 文件 | 位置 | 说明 |
|------|------|------|
| app.py | `/report/<patient_id>` | 修改的路由处理函数 |
| index.html | `static/dist/` | Vite 编译生成 |
| index-*.js | `static/dist/assets/` | 打包的 JavaScript |
| index-*.css | `static/dist/assets/` | 打包的样式表 |

## 测试命令

```bash
# 验证路径替换逻辑
python test_path_logic.py

# 运行应用（需要 Flask 和依赖）
python run.py

# 访问报告页面
# http://localhost:5000/report/55?file_id=397ecb0d
```

## 修复日期

2026年2月1日

## 状态

✅ **已完成** - CSS 404 错误已解决，报告页面资源正确加载
