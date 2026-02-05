'use client'

import { useState, useRef, useEffect } from 'react'
import { useChat } from 'ai/react'
import { ScrollArea } from '@radix-ui/react-scroll-area'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Send, Image, X, Loader2 } from 'lucide-react'

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

interface MainChatProps {
  conversation?: Conversation
  onUpdateConversation: (conversation: Conversation) => void
  onAnalysisUpdate?: (analysis: any) => void
}

export function MainChat({ conversation, onUpdateConversation, onAnalysisUpdate }: MainChatProps) {
  // 生成对话标题的函数
  const generateTitle = (messages: any[]) => {
    const firstUserMessage = messages.find(m => m.role === 'user')?.content
    if (firstUserMessage) {
      return firstUserMessage.substring(0, 20) + (firstUserMessage.length > 20 ? '...' : '')
    }
    return '新对话'
  }

  // 生成分析的函数 - 根据对话内容智能分析
  const generateAnalysis = (messages: any[]) => {
    console.log('generateAnalysis called with messages:', messages)

    if (messages.length > 0) {
      const latestMessage = messages[messages.length - 1]
      console.log('Generating analysis for message:', latestMessage)

      // 检查消息内容是否包含医疗关键词
      const medicalAnalysis = analyzeMedicalContent(latestMessage?.content || '')
      console.log('Medical analysis result:', medicalAnalysis)

      if (medicalAnalysis) {
        const analysisResult = {
          id: Date.now().toString(),
          risks: medicalAnalysis.risks,
          keypoints: medicalAnalysis.keypoints,
          triggerMessage: {
            id: latestMessage?.id || Date.now().toString(),
            content: latestMessage?.content || '医疗相关消息',
            timestamp: new Date().toISOString()
          },
          timestamp: new Date().toISOString()
        }
        console.log('Generated analysis:', analysisResult)
        return analysisResult
      } else {
        // 非医疗消息，不生成分析
        console.log('No medical analysis generated - not a medical message')
        return null
      }
    }

    return null
  }

  // 智能分析医疗内容的函数
  const analyzeMedicalContent = (content: string) => {
    console.log('Analyzing content:', content)
    const hasStroke = /卒中|stroke|中风|脑梗|脑出血|缺血性|出血性/i.test(content)
    const hasCardiac = /心脏|心梗|心肌梗死|心律失常|心力衰竭/i.test(content)
    const hasRespiratory = /呼吸|肺炎|哮喘|呼吸衰竭|肺部/i.test(content)
    const hasNeurological = /神经|癫痫|帕金森|阿尔茨海默/i.test(content)
    const hasTrauma = /创伤|骨折|外伤|事故/i.test(content)
    const hasInfection = /感染|发热|炎症|败血症/i.test(content)
    const hasCancer = /肿瘤|癌症|恶性|癌/i.test(content)

    console.log('Medical content analysis:', {
      hasStroke, hasCardiac, hasRespiratory, hasNeurological,
      hasTrauma, hasInfection, hasCancer
    })

    if (hasStroke) {
      return {
        risks: [
          { level: 'high' as const, description: '急性脑卒中风险', suggestion: '立即评估NIHSS评分，考虑急诊溶栓治疗' },
          { level: 'medium' as const, description: '并发症风险', suggestion: '监测血压、血糖，预防肺炎和深静脉血栓' }
        ],
        keypoints: ['神经功能评估', '生命体征监测', '实验室检查', '影像学检查', '早期康复']
      }
    }

    if (hasCardiac) {
      return {
        risks: [
          { level: 'high' as const, description: '心血管事件风险', suggestion: '立即心电图检查，评估心肌标志物' },
          { level: 'medium' as const, description: '心力衰竭风险', suggestion: '控制血压和心率，监测体液平衡' }
        ],
        keypoints: ['心电图检查', '心肌标志物检测', '超声心动图', '血压监测', '药物治疗']
      }
    }

    if (hasRespiratory) {
      return {
        risks: [
          { level: 'high' as const, description: '呼吸衰竭风险', suggestion: '立即评估呼吸频率和血氧饱和度' },
          { level: 'medium' as const, description: '感染扩散风险', suggestion: '隔离措施，抗感染治疗' }
        ],
        keypoints: ['呼吸功能评估', '血气分析', '胸部X线', '痰培养', '氧疗支持']
      }
    }

    if (hasNeurological) {
      return {
        risks: [
          { level: 'medium' as const, description: '神经功能恶化风险', suggestion: '定期神经功能评估，调整治疗方案' },
          { level: 'medium' as const, description: '并发症风险', suggestion: '预防肺炎和压疮，康复训练' }
        ],
        keypoints: ['神经系统检查', '脑电图', 'MRI检查', '康复评估', '药物治疗']
      }
    }

    if (hasTrauma) {
      return {
        risks: [
          { level: 'high' as const, description: '休克风险', suggestion: '立即评估ABCDE，维持生命体征稳定' },
          { level: 'medium' as const, description: '感染风险', suggestion: '伤口处理，预防破伤风' }
        ],
        keypoints: ['创伤评估', 'X线检查', 'CT扫描', '伤口处理', '疼痛管理']
      }
    }

    if (hasInfection) {
      return {
        risks: [
          { level: 'high' as const, description: '败血症风险', suggestion: '立即抗感染治疗，监测生命体征' },
          { level: 'medium' as const, description: '多器官衰竭风险', suggestion: '支持治疗，器官功能监测' }
        ],
        keypoints: ['体温监测', '血培养', '抗感染治疗', '支持治疗', '感染源控制']
      }
    }

    if (hasCancer) {
      return {
        risks: [
          { level: 'medium' as const, description: '肿瘤进展风险', suggestion: '定期肿瘤标志物监测，影像学随访' },
          { level: 'medium' as const, description: '治疗副作用风险', suggestion: '监测血常规，调整治疗方案' }
        ],
        keypoints: ['肿瘤标志物检测', '影像学检查', '病理检查', '多学科讨论', '姑息治疗']
      }
    }

    // 如果没有识别到特定疾病，但包含医疗关键词
    if (/疼痛|不适|症状|诊断|治疗|检查|药物/i.test(content)) {
      return {
        risks: [
          { level: 'medium' as const, description: '临床评估需求', suggestion: '完善病史采集和体格检查' }
        ],
        keypoints: ['症状评估', '体格检查', '辅助检查', '诊断分析', '治疗建议']
      }
    }

    // 如果不包含医疗关键词，不显示安全卡
    return null
  }

  // 使用外部conversation的消息
  const messages = conversation?.messages || []
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)


  // 图片预览状态 - 支持多个图片
  interface FileInfo {
    data: string
    type: string
    name: string
    isPDF: boolean
  }
  const [selectedImages, setSelectedImages] = useState<(string | FileInfo)[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleInputChangeLocal = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInput(e.target.value)
  }

  const handleSubmitLocal = async (e: React.FormEvent) => {
    e.preventDefault()
    
    // 验证是否有输入或图片
    const hasInput = input.trim().length > 0
    const hasImages = selectedImages.length > 0
    
    if (!hasInput && !hasImages) {
      console.warn('❌ 提交失败: 必须输入问题或上传文件')
      return
    }

    if (!conversation) {
      console.warn('❌ 提交失败: 会话不存在')
      return
    }

    // 问题必须有输入
    if (!hasInput) {
      console.warn('❌ 提交失败: 必须输入医学问题')
      return
    }

    setIsLoading(true)

    // 创建用户消息，包含文字和图片
    const userMessage = {
      role: 'user',
      content: input.trim(),
      images: selectedImages.length > 0 ? selectedImages : undefined
    }
    const updatedMessages = [...messages, userMessage]

    // 生成新的analysis
    const newAnalysis = generateAnalysis(updatedMessages)

    // 更新对话（用户消息）
    const updatedHistory = newAnalysis
      ? [...(conversation.analysisHistory || []), newAnalysis]
      : (conversation.analysisHistory || [])

    const tempConversation = {
      ...conversation,
      messages: updatedMessages,
      title: conversation.title === '新对话' ? generateTitle(updatedMessages) : conversation.title,
      analysisHistory: updatedHistory
    }
    onUpdateConversation(tempConversation)


    // 清空输入和选中的图片
    const questionText = input.trim()
    setInput('')
    const imagesToSend = selectedImages
      .map(file => {
        // 支持新格式 {data, type, name, isPDF} 和旧格式 (直接字符串)
        if (typeof file === 'string') {
          return file
        } else if (file && typeof file === 'object' && 'data' in file) {
          return file.data
        }
        return null
      })
      .filter(data => data) // 过滤掉undefined/null
    setSelectedImages([])

    try {
      // 调用医学问诊 API
      console.log('📤 准备发送API请求:', {
        sessionId: conversation.id,
        question: questionText,
        imagesCount: imagesToSend.length
      })

      const response = await fetch('/api/chat/clinical/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          sessionId: conversation.id,
          question: questionText,
          images: imagesToSend,
          patientContext: {
            patientId: conversation.id,
            name: 'Patient',
            age: 65,
            medicalHistory: [],
            currentDiagnosis: 'Consultation'
          }
        }),
      })

      console.log('📡 API响应状态:', response.status, response.statusText)

      if (!response.ok) {
        const errorText = await response.text()
        console.error('API错误响应:', errorText)
        throw new Error(`API error: ${response.status} - ${errorText}`)
      }

      const data = await response.json()
      console.log('✅ API返回数据:', data)
      
      if (!data.success) {
        throw new Error(data.error || 'API request failed')
      }
      const aiMessage = { role: 'assistant', content: data.message.content }

      // 更新对话（包含AI响应）
      const finalMessages = [...updatedMessages, aiMessage]
      const finalConversation = {
        ...conversation,
        messages: finalMessages,
        title: conversation.title === '新对话' ? generateTitle(finalMessages) : conversation.title,
        analysisHistory: tempConversation.analysisHistory
      }
      onUpdateConversation(finalConversation)
    } catch (error) {
      console.error('❌ Chat错误:', error)
      console.error('错误详情:', error instanceof Error ? error.message : String(error))
      
      // 显示错误信息给用户
      const errorMessage = error instanceof Error ? error.message : '连接失败，请检查网络和API配置'
      const mockAIMessage = {
        role: 'assistant',
        content: `⚠️ 抱歉，系统出现错误：\n\n${errorMessage}\n\n请检查：\n1. API端点是否正确\n2. Baichuan API密钥是否有效\n3. 网络连接是否正常`
      }
      const finalMessages = [...updatedMessages, mockAIMessage]
      const finalConversation = {
        ...conversation,
        messages: finalMessages,
        analysisHistory: updatedHistory
      }
      onUpdateConversation(finalConversation)
    } finally {
      setIsLoading(false)
    }
  }

  const handleImageUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files
    if (files) {
      Array.from(files).forEach(file => {
        const reader = new FileReader()
        reader.onload = (e) => {
          const fileData = e.target?.result as string
          // 存储文件数据和类型信息
          const fileInfo = {
            data: fileData,
            type: file.type,
            name: file.name,
            isPDF: file.type === 'application/pdf'
          }
          setSelectedImages(prev => [...prev, fileInfo as any])
        }
        reader.readAsDataURL(file)
      })
    }
    // 重置文件输入
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const removeImage = (index: number) => {
    setSelectedImages(prev => prev.filter((_, i) => i !== index))
  }

  return (
    <div className="flex-1 flex flex-col bg-black">
      {/* 顶部标题栏 */}
      <div className="h-16 bg-gray-900 border-b border-gray-700 flex items-center px-6">
        <h1 className="text-xl font-semibold text-white">NeuroMatrix AI 医生助手</h1>
      </div>

      {/* 对话区域 - 医学严谨风格 */}
      <ScrollArea className="flex-1">
        <div className="max-w-4xl mx-auto p-4 space-y-3">
          {messages.length === 0 && (
            <div className="text-center text-gray-400 py-8">
              <div className="text-5xl mb-3">🩺</div>
              <h3 className="text-lg font-medium mb-2">NeuroMatrix AI 医生助手</h3>
              <p className="text-sm">上传CTP灌注图或输入临床问题，开始AI分析</p>
            </div>
          )}

          {messages.map((message, index) => (
            <div key={index} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-3xl rounded-lg px-4 py-3 ${
                message.role === 'user'
                  ? 'bg-blue-600 text-white ml-8'
                  : 'bg-gray-800 text-white mr-8 border border-gray-700'
              }`}>
                {message.role === 'assistant' ? (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center">
                        <span className="text-white text-xs font-bold">AI</span>
                      </div>
                      <span className="text-gray-300 text-xs">NeuroMatrix AI</span>
                    </div>

                    {/* 临床分析文本 */}
                    <div className="text-sm leading-relaxed text-gray-200">
                      {message.content}
                    </div>
                  </div>
                ) : (
                  <div className="flex items-start gap-2">
                    <div className="w-6 h-6 bg-gray-600 rounded-full flex items-center justify-center">
                      <span className="text-white text-xs font-bold">我</span>
                    </div>
                    <div className="flex-1 space-y-2">
                      {/* 显示多个图片如果存在 */}
                      {message.images && message.images.length > 0 && (
                        <div className="flex flex-wrap gap-2">
                          {message.images.map((image: string, imgIndex: number) => (
                            <div key={imgIndex} className="w-20 h-20 flex-shrink-0">
                              <img
                                src={image}
                                alt={`上传的医学影像 ${imgIndex + 1}`}
                                className="w-full h-full object-cover rounded border border-gray-600"
                              />
                            </div>
                          ))}
                        </div>
                      )}
                      {/* 显示文本内容 */}
                      {message.content && <p className="text-sm leading-relaxed">{message.content}</p>}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}

          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-gray-800 rounded-lg px-4 py-3 mr-8 border border-gray-700">
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center">
                    <span className="text-white text-xs font-bold">AI</span>
                  </div>
                  <div className="flex space-x-1">
                    <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce"></div>
                    <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                    <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </ScrollArea>

      {/* 输入区域 */}
      <div className="p-4 bg-gray-900 border-t border-gray-700">
        {/* 图片预览区域 */}
        {selectedImages.length > 0 && (
          <div className="mb-4 max-w-4xl mx-auto">
            <div className="flex flex-wrap gap-2 p-3 bg-gray-800 rounded-lg border border-gray-600">
              {selectedImages.map((file, index) => (
                <div key={index} className="relative group">
                  <div className="w-16 h-16 rounded border border-gray-500 overflow-hidden bg-gray-700 flex items-center justify-center">
                    {(typeof file === 'object' && file !== null && 'isPDF' in file && file.isPDF) ? (
                      <div className="flex flex-col items-center justify-center text-xs text-white">
                        <div className="text-lg font-bold">PDF</div>
                        <div className="truncate max-w-12 text-gray-300 text-[10px]">{(file as any).name?.split('.')[0]}</div>
                      </div>
                    ) : (
                      <img
                        src={typeof file === 'string' ? file : (file as any).data}
                        alt={`预览 ${index + 1}`}
                        className="w-full h-full object-cover"
                      />
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={() => removeImage(index)}
                    className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 hover:bg-red-600 text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        <form onSubmit={handleSubmitLocal} className="flex gap-3 max-w-4xl mx-auto">
          <input
            type="file"
            accept="image/*,.pdf"
            multiple
            onChange={handleImageUpload}
            ref={fileInputRef}
            className="hidden"
          />
          <Button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            size="icon"
            className="bg-gray-700 hover:bg-gray-600"
          >
            <Image className="w-4 h-4" />
          </Button>
          <input
            type="text"
            value={input}
            onChange={handleInputChangeLocal}
            placeholder="输入您的临床问题..."
            className="flex-1 px-3 py-2 bg-gray-800 border border-gray-600 rounded-md text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={isLoading}
          />
          <Button type="submit" size="icon" disabled={isLoading} className="bg-blue-600 hover:bg-blue-700">
            <Send className="w-4 h-4" />
          </Button>
        </form>
      </div>
    </div>
  )
}