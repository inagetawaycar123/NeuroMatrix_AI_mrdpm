/**
 * B端系统集成示例
 * 展示如何在现有B端系统中嵌入NeuroMatrix问答组件
 */

import React, { useState, useEffect } from 'react'
import { EmbeddedChat, DataAdapter } from '../src'

// 假设的B端API服务
class BEndApiService {
  static async getAuthToken(): Promise<string> {
    // 实现B端认证逻辑
    const response = await fetch('/api/auth/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: 'doctor@example.com',
        password: 'password123'
      })
    })
    const data = await response.json()
    return data.token
  }

  static async saveAnalysis(analysis: any, sessionId: string): Promise<void> {
    // 将分析结果保存到B端数据库
    await fetch('/api/analysis/save', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('authToken')}`
      },
      body: JSON.stringify({
        session_id: sessionId,
        analysis_data: analysis,
        created_at: new Date().toISOString()
      })
    })
  }

  static async logMessage(message: any): Promise<void> {
    // 记录消息到B端日志系统
    await fetch('/api/logs/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('authToken')}`
      },
      body: JSON.stringify(message)
    })
  }
}

// 主集成组件
export function BEndIntegrationExample() {
  const [authToken, setAuthToken] = useState<string>('')
  const [currentSessionId, setCurrentSessionId] = useState<string>('')
  const [isChatVisible, setIsChatVisible] = useState<boolean>(false)

  // 初始化认证和会话
  useEffect(() => {
    initializeIntegration()
  }, [])

  const initializeIntegration = async () => {
    try {
      // 获取认证token
      const token = await BEndApiService.getAuthToken()
      setAuthToken(token)

      // 生成或获取当前会话ID
      const sessionId = localStorage.getItem('currentSessionId') ||
                       `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      setCurrentSessionId(sessionId)
      localStorage.setItem('currentSessionId', sessionId)

    } catch (error) {
      console.error('初始化失败:', error)
      // 处理认证失败的情况
    }
  }

  // 处理分析完成
  const handleAnalysisComplete = async (analysis: any) => {
    try {
      console.log('收到AI分析结果:', analysis)

      // 转换格式并保存到B端
      const bEndAnalysis = DataAdapter.convertAnalysisToBEndFormat(analysis)
      await BEndApiService.saveAnalysis(bEndAnalysis, currentSessionId)

      // 触发B端系统的后续处理
      triggerWorkflow(bEndAnalysis)

      // 显示成功提示
      showNotification('AI分析已保存到患者记录')

    } catch (error) {
      console.error('保存分析结果失败:', error)
      showNotification('保存失败，请重试', 'error')
    }
  }

  // 处理消息发送
  const handleMessageSend = async (message: string) => {
    try {
      // 记录消息到B端日志
      await BEndApiService.logMessage({
        content: message,
        session_id: currentSessionId,
        user_id: getCurrentUserId(),
        timestamp: new Date().toISOString(),
        message_type: 'doctor_input'
      })

      // 更新B端UI状态
      updateConsultationStatus('ai_processing')

    } catch (error) {
      console.error('记录消息失败:', error)
    }
  }

  // 触发B端工作流
  const triggerWorkflow = (analysis: any) => {
    // 根据分析结果触发不同工作流
    if (analysis.risk_level === 'high') {
      // 触发紧急处理工作流
      initiateEmergencyProtocol(analysis)
    } else if (analysis.risk_level === 'medium') {
      // 触发常规处理工作流
      initiateStandardProtocol(analysis)
    }

    // 更新患者状态
    updatePatientStatus(analysis)
  }

  return (
    <div className="b-end-integration">
      {/* B端系统主要内容 */}
      <div className="main-content">
        <h1>患者诊疗系统</h1>

        {/* 其他B端功能 */}
        <div className="patient-info">
          <h2>患者信息</h2>
          {/* 患者信息展示 */}
        </div>

        <div className="medical-records">
          <h2>诊疗记录</h2>
          {/* 诊疗记录展示 */}
        </div>
      </div>

      {/* AI问答组件集成 */}
      <div className="ai-assistant-section">
        <button
          onClick={() => setIsChatVisible(!isChatVisible)}
          className="toggle-chat-btn"
        >
          {isChatVisible ? '隐藏' : '显示'} AI助手
        </button>

        {isChatVisible && (
          <div className="chat-container">
            <EmbeddedChat
              apiEndpoint="https://api.neuromatrix.ai/v1"
              userToken={authToken}
              sessionId={currentSessionId}
              userId={getCurrentUserId()}
              onAnalysisComplete={handleAnalysisComplete}
              onMessageSend={handleMessageSend}
              placeholder="请描述患者的症状、检查结果..."
              theme="auto"
              className="integrated-chat"
              showCloseButton={true}
              onClose={() => setIsChatVisible(false)}
            />
          </div>
        )}
      </div>

      {/* 集成样式 */}
      <style jsx>{`
        .b-end-integration {
          display: flex;
          height: 100vh;
        }

        .main-content {
          flex: 1;
          padding: 20px;
        }

        .ai-assistant-section {
          width: 400px;
          border-left: 1px solid #e5e7eb;
          padding: 20px;
          background: #f9fafb;
        }

        .toggle-chat-btn {
          width: 100%;
          padding: 10px;
          background: #3b82f6;
          color: white;
          border: none;
          border-radius: 6px;
          cursor: pointer;
          margin-bottom: 20px;
        }

        .chat-container {
          height: calc(100vh - 100px);
        }

        .integrated-chat {
          height: 100%;
          border: 1px solid #e5e7eb;
          border-radius: 8px;
        }
      `}</style>
    </div>
  )
}

// 工具函数
function getCurrentUserId(): string {
  // 从B端系统获取当前用户ID
  return localStorage.getItem('userId') || 'anonymous'
}

function showNotification(message: string, type: 'success' | 'error' = 'success') {
  // B端系统的通知显示逻辑
  console.log(`${type}: ${message}`)
}

function updateConsultationStatus(status: string) {
  // 更新B端会诊状态
  console.log('更新会诊状态:', status)
}

function initiateEmergencyProtocol(analysis: any) {
  // 触发紧急处理协议
  console.log('触发紧急处理协议:', analysis)
}

function initiateStandardProtocol(analysis: any) {
  // 触发标准处理协议
  console.log('触发标准处理协议:', analysis)
}

function updatePatientStatus(analysis: any) {
  // 更新患者状态
  console.log('更新患者状态:', analysis)
}

export default BEndIntegrationExample