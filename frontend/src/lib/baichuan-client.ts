/**
 * 百川 M3 API 客户端
 * 处理鉴权、签名、请求/响应、Token 刷新
 */

import { createHash } from 'crypto'

interface BaichuanConfig {
  apiKey: string
  secretKey: string
  apiUrl: string
  model?: string
}

interface BaichuanMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
}

interface BaichuanRequestBody {
  model: string
  messages: BaichuanMessage[]
  temperature?: number
  top_p?: number
  max_tokens?: number
  stream?: boolean
}

interface BaichuanResponse {
  id: string
  object: string
  created: number
  model: string
  choices: Array<{
    index: number
    message: BaichuanMessage
    finish_reason: string
  }>
  usage: {
    prompt_tokens: number
    completion_tokens: number
    total_tokens: number
    search_count?: number
  }
}

/**
 * 网页搜索结果
 */
interface SearchResult {
  title: string
  url: string
  snippet: string
  publishTime?: string
}

/**
 * 知识检索结果
 */
interface KnowledgeResult {
  id: string
  title: string
  content: string
  source: string
  relevance: number
  metadata?: Record<string, any>
}

/**
 * 搜索和知识检索选项
 */
interface SearchOptions {
  enableWebSearch?: boolean
  enableKnowledgeBase?: boolean
  searchCount?: number
  topK?: number
}

/**
 * 带搜索结果的消息请求体
 */
interface BaichuanSearchRequestBody extends BaichuanRequestBody {
  tools?: Array<{
    type: 'web_search' | 'knowledge_base'
    enabled: boolean
  }>
  search_options?: SearchOptions
}

/**
 * 百川 M3 API 客户端
 */
export class BaichuanClient {
  private config: BaichuanConfig
  private accessToken: string | null = null
  private tokenExpireTime: number = 0
  private searchResults: SearchResult[] = []
  private knowledgeResults: KnowledgeResult[] = []

  constructor(config: BaichuanConfig) {
    this.config = {
      model: 'Baichuan3-Turbo',
      ...config,
    }
  }

  /**
   * 生成签名
   * 百川 API 使用 MD5(用户密钥 + 时间戳 + 次数) 的方式进行签名
   */
  private generateSignature(timestamp: string, nonce: string): string {
    const signStr = `${this.config.secretKey}${timestamp}${nonce}`
    return createHash('md5').update(signStr).digest('hex')
  }

  /**
   * 执行网页搜索
   * @param query 搜索词
   * @param limit 返回结果数量
   */
  async webSearch(query: string, limit: number = 5): Promise<SearchResult[]> {
    try {
      const token = await this.getAccessToken()

      // 使用百川API的tools参数来启用网页搜索
      const requestBody = {
        model: this.config.model!,
        messages: [
          {
            role: 'user' as const,
            content: query
          }
        ],
        tools: [
          {
            type: 'web_search' as const,
            web_search: {
              enable: true,
              search_mode: 'performance_first' // 或 'quality_first'
            }
          }
        ]
      }

      const response = await fetch(
        `${this.config.apiUrl}/chat/completions`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
            'X-BC-Request-Id': `${Date.now()}`,
          },
          body: JSON.stringify(requestBody),
        }
      )

      if (!response.ok) {
        console.warn(`Web search failed: ${response.status}`)
        return []
      }

      const data = await response.json()
      
      // 提取搜索结果
      const toolCalls = data.choices?.[0]?.message?.tool_calls || []
      const searchResults: SearchResult[] = []
      
      for (const toolCall of toolCalls) {
        if (toolCall.type === 'web_search' && toolCall.web_search?.search_result) {
          const results = toolCall.web_search.search_result
          for (const result of results.slice(0, limit)) {
            searchResults.push({
              title: result.title || '',
              url: result.link || '',
              snippet: result.content || '',
              publishTime: result.publish_time
            })
          }
        }
      }
      
