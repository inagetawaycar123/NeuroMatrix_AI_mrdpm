/**
 * 会话管理模块
 * 处理会话创建、历史消息存储、患者上下文管理
 */

import { createClient, SupabaseClient } from '@supabase/supabase-js'

export interface PatientContext {
  patientId: string
  name?: string
  age?: number
  gender?: 'male' | 'female' | 'other'
  medicalHistory?: string
  currentDiagnosis?: string
  imagingData?: {
    cbf?: string // CBF 灌注图信息
    cbv?: string // CBV 灌注图信息
    tmax?: string // Tmax 灌注图信息
    otherImages?: string
  }
  clinicalScores?: {
    nihss?: number // NIHSS 评分
    mrs?: number // mRS 评分
    otherScores?: Record<string, number>
  }
  [key: string]: any // 其他自定义数据
}

export interface ChatMessage {
  id?: string
  role: 'user' | 'assistant'
  content: string
  timestamp?: string
  imageAttachment?: {
    url: string
    description?: string
    features?: string // AI 识别的特征
  }
}

export interface ChatSession {
  id: string
  patientId: string
  title: string
  doctorId?: string
  status: 'active' | 'archived' | 'closed'
  patientContext: PatientContext
  messages: ChatMessage[]
  createdAt: string
  updatedAt: string
  metadata?: Record<string, any>
}

/**
 * 会话管理器
 */
export class SessionManager {
  private supabase: SupabaseClient

  constructor(supabaseUrl: string, supabaseKey: string) {
    this.supabase = createClient(supabaseUrl, supabaseKey)
  }

  /**
   * 创建新的聊天会话
   */
  async createSession(
    patientId: string,
    patientContext: PatientContext,
    title?: string,
    doctorId?: string,
    sessionId?: string
  ): Promise<ChatSession> {
    const session: ChatSession = {
      id: sessionId || `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      patientId,
      title: title || `诊询-${new Date().toLocaleDateString('zh-CN')}`,
      doctorId,
      status: 'active',
      patientContext,
      messages: [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    }

    try {
      const { data, error } = await this.supabase
        .from('chat_sessions')
        .insert([
          {
            id: session.id,
            patient_id: patientId,
            title: session.title,
            doctor_id: doctorId,
            status: session.status,
            patient_context: patientContext,
            messages: [],
            created_at: session.createdAt,
            updated_at: session.updatedAt,
          },
        ])
        .select()
        .single()

      if (error) {
        console.error('Error creating session:', error)
        throw error
      }

      return session
    } catch (error) {
      console.error('Failed to create session:', error)
      throw error
    }
  }

  /**
   * 获取会话信息
   */
  async getSession(sessionId: string): Promise<ChatSession | null> {
    try {
      const { data, error } = await this.supabase
        .from('chat_sessions')
        .select('*')
        .eq('id', sessionId)
        .single()

      if (error) {
        if (error.code === 'PGRST116') {
          return null // 会话不存在
        }
        throw error
      }

      return {
        id: data.id,
        patientId: data.patient_id,
        title: data.title,
        doctorId: data.doctor_id,
        status: data.status,
        patientContext: data.patient_context,
        messages: data.messages || [],
        createdAt: data.created_at,
        updatedAt: data.updated_at,
        metadata: data.metadata,
      }
    } catch (error) {
      console.error('Error fetching session:', error)
      throw error
    }
  }

  /**
   * 添加消息到会话
   */
  async addMessage(
    sessionId: string,
    message: ChatMessage
  ): Promise<ChatMessage> {
    const completeMessage: ChatMessage = {
      id: `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date().toISOString(),
      ...message,
    }

    try {
      // 获取当前会话
      const session = await this.getSession(sessionId)
      if (!session) {
        throw new Error(`Session ${sessionId} not found`)
      }

      // 添加消息
      const updatedMessages = [...session.messages, completeMessage]

      // 更新会话
      const { error } = await this.supabase
        .from('chat_sessions')
        .update({
          messages: updatedMessages,
          updated_at: new Date().toISOString(),
        })
        .eq('id', sessionId)

      if (error) {
        throw error
      }

      return completeMessage
    } catch (error) {
      console.error('Error adding message:', error)
      throw error
    }
  }

  /**
   * 获取会话的所有消息
   */
  async getMessages(sessionId: string): Promise<ChatMessage[]> {
    try {
      const session = await this.getSession(sessionId)
      if (!session) {
        return []
      }
      return session.messages
    } catch (error) {
      console.error('Error fetching messages:', error)
      return []
    }
  }

  /**
   * 更新患者上下文
   */
  async updatePatientContext(
    sessionId: string,
    patientContext: Partial<PatientContext>
  ): Promise<void> {
    try {
      const session = await this.getSession(sessionId)
      if (!session) {
        throw new Error(`Session ${sessionId} not found`)
      }

      const updatedContext = {
        ...session.patientContext,
        ...patientContext,
      }

      const { error } = await this.supabase
        .from('chat_sessions')
        .update({
          patient_context: updatedContext,
          updated_at: new Date().toISOString(),
        })
        .eq('id', sessionId)

      if (error) {
        throw error
      }
    } catch (error) {
      console.error('Error updating patient context:', error)
      throw error
    }
  }

  /**
   * 存档会话
   */
  async archiveSession(sessionId: string): Promise<void> {
    try {
      const { error } = await this.supabase
        .from('chat_sessions')
        .update({
          status: 'archived',
          updated_at: new Date().toISOString(),
        })
        .eq('id', sessionId)

      if (error) {
        throw error
      }
    } catch (error) {
      console.error('Error archiving session:', error)
      throw error
    }
  }

  /**
   * 获取患者的所有会话
   */
  async getPatientSessions(patientId: string): Promise<ChatSession[]> {
    try {
      const { data, error } = await this.supabase
        .from('chat_sessions')
        .select('*')
        .eq('patient_id', patientId)
        .order('created_at', { ascending: false })

      if (error) {
        throw error
      }

      return (data || []).map((d) => ({
        id: d.id,
        patientId: d.patient_id,
        title: d.title,
        doctorId: d.doctor_id,
        status: d.status,
        patientContext: d.patient_context,
        messages: d.messages || [],
        createdAt: d.created_at,
        updatedAt: d.updated_at,
        metadata: d.metadata,
      }))
    } catch (error) {
      console.error('Error fetching patient sessions:', error)
      return []
    }
  }

  /**
   * 清空会话（不删除，仅清空消息）
   */
  async clearMessages(sessionId: string): Promise<void> {
    try {
      const { error } = await this.supabase
        .from('chat_sessions')
        .update({
          messages: [],
          updated_at: new Date().toISOString(),
        })
        .eq('id', sessionId)

      if (error) {
        throw error
      }
    } catch (error) {
      console.error('Error clearing messages:', error)
      throw error
    }
  }
}

/**
 * 创建会话管理器的工厂函数
 */
export function createSessionManager(
  supabaseUrl: string,
  supabaseKey: string
): SessionManager {
  return new SessionManager(supabaseUrl, supabaseKey)
}
