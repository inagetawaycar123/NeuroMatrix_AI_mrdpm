# CTP血管堵塞三分类功能完整集成文档

本文档描述了CTP血管堵塞三分类功能如何全面融入到NeuroMatrix AI系统的报告生成、模型分析和校验中心。

## 功能概述

CTP血管堵塞三分类（基于DINOv3模型）能够自动分析CTP灌注图像，将血管状态分为三类：
- **无阻塞（无明显血管狭窄）**
- **LVO（大血管闭塞，Large Vessel Occlusion）**
- **MEVO（小血管病变）**

该分类结果现已全面集成到以下三个关键系统：

---

## 一、报告生成集成

### 1.1 百川大模型Prompt增强

**文件位置**: `backend/app.py:551-648`

#### Markdown报告模板 (REPORT_PROMPT_TEMPLATE)

**新增输入参数：**
```python
【CTP血管堵塞AI分类结果】
- 分类结论: {vessel_classification}
- 置信度: {vessel_confidence}
- 临床意义: {vessel_clinical_significance}
- 治疗方向: {vessel_treatment_suggestion}
```

**写作要求增强：**
- 新增 **血管评估** 章节，要求明确描述血管堵塞分类结果（LVO/MEVO/无明显狭窄）
- 治疗建议必须结合血管分类结论：
  - LVO患者 → 重点提示机械取栓适应症
  - 无明显狭窄/小血管病变 → 侧重内科治疗

**输出结构增强：**
```markdown
## 血管评估
基于CTP灌注图的AI辅助分析系统，对血管堵塞情况进行分类评估：
1. **分类结果**: {vessel_classification}（置信度：{vessel_confidence}）
2. **临床意义**: {vessel_clinical_significance}
3. **血管特征**: 结合CTP灌注特征和动态血管显影，综合判断血管通畅情况。

## 影像学结论
综合影像所见与血管评估...
- 是否提示大血管闭塞（LVO）或小血管病变

## 治疗建议
- **血管评估结论**：{vessel_treatment_suggestion}
```

#### JSON报告模板 (REPORT_JSON_PROMPT)

**新增字段：**
```json
"血管评估": {
    "分类结果": "{vessel_classification}",
    "置信度": "{vessel_confidence}",
    "临床意义": "{vessel_clinical_significance}",
    "堵塞类型": "基于分类结果推断（LVO/MEVO/无明显狭窄）"
}
```

### 1.2 数据提取与映射

**文件位置**: `backend/app.py:650-748`

**函数**: `generate_report_with_baichuan(structured_data, output_format)`

**实现逻辑：**
```python
# 从structured_data中提取occlusion_classification
occlusion_data = structured_data.get("occlusion_classification", {})

if occlusion_data and occlusion_data.get("success"):
    class_name = occlusion_data.get("class_name", "未分类")
    confidence = occlusion_data.get("confidence", 0)
    
    # 中文映射
    class_name_cn = {
        "无阻塞": "无明显血管狭窄",
        "LVO": "大血管闭塞（LVO）",
        "MEVO": "小血管病变"
    }.get(class_name, class_name)
    
    vessel_classification = class_name_cn
    vessel_confidence = f"{confidence * 100:.1f}%"
    
    # 根据分类结果设置临床意义和治疗建议
    if class_name == "LVO":
        vessel_clinical_significance = "检测到大血管闭塞，可能适合血管内治疗..."
        vessel_treatment_suggestion = "符合适应症的患者可考虑血管内取栓治疗（机械取栓）。"
    # ...其他分类处理
```

**传入Prompt：**
```python
prompt = REPORT_PROMPT_TEMPLATE.format(
    # ...现有参数
    vessel_classification=vessel_classification,
    vessel_confidence=vessel_confidence,
    vessel_clinical_significance=vessel_clinical_significance,
    vessel_treatment_suggestion=vessel_treatment_suggestion,
)
```

### 1.3 Mock报告同步更新

**文件位置**: `backend/app.py:862-940`

