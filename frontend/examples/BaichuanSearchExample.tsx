/**
 * 百川搜索功能示例组件
 * 展示如何在前端使用知识检索和网页搜索
 */

'use client'

import { useState } from 'react'

interface SearchResult {
  title: string
  url: string
  snippet: string
  publishTime?: string
}

interface KnowledgeResult {
  id: string
  title: string
  content: string
  source: string
  relevance: number
}

export default function BaichuanSearchExample() {
  const [query, setQuery] = useState('')
  const [searchType, setSearchType] = useState<'web' | 'knowledge' | 'both'>('web')
  const [loading, setLoading] = useState(false)
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [knowledgeResults, setKnowledgeResults] = useState<KnowledgeResult[]>([])
  const [error, setError] = useState<string | null>(null)

  const handleSearch = async () => {
    if (!query.trim()) {
      setError('请输入搜索关键词')
      return
    }

    setLoading(true)
    setError(null)
    setSearchResults([])
    setKnowledgeResults([])

    try {
      const response = await fetch('/api/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query,
          type: searchType,
          limit: 5,
        }),
      })

      const data = await response.json()

      if (data.success) {
        setSearchResults(data.results.webSearch || [])
        setKnowledgeResults(data.results.knowledgeBase || [])
      } else {
        setError(data.error || '搜索失败')
      }
    } catch (err) {
      setError('网络错误，请稍后重试')
      console.error('Search error:', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">百川知识检索和网页搜索</h1>

      {/* 搜索输入区 */}
      <div className="bg-white shadow-md rounded-lg p-6 mb-6">
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            搜索关键词
          </label>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="例如：脑卒中最新治疗方法"
            className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            搜索类型
          </label>
          <div className="flex gap-4">
            <label className="flex items-center">
              <input
                type="radio"
                value="web"
                checked={searchType === 'web'}
                onChange={(e) => setSearchType(e.target.value as any)}
                className="mr-2"
              />
              网页搜索
            </label>
            <label className="flex items-center">
              <input
                type="radio"
                value="knowledge"
                checked={searchType === 'knowledge'}
                onChange={(e) => setSearchType(e.target.value as any)}
                className="mr-2"
              />
              知识库检索
            </label>
            <label className="flex items-center">
              <input
                type="radio"
                value="both"
                checked={searchType === 'both'}
                onChange={(e) => setSearchType(e.target.value as any)}
                className="mr-2"
              />
              混合搜索
            </label>
          </div>
        </div>

        <button
          onClick={handleSearch}
          disabled={loading}
          className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? '搜索中...' : '开始搜索'}
        </button>

        {error && (
          <div className="mt-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
            {error}
          </div>
        )}
      </div>

      {/* 网页搜索结果 */}
      {searchResults.length > 0 && (
        <div className="bg-white shadow-md rounded-lg p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4 flex items-center">
            <span className="mr-2">🌐</span>
            网页搜索结果 ({searchResults.length})
          </h2>
          <div className="space-y-4">
            {searchResults.map((result, index) => (
              <div key={index} className="border-l-4 border-blue-500 pl-4 py-2">
                <a
                  href={result.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-lg font-medium text-blue-600 hover:underline"
                >
                  {result.title}
                </a>
                <p className="text-sm text-gray-600 mt-1">{result.snippet}</p>
                {result.publishTime && (
                  <p className="text-xs text-gray-400 mt-1">
                    发布时间: {result.publishTime}
                  </p>
                )}
                <p className="text-xs text-gray-400 mt-1">{result.url}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 知识库检索结果 */}
      {knowledgeResults.length > 0 && (
        <div className="bg-white shadow-md rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4 flex items-center">
            <span className="mr-2">📚</span>
            知识库检索结果 ({knowledgeResults.length})
          </h2>
          <div className="space-y-4">
            {knowledgeResults.map((result, index) => (
              <div
                key={index}
                className="border-l-4 border-green-500 pl-4 py-2"
              >
                <h3 className="text-lg font-medium text-gray-900">
                  {result.title}
                </h3>
                <p className="text-sm text-gray-700 mt-2">{result.content}</p>
                <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                  <span>来源: {result.source}</span>
                  <span>
                    相关性: {(result.relevance * 100).toFixed(1)}%
                  </span>
                  <span>ID: {result.id}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 使用说明 */}
      <div className="mt-8 bg-gray-50 rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-3">💡 使用说明</h3>
        <ul className="space-y-2 text-sm text-gray-700">
          <li>• <strong>网页搜索</strong>：实时搜索互联网最新信息</li>
          <li>• <strong>知识库检索</strong>：从预设知识库中检索专业知识</li>
          <li>• <strong>混合搜索</strong>：同时使用两种方式，获得更全面的结果</li>
          <li>• 搜索结果会按相关性排序</li>
          <li>• 支持中文和医学术语搜索</li>
        </ul>

        <h3 className="text-lg font-semibold mt-6 mb-3">🔧 API调用示例</h3>
        <pre className="bg-gray-800 text-gray-100 p-4 rounded text-xs overflow-x-auto">
{`// 基础搜索
const response = await fetch('/api/search', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query: '脑卒中治疗',
    type: 'web',
    limit: 5
  })
})

// 在临床问诊中使用
const response = await fetch('/api/chat/clinical', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    sessionId: 'session_123',
    question: '如何诊断急性卒中？',
    enableWebSearch: true,
    enableKnowledgeBase: true
  })
})`}
        </pre>
      </div>
    </div>
  )
}
