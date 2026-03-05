import { useState, useEffect } from 'react'
import { ArrowLeft, Plus, History, MessageSquare, ChevronDown, ChevronUp, X, Search, FileText } from 'lucide-react'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { useRouter } from 'next/navigation'

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

interface SidebarProps {
  conversations: Conversation[]
  activeId: string
  onSelectConversation: (id: string) => void
  onNewConversation: () => void
  onDeleteConversation: (id: string) => void
  onShowHistory?: () => void
}

export function Sidebar({ conversations, activeId, onSelectConversation, onNewConversation, onDeleteConversation, onShowHistory }: SidebarProps) {
  const router = useRouter()
  const [isExpanded, setIsExpanded] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [highlightedId, setHighlightedId] = useState<string | null>(null)
  const maxVisibleConversations = 5
  const maxExpandedConversations = 10

  // 反转对话顺序，最新的在前面
  const reversedConversations = [...conversations].reverse()

  // 搜索过滤逻辑
  const filteredConversations = searchQuery
    ? reversedConversations.filter(conversation =>
        conversation.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        conversation.messages.some(msg =>
          msg.content?.toLowerCase().includes(searchQuery.toLowerCase())
        )
      )
    : reversedConversations

  // 显示的对话列表
  const visibleConversations = searchQuery
    ? filteredConversations  // 搜索模式：显示搜索结果
    : showHistory
      ? reversedConversations  // 历史对话：显示所有
      : isExpanded
        ? reversedConversations.slice(0, Math.min(maxExpandedConversations, reversedConversations.length))  // 展开：显示更多
        : reversedConversations.slice(0, maxVisibleConversations)  // 默认：显示最近的几个

  const hasMoreConversations = conversations.length > maxVisibleConversations
  const hasManyConversations = conversations.length > maxExpandedConversations

  // 搜索时自动切换到历史模式并高亮结果
  useEffect(() => {
    if (searchQuery) {
      setShowHistory(true)
      setIsExpanded(false)
      // 如果只有一个搜索结果，自动高亮它
      if (filteredConversations.length === 1) {
        setHighlightedId(filteredConversations[0].id)
        // 自动选择唯一的搜索结果
        onSelectConversation(filteredConversations[0].id)
      } else {
        setHighlightedId(null)
      }
    } else {
      setHighlightedId(null)
    }
  }, [searchQuery, filteredConversations, onSelectConversation])
  return (
    <div className="w-64 bg-gray-900 border-r border-gray-700 flex flex-col">
      {/* 顶部功能按钮 */}
      <div className="p-4 border-b border-gray-700">
        <div className="flex flex-col gap-2">
          <Button className="justify-start text-white hover:bg-gray-800 bg-transparent">
            <ArrowLeft className="w-4 h-4 mr-2" />
            返回
          </Button>
          <Button
            className="justify-start text-white hover:bg-gray-800 bg-transparent"
            onClick={onNewConversation}
          >
            <Plus className="w-4 h-4 mr-2" />
            新对话
          </Button>
          <Button
            className={`justify-start text-white hover:bg-gray-800 bg-transparent ${showHistory ? 'bg-gray-800' : ''}`}
            onClick={() => {
              setShowHistory(!showHistory)
              if (!showHistory) setIsExpanded(false)  // 进入历史模式时收起展开状态
            }}
          >
            <History className="w-4 h-4 mr-2" />
            历史对话
          </Button>
          <Button
            className="justify-start text-white hover:bg-gray-800 bg-transparent"
            onClick={() => router.push('/reports')}
          >
            <FileText className="w-4 h-4 mr-2" />
            报告查询
          </Button>
        </div>
      </div>

      {/* 搜索框 */}
      <div className="p-4 border-b border-gray-700">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="搜索对话..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="flex-1 pl-10 bg-gray-800 border border-gray-600 rounded-md text-white placeholder-gray-400 text-sm h-9 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          {searchQuery && (
            <button
              className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-white"
              onClick={() => {
                setSearchQuery('')
                setShowHistory(false)
                setHighlightedId(null)
              }}
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* 最近对话列表 */}
      <div className="flex-1 p-4 min-h-0">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-medium text-gray-400">
            {searchQuery ? `搜索结果 (${filteredConversations.length})` : showHistory ? '所有对话' : '最近对话'}
          </h3>
          {!searchQuery && !showHistory && hasMoreConversations && (
            <button
              className="h-6 w-6 p-0 text-gray-400 hover:text-white bg-transparent border-none cursor-pointer flex items-center justify-center"
              onClick={() => setIsExpanded(!isExpanded)}
            >
              {isExpanded ? (
                <ChevronUp className="w-4 h-4" />
              ) : (
                <ChevronDown className="w-4 h-4" />
              )}
            </button>
          )}
          {!searchQuery && showHistory && (
            <button
              className="h-6 w-6 p-0 text-gray-400 hover:text-white bg-transparent border-none cursor-pointer flex items-center justify-center"
              onClick={() => setShowHistory(false)}
              title="返回最近对话"
            >
              <ChevronUp className="w-4 h-4" />
            </button>
          )}
        </div>
        <div className="max-h-96 overflow-y-auto space-y-2">
          {visibleConversations.map((conversation) => (
            <div
              key={conversation.id}
              className={`p-3 rounded-lg cursor-pointer transition-all group ${
                conversation.id === activeId
                  ? 'bg-blue-600 shadow-lg'
                  : conversation.id === highlightedId
                    ? 'bg-yellow-600 shadow-lg animate-pulse'
                    : 'bg-gray-800 hover:bg-gray-700'
              }`}
              onClick={() => onSelectConversation(conversation.id)}
            >
              <div className="flex items-center gap-2">
                <MessageSquare className="w-4 h-4 flex-shrink-0" />
                <span className="text-sm truncate flex-1">{conversation.title}</span>
                <button
                  className="opacity-0 group-hover:opacity-100 w-5 h-5 flex items-center justify-center text-gray-400 hover:text-red-400 hover:bg-gray-600 rounded transition-all"
                  onClick={(e) => {
                    e.stopPropagation()
                    onDeleteConversation(conversation.id)
                  }}
                  title="删除对话"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            </div>
          ))}
          {!searchQuery && !showHistory && hasMoreConversations && !isExpanded && (
            <div className="text-center py-2">
              <span className="text-xs text-gray-500">
                还有 {conversations.length - maxVisibleConversations} 个对话...
              </span>
            </div>
          )}
          {!searchQuery && showHistory && hasManyConversations && (
            <div className="text-center py-2">
              <span className="text-xs text-gray-500">
                显示所有 {conversations.length} 个对话
              </span>
            </div>
          )}
          {searchQuery && filteredConversations.length === 0 && (
            <div className="text-center py-2">
              <span className="text-xs text-gray-500">
                未找到包含 "{searchQuery}" 的对话
              </span>
            </div>
          )}
          {searchQuery && filteredConversations.length > 0 && (
            <div className="text-center py-2">
              <span className="text-xs text-gray-500">
                找到 {filteredConversations.length} 个相关对话
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}