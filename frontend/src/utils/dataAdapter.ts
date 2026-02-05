/**
 * 数据格式适配器
 * 用于在不同系统间转换数据格式
 */

export interface BEndMessage {
  id: string
  sender: 'doctor' | 'patient' | 'ai'
  content: string
  timestamp: string
  session_id?: string
  user_id?: string
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  id?: string
  timestamp?: string
}

export interface MedicalAnalysis {
  risks: Array<{
    level: 'high' | 'medium' | 'low'
    description: string
    suggestion: string
  }>
  keypoints: string[]
  recommendations?: string[]
  timestamp: string
}

export interface BEndAnalysis {
  risk_level: 'high' | 'medium' | 'low'
  findings: string[]
  suggestions: string[]
  created_at: string
  analysis_type: string
}

export class DataAdapter {
  /**
   * 将B端消息格式转换为问答系统格式
   */
  static convertMessagesToChatFormat(bEndMessages: BEndMessage[]): ChatMessage[] {
    return bEndMessages.map(msg => ({
      role: msg.sender === 'ai' ? 'assistant' : 'user',
      content: msg.content,
      id: msg.id,
      timestamp: msg.timestamp
    }))
  }

  /**
   * 将问答系统消息格式转换为B端格式
   */
  static convertMessagesToBEndFormat(chatMessages: ChatMessage[], sessionId?: string, userId?: string): BEndMessage[] {
    return chatMessages.map((msg, index) => ({
      id: msg.id || `msg_${Date.now()}_${index}`,
      sender: msg.role === 'assistant' ? 'ai' : 'doctor', // 假设医生在问答
      content: msg.content,
      timestamp: msg.timestamp || new Date().toISOString(),
      session_id: sessionId,
      user_id: userId
    }))
  }

  /**
   * 将问答系统分析结果转换为B端格式
   */
  static convertAnalysisToBEndFormat(analysis: MedicalAnalysis): BEndAnalysis {
    const highestRisk = analysis.risks.reduce((highest, current) =>
      this.getRiskPriority(current.level) > this.getRiskPriority(highest.level) ? current : highest
    , analysis.risks[0])

    return {
      risk_level: highestRisk?.level || 'low',
      findings: analysis.keypoints,
      suggestions: [
        ...analysis.risks.map(risk => risk.suggestion),
        ...(analysis.recommendations || [])
      ],
      created_at: analysis.timestamp,
      analysis_type: 'stroke_analysis'
    }
  }

  /**
   * 将B端分析结果转换为问答系统格式
   */
  static convertAnalysisFromBEndFormat(bEndAnalysis: BEndAnalysis): MedicalAnalysis {
    return {
      risks: [{
        level: bEndAnalysis.risk_level,
        description: bEndAnalysis.findings.join('; '),
        suggestion: bEndAnalysis.suggestions.join('; ')
      }],
      keypoints: bEndAnalysis.findings,
      recommendations: bEndAnalysis.suggestions,
      timestamp: bEndAnalysis.created_at
    }
  }

  /**
   * 标准化会话ID
   */
  static normalizeSessionId(sessionId: string | undefined): string {
    return sessionId || `session_${Date.now()}`
  }

  /**
   * 标准化用户ID
   */
  static normalizeUserId(userId: string | undefined): string {
    return userId || 'anonymous'
  }

  /**
   * 验证消息格式
   */
  static validateMessage(message: any): boolean {
    return (
      message &&
      typeof message.content === 'string' &&
      message.content.trim().length > 0 &&
      ['user', 'assistant'].includes(message.role)
    )
  }

  /**
   * 清理消息内容（移除敏感信息等）
   */
  static sanitizeMessage(content: string): string {
    // 这里可以添加内容清理逻辑
    // 例如：移除患者个人信息、敏感数据等
    return content
      .replace(/\b\d{11}\b/g, '[手机号]') // 隐藏手机号
      .replace(/\b\d{18}\b/g, '[身份证号]') // 隐藏身份证号
  }

  /**
   * 获取风险等级优先级
   */
  private static getRiskPriority(level: string): number {
    const priorities = { high: 3, medium: 2, low: 1 }
    return priorities[level as keyof typeof priorities] || 0
  }

  /**
   * 格式化时间戳
   */
  static formatTimestamp(timestamp: string | Date): string {
    const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp
    return date.toISOString()
  }

  /**
   * 创建标准API响应
   */
  static createStandardResponse(data: any, success: boolean = true, message?: string) {
    return {
      success,
      message: message || (success ? '操作成功' : '操作失败'),
      data,
      timestamp: new Date().toISOString()
    }
  }

  /**
   * 解析API错误
   */
  static parseApiError(error: any): string {
    if (typeof error === 'string') return error
    if (error?.message) return error.message
    if (error?.response?.data?.message) return error.response.data.message
    return '未知错误'
  }
}