      this.searchResults = searchResults
      return this.searchResults
    } catch (error) {
      console.error('Error performing web search:', error)
      return []
    }
  }

  /**
   * 查询知识库
   * @param query 查询词
   * @param topK 返回结果数量
   */
  async queryKnowledgeBase(query: string, topK: number = 5): Promise<KnowledgeResult[]> {
    try {
      const token = await this.getAccessToken()
      const kbId = process.env.BAICHUAN_KNOWLEDGE_BASE_ID || process.env.NEXT_PUBLIC_BAICHUAN_KNOWLEDGE_BASE_ID

      if (!kbId) {
        console.warn('知识库ID未配置')
        return []
      }

      // 根据文档，使用tools.retrieval参数进行知识库检索
      // 文档链接: https://platform.baichuan-ai.com/docs/knowledgeBase 第13部分
      const requestBody = {
        model: this.config.model!,
        messages: [
          {
            role: 'user' as const,
            content: query
          }
        ],
        tools: [
          {
            type: 'retrieval' as const,
            retrieval: {
              kb_ids: [kbId]  // 使用kb_ids数组而不是单个knowledge_base_id
            }
          }
        ]
      }

      const response = await fetch(
        `${this.config.apiUrl}/chat/completions`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
            'X-BC-Request-Id': `${Date.now()}`,
          },
          body: JSON.stringify(requestBody),
        }
      )

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        console.warn(`Knowledge base query failed: ${response.status}`, errorData)
        return []
      }

      const data = await response.json()
      
      // 百川API返回的知识库结果包含在响应中
      const content = data.choices?.[0]?.message?.content || ''
      const knowledgeBase = data.knowledge_base
      
      // 构建结果
      const knowledgeResults: KnowledgeResult[] = []
      
      // 检查是否有知识库引用信息
      if (knowledgeBase && knowledgeBase.cites && Array.isArray(knowledgeBase.cites)) {
        for (const cite of knowledgeBase.cites.slice(0, topK)) {
          knowledgeResults.push({
            id: cite.file_id || `kb_${Date.now()}`,
            title: cite.title || 'Untitled',
            content: cite.content || '',
            source: 'knowledge_base',
            relevance: 0.8,
            metadata: { file_id: cite.file_id }
          })
        }
      }
      
      // 如果没有直接的cites字段，从content中创建结果
      if (knowledgeResults.length === 0 && content) {
        knowledgeResults.push({
          id: `kb_${Date.now()}`,
          title: '知识库回复',
          content: content,
          source: 'knowledge_base',
          relevance: 1.0,
          metadata: { raw_response: true }
        })
      }
      
      this.knowledgeResults = knowledgeResults
      return this.knowledgeResults
    } catch (error) {
      console.error('Error querying knowledge base:', error)
      return []
    }
  }

  /**
   * 获取 Access Token
   * 直接返回 API Key 作为 token
   */
  async getAccessToken(): Promise<string> {
    // 百川 M3 API 直接使用 API Key 作为 Bearer token
    return this.config.apiKey
  }

  /**
   * 发送聊天消息到百川 M3（带搜索支持）
   */
  async sendMessageWithSearch(
    messages: BaichuanMessage[],
    searchOptions?: SearchOptions,
    options?: {
      temperature?: number
      top_p?: number
      max_tokens?: number
      stream?: boolean
    }
  ): Promise<BaichuanResponse & { searchResults?: SearchResult[]; knowledgeResults?: KnowledgeResult[] }> {
    try {
      const token = await this.getAccessToken()

      // 构建tools参数
      const tools: any[] = []
      
      if (searchOptions?.enableWebSearch) {
        tools.push({
          type: 'web_search',
          web_search: {
            enable: true,
            search_mode: 'performance_first'
          }
        })
      }

      if (searchOptions?.enableKnowledgeBase) {
        const kbId = process.env.BAICHUAN_KNOWLEDGE_BASE_ID || process.env.NEXT_PUBLIC_BAICHUAN_KNOWLEDGE_BASE_ID
        if (kbId) {
          tools.push({
            type: 'retrieval',
            retrieval: {
              kb_ids: [kbId]  // 使用kb_ids数组
            }
          })
        }
      }

      // 构建请求体
      const requestBody: any = {
        model: this.config.model!,
        messages,
        temperature: options?.temperature ?? 0.7,
        top_p: options?.top_p ?? 0.95,
        max_tokens: options?.max_tokens ?? 2000,
        stream: options?.stream ?? false,
      }

      // 只有在启用了搜索或知识库时才添加tools参数
      if (tools.length > 0) {
        requestBody.tools = tools
      }

      const response = await fetch(
        `${this.config.apiUrl}/chat/completions`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
            'X-BC-Request-Id': `${Date.now()}`,
          },
          body: JSON.stringify(requestBody),
        }
      )

      if (!response.ok) {
        throw new Error(
          `Baichuan API error: ${response.status} ${response.statusText}`
        )
      }

      const data = (await response.json()) as BaichuanResponse
      if (!data.choices || data.choices.length === 0) {
        throw new Error(`Baichuan error: No choices in response`)
      }

      // 提取搜索结果和知识库结果
      const searchResults: SearchResult[] = []
      const knowledgeResults: KnowledgeResult[] = []
      
      const toolCalls = (data.choices[0].message as any).tool_calls || []
      
      for (const toolCall of toolCalls) {
        if (toolCall.type === 'web_search' && toolCall.web_search?.search_result) {
          const results = toolCall.web_search.search_result
          for (const result of results) {
            searchResults.push({
              title: result.title || '',
              url: result.link || '',
              snippet: result.content || '',
              publishTime: result.publish_time
            })
          }
        }
        
        if (toolCall.type === 'retrieval' && toolCall.retrieval?.documents) {
          const docs = toolCall.retrieval.documents
          for (const doc of docs) {
            knowledgeResults.push({
              id: doc.id || `doc_${Date.now()}`,
              title: doc.title || 'Untitled',
              content: doc.content || '',
              source: doc.source || 'knowledge_base',
              relevance: doc.score || 0,
              metadata: doc.metadata
            })
          }
        }
      }

      return {
        ...data,
        searchResults: searchResults.length > 0 ? searchResults : undefined,
        knowledgeResults: knowledgeResults.length > 0 ? knowledgeResults : undefined,
      }
    } catch (error) {
      console.error('Error sending message with search:', error)
      throw error
    }
  }

  /**
   * 发送聊天消息到百川 M3
   */
  async sendMessage(
    messages: BaichuanMessage[],
    options?: {
      temperature?: number
      top_p?: number
      max_tokens?: number
      stream?: boolean
    }
  ): Promise<BaichuanResponse> {
    try {
      const token = await this.getAccessToken()

      const requestBody: BaichuanRequestBody = {
        model: this.config.model!,
        messages,
        temperature: options?.temperature ?? 0.7,
        top_p: options?.top_p ?? 0.95,
        max_tokens: options?.max_tokens ?? 2000,
        stream: options?.stream ?? false,
      }

      const response = await fetch(
        `${this.config.apiUrl}/chat/completions`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
            'X-BC-Request-Id': `${Date.now()}`,
          },
          body: JSON.stringify(requestBody),
        }
      )

      if (!response.ok) {
        throw new Error(
          `Baichuan API error: ${response.status} ${response.statusText}`
        )
      }

      const data = (await response.json()) as BaichuanResponse
      if (!data.choices || data.choices.length === 0) {
        throw new Error(`Baichuan error: No choices in response`)
      }

      return data
    } catch (error) {
      console.error('Error sending message to Baichuan:', error)
      throw error
    }
  }

  /**
   * 流式发送聊天消息
   * 用于实时显示 AI 回答的打字效果
   */
  async *sendMessageStream(
    messages: BaichuanMessage[],
    options?: {
      temperature?: number
      top_p?: number
      max_tokens?: number
    }
  ): AsyncGenerator<string, void, unknown> {
    try {
      const token = await this.getAccessToken()

      const requestBody: BaichuanRequestBody = {
        model: this.config.model!,
        messages,
        temperature: options?.temperature ?? 0.7,
        top_p: options?.top_p ?? 0.95,
        max_tokens: options?.max_tokens ?? 2000,
        stream: true,
      }

      const response = await fetch(
        `${this.config.apiUrl}/chat/completions`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
            'X-BC-Request-Id': `${Date.now()}`,
          },
          body: JSON.stringify(requestBody),
        }
      )

      if (!response.ok) {
        throw new Error(
          `Baichuan API error: ${response.status} ${response.statusText}`
        )
      }

      if (!response.body) {
        throw new Error('No response body for streaming')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()

      try {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          const chunk = decoder.decode(value)
          const lines = chunk.split('\n')

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6).trim()
              if (data && data !== '[DONE]') {
                try {
                  const parsed = JSON.parse(data)
                  const content = parsed.choices?.[0]?.delta?.content
                  if (content) {
                    yield content
                  }
                } catch (e) {
                  // 忽略 JSON 解析错误
                  console.error('Error parsing stream data:', e)
                }
              }
            }
          }
        }
      } finally {
        reader.releaseLock()
      }
    } catch (error) {
      console.error('Error in streaming message:', error)
      throw error
    }
  }

  /**
   * 验证 API 连接
   */
  async healthCheck(): Promise<boolean> {
    try {
      const token = await this.getAccessToken()
      return !!token
    } catch (error) {
      console.error('Health check failed:', error)
      return false
    }
  }

  /**
   * 获取最后的搜索结果
   */
  getLastSearchResults(): SearchResult[] {
    return this.searchResults
  }

  /**
   * 获取最后的知识库查询结果
   */
  getLastKnowledgeResults(): KnowledgeResult[] {
    return this.knowledgeResults
  }

  /**
   * 清除搜索缓存
   */
  clearSearchCache(): void {
    this.searchResults = []
    this.knowledgeResults = []
  }
}

/**
 * 创建百川客户端的工厂函数
 */
export function createBaichuanClient(
  apiKey: string,
  secretKey: string,
  apiUrl: string
): BaichuanClient {
  return new BaichuanClient({
    apiKey,
    secretKey,
    apiUrl,
  })
}

export type { BaichuanMessage, BaichuanRequestBody, BaichuanResponse, SearchResult, KnowledgeResult, SearchOptions }
