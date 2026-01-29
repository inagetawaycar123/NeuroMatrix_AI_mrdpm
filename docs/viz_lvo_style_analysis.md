# Viz LVO 风格分析与设计方案

## 🎯 Viz LVO 核心设计特点

### 1. **布局结构** - PACS风格网格系统
```
┌────────────────────────────────────────────────────────┐
│ 顶部工具栏 (40px) - 极简、扁平、功能性                  │
├────────────────────────────────────────────────────────┤
│                                                        │
│  ┌──────────┬──────────┬──────────┬──────────┐       │
│  │          │          │          │          │       │
│  │  图像1   │  图像2   │  图像3   │  图像4   │       │
│  │  (CTA)   │  (NCCT)  │  (CBF)   │  (CBV)   │       │
│  │          │          │          │          │       │
│  └──────────┴──────────┴──────────┴──────────┘       │
│  ┌──────────┬──────────┬──────────┬──────────┐       │
│  │          │          │          │          │       │
│  │  图像5   │  图像6   │  图像7   │  图像8   │       │
│  │  (Tmax)  │  (掩码)  │  (半暗带)│  (核心)  │       │
│  │          │          │          │          │       │
│  └──────────┴──────────┴──────────┴──────────┘       │
│                                                        │
├────────────────────────────────────────────────────────┤
│ 底部信息栏 (60px) - 切片导航 + 关键指标                 │
└────────────────────────────────────────────────────────┘
```

### 2. **设计原则**
- ✅ **极简主义** - 无圆角、无渐变、无阴影
- ✅ **网格对齐** - 严格的网格系统
- ✅ **黑色背景** - 纯黑 #000000
- ✅ **细线分隔** - 1px 深灰线条
- ✅ **小字体** - 11-13px 系统字体
- ✅ **无装饰** - 纯功能性UI

### 3. **配色方案**
```css
背景: #000000 (纯黑)
分隔线: #1a1a1a (极深灰)
文字: #ffffff (纯白)
次级文字: #808080 (中灰)
强调: #00a8ff (医学蓝 - 仅用于关键信息)
警告: #ff6b6b (红色 - 仅用于警告)
成功: #51cf66 (绿色 - 仅用于成功状态)
```

### 4. **字体规范**
```css
font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
font-size: 11px (小文字)
font-size: 12px (正文)
font-size: 13px (标题)
font-weight: 400 (正常)
font-weight: 500 (中等 - 用于强调)
font-weight: 600 (粗体 - 仅用于重要标题)
```

---

## 🎨 NeuroMatrix AI 的 Viz LVO 风格设计

### 布局方案

#### 方案A：2x4网格布局（推荐）
```
┌─────────────────────────────────────────────────────────────┐
│ 顶栏: NeuroMatrix AI | 患者ID | 切片 1/100 | [工具按钮]     │
├─────────────┬─────────────┬─────────────┬─────────────────┤
│             │             │             │                 │
│   RGB合成   │     CTA     │    NCCT     │     掩码        │
│             │             │             │                 │
├─────────────┼─────────────┼─────────────┼─────────────────┤
│             │             │             │                 │
│   CBF灌注   │   CBV灌注   │  Tmax灌注   │   脑卒中分析    │
│             │             │             │                 │
├─────────────┴─────────────┴─────────────┴─────────────────┤
│ 底栏: ◀ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ ▶      │
│       半暗带: XX ml | 核心: XX ml | 不匹配: X.XX          │
└─────────────────────────────────────────────────────────────┘
```

#### 方案B：主视图+缩略图（类似PACS）
```
┌─────────────────────────────────────────────────────────────┐
│ 顶栏: NeuroMatrix AI | 序列选择 | 工具                      │
├───────────┬─────────────────────────────────────────────────┤
│           │                                                 │
│ 缩略图    │                                                 │
│ 列表      │          主图像显示区                            │
│           │          (当前选中的图像)                        │
│ [切片1]   │                                                 │
│ [切片2]   │                                                 │
│ [切片3]   │                                                 │
│ ...       │                                                 │
│           │                                                 │
├───────────┼─────────────────────────────────────────────────┤
│ AI结果    │ 底部信息栏: 测量值 | AI分析结果                  │
│ [CBF]     │                                                 │
│ [CBV]     │                                                 │
│ [Tmax]    │                                                 │
└───────────┴─────────────────────────────────────────────────┘
```

### 推荐：方案A（2x4网格）
**原因**:
1. 可以同时显示所有关键图像
2. 便于对比不同模态
3. 符合多模态融合的特点
4. 类似Viz LVO的多视图布局

---

## 🎨 具体设计规范

### 1. 顶部工具栏
```html
<div class="top-bar">
    <div class="logo">NeuroMatrix AI</div>
    <div class="patient-info">患者ID: XXXX | 切片: 1/100</div>
    <div class="tools">
        <button>生成伪彩图</button>
        <button>脑卒中分析</button>
        <button>下载</button>
    </div>
</div>
```

