'use client'

import { useState, useRef, useEffect } from 'react'
import { useChat } from 'ai/react'
import { ScrollArea } from '@radix-ui/react-scroll-area'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Send, Loader2, MessageCircle, X } from 'lucide-react'

interface EmbeddedChatProps {
  /**
   * API端点URL
   */
  apiEndpoint?: string
  /**
   * 用户认证token
   */
  userToken?: string
  /**
   * 会话ID
   */
  sessionId?: string
  /**
   * 用户ID
   */
  userId?: string
  /**
   * 分析完成回调
   */
  onAnalysisComplete?: (analysis: any) => void
  /**
   * 消息发送回调
   */
  onMessageSend?: (message: string) => void
  /**
   * 自定义样式类名
   */
  className?: string
  /**
   * 占位符文本
   */
  placeholder?: string
  /**
   * 是否显示关闭按钮
   */
  showCloseButton?: boolean
  /**
   * 关闭回调
   */
  onClose?: () => void
  /**
   * 主题配置
   */
  theme?: 'light' | 'dark' | 'auto'
}

interface Conversation {
  id: string
  title: string
  messages: any[]
  analysisHistory?: Array<{
    id: string
    risks: Array<{ level: 'high' | 'medium', description: string, suggestion: string }>
    keypoints: string[]
    triggerMessage?: {
      id: string
      content: string
      timestamp: string
    }
    timestamp: string
  }>
}

export function EmbeddedChat({
  apiEndpoint = '/api/chat',
  userToken,
  sessionId,
  userId,
  onAnalysisComplete,
  onMessageSend,
  className = '',
  placeholder = '输入您的医疗问题...',
  showCloseButton = false,
  onClose,
  theme = 'auto'
}: EmbeddedChatProps) {
  const [isMinimized, setIsMinimized] = useState(false)
  const [conversation, setConversation] = useState<Conversation | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // 初始化对话
  useEffect(() => {
    if (!conversation) {
      const defaultConversation: Conversation = {
        id: sessionId || 'embedded-session',
        title: '医疗问答',
        messages: [],
        analysisHistory: []
      }
      setConversation(defaultConversation)
    }
  }, [sessionId, conversation])

  // 聊天配置
  const chatConfig = {
    api: apiEndpoint,
    headers: userToken ? {
      'Authorization': `Bearer ${userToken}`,
      'X-Session-ID': sessionId || '',
      'X-User-ID': userId || ''
    } : undefined,
    onFinish: (message: any) => {
      // 处理分析完成
      if (onAnalysisComplete && message.analysis) {
        onAnalysisComplete(message.analysis)
      }
    }
  }

  const { messages, input, handleInputChange, handleSubmit, isLoading } = useChat(chatConfig)

  // 消息发送处理
  const handleFormSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (input.trim() && !isLoading) {
      onMessageSend?.(input.trim())
      handleSubmit(e)
    }
  }

  // 滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // 主题处理
  const getThemeClasses = () => {
    const baseClasses = 'embedded-chat border rounded-lg shadow-lg bg-white dark:bg-gray-800'
    if (theme === 'dark') return `${baseClasses} dark`
    if (theme === 'light') return baseClasses
    return baseClasses // auto theme
  }

  if (isMinimized) {
    return (
      <div className={`fixed bottom-4 right-4 z-50 ${getThemeClasses()} ${className}`}>
        <button
          onClick={() => setIsMinimized(false)}
          className="w-full p-3 flex items-center gap-2 hover:bg-gray-50 dark:hover:bg-gray-700 rounded-lg"
        >
          <MessageCircle className="w-5 h-5" />
          <span className="text-sm font-medium">医疗助手</span>
        </button>
      </div>
    )
  }

  return (
    <div className={`embedded-chat ${getThemeClasses()} ${className}`}>
      {/* 头部 */}
      <div className="flex items-center justify-between p-4 border-b dark:border-gray-700">
        <div className="flex items-center gap-2">
          <MessageCircle className="w-5 h-5 text-blue-600" />
          <h3 className="font-semibold text-gray-900 dark:text-white">NeuroMatrix AI助手</h3>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsMinimized(true)}
            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
            title="最小化"
          >
            <span className="text-xs">−</span>
          </button>
          {showCloseButton && (
            <button
              onClick={onClose}
              className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
              title="关闭"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* 消息区域 */}
      <ScrollArea className="h-96 p-4">
        <div className="space-y-4">
          {messages.length === 0 && (
            <div className="text-center text-gray-500 dark:text-gray-400 py-8">
              <MessageCircle className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p className="text-sm">我是NeuroMatrix AI医生助手</p>
              <p className="text-xs mt-1">专注于脑卒中影像分析，请描述您的临床问题</p>
            </div>
          )}

          {messages.map((message: any) => (
            <div
              key={message.id}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] p-3 rounded-lg ${
                  message.role === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white'
                }`}
              >
                <p className="text-sm whitespace-pre-wrap">{message.content}</p>
              </div>
            </div>
          ))}

          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-gray-100 dark:bg-gray-700 p-3 rounded-lg">
                <div className="flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span className="text-sm text-gray-600 dark:text-gray-300">AI正在思考...</span>
                </div>
              </div>
            </div>
          )}
        </div>
        <div ref={messagesEndRef} />
      </ScrollArea>

      {/* 输入区域 */}
      <div className="p-4 border-t dark:border-gray-700">
        <form onSubmit={handleFormSubmit} className="flex gap-2">
          <Input
            value={input}
            onChange={handleInputChange}
            placeholder={placeholder}
            disabled={isLoading}
            className="flex-1"
          />
          <Button
            type="submit"
            disabled={!input.trim() || isLoading}
            size="sm"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </Button>
        </form>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
          支持脑卒中诊断、CTP参数解读、治疗方案建议等专业问题
        </p>
      </div>
    </div>
  )
}

export default EmbeddedChat