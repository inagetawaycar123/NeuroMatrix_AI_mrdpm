'use client'

import { useState, useEffect } from 'react'
import { Sidebar } from '@/components/Sidebar'
import { MainChat } from '@/components/MainChat'
import { SafetyPanel } from '@/components/SafetyPanel'

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

export default function Home() {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeConversationId, setActiveConversationId] = useState<string>('')
  const [isInitialized, setIsInitialized] = useState(false)

  // 初始化默认对话 - 只在组件首次加载时执行
  useEffect(() => {
    if (!isInitialized && conversations.length === 0) {
      const defaultConversation: Conversation = {
        id: 'default',
        title: '新对话',
        messages: [],
        analysisHistory: []
      }
      setConversations([defaultConversation])
      setActiveConversationId('default')
      setIsInitialized(true)
    }
  }, [isInitialized, conversations.length])

  const activeConversation = conversations.find(c => c.id === activeConversationId)

  const handleNewConversation = () => {
    const newId = Date.now().toString()
    const newConversation: Conversation = {
      id: newId,
      title: '新对话',
      messages: [],
      analysisHistory: []
    }
    setConversations(prev => [...prev, newConversation])
    setActiveConversationId(newId)
  }

  // 传递analysis更新函数给MainChat
  const handleAnalysisUpdate = (analysis: any) => {
    // analysis更新由MainChat组件直接处理，这里不需要额外逻辑
  }

  // 删除对话
  const handleDeleteConversation = (id: string) => {
    if (window.confirm('确定要删除这个对话吗？')) {
      setConversations(prev => prev.filter(c => c.id !== id))

      // 如果删除的是当前活跃对话，切换到第一个对话
      if (activeConversationId === id) {
        const remainingConversations = conversations.filter(c => c.id !== id)
        if (remainingConversations.length > 0) {
          setActiveConversationId(remainingConversations[0].id)
        } else {
          // 如果没有对话了，创建一个新的
          handleNewConversation()
        }
      }
    }
  }

  return (
    <div className="min-h-screen bg-black text-white flex">
      <Sidebar
        conversations={conversations}
        activeId={activeConversationId}
        onSelectConversation={setActiveConversationId}
        onNewConversation={handleNewConversation}
        onDeleteConversation={handleDeleteConversation}
      />
      <MainChat
        conversation={activeConversation}
        onUpdateConversation={(updated) => {
          setConversations(prev => {
            // 创建全新的conversations数组，确保React能检测到状态变化
            return prev.map(c => c.id === updated.id ? updated : c)
          })
        }}
        onAnalysisUpdate={handleAnalysisUpdate}
      />
      <SafetyPanel analysisHistory={activeConversation?.analysisHistory || []} />
    </div>
  )
}