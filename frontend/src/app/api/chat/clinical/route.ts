/**
 * Next.js API 路由：医学问诊对话
 * 集成百川 M3、Supabase 会话管理、Prompt 工程
 */

import { NextRequest, NextResponse } from 'next/server'
import { createBaichuanClient, BaichuanMessage } from '@/lib/baichuan-client'
import { createSessionManager, PatientContext } from '@/lib/session-manager'
import {
  SYSTEM_PROMPT,
  buildPrompt,
  addDisclaimerToResponse,
} from '@/lib/prompt-engineer'

export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

// 验证环境变量
function validateEnv() {
  const required = [
    'BAICHUAN_API_KEY',
    'BAICHUAN_API_URL',
  ]

  const missing = required.filter((key) => !process.env[key])
  if (missing.length > 0) {
    throw new Error(
      `Missing required environment variables: ${missing.join(', ')}`
    )
  }
}

interface ChatRequestBody {
  sessionId: string
  question: string
  patientContext?: PatientContext
  userId?: string
  images?: string[]
  enableWebSearch?: boolean
  enableKnowledgeBase?: boolean
}

interface ChatStreamChunk {
  type: 'content' | 'done' | 'error'
  data?: string
  error?: string
}

/**
 * POST /api/chat/clinical
 * 医学问诊对话端点
 *
 * 请求体：
 * {
 *   sessionId: string - 会话 ID
 *   question: string - 医生提问
 *   patientContext?: PatientContext - 患者信息
 *   userId?: string - 用户 ID
 * }
 */