Mock报告（百川API未配置时的降级方案）同样包含血管评估信息：

```markdown
检查方法:
...+ CTP灌注成像 + AI辅助血管分析

血管评估:
CTP血管堵塞AI分类结果: {vessel_info}

治疗建议:
1. {vessel_suggestion}  # 根据血管分类动态生成
```

---

## 二、ICV（内在一致性校验）集成

### 2.1 新增规则：R6_vessel_classification

**文件位置**: `backend/icv.py:597-667`

**规则目标**: 检查CTP血管分类结果的内部一致性

**评估维度：**

#### (1) 分类成功性检查
```python
if not success:
    status = "fail"
    message = f"CTP血管分类失败: {error}"
```

#### (2) 置信度阈值检查
```python
if confidence < 0.5:
    status = "warn"
    message = f"CTP血管分类置信度较低 ({confidence:.2%})，建议人工复核"
```

#### (3) 分类与定量参数一致性检查

**逻辑规则：**

| 分类结果 | 定量参数条件 | 一致性判断 |
|---------|------------|-----------|
| LVO | 总病灶 < 10ml | ⚠️ 警告：大血管闭塞但病灶很小 |
| 无阻塞 | 核心梗死 > 50ml | ⚠️ 警告：无狭窄但梗死很大 |
| 其他 | - | ✅ 通过 |

**代码实现：**
```python
if class_name == "LVO" and total_lesion < 10:
    consistency_warning = True
    consistency_msg = f"血管分类为LVO，但总病灶体积较小（{total_lesion:.1f} ml）"

elif class_name == "无阻塞" and core_vol > 50:
    consistency_warning = True
    consistency_msg = f"血管分类为无明显狭窄，但核心梗死体积较大（{core_vol:.1f} ml）"
```

**输出示例：**
```python
{
    "id": "R6_vessel_classification",
    "status": "pass" | "warn" | "fail",
    "message": "CTP血管分类结果 LVO (置信度: 89.2%) 与定量参数基本一致"
}
```

### 2.2 校验流程集成

ICV评估函数会自动：
1. 从`analysis_result.occlusion_classification`提取数据
2. 从`tool_results`中的`run_stroke_analysis`工具提取备用数据
3. 执行R6规则评估
4. 将结果纳入overall status和score计算

---

## 三、EKV（外部知识验证）集成

### 3.1 新增Claim：vessel_occlusion_classification

**文件位置**: `backend/ekv.py:367-422`

**Claim ID**: `vessel_occlusion_classification`

**Claim Text**: "CTP vessel occlusion classification is evidence-based."

**验证逻辑：**

#### (1) 基于置信度的验证
```python
if confidence < 0.5:
    verdict = "partially_supported"
    message = f"CTP血管分类结果为 {class_name}，但置信度较低 ({confidence:.2%})"
```

#### (2) 与ICV R6的联动验证
```python
r6_status = icv_finding_status_map.get("R6_vessel_classification")

if r6_status == "fail":
    verdict = "not_supported"
    message = f"CTP血管分类结果 {class_name} 与ICV规则校验冲突"
elif r6_status == "warn":
    verdict = "partially_supported"
```

#### (3) 与定量参数的逻辑一致性验证

**LVO验证逻辑：**
```python
if class_name == "LVO":
    total_lesion = core + penumbra
    if total_lesion > 10 or mismatch_ratio > 1.8:
        verdict = "supported"
        message = f"血管分类 {class_name} 与定量参数一致，符合LVO特征"
    else:
        verdict = "partially_supported"
        message = f"血管分类 {class_name}，但定量参数提示病灶较小"
```

**无阻塞验证逻辑：**
```python
if class_name == "无阻塞":
    if core < 20:
        verdict = "supported"
    else:
        verdict = "partially_supported"
        message = f"血管分类 {class_name}，但核心梗死体积较大"
```

### 3.2 高风险Claim标记

**文件位置**: `backend/ekv.py:12-18`

