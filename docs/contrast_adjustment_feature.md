# 图像对比度调节功能说明

## 功能概述

本功能实现了类似ITK-SNAP软件的图像对比度调节功能，用于调节NCCT和CTA医学影像的显示对比度。

## 核心特性

### 1. 窗宽/窗位调节 (Window Width/Level)

- **窗宽 (Window Width)**: 控制图像对比度范围，值越小对比度越高
- **窗位 (Window Level/Center)**: 控制图像亮度中心点

### 2. 交互方式

#### 滑块调节
- 窗宽滑块: 范围 1-4000
- 窗位滑块: 范围 -1000 到 3000

#### 鼠标拖拽调节
- **水平拖拽**: 调节窗宽（向右增大，向左减小）
- **垂直拖拽**: 调节窗位（向上增大，向下减小）
- **双击**: 重置为默认值

### 3. 医学影像预设值

| 预设名称 | 窗宽 | 窗位 | 用途 |
|---------|------|------|------|
| 脑窗 | 80 | 40 | 查看脑实质 |
| 卒中窗 | 40 | 40 | 查看缺血区域 |
| 骨窗 | 2000 | 500 | 查看骨骼结构 |
| 软组织窗 | 400 | 40 | 查看软组织 |
| 血管窗 | 600 | 300 | 查看血管 |
| 硬膜下窗 | 200 | 75 | 查看硬膜下出血 |
| CT默认 | 350 | 50 | CT扫描默认窗口 |

### 4. 直方图显示

- 实时显示图像强度分布
- 标记当前窗口范围（蓝色=最小值，红色=最大值）

### 5. 自动调节

- 分析图像数据自动计算最佳窗宽窗位
- 忽略背景区域（灰度值<5）

## 文件结构

```
static/
├── js/
│   └── contrast_control.js    # 对比度控制器主模块 (821行)
└── css/
    └── contrast_control.css   # 对比度面板样式 (425行)

templates/
└── index.html                 # 集成对比度功能的主页面

app.py                         # 后端API（对比度调节相关路由）
```

## 前端实现

### ContrastController 类

```javascript
class ContrastController {
    constructor(options) {
        // 配置选项
        this.options = {
            containerId: 'contrast-panel-container',
            onUpdate: null,           // 更新回调
            useServerSide: false,     // 是否使用服务器端调节
            fileId: null
        };
        
        // 每个图像的对比度设置
        this.imageSettings = {};
        
        // 预设值
        this.presets = { ... };
    }
    
    // 核心方法
    applyContrastToImage(imageId)     // 应用对比度到图像
    enableDragAdjust(imageId)         // 启用拖拽调节
    applyPreset(presetKey)            // 应用预设
    autoAdjust()                      // 自动调节
    resetCurrent()                    // 重置当前图像
    applyToAll()                      // 应用到所有图像
}
```

### CSS滤镜实现

```javascript
// 窗宽窗位转换为CSS滤镜
const contrast = 256 / windowWidth;
const brightness = 128 - (windowLevel * contrast);
imgElement.style.filter = `contrast(${contrast}) brightness(${1 + brightness/256})`;
```

## 后端API

### 1. 对比度调节

```
GET /adjust_contrast/<file_id>/<slice_index>/<image_type>?ww=80&wl=40
```

参数:
- `file_id`: 文件ID
- `slice_index`: 切片索引
- `image_type`: 图像类型 (mcta, ncct)
- `ww`: 窗宽
- `wl`: 窗位

### 2. 获取直方图

```
GET /get_image_histogram/<file_id>/<slice_index>/<image_type>
```

返回:
```json
{
    "success": true,
    "histogram": [0, 10, 25, ...],
    "statistics": {
        "min": 0,
        "max": 255,
        "mean": 128,
        "std": 45
    },
    "suggested_window": {
        "width": 255,
        "level": 127.5
    }
}
```

### 3. 保存设置

```
POST /save_contrast_settings/<file_id>
Content-Type: application/json

{
    "cta": {"windowWidth": 80, "windowLevel": 40},
    "ncct": {"windowWidth": 80, "windowLevel": 40}
}
```

### 4. 加载设置

```
GET /load_contrast_settings/<file_id>
```

## 使用方法

### 1. 打开对比度面板

点击工具栏中的"对比度调节"按钮

### 2. 选择图像

在面板中选择要调节的图像（CTA或NCCT）

### 3. 调节对比度

- 使用滑块精确调节
- 在图像上拖拽快速调节
- 选择预设值快速切换

### 4. 查看效果

- 实时预览调节效果
- 查看直方图了解数据分布

### 5. 保存设置

设置会自动保存，切换切片时保持

## 技术细节

### 窗宽窗位变换公式

```python
def apply_window_level(img_array, window_width, window_level):
    window_min = window_level - window_width / 2
    window_max = window_level + window_width / 2
    adjusted = np.clip(img_array, window_min, window_max)
    adjusted = ((adjusted - window_min) / (window_max - window_min)) * 255
    return adjusted
```

### 拖拽灵敏度

```javascript
const wwSensitivity = 2;  // 窗宽灵敏度
const wlSensitivity = 1;  // 窗位灵敏度

const newWW = dragStartWW + deltaX * wwSensitivity;
const newWL = dragStartWL - deltaY * wlSensitivity;
```

## 界面截图

### 对比度调节面板

```
┌─────────────────────────────────┐
│ 图像对比度调节              [×] │
├─────────────────────────────────┤
│ 选择图像                        │
│ [CTA] [NCCT]                    │
├─────────────────────────────────┤
│ 窗宽 (Window Width)             │
│ ────●──────────────── [80]      │
├─────────────────────────────────┤
│ 窗位 (Window Level)             │
│ ────●──────────────── [40]      │
├─────────────────────────────────┤
│ 强度直方图                      │
│ ┌───────────────────────────┐   │
│ │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│   │
│ └───────────────────────────┘   │
├─────────────────────────────────┤
│ 预设值                          │
│ [脑窗] [卒中窗] [骨窗]          │
│ [软组织] [血管窗] [硬膜下]      │
├─────────────────────────────────┤
│ [重置] [应用全部] [自动调节]    │
├─────────────────────────────────┤
│ 💡 在图像上拖拽：水平=窗宽      │
│    垂直=窗位                    │
└─────────────────────────────────┘
```

### 图像单元格指示器

```
┌─────────────────────────────────┐
│ CTA                         ✓  │
│                                 │
│         [医学图像]              │
│                                 │
│ W:80 L:40                       │
└─────────────────────────────────┘
```

## 注意事项

1. **实时预览**: 使用CSS滤镜实现实时预览，性能优秀
2. **服务器端调节**: 可选的服务器端精确调节模式
3. **设置持久化**: 对比度设置在切换切片时保持
4. **跨浏览器兼容**: 支持所有现代浏览器

## 后续优化建议

1. 添加对比度调节历史记录
2. 支持自定义预设值
3. 添加对比度曲线编辑器
4. 支持多图像同步调节
5. 添加键盘快捷键支持

## 更新日志

### v1.0.0 (2024-12-11)
- 初始版本
- 实现窗宽/窗位滑块调节
- 实现鼠标拖拽调节
- 添加医学影像预设值
- 实现直方图显示
- 添加自动调节功能
- 集成到NCCT和CTA图像显示