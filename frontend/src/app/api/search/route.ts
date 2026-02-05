/**
 * Next.js API 路由：知识检索和网页搜索
 * 提供独立的搜索功能接口
 */

import { NextRequest, NextResponse } from 'next/server'
import { createBaichuanClient } from '@/lib/baichuan-client'

export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

// 验证环境变量
function validateEnv() {
  const required = ['BAICHUAN_API_KEY']
  const missing = required.filter((key) => !process.env[key])
  
  if (missing.length > 0) {
    throw new Error(
      `Missing required environment variables: ${missing.join(', ')}`
    )
  }
}

interface SearchRequestBody {
  query: string
  type: 'web' | 'knowledge' | 'both'
  limit?: number
}

/**
 * POST /api/search
 * 执行搜索（网页搜索或知识库检索）
 *
 * 请求体：
 * {
 *   query: string - 搜索关键词
 *   type: 'web' | 'knowledge' | 'both' - 搜索类型
 *   limit?: number - 返回结果数量（默认5）
 * }
 */
export async function POST(req: NextRequest) {
  try {
    validateEnv()

    const body = (await req.json()) as SearchRequestBody
    const { query, type, limit = 5 } = body

    if (!query) {
      return NextResponse.json(
        { error: 'Missing required field: query' },
        { status: 400 }
      )
    }

    if (!type || !['web', 'knowledge', 'both'].includes(type)) {
      return NextResponse.json(
        { error: 'Invalid type. Must be "web", "knowledge", or "both"' },
        { status: 400 }
      )
    }

    // 初始化百川客户端
    const baichuanClient = createBaichuanClient(
      process.env.BAICHUAN_API_KEY!,
      process.env.BAICHUAN_SECRET_KEY || '',
      process.env.BAICHUAN_API_URL!
    )

    let searchResults: any[] = []
    let knowledgeResults: any[] = []

    try {
      // 执行网页搜索
      if (type === 'web' || type === 'both') {
        searchResults = await baichuanClient.webSearch(query, limit)
      }

      // 执行知识库检索
      if (type === 'knowledge' || type === 'both') {
        knowledgeResults = await baichuanClient.queryKnowledgeBase(
          query,
          limit
        )
      }

      return NextResponse.json(
        {
          success: true,
          query,
          type,
          results: {
            webSearch:
              searchResults.length > 0 ? searchResults : undefined,
            knowledgeBase:
              knowledgeResults.length > 0
                ? knowledgeResults
                : undefined,
          },
          timestamp: new Date().toISOString(),
        },
        { status: 200 }
      )
    } catch (searchError) {
      console.error('Search error:', searchError)

      return NextResponse.json(
        {
          success: false,
          error:
            searchError instanceof Error
              ? searchError.message
              : 'Search failed',
          query,
          type,
        },
        { status: 500 }
      )
    }
  } catch (error) {
    console.error('Search API error:', error)
    return NextResponse.json(
      {
        error:
          error instanceof Error
            ? error.message
            : 'Internal server error',
      },
      { status: 500 }
    )
  }
}

/**
 * GET /api/search
 * 快速测试搜索功能
 */
export async function GET(req: NextRequest) {
  try {
    validateEnv()

    const searchParams = req.nextUrl.searchParams
    const query = searchParams.get('query') || '卒中治疗'
    const type = (searchParams.get('type') || 'web') as
      | 'web'
      | 'knowledge'
      | 'both'

    // 初始化百川客户端
    const baichuanClient = createBaichuanClient(
      process.env.BAICHUAN_API_KEY!,
      process.env.BAICHUAN_SECRET_KEY || '',
      process.env.BAICHUAN_API_URL!
    )

    let searchResults: any[] = []
    let knowledgeResults: any[] = []

    try {
      // 执行网页搜索
      if (type === 'web' || type === 'both') {
        searchResults = await baichuanClient.webSearch(query, 3)
      }

      // 执行知识库检索
      if (type === 'knowledge' || type === 'both') {
        knowledgeResults = await baichuanClient.queryKnowledgeBase(
          query,
          3
        )
      }

      return NextResponse.json(
        {
          success: true,
          query,
          type,
          results: {
            webSearch:
              searchResults.length > 0 ? searchResults : undefined,
            knowledgeBase:
              knowledgeResults.length > 0
                ? knowledgeResults
                : undefined,
          },
          timestamp: new Date().toISOString(),
        },
        { status: 200 }
      )
    } catch (searchError) {
      console.error('Search error:', searchError)

      return NextResponse.json(
        {
          success: false,
          error:
            searchError instanceof Error
              ? searchError.message
              : 'Search failed',
          query,
          type,
        },
        { status: 500 }
      )
    }
  } catch (error) {
    console.error('Search API GET error:', error)
    return NextResponse.json(
      {
        error:
          error instanceof Error
            ? error.message
            : 'Internal server error',
      },
      { status: 500 }
    )
  }
}
