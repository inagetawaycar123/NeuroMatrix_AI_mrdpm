/**
 * Prompt 工程模块
 * 按 AHA 卒中指南编写带约束的 Prompt 模板
 * 包含免责声明和循证医学建议
 */

import { PatientContext, ChatMessage } from './session-manager'

/**
 * 系统 Prompt 模板
 * 定义 AI 助手的角色和行为约束
 */
export const SYSTEM_PROMPT = `你是一个卒中领域的医学辅助决策助手，由 NeuroMatrix AI 提供支持。

**你的角色与责任：**
1. 根据 AHA/ASA（美国心脏协会/美国卒中协会）最新卒中指南提供建议
2. 对患者的临床数据进行分析和解释
3. 协助医生进行临床决策，但绝不替代医生的专业判断
4. 确保所有建议均基于现有的循证医学证据

**你必须遵守的约束：**
1. 所有医学建议必须明确标注来源和证据等级
2. 识别患者数据中的关键医学指标和异常值
3. 对不确定的信息明确说明置信度
4. 如果超出你的医学知识范围，明确指出并建议咨询专科医生
5. 不提供个人化治疗处方，仅提供基于指南的一般性建议

**重要免责声明（必须在每个响应中体现）：**
⚠️ 本系统仅供医学辅助参考，不能替代医生的临床决策
⚠️ 所有建议必须结合患者具体情况和医生专业判断
⚠️ 在任何医疗决策前，请咨询持证医生

**响应格式：**
- 使用结构化的列表或表格展示关键信息
- 标注每条建议的证据等级（I级/IIa级/IIb级/III级）
- 明确区分事实陈述和专业建议
- 包含相关的 AHA 指南条款编号

**关于卒中的关键知识：**
- 卒中包括缺血性卒中（占 87%）和出血性卒中（占 13%）
- CBF（脑血流）、CBV（脑血容量）、Tmax（达峰时间）是 CTP 的关键参数
- Tmax 延迟通常表示缺血区域，可以指导溶栓治疗时间窗
- NIHSS 评分用于评估卒中严重程度，指导治疗策略`

/**
 * 患者数据格式化器
 * 将患者信息转换为清晰的文本表示
 */
function formatPatientData(context: PatientContext): string {
  const lines: string[] = []

  // 基本信息
  lines.push('【患者基本信息】')
  if (context.name) lines.push(`姓名: ${context.name}`)
  if (context.age) lines.push(`年龄: ${context.age} 岁`)
  if (context.gender) {
    const genderMap: Record<string, string> = {
      male: '男性',
      female: '女性',
      other: '其他',
    }
    lines.push(`性别: ${genderMap[context.gender] || context.gender}`)
  }

  // 医学史
  if (context.medicalHistory) {
    lines.push('\n【既往史】')
    lines.push(context.medicalHistory)
  }

  // 当前诊断
  if (context.currentDiagnosis) {
    lines.push('\n【现病史】')
    lines.push(context.currentDiagnosis)
  }

  // 临床评分
  if (context.clinicalScores && Object.keys(context.clinicalScores).length > 0) {
    lines.push('\n【临床评分】')
    if (context.clinicalScores.nihss !== undefined) {
      lines.push(`NIHSS评分: ${context.clinicalScores.nihss}`)
      // 解释 NIHSS 评分
      if (context.clinicalScores.nihss <= 4) {
        lines.push('  → 轻微卒中（通常门诊管理）')
      } else if (context.clinicalScores.nihss <= 10) {
        lines.push('  → 轻度卒中')
      } else if (context.clinicalScores.nihss <= 20) {
        lines.push('  → 中度卒中')
      } else {
        lines.push('  → 重度卒中（高风险，需要集中监护）')
      }
    }
    if (context.clinicalScores.mrs !== undefined) {
      lines.push(`mRS评分: ${context.clinicalScores.mrs}`)
    }
    if (context.clinicalScores.otherScores) {
      for (const [key, value] of Object.entries(
        context.clinicalScores.otherScores
      )) {
        lines.push(`${key}: ${value}`)
      }
    }
  }

  // 影像数据
  if (context.imagingData && Object.keys(context.imagingData).length > 0) {
    lines.push('\n【影像学检查】')
    if (context.imagingData.cbf) {
      lines.push(`CBF (脑血流): ${context.imagingData.cbf}`)
    }
    if (context.imagingData.cbv) {
      lines.push(`CBV (脑血容量): ${context.imagingData.cbv}`)
    }
    if (context.imagingData.tmax) {
      lines.push(`Tmax (达峰时间): ${context.imagingData.tmax}`)
      lines.push('  → Tmax 延迟区通常表示缺血半暗带，可能可逆')
    }
    if (context.imagingData.otherImages) {
      lines.push(`其他影像: ${context.imagingData.otherImages}`)
    }
  }

  // 自定义字段
  for (const [key, value] of Object.entries(context)) {
    if (
      ![
        'patientId',
        'name',
        'age',
        'gender',
        'medicalHistory',
        'currentDiagnosis',
        'imagingData',
        'clinicalScores',
      ].includes(key)
    ) {
      if (value && typeof value === 'string') {
        lines.push(`${key}: ${value}`)
      }
    }
  }

  return lines.join('\n')
}