**样式**:
```css
.top-bar {
    height: 40px;
    background: #000;
    border-bottom: 1px solid #1a1a1a;
    display: flex;
    align-items: center;
    padding: 0 16px;
    justify-content: space-between;
}

.logo {
    font-size: 13px;
    font-weight: 500;
    color: #fff;
}

.patient-info {
    font-size: 11px;
    color: #808080;
}

.tools button {
    background: transparent;
    border: 1px solid #333;
    color: #fff;
    padding: 4px 12px;
    font-size: 11px;
    margin-left: 8px;
}
```

### 2. 图像网格
```html
<div class="image-grid">
    <div class="grid-cell">
        <div class="cell-label">RGB</div>
        <img src="..." class="grid-image">
    </div>
    <!-- 重复7次 -->
</div>
```

**样式**:
```css
.image-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    grid-template-rows: repeat(2, 1fr);
    gap: 1px;
    background: #1a1a1a;
    height: calc(100vh - 100px);
}

.grid-cell {
    background: #000;
    position: relative;
    overflow: hidden;
}

.cell-label {
    position: absolute;
    top: 4px;
    left: 4px;
    font-size: 10px;
    color: #808080;
    background: rgba(0,0,0,0.7);
    padding: 2px 6px;
    z-index: 10;
}

.grid-image {
    width: 100%;
    height: 100%;
    object-fit: contain;
    transform: rotate(-90deg);
}
```

### 3. 底部信息栏
```html
<div class="bottom-bar">
    <div class="slice-nav">
        <button>◀</button>
        <input type="range" class="slider">
        <span>1 / 100</span>
        <button>▶</button>
    </div>
    <div class="metrics">
        <span>半暗带: 45.2 ml</span>
        <span>核心: 12.8 ml</span>
        <span>不匹配: 3.53</span>
    </div>
</div>
```

**样式**:
```css
.bottom-bar {
    height: 60px;
    background: #000;
    border-top: 1px solid #1a1a1a;
    display: flex;
    align-items: center;
    padding: 0 16px;
    justify-content: space-between;
}

.slice-nav {
    display: flex;
    align-items: center;
    gap: 12px;
}

.slider {
    width: 300px;
    height: 2px;
    background: #333;
}

.metrics {
    display: flex;
    gap: 24px;
    font-size: 11px;
    color: #808080;
}

.metrics span {
    padding: 4px 8px;
    background: #1a1a1a;
}
```

---

## 🚫 需要移除的元素

### 花哨的装饰
- ❌ 所有圆角 (border-radius)
- ❌ 所有渐变 (linear-gradient)
- ❌ 所有阴影 (box-shadow)
- ❌ 所有动画 (animation, pulse)
- ❌ 悬停变换 (transform on hover)
- ❌ 彩色图标和emoji
- ❌ 大标题和描述文字

### 不专业的UI
- ❌ 上传区域的大图标 (⚡)
- ❌ 彩色通道标签
- ❌ 装饰性边框
- ❌ 过大的padding
- ❌ 居中的大按钮

---

## ✅ 需要保留的功能

### 必须显示的图像（8个）
1. RGB合成图
2. CTA图像
3. NCCT图像
4. 脑部掩码
5. CBF灌注图
6. CBV灌注图
7. Tmax灌注图
8. 脑卒中分析结果（半暗带+核心梗死综合图）

### 必须保留的功能
- 文件上传
- 切片导航
- AI推理
- 伪彩图生成
- 脑卒中分析
- 偏侧选择
- 数据下载
- 量化指标显示

### 必须保留的提示
- "AI推理结果仅供参考"
- "请确保输入数据无明显伪影"
- 处理状态提示
- 错误提示

---

## 📐 最终设计方案

### 布局：2x4网格 + 可展开的分析面板

```
┌──────────────────────────────────────────────────────────────┐
│ NeuroMatrix AI  |  患者: XXXX  |  切片: 1/100  | [工具]      │ 40px
├────────────┬────────────┬────────────┬────────────────────────┤
│            │            │            │                        │
│  RGB合成   │    CTA     │   NCCT     │      掩码              │
│            │            │            │                        │
│            │            │            │                        │
├────────────┼────────────┼────────────┼────────────────────────┤
│            │            │            │                        │
│  CBF灌注   │  CBV灌注   │  Tmax灌注  │   脑卒中分析           │
│            │            │            │   [展开/收起]          │
│            │            │            │                        │
├────────────┴────────────┴────────────┴────────────────────────┤
│ ◀ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ ▶    │ 60px
│ 半暗带: 45.2ml | 核心: 12.8ml | 不匹配: 3.53 | [生成伪彩图] │
└──────────────────────────────────────────────────────────────┘
```

