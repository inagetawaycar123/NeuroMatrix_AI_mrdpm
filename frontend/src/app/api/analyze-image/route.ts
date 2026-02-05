import { NextRequest } from 'next/server'

export async function POST(req: NextRequest) {
  try {
    const body = await req.json()

    // 调用Flask后端的影像分析API
    const flaskResponse = await fetch('http://localhost:5000/api/analyze-image', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    })

    if (!flaskResponse.ok) {
      throw new Error(`Flask API error: ${flaskResponse.status}`)
    }

    const data = await flaskResponse.json()
    return new Response(JSON.stringify(data), {
      headers: {
        'Content-Type': 'application/json',
      },
    })
  } catch (error) {
    console.error('Analyze image API error:', error)
    return new Response(JSON.stringify({
      error: 'Failed to analyze image',
      details: error instanceof Error ? error.message : 'Unknown error',
    }), {
      status: 500,
      headers: {
        'Content-Type': 'application/json',
      },
    })
  }
}