/**
 * 构建完整的 Prompt
 * 包括系统指令、患者数据、对话历史和当前问题
 */
export function buildPrompt(
  patientContext: PatientContext,
  messages: ChatMessage[],
  currentQuestion: string
): string {
  const parts: string[] = []

  // 1. 患者数据上下文
  parts.push('【患者临床信息】')
  parts.push(formatPatientData(patientContext))

  // 2. 对话历史摘要（最近的 3 条消息）
  if (messages.length > 0) {
    parts.push('\n【诊询历史（摘要）】')
    const recentMessages = messages.slice(-3)
    for (const msg of recentMessages) {
      const role = msg.role === 'user' ? '医生' : 'AI助手'
      parts.push(`${role}: ${msg.content.substring(0, 100)}${msg.content.length > 100 ? '...' : ''}`)
    }
  }

  // 3. 当前医生提问
  parts.push('\n【医生提问】')
  parts.push(currentQuestion)

  // 4. 指示
  parts.push('\n【要求】')
  parts.push('请基于上述患者信息和 AHA 卒中指南，回答医生的问题。')
  parts.push('记得：')
  parts.push('1. 标注证据等级（如 IIa 级推荐）')
  parts.push('2. 明确医学置信度')
  parts.push('3. 包含重要免责声明')

  return parts.join('\n')
}

/**
 * Prompt 模板类
 * 提供各种标准化的医学提问模板
 */
export class PromptTemplate {
  /**
   * 卒中风险评估
   */
  static strokeRiskAssessment(patientContext: PatientContext): string {
    return `基于患者的临床信息，请进行卒中风险评估：
1. 识别主要风险因素
2. 评估当前卒中风险等级
3. 推荐的预防性治疗
4. 建议的随访计划

患者信息：
${formatPatientData(patientContext)}`
  }

  /**
   * 溶栓治疗决策
   */
  static thrombolyticDecision(patientContext: PatientContext): string {
    return `基于患者信息，请评估是否适合溶栓治疗：
1. 发病时间（IV-tPA 4.5 小时窗口，机械取栓 24 小时窗口）
2. 禁忌症评估
3. 利益风险比分析
4. 建议方案

患者信息：
${formatPatientData(patientContext)}`
  }

  /**
   * 影像学解释
   */
  static imagingInterpretation(patientContext: PatientContext): string {
    return `请解释患者的 CTP 参数，并指导临床决策：
1. CBF/CBV/Tmax 的异常模式识别
2. 缺血半暗带的评估
3. 对卒中亚型的提示
4. 对治疗策略的影响

患者信息：
${formatPatientData(patientContext)}`
  }

  /**
   * 症状管理
   */
  static symptomManagement(patientContext: PatientContext, symptom: string): string {
    return `患者出现 "${symptom}" 症状，请提供处理建议：
1. 鉴别诊断
2. 紧急评估步骤
3. 对症治疗选项
4. 监测要点

患者信息：
${formatPatientData(patientContext)}`
  }

  /**
   * 康复规划
   */
  static rehabilitationPlanning(patientContext: PatientContext): string {
    return `请为患者制定卒中康复计划：
1. 当前神经功能状态评估
2. 康复潜能评估
3. 推荐的康复治疗模式
4. 预期恢复时间表

患者信息：
${formatPatientData(patientContext)}`
  }

  /**
   * 药物治疗建议
   */
  static medicationAdvisory(patientContext: PatientContext): string {
    return `请为患者提供药物治疗建议：
1. 当前卒中亚型的一线药物
2. 禁忌药物和相互作用
3. 剂量和给药方式
4. 疗效监测指标

患者信息：
${formatPatientData(patientContext)}`
  }
}

/**
 * 免责声明文本
 */
export const DISCLAIMER = `
⚠️ 【重要医学免责声明】
本系统提供的所有信息、分析和建议仅供医学专业人士参考，不构成医学诊断或治疗建议。

✓ 我们的承诺：
  • 所有内容基于 AHA/ASA 最新卒中指南
  • 采用循证医学原理
  • 提供透明的证据等级标注

✗ 我们的限制：
  • 不能替代医生的临床判断
  • 无法进行远程诊断
  • 不负责因使用本系统而导致的医疗后果
  • 所有临床决策必须由持证医生做出

📋 使用规则：
  1. 医生在使用任何建议前必须进行独立的临床评估
  2. 所有治疗决策必须与患者充分沟通并获得知情同意
  3. 定期评估治疗效果并灵活调整方案
  4. 遇到复杂情况应咨询相关专科医生

使用本系统即表示您同意上述条款。
`

export function addDisclaimerToResponse(response: string): string {
  return `${response}\n\n${DISCLAIMER}`
}
