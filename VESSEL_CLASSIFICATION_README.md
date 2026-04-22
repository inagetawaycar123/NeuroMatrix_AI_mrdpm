# 血管堵塞三分类系统 - 使用说明

## 📌 系统概述

基于DINOv3的CTP影像血管堵塞三分类系统，用于自动识别：
- **无明显血管狭窄** (Class_0)
- **大血管闭塞** (Class_1_LVO - Large Vessel Occlusion)
- **小血管病变** (Class_2_MEVO - Medium/Small Vessel Disease)

## 🎯 功能特点

- ✅ 自动集成到Processing页面工作流
- ✅ 在CTP生成后、卒中分析前自动执行
- ✅ 使用Tmax图像进行分类
- ✅ 提供置信度和临床解释
- ✅ 生成治疗建议

## 📊 输出格式

```json
{
  "血管分类": "大血管闭塞（LVO）",
  "置信度": "94.00%",
  "临床意义": "检测到大血管闭塞，可能适合血管内治疗。建议结合临床症状和时间窗判断。",
  "治疗建议": "符合适应症的患者可考虑血管内取栓治疗（机械取栓）。"
}
```

## 🚀 使用方法

### 1. 通过Processing页面（自动执行）

上传NCCT + 3-phase CTA数据后，系统会自动：
1. 生成CTP图谱
2. **执行血管堵塞三分类** ← 自动触发
3. 进行卒中病灶分析
4. 生成AI报告

### 2. 查看结果

在Processing页面的实时feed中可以看到：
```
Vessel_Classification.classify()
血管分类=大血管闭塞（LVO), 置信度=94.00%, 
临床意义=检测到大血管闭塞..., 
治疗建议=符合适应症的患者...
```

## 📁 文件结构

```
exp_dinov3/
├── src/
│   ├── ckpt/
│   │   └── dinov3_vitb16_pretrain_lvd1689m-73cec8be.pth  # DINOv3预训练权重
│   ├── dinov3/                    # DINOv3模型目录
│   │   └── termcolor.py          # termcolor mock (解决依赖)
│   ├── dinov3权重.pth             # 训练好的分类权重
│   ├── predict.py                # 单张图像预测
│   ├── predict_ctp.py            # CTP序列批量预测
│   └── termcolor.py              # termcolor mock
└── README.md
```

## 🔧 技术细节

### 模型架构
- **Backbone**: DINOv3 ViT-B/16
- **分类头**: MLP (2层)
- **输入尺寸**: 224×224
- **类别数**: 3
- **冻结比例**: 35%
- **Dropout率**: 35%

### 图像处理
- 使用Tmax图像进行分类
- 自动过滤伪彩图(pseudocolor)
- 自动过滤叠加图(overlay)
- 批量处理所有CTP切片

### 路径查找
系统自动在以下位置查找CTP图像：
1. `static/processed/{file_id}/` ← 优先
2. `static/uploads/{patient_id}/{file_id}/`
3. `uploads/{patient_id}/{file_id}/`

## 🐛 故障排除

### 问题1: ModuleNotFoundError: No module named 'termcolor'
**解决方案**: 已在`exp_dinov3/src/dinov3/termcolor.py`中创建mock文件

### 问题2: CTP图像未找到
**排查**:
1. 确认CTP生成成功
2. 检查`static/processed/{file_id}/`目录
3. 查看日志中的路径搜索信息

### 问题3: 所有图像预测均失败
**排查**:
1. 检查PyTorch版本
2. 确认权重文件存在
3. 查看完整的错误堆栈

## 📝 修改记录

### v1.2 (2026-04-21)
- ✅ 简化输出格式，只显示4个关键字段
- ✅ 中文字段名，更易读
- ✅ 优化Processing页面显示效果

### v1.1 (2026-04-21)
- ✅ 修复torch.hub.load调用方式
- ✅ 添加termcolor mock
- ✅ 优化路径查找逻辑
- ✅ 增强错误日志

### v1.0 (2026-04-21)
- ✅ 初始版本发布
- ✅ 集成到Processing页面
- ✅ 实现三分类功能

## 🏥 临床解释

### 大血管闭塞（LVO）
- **临床意义**: 可能适合血管内治疗
- **治疗建议**: 符合适应症可考虑机械取栓

### 小血管病变（MEVO）
- **临床意义**: 可能为慢性小血管性脑病或腔隙性梗死
- **治疗建议**: 内科治疗，危险因素控制

### 无明显狭窄
- **临床意义**: 大血管通畅，无明显闭塞
- **治疗建议**: 不建议血管内治疗，关注内科治疗

## 📞 支持

如有问题，请查看日志输出或联系开发团队。

---

**更新时间**: 2026-04-21 23:27
**版本**: 1.2