```python
HIGH_RISK_CLAIM_IDS = {
    "core_infarct_volume",
    "penumbra_volume",
    "mismatch_ratio",
    "significant_mismatch",
    "treatment_window_notice",
    "vessel_occlusion_classification",  # 新增
}
```

血管分类被标记为高风险claim，任何不支持（not_supported）的验证结果将导致整体校验状态降级。

### 3.3 证据引用配置

**文件位置**: `backend/ekv.py:67-84`

```python
source_map = {
    # ...
    "vessel_occlusion_classification": "internal_guideline:vessel_classification_ai_v1",
}
```

---

## 四、Summary Assembler集成

### 4.1 关键Claim配置

**文件位置**: `backend/summary_assembler.py:9-42`

**KEY_CLAIM_IDS更新：**
```python
KEY_CLAIM_IDS: List[str] = [
    "hemisphere",
    "core_infarct_volume",
    "penumbra_volume",
    "mismatch_ratio",
    "significant_mismatch",
    "treatment_window_notice",
    "vessel_occlusion_classification",  # 新增
]
```

**CLAIM_TITLES映射：**
```python
CLAIM_TITLES = {
    # ...
    "vessel_occlusion_classification": "CTP血管分类",
}
```

**QUESTION_FOCUS_KEYWORDS扩展：**
```python
QUESTION_FOCUS_KEYWORDS = {
    # ...
    "vessel_occlusion_classification": [
        "血管", "闭塞", "堵塞", "LVO", "MEVO", "vessel", "occlusion"
    ],
}
```

### 4.2 综合摘要生成

当用户通过AI问诊或报告浏览询问血管相关问题时，系统会：
1. 识别关键词（"血管"、"LVO"、"闭塞"等）
2. 提取`vessel_occlusion_classification` claim的验证结果
3. 结合ICV R6和EKV验证状态，生成综合回答

---

## 五、数据流程图

```
┌─────────────────────────────────────────────────────────────┐
│ 1. 影像上传 & CTP生成                                          │
│    upload → processing → generate_ctp_maps                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. 脑卒中分析执行 (stroke_analysis.py:auto_analyze_stroke) │
│    • 运行核心梗死/半暗带分析                                    │
│    • 调用 analyze_occlusion(case_id)                         │
│    • 调用 generate_case_gradcam_visualizations(case_id)     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. 数据存储 (analysis_result.occlusion_classification)     │
│    {                                                         │
│      "success": true,                                        │
│      "class_name": "LVO",                                    │
│      "confidence": 0.892,                                    │
│      "gradcam_visualizations": [...]                         │
│    }                                                         │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
┌──────────┐  ┌──────────┐  ┌──────────────┐
│ ICV校验   │  │ EKV校验   │  │ 报告生成      │
│ (R6规则)  │  │ (Claim7) │  │ (百川大模型)  │
└──────────┘  └──────────┘  └──────────────┘
     │             │              │
     └─────────────┼──────────────┘
                   ▼
          ┌─────────────────┐
          │ Viewer侧边栏展示 │
          │ • 血管分类结果   │
          │ • GradCAM可视化 │
          └─────────────────┘
```

---

## 六、前端展示集成

### 6.1 Viewer侧边栏

**文件位置**: `backend/templates/patient/upload/viewer/index.html:144-174`

**新增区域1：CTP血管分类**
```html
<div class="panel-section analysis-results" id="ctpClassificationSection">
    <div class="section-title">CTP 血管分类</div>
    <div class="metrics-list">
        <div class="metric-row">
            <span class="metric-label">分类结果</span>
            <span class="metric-value" id="ctp-class-name">--</span>
        </div>
        <div class="metric-row">
            <span class="metric-label">置信度</span>
            <span class="metric-value" id="ctp-confidence">--</span>
        </div>
        <!-- 临床意义、治疗建议 -->
    </div>
</div>
```

