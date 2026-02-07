'use client'

import { useState, useRef, useEffect } from 'react'
import { Send, Loader2, MessageCircle, X, ChevronDown, ChevronUp } from 'lucide-react'

interface MedicalAIChatProps {
  /**
   * 是否显示聊天组件
   */
  isVisible: boolean
  /**
   * 关闭回调
   */
  onClose: () => void
  /**
   * 用户ID
   */
  userId?: string
  /**
   * 会话ID
   */
  sessionId?: string
  /**
   * 自定义样式类名
   */
  className?: string
}

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

interface Conversation {
  id: string
  messages: Message[]
}

export const MedicalAIChat: React.FC<MedicalAIChatProps> = ({
  isVisible,
  onClose,
  userId = 'default-user',
  sessionId = `session-${Date.now()}`,
  className = ''
}) => {
  const [conversation, setConversation] = useState<Conversation>({
    id: sessionId,
    messages: []
  })
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isMinimized, setIsMinimized] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // 滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [conversation.messages])

  // 消息发送处理
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!input.trim() || isLoading) return

    const userMessage: Message = {
      id: `msg-${Date.now()}-user`,
      role: 'user',
      content: input.trim(),
      timestamp: new Date()
    }

    // 添加用户消息
    setConversation(prev => ({
      ...prev,
      messages: [...prev.messages, userMessage]
    }))

    setInput('')
    setIsLoading(true)

    let aiMessageId: string | null = null

    try {
      aiMessageId = `msg-${Date.now()}-ai`
      const aiMessage: Message = {
        id: aiMessageId,
        role: 'assistant',
        content: '',
        timestamp: new Date()
      }

      setConversation(prev => ({
        ...prev,
        messages: [...prev.messages, aiMessage]
      }))

      const response = await fetch('/api/chat/clinical/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          sessionId: conversation.id,
          question: userMessage.content,
          patientContext: {
            patientId: conversation.id,
            name: 'Patient',
            age: 65,
            medicalHistory: [],
            currentDiagnosis: 'Consultation'
          }
        }),
      })

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`)
      }

      if (!response.body) {
        throw new Error('Streaming response not supported')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''

      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        const events = buffer.split('\n\n')
        buffer = events.pop() || ''

        for (const event of events) {
          const lines = event.split('\n')
          for (const line of lines) {
            if (!line.startsWith('data:')) continue
            const dataStr = line.slice(5).trim()
            if (!dataStr || dataStr === '[DONE]') continue

            let payload: { type?: string; content?: string; error?: string } | null = null
            try {
              payload = JSON.parse(dataStr)
            } catch {
              payload = null
            }

            if (!payload) continue
            if (payload.type === 'delta' && payload.content) {
              const delta = payload.content
              setConversation(prev => ({
                ...prev,
                messages: prev.messages.map(msg =>
                  msg.id === aiMessageId
                    ? { ...msg, content: msg.content + delta }
                    : msg
                )
              }))
            }

            if (payload.type === 'error' && payload.error) {
              setConversation(prev => ({
                ...prev,
                messages: prev.messages.map(msg =>
                  msg.id === aiMessageId
                    ? { ...msg, content: msg.content + `\n\n错误：${payload.error}` }
                    : msg
                )
              }))
            }
          }
        }
      }
    } catch (error) {
      console.error('Chat error:', error)

      if (aiMessageId) {
        setConversation(prev => ({
          ...prev,
          messages: prev.messages.filter(message => message.id !== aiMessageId)
        }))
      }
      
      const errorMessage: Message = {
        id: `msg-${Date.now()}-error`,
        role: 'assistant',
        content: `抱歉，系统出现错误：\n\n${error instanceof Error ? error.message : '连接失败，请检查网络和API配置'}`,
        timestamp: new Date()
      }

      setConversation(prev => ({
        ...prev,
        messages: [...prev.messages, errorMessage]
      }))
    } finally {
      setIsLoading(false)
    }
  }

  if (!isVisible) return null

  return (
    <div className={`fixed right-4 bottom-4 z-50 w-80 md:w-96 bg-gray-900 border border-gray-700 rounded-lg shadow-xl flex flex-col ${className}`}>
      {/* 头部 */}
      <div className="flex items-center justify-between p-4 border-b border-gray-700 bg-gray-800">
        <div className="flex items-center gap-2">
          <MessageCircle className="w-5 h-5 text-blue-500" />
          <h3 className="font-semibold text-white">NeuroMatrix AI 医生助手</h3>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsMinimized(!isMinimized)}
            className="p-1 hover:bg-gray-700 rounded"
            title={isMinimized ? '最大化' : '最小化'}
          >
            {isMinimized ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
          </button>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-700 rounded"
            title="关闭"
          >
            <X className="w-4 h-4 text-gray-400" />
          </button>
        </div>
      </div>

      {!isMinimized && (
        <>
          {/* 消息区域 */}
          <div className="flex-1 p-4 overflow-y-auto max-h-[400px]">
            <div className="space-y-4">
              {conversation.messages.length === 0 && (
                <div className="text-center text-gray-500 py-8">
                  <MessageCircle className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p className="text-sm">我是NeuroMatrix AI医生助手</p>
                  <p className="text-xs mt-1">专注于脑卒中影像分析，请描述您的临床问题</p>
                </div>
              )}

              {conversation.messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[80%] p-3 rounded-lg ${message.role === 'user' 
                      ? 'bg-blue-600 text-white' 
                      : 'bg-gray-800 text-gray-200 border border-gray-700'
                    }`}
                  >
                    <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                    <p className="text-xs mt-1 opacity-70">
                      {message.timestamp.toLocaleTimeString()}
                    </p>
                  </div>
                </div>
              ))}

              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-gray-800 p-3 rounded-lg border border-gray-700">
                    <div className="flex items-center gap-2">
                      <Loader2 className="w-4 h-4 animate-spin text-blue-400" />
                      <span className="text-sm text-gray-400">AI正在思考...</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
            <div ref={messagesEndRef} />
          </div>

          {/* 输入区域 */}
          <div className="p-4 border-t border-gray-700 bg-gray-800">
            <form onSubmit={handleSubmit} className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="输入您的临床问题..."
                disabled={isLoading}
                className="flex-1 px-3 py-2 bg-gray-900 border border-gray-700 rounded-md text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                type="submit"
                disabled={!input.trim() || isLoading}
                className="p-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
              </button>
            </form>
            <p className="text-xs text-gray-500 mt-2">
              支持脑卒中诊断、CTP参数解读、治疗方案建议等专业问题
            </p>
          </div>
        </>
      )}

      {isMinimized && (
        <div className="p-3 border-t border-gray-700">
          <button
            onClick={() => setIsMinimized(false)}
            className="w-full flex items-center justify-center gap-2 py-2 hover:bg-gray-800 rounded"
          >
            <MessageCircle className="w-4 h-4 text-blue-500" />
            <span className="text-sm text-gray-400">NeuroMatrix AI 助手</span>
          </button>
        </div>
      )}
    </div>
  )
}

export default MedicalAIChat