### 展开脑卒中分析面板时
```
┌──────────────────────────────────────────────────────────────┐
│ NeuroMatrix AI  |  患者: XXXX  |  切片: 1/100  | [工具]      │
├────────────┬────────────┬────────────┬────────────────────────┤
│  RGB合成   │    CTA     │   NCCT     │      掩码              │
├────────────┼────────────┼────────────┼────────────────────────┤
│  CBF灌注   │  CBV灌注   │  Tmax灌注  │   脑卒中分析 [收起]    │
├────────────┴────────────┴────────────┼────────────────────────┤
│                                      │ 偏侧: [右][左][双侧]   │
│  脑卒中分析详细面板                  │ [开始分析]             │
│  ┌──────────┬──────────┬──────────┐ │                        │
│  │  半暗带  │ 核心梗死 │  综合图  │ │ 半暗带: 45.2 ml        │
│  └──────────┴──────────┴──────────┘ │ 核心: 12.8 ml          │
│                                      │ 不匹配: 3.53           │
│                                      │ 状态: 存在不匹配       │
└──────────────────────────────────────┴────────────────────────┘
```

---

## 🎨 CSS设计规范

### 核心样式
```css
/* 全局重置 */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-size: 12px;
    background: #000;
    color: #fff;
    overflow: hidden;
}

/* 无圆角、无渐变、无阴影 */
.no-decoration {
    border-radius: 0;
    background: solid color;
    box-shadow: none;
}

/* 极简按钮 */
.btn-minimal {
    background: transparent;
    border: 1px solid #333;
    color: #fff;
    padding: 4px 12px;
    font-size: 11px;
    cursor: pointer;
    transition: border-color 0.2s;
}

.btn-minimal:hover {
    border-color: #00a8ff;
}

/* 网格单元 */
.grid-cell {
    background: #000;
    border: 1px solid #1a1a1a;
    position: relative;
}

/* 图像标签 */
.image-label {
    position: absolute;
    top: 4px;
    left: 4px;
    font-size: 10px;
    color: #808080;
    background: rgba(0,0,0,0.8);
    padding: 2px 6px;
    font-weight: 400;
}

/* 状态指示 */
.status-indicator {
    font-size: 10px;
    padding: 2px 6px;
    background: #1a1a1a;
}

.status-success { color: #51cf66; }
.status-warning { color: #ffd43b; }
.status-error { color: #ff6b6b; }
```

---

## 📝 专业提示语设计

### 位置：顶部工具栏右侧
```html
<div class="disclaimer">
    ⚠️ AI分析结果仅供临床参考 | 请确保输入数据无明显伪影
</div>
```

**样式**:
```css
.disclaimer {
    font-size: 10px;
    color: #ffd43b;
    background: rgba(255, 212, 59, 0.1);
    padding: 4px 12px;
    border-left: 2px solid #ffd43b;
}
```

### 其他提示位置
1. **上传区域**: "支持NIfTI格式 (.nii, .nii.gz) | 最大100MB"
2. **AI分析中**: "AI推理中，请稍候..."
3. **分析完成**: "分析完成 | 不匹配比例: X.XX"
4. **错误提示**: "处理失败: [具体原因]"

---

## 🎯 实施要点

### 关键改变
1. **移除所有装饰** - 圆角、渐变、阴影、动画
2. **采用网格布局** - 2x4或3x3严格网格
3. **极简化UI** - 小字体、细边框、纯色
4. **功能优先** - 每个元素都有明确功能
5. **专业提示** - 添加临床相关的警告和说明

### 保持不变
1. **所有功能** - 上传、AI推理、伪彩图、脑卒中分析
2. **图像旋转** - 保持90度旋转
3. **数据处理** - 后端逻辑不变
4. **交互逻辑** - JavaScript功能不变

---

## 🎓 Viz LVO vs 当前设计

| 特性 | Viz LVO | 当前版本 | 目标版本 |
|------|---------|----------|----------|
| 背景 | 纯黑 #000 | 深灰 #1a1a1a | 纯黑 #000 ✅ |
| 圆角 | 无 (0px) | 有 (8-15px) | 无 (0px) ✅ |
| 渐变 | 无 | 有 | 无 ✅ |
| 阴影 | 无 | 有 | 无 ✅ |
| 字体 | 11-12px | 14-16px | 11-12px ✅ |
| 布局 | 网格 | 流式 | 网格 ✅ |
| 间距 | 1px | 12-30px | 1px ✅ |
| 按钮 | 极简 | 圆角彩色 | 极简 ✅ |

---

## 📋 实施步骤

1. ✅ 分析Viz LVO风格特点
2. ⏳ 创建2x4网格布局
3. ⏳ 移除所有装饰性元素
4. ⏳ 实现极简按钮和控件
5. ⏳ 添加专业提示语
6. ⏳ 优化信息密度
7. ⏳ 测试所有功能

---

这个设计方案将使NeuroMatrix AI真正达到Viz LVO的专业水准！