**新增区域2：GradCAM特征可视化**
```html
<div class="panel-section analysis-results" id="gradcamVisualizationSection">
    <div class="section-title">GradCAM 特征可视化</div>
    <div class="result-images" id="gradcam-images">
        <!-- 动态加载GradCAM热力图 -->
    </div>
</div>
```

### 6.2 JavaScript渲染

**文件位置**: `static/js/viewer.js:991-1119`

**函数**: `displayCTPClassification()`

**渲染逻辑：**
1. 从`analysisResults.occlusion_classification`提取数据
2. 根据分类设置颜色（LVO红色、MEVO橙色、无阻塞绿色）
3. 动态加载GradCAM图像（前3个最高置信度切片）
4. 显示临床意义和治疗建议

---

## 七、测试验证

### 7.1 单元测试

**测试文件**: `test_gradcam_fix.py`

验证GradCAM生成功能：
```bash
python test_gradcam_fix.py
# 预期输出：All tests passed!
```

### 7.2 集成测试流程

1. **上传影像** → Processing页面
2. **执行分析** → 自动运行CTP三分类
3. **查看侧边栏** → Viewer页面 "脑卒中分析"
   - 验证"CTP血管分类"区域显示
   - 验证"GradCAM特征可视化"显示
4. **查看校验** → Validation页面
   - ICV检查：R6_vessel_classification
   - EKV检查：vessel_occlusion_classification claim
5. **生成报告** → 手动生成AI报告
   - 验证报告中包含"血管评估"章节
   - 验证治疗建议结合血管分类结论

---

## 八、配置说明

### 8.1 模型文件

- **DINOv3预训练权重**: `exp_dinov3/src/ckpt/dinov3_vitb16_pretrain_lvd1689m-73cec8be.pth`
- **三分类权重**: `exp_dinov3/src/dinov3权重.pth`

### 8.2 分类类别映射

```python
CLASS_NAMES = ["无阻塞", "LVO", "MEVO"]
```

### 8.3 GradCAM输出目录

```
static/processed/{case_id}/gradcam/
├── gradcam_tmax_0001.png
├── gradcam_tmax_0002.png
└── gradcam_tmax_0003.png
```

---

## 九、关键文件清单

| 文件路径 | 修改内容 | 行数范围 |
|---------|---------|---------|
| `backend/app.py` | 百川Prompt增强、数据提取 | 551-748, 862-940 |
| `backend/icv.py` | R6规则添加 | 597-667 |
| `backend/ekv.py` | Claim7添加、HIGH_RISK更新 | 12-18, 67-84, 367-422 |
| `backend/summary_assembler.py` | KEY_CLAIM配置更新 | 9-42 |
| `backend/stroke_analysis.py` | GradCAM生成调用 | 698-716 |
| `backend/occlusion_classifier.py` | GradCAM核心实现 | 256-492 |
| `backend/templates/.../index.html` | 侧边栏HTML | 144-174 |
| `static/js/viewer.js` | 前端渲染逻辑 | 991-1119 |
| `static/css/main.css` | CSS样式 | 1418-1459 |

---

## 十、常见问题

### Q1: GradCAM生成失败怎么办？
A: 系统有容错机制，即使GradCAM失败，也不会影响分类结果和报告生成。查看日志中的`[WARN] GradCAM visualization error`。

### Q2: 如何调整置信度阈值？
A: 修改`backend/icv.py`和`backend/ekv.py`中的0.5阈值。

### Q3: 如何禁用血管分类功能？
A: 在`backend/stroke_analysis.py:698`注释掉相关调用即可。

### Q4: 百川报告没有包含血管评估？
A: 检查：
1. `structured_data`是否包含`occlusion_classification`
2. 百川API Key是否配置
3. Prompt模板是否正确更新

---

## 十一、技术支持

如有问题，请查看：
- 详细使用说明：`VESSEL_CLASSIFICATION_README.md`
- GradCAM测试：`test_gradcam_fix.py`
- 项目主文档：`README.md`

---

**文档版本**: v1.0  
**更新日期**: 2026-04-22  
**作者**: NeuroMatrix AI Development Team
