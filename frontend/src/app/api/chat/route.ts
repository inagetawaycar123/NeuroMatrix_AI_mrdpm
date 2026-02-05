import { NextRequest } from 'next/server'

export const dynamic = 'force-dynamic'

export async function POST(req: NextRequest) {
  try {
    const body = await req.json()
    const { messages, session_id, user_id } = body

    // 获取认证信息
    const authHeader = req.headers.get('authorization')
    const sessionId = req.headers.get('x-session-id') || session_id
    const userId = req.headers.get('x-user-id') || user_id

    // 调用后端API
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:5000'
    const requestBody: any = { messages }

    // 如果有会话和用户ID，添加到请求体
    if (sessionId) requestBody.session_id = sessionId
    if (userId) requestBody.user_id = userId

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    }

    // 如果有认证头，转发给后端
    if (authHeader) {
      headers['Authorization'] = authHeader
    }

    const backendResponse = await fetch(`${backendUrl}/api/chat`, {
      method: 'POST',
      headers,
      body: JSON.stringify(requestBody),
    })

    // 如果后端不可用，返回模拟响应（用于B端集成测试）
    if (!backendResponse.ok) {
      console.warn(`Backend API unavailable (${backendResponse.status}), using fallback response`)

      // 基于关键词提供基础响应
      const lastMessage = messages[messages.length - 1]?.content?.toLowerCase() || ''
      let fallbackResponse = '我是NeuroMatrix AI医生助手。请描述您的临床问题，我将为您提供专业建议。'

      if (lastMessage.includes('卒中') || lastMessage.includes('stroke')) {
        fallbackResponse = '基于您的描述，这可能涉及脑卒中相关问题。建议立即进行临床评估，包括NIHSS评分和影像检查。'
      } else if (lastMessage.includes('cbf') || lastMessage.includes('cbv') || lastMessage.includes('tmax')) {
        fallbackResponse = '关于CTP参数：CBF反映局部血流量，CBV反映血容量，Tmax反映达峰时间。这些参数对评估缺血半暗带有重要价值。'
      }

      return new Response(JSON.stringify({
        id: Date.now().toString(),
        object: 'chat.completion',
        created: Date.now(),
        model: 'neuromatrix-ai-fallback',
        choices: [{
          index: 0,
          message: {
            role: 'assistant',
            content: fallbackResponse,
          },
          finish_reason: 'stop',
        }],
        usage: {
          prompt_tokens: messages.length * 10,
          completion_tokens: fallbackResponse.length / 4,
          total_tokens: messages.length * 10 + fallbackResponse.length / 4,
        },
      }), {
        headers: {
          'Content-Type': 'application/json',
        },
      })
    }

    const backendData = await backendResponse.json()
    const response = backendData.response || '抱歉，后端服务无响应。'

    // 返回与ai/react兼容的格式
    return new Response(JSON.stringify({
      id: Date.now().toString(),
      object: 'chat.completion',
      created: Date.now(),
      model: 'neuromatrix-ai',
      choices: [{
        index: 0,
        message: {
          role: 'assistant',
          content: response,
        },
        finish_reason: 'stop',
      }],
      usage: {
        prompt_tokens: 0,
        completion_tokens: 0,
        total_tokens: 0,
      },
    }), {
      headers: {
        'Content-Type': 'application/json',
      },
    })
  } catch (error) {
    console.error('Chat API error:', error)

    // 返回友好的错误响应
    return new Response(JSON.stringify({
      id: Date.now().toString(),
      object: 'chat.completion',
      created: Date.now(),
      model: 'neuromatrix-ai-error',
      choices: [{
        index: 0,
        message: {
          role: 'assistant',
          content: '抱歉，服务暂时不可用。请稍后重试或联系技术支持。',
        },
        finish_reason: 'stop',
      }],
      usage: {
        prompt_tokens: 0,
        completion_tokens: 0,
        total_tokens: 0,
      },
    }), {
      status: 500,
      headers: {
        'Content-Type': 'application/json',
      },
    })
  }
}