export async function POST(req: NextRequest) {
  try {
    validateEnv()

    const body = (await req.json()) as ChatRequestBody
    const {
      sessionId,
      question,
      patientContext,
      userId,
      images,
      enableWebSearch,
      enableKnowledgeBase,
    } = body

    if (!sessionId || !question) {
      return NextResponse.json(
        {
          error: 'Missing required fields: sessionId, question',
        },
        { status: 400 }
      )
    }

    // 初始化管理器
    const baichuanClient = createBaichuanClient(
      process.env.BAICHUAN_API_KEY!,
      process.env.BAICHUAN_SECRET_KEY || '',
      process.env.BAICHUAN_API_URL!
    )

    const sessionManager = createSessionManager(
      process.env.SUPABASE_URL || 'http://localhost:54321',
      process.env.SUPABASE_ANON_KEY || 'sk-test-key'
    )

    // 获取或创建会话
    let session = await sessionManager.getSession(sessionId)

    if (!session) {
      if (!patientContext) {
        return NextResponse.json(
          {
            error:
              'New session requires patientContext',
          },
          { status: 400 }
        )
      }

      // 创建新会话，使用客户端提供的 sessionId
      session = await sessionManager.createSession(
        patientContext.patientId,
        patientContext,
        undefined,
        userId,
        sessionId
      )
    } else if (patientContext) {
      // 如果提供了新的患者信息，更新会话
      await sessionManager.updatePatientContext(sessionId, patientContext)
      session.patientContext = {
        ...session.patientContext,
        ...patientContext,
      }
    }

    // 获取会话消息历史
    const messages = await sessionManager.getMessages(sessionId)

    // 处理上传的医学影像
    let imageAnalysisText = ''
    if (images && images.length > 0) {
      try {
        // 动态导入图像分析模块（避免 Node.js 环境问题）
        const { analyzeImages, formatImageAnalysisForPrompt } = await import(
          '@/lib/image-analyzer'
        )
        
        const analysisResults = await analyzeImages(images)
        
        if (analysisResults.length > 0) {
          imageAnalysisText = formatImageAnalysisForPrompt(analysisResults)
          console.log(`Successfully analyzed ${analysisResults.length} images`)
        }
        
      } catch (imageError) {
        console.warn('Image processing failed, continuing with text analysis:', imageError)
        // 继续处理，即使图像分析失败
      }
    }

    // 保存用户提问到会话
    await sessionManager.addMessage(sessionId, {
      role: 'user',
      content: question,
    })

    // 构建完整的 Prompt，包含图像信息提示
    const fullPrompt = buildPrompt(
      session.patientContext,
      messages,
      question + imageAnalysisText
    )

    // 构建发送给百川的消息
    const baichuanMessages: BaichuanMessage[] = [
      {
        role: 'system',
        content: SYSTEM_PROMPT,
      },
      {
        role: 'user',
        content: fullPrompt,
      },
    ]

    // 调用百川 M3 API
    let aiResponse = ''
    let searchResults: any[] | undefined = undefined
    let knowledgeResults: any[] | undefined = undefined

    try {
      // 检查 Accept 头是否支持流式响应
      const acceptHeader = req.headers.get('accept')
      const supportsStream =
        acceptHeader?.includes('text/event-stream') ||
        acceptHeader?.includes('application/json')

      if (supportsStream && acceptHeader?.includes('text/event-stream')) {
        // 流式响应
        return new NextResponse(
          new ReadableStream({
            async start(controller) {
              try {
                // 流式获取 AI 响应
                for await (const chunk of baichuanClient.sendMessageStream(
                  baichuanMessages
                )) {
                  aiResponse += chunk
                  const event = `data: ${JSON.stringify({
                    type: 'content',
                    data: chunk,
                  })}\n\n`
                  controller.enqueue(new TextEncoder().encode(event))
                }

                // 添加完整响应到会话
                const responseWithDisclaimer =
                  addDisclaimerToResponse(aiResponse)
                await sessionManager.addMessage(sessionId, {
                  role: 'assistant',
                  content: responseWithDisclaimer,
                })

                // 发送完成信号
                const doneEvent = `data: ${JSON.stringify({
                  type: 'done',
                })}\n\n`
                controller.enqueue(
                  new TextEncoder().encode(doneEvent)
                )
                controller.close()
              } catch (error) {
                console.error('Stream error:', error)
                const errorEvent = `data: ${JSON.stringify({
                  type: 'error',
                  error: error instanceof Error ? error.message : 'Unknown error',
                })}\n\n`
                controller.enqueue(
                  new TextEncoder().encode(errorEvent)
                )
                controller.close()
              }
            },
          }),
          {
            status: 200,
            headers: {
              'Content-Type': 'text/event-stream',
              'Cache-Control': 'no-cache',
              'Connection': 'keep-alive',
            },
          }
        )
      } else {
        // 非流式响应，使用带搜索的API
        const response = await baichuanClient.sendMessageWithSearch(
          baichuanMessages,
          {
            enableWebSearch: enableWebSearch ?? false,
            enableKnowledgeBase: enableKnowledgeBase ?? false,
            searchCount: 5,
            topK: 5,
          }
        )

        if (!response.choices || response.choices.length === 0) {
          throw new Error('No response from Baichuan API')
        }

        aiResponse = response.choices[0].message.content || ''
        searchResults = response.searchResults
        knowledgeResults = response.knowledgeResults
        
        const responseWithDisclaimer =
          addDisclaimerToResponse(aiResponse)

        // 保存 AI 响应到会话
        await sessionManager.addMessage(sessionId, {
          role: 'assistant',
          content: responseWithDisclaimer,
        })

        // 构建返回数据
        const responseData: any = {
          success: true,
          sessionId,
          message: {
            role: 'assistant',
            content: responseWithDisclaimer,
            timestamp: new Date().toISOString(),
          },
          usage: response.usage,
        }

        // 如果有搜索结果，添加到响应中
        if (searchResults && searchResults.length > 0) {
          responseData.searchResults = searchResults
        }

        if (knowledgeResults && knowledgeResults.length > 0) {
          responseData.knowledgeResults = knowledgeResults
        }

        return NextResponse.json(responseData, { status: 200 })
      }
    } catch (baichuanError) {
      console.error('Baichuan API error:', baichuanError)

      // 如果 Baichuan 失败，返回错误信息
      const errorMessage = `抱歉，AI 服务暂时无法使用。请稍后重试。\n\n错误信息: ${baichuanError instanceof Error ? baichuanError.message : 'Unknown error'}`

      return NextResponse.json(
        {
          success: false,
          sessionId,
          error: errorMessage,
          timestamp: new Date().toISOString(),
        },
        { status: 500 }
      )
    }
  } catch (error) {
    console.error('Chat API error:', error)
    return NextResponse.json(
      {
        error: error instanceof Error ? error.message : 'Internal server error',
      },
      { status: 500 }
    )
  }
}

/**
 * GET /api/chat/clinical
 * 获取会话信息
 */
export async function GET(req: NextRequest) {
  try {
    validateEnv()

    const searchParams = req.nextUrl.searchParams
    const sessionId = searchParams.get('sessionId')

    if (!sessionId) {
      return NextResponse.json(
        { error: 'Missing sessionId parameter' },
        { status: 400 }
      )
    }

    const sessionManager = createSessionManager(
      process.env.SUPABASE_URL!,
      process.env.SUPABASE_ANON_KEY!
    )

    const session = await sessionManager.getSession(sessionId)

    if (!session) {
      return NextResponse.json(
        { error: 'Session not found' },
        { status: 404 }
      )
    }

    return NextResponse.json(
      {
        success: true,
        session: {
          id: session.id,
          title: session.title,
          status: session.status,
          messagesCount: session.messages.length,
          createdAt: session.createdAt,
          updatedAt: session.updatedAt,
          patientContext: {
            patientId: session.patientContext.patientId,
            name: session.patientContext.name,
            age: session.patientContext.age,
            // 不包含敏感信息
          },
        },
      },
      { status: 200 }
    )
  } catch (error) {
    console.error('Get session error:', error)
    return NextResponse.json(
      {
        error: error instanceof Error ? error.message : 'Internal server error',
      },
      { status: 500 }
    )
  }
}
