# 图像控制模块集成详细步骤

## 📍 问题说明

您需要在现有的 `templates/index.html` 文件中引入新创建的图像控制模块 `static/js/image_controls.js`。

## 🎯 具体操作步骤

### 步骤1：找到正确的位置

打开文件：`templates/index.html`

在文件的**最底部**找到这两行：

```html
    </script>
</body>
</html>
```

### 步骤2：在正确位置添加代码

在 `</body>` 标签**之前**，`</script>` 标签**之后**添加以下代码：

```html
    </script>
    
    <!-- 新增：图像控制模块 -->
    <script src="/static/js/image_controls.js"></script>
    
</body>
</html>
```

## 📝 完整示例

### 修改前（原文件末尾）：
```html
        function hideMessages() {
            document.getElementById('errorMessage').style.display = 'none';
            document.getElementById('successMessage').style.display = 'none';
        }
    </script>
</body>
</html>
```

### 修改后（添加图像控制模块）：
```html
        function hideMessages() {
            document.getElementById('errorMessage').style.display = 'none';
            document.getElementById('successMessage').style.display = 'none';
        }
    </script>
    
    <!-- 图像控制模块 -->
    <script src="/static/js/image_controls.js"></script>
    
</body>
</html>
```

## 🔍 如何找到正确位置

### 方法1：使用编辑器搜索
1. 打开 `templates/index.html`
2. 按 `Ctrl+F`（Windows）或 `Cmd+F`（Mac）
3. 搜索：`</body>`
4. 找到后，在 `</body>` 标签**上面一行**添加代码

### 方法2：滚动到文件末尾
1. 打开 `templates/index.html`
2. 按 `Ctrl+End`（Windows）或 `Cmd+Down`（Mac）跳到文件末尾
3. 向上滚动找到 `</body>` 标签
4. 在 `</body>` 标签**上面一行**添加代码

## 📋 完整的添加位置示意图

```
templates/index.html 文件结构：

<!DOCTYPE html>
<html>
<head>
    ...
</head>
<body>
    ...
    
    <script>
        // 原有的JavaScript代码
        let currentFileId = null;
        ...
        
        function hideMessages() {
            ...
        }
    </script>                          ← 原有脚本结束
    
    <!-- 在这里添加 -->
    <script src="/static/js/image_controls.js"></script>  ← 新增这一行
    
</body>                                ← body标签结束
</html>                                ← html标签结束
```

## ✅ 验证是否添加成功

### 方法1：查看浏览器控制台
1. 启动服务器：`python app.py`
2. 打开浏览器访问：`http://localhost:5000`
3. 按 `F12` 打开开发者工具
4. 切换到 "Console" 标签
5. 如果没有看到 `image_controls.js` 相关的错误，说明加载成功

### 方法2：查看网络请求
1. 按 `F12` 打开开发者工具
2. 切换到 "Network" 标签
3. 刷新页面
4. 查找 `image_controls.js` 文件
5. 如果状态码是 `200`，说明加载成功

### 方法3：在控制台测试
在浏览器控制台输入：
```javascript
typeof MedicalImageController
```
如果返回 `"function"`，说明模块加载成功。

## 🚨 常见错误

### 错误1：404 Not Found
**原因**：文件路径不正确
**解决**：确保文件在 `static/js/image_controls.js`

### 错误2：脚本不执行
**原因**：添加位置不对
**解决**：确保在 `</body>` 之前，所有其他 `<script>` 之后

### 错误3：功能不工作
**原因**：可能有JavaScript错误
**解决**：打开浏览器控制台查看错误信息

## 🎨 可选：添加窗宽窗位功能到现有界面

如果您想在现有界面中使用窗宽窗位功能，需要额外添加以下代码：

### 在 `templates/index.html` 的 `<script>` 部分末尾添加：

```javascript
// 初始化图像控制器
let imageController = null;

// 在图像加载后初始化控制器
function initImageController() {
    if (!imageController) {
        imageController = new MedicalImageController('mainImage');
    }
}

// 修改 loadSlice 函数，在图像加载后初始化控制器
function loadSlice(sliceIndex) {
    // ... 原有代码 ...
    
    const img = document.getElementById('mainImage');
    img.onload = function() {
        initImageController();
    };
}

// 添加窗宽窗位调整函数
function adjustWindowLevel(deltaX, deltaY) {
    if (imageController) {
        imageController.adjustWindowLevel(deltaX, deltaY);
    }
}

// 添加亮度调整函数
function adjustBrightness(delta) {
    if (imageController) {
        imageController.adjustBrightness(delta);
    }
}

// 添加对比度调整函数
function adjustContrast(delta) {
    if (imageController) {
        imageController.adjustContrast(delta);
    }
}
```

## 📞 需要帮助？

如果按照以上步骤操作后仍有问题，请检查：

1. ✅ 文件 `static/js/image_controls.js` 是否存在
2. ✅ 代码是否添加在 `</body>` 标签之前
3. ✅ 浏览器控制台是否有错误信息
4. ✅ 服务器是否正常运行

## 🎯 总结

**关键点**：
- 文件位置：`templates/index.html` 的末尾
- 添加位置：`</body>` 标签**之前**
- 添加内容：`<script src="/static/js/image_controls.js"></script>`
- 验证方法：浏览器控制台检查是否有错误

按照这个步骤，您就可以成功集成图像控制模块了！