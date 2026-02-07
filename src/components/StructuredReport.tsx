import React, { useState, useEffect } from 'react'
import { X, Star } from 'lucide-react'
import { PatientInfoModule } from './PatientInfoModule'
import { ImageFindingsModule } from './ImageFindingsModule'
import { DoctorNotesModule } from './DoctorNotesModule'
import { MedicalAIChat } from './MedicalAIChat'
import '../styles/report.css'

interface PatientData {
  patient_name: string
  patient_age: number
  patient_sex: string
  onset_exact_time?: string
  admission_time?: string
  admission_nihss: number
  surgery_time?: string
}

interface StructuredReportProps {
  patientId: number
  fileId: string
  analysisData?: any
}

// Markdown 转 HTML（简单版本）
const parseMarkdown = (text: string): string => {
  if (!text) return ''
  
  let html = text
    // 处理标题 - 简洁样式（检查方法、影像学表现、血管评估、诊断意见、治疗建议）
    .replace(/^## (检查方法|影像学表现|血管评估|诊断意见|治疗建议|影像诊断报告)$/gm, 
      '<div style="margin: 20px 0 12px 0; padding-bottom: 8px; border-bottom: 2px solid #3b82f6; color: #3b82f6; font-size: 18px; font-weight: 600;">$1</div>')
    // 处理普通二级标题
    .replace(/^## (.+)$/gm, '<h2 style="color: #3b82f6; border-bottom: 3px solid #60a5fa; padding-bottom: 10px; margin: 24px 0 16px 0; font-size: 20px; font-weight: 700;">$1</h2>')
    // 处理三级标题
    .replace(/^### (.+)$/gm, '<h3 style="color: #60a5fa; margin: 20px 0 12px 0; font-size: 17px; font-weight: 600; padding-left: 12px; border-left: 4px solid #93c5fd;">$1</h3>')
    // 处理粗体标记 - 直接保留普通文字
    .replace(/\*\*(.+?)\*\*/g, '$1')
    // 处理列表
    .replace(/^\d+\. (.+)$/gm, '<li style="margin-left: 24px; margin-bottom: 8px; color: #e5e7eb;">$1</li>')
    .replace(/^- (.+)$/gm, '<li style="margin-left: 24px; margin-bottom: 8px; color: #e5e7eb;">$1</li>')
    // 处理段落
    .replace(/\n\n/g, '</p><p style="margin: 10px 0; line-height: 1.9; color: #d1d5db;">')
  
  return '<p style="margin: 10px 0; line-height: 1.9; color: #d1d5db;">' + html + '</p>'
}

export const StructuredReport: React.FC<StructuredReportProps> = ({
  patientId,
  fileId,
  analysisData
}) => {
  const [isEditing, setIsEditing] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [patient, setPatient] = useState<PatientData | null>(null)
  const [findings, setFindings] = useState({
    core: '',
    penumbra: '',
    vessel: '',
    perfusion: ''
  })
  const [notes, setNotes] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [aiReport, setAiReport] = useState<string | null>(null)
  const [isGeneratingReport, setIsGeneratingReport] = useState(false)
  const [showAIChat, setShowAIChat] = useState(false)

  // 初始化：加载患者信息
  useEffect(() => {
    if (!patientId) {
      setError('缺少患者ID')
      setLoading(false)
      return
    }
    loadPatientInfo()
    
    // 监听 storage 事件（跨标签页同步 AI 报告和生成状态）
    const handleStorage = (e: StorageEvent) => {
      if (e.key === 'ai_report_generating' && e.newValue === 'true') {
        setIsGeneratingReport(true)
      }
      if (e.key === 'ai_report' && e.newValue) {
        setAiReport(e.newValue)
        setIsGeneratingReport(false)
      }
    }
    window.addEventListener('storage', handleStorage)
    
    return () => window.removeEventListener('storage', handleStorage)
  }, [patientId])

  const loadPatientInfo = async () => {
    try {
      const res = await fetch(`/api/get_patient/${patientId}`)
      const data = await res.json()
      if (data.status === 'success') {
        setPatient(data.data)
        generateImageFindings(data.data)
      } else {
        setError(data.message || '加载患者信息失败')
      }
    } catch (err) {
      setError('网络错误：' + (err as Error).message)
    } finally {
      setLoading(false)
    }
  }

  const generateImageFindings = (patientData: PatientData) => {
    if (!analysisData) return

    const hemName: Record<string, string> = {
      left: '左侧',
      right: '右侧',
      both: '双侧'
    }

    const coreText = `<p>核心梗死区位于${hemName[analysisData.hemisphere] || '双侧'}大脑半球，体积约 <strong>${
      analysisData.core_volume?.toFixed(1) || '--'
    } ml</strong>。病灶界限清晰，灌注信号明显降低。</p>`

    const penumbraText = `<p>半暗带（缺血半影）范围广泛，体积约 <strong>${
      analysisData.penumbra_volume?.toFixed(1) || '--'
    } ml</strong>，较核心梗死区明显扩大，提示存在大量可挽救脑组织。</p>`

    const vesselText =
      '<p>需根据CTA序列进一步评估脑血管通畅性，判断是否存在大血管闭塞，为血管内治疗提供依据。</p>'

    const perfusionText = `<p>灌注参数分析：</p>
<ul>
<li>CBF（脑血流量）：核心梗死区显著降低，半暗带区域相对保留</li>
<li>CBV（脑血容量）：与梗死灶分布相符，周围相对升高</li>
<li>Tmax（平均通过时间）：延迟区域远大于核心区，不匹配比例 ${analysisData.mismatch_ratio?.toFixed(2) || '--'}</li>
<li>不匹配评估：${
      analysisData.has_mismatch
        ? '存在显著核心-半暗带不匹配，提示可能存在可挽救脑组织，需评估血管内治疗适应证'
        : '无显著不匹配'
    }</li>
</ul>`

    setFindings({
      core: coreText,
      penumbra: penumbraText,
      vessel: vesselText,
      perfusion: perfusionText
    })
  }

  const handlePatientUpdate = (field: string, value: any) => {
    setPatient((prev) => (prev ? { ...prev, [field]: value } : null))
  }

  const handleFindingsUpdate = (field: string, value: string) => {
    setFindings((prev) => ({ ...prev, [field]: value }))
  }

  const saveReport = async () => {
    if (!patientId || !fileId) return
    setIsSaving(true)

    try {
      const res = await fetch('/api/save_report', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          patient_id: patientId,
          file_id: fileId,
          patient: patient,
          findings: findings,
          notes: notes,
          saved_at: new Date().toISOString()
        })
      })

      const data = await res.json()
      if (data.status === 'success') {
        setIsEditing(false)
        alert('报告保存成功')
      } else {
        alert('保存失败：' + data.message)
      }
    } catch (err) {
      alert('保存失败：' + (err as Error).message)
    } finally {
      setIsSaving(false)
    }
  }

  const exportPDF = async () => {
    alert('PDF导出功能开发中...')
  }

  // 从 localStorage 读取已有的 AI 报告（支持跨标签页同步）
  useEffect(() => {
    const savedReport = localStorage.getItem('ai_report')
    if (savedReport) {
      setAiReport(savedReport)
    }
  }, [])

  if (loading) {
    return (
      <div className="report-container">
        <div className="loading">加载中...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="report-container">
        <div className="error"><X className="inline w-4 h-4 mr-1" /> {error}</div>
      </div>
    )
  }

  return (
    <div className="report-container">
      <div className="report-header">
        <h2 style={{ 
          background: 'linear-gradient(135deg, #60a5fa 0%, #3b82f6 100%)', 
          color: 'white',
          padding: '16px 24px',
          borderRadius: '12px',
          margin: 0,
          fontSize: '20px',
          fontWeight: 600,
          boxShadow: '0 4px 12px rgba(59, 130, 246, 0.4)'
        }}>脑卒中临床诊断报告</h2>
        <div className="report-actions">
          <button
            className={`action-btn ${isEditing ? 'cancel' : 'primary'}`}
            onClick={() => setIsEditing(!isEditing)}
          >
            {isEditing ? '取消编辑' : '编辑报告'}
          </button>
          {isEditing && (
            <button
              className="action-btn primary"
              onClick={saveReport}
              disabled={isSaving}
            >
              {isSaving ? '保存中...' : '保存报告'}
            </button>
          )}
          {!isEditing && (
            <button className="action-btn" onClick={exportPDF}>
              导出PDF
            </button>
          )}
          <button
            className="action-btn ai-consult-btn"
            onClick={() => setShowAIChat(!showAIChat)}
          >
            AI问诊
          </button>
        </div>
      </div>

      <div className="report-body">
        <PatientInfoModule
          data={patient}
          isEditing={isEditing}
          onUpdate={handlePatientUpdate}
        />
        <ImageFindingsModule
          data={analysisData || null}
          findings={findings}
          isEditing={isEditing}
          onUpdate={handleFindingsUpdate}
        />
        
        <DoctorNotesModule
          notes={notes}
          isEditing={isEditing}
          onUpdate={setNotes}
        />

        {/* AI 生成的报告展示 */}
        {!analysisData || analysisData.core_volume === 0 ? (
          <div style={{ 
            background: '#1a1a1a', 
            borderRadius: '12px', 
            padding: '40px', 
            marginTop: '20px',
            border: '1px solid #333',
            textAlign: 'center'
          }}>
            <div style={{ 
              marginBottom: '16px'
            }}>
              <Star style={{ fontSize: 48, color: '#60a5fa' }} />
            </div>
            <h3 style={{ 
              color: '#fff', 
              fontSize: '18px',
              marginBottom: '12px'
            }}>请先完成脑卒中分析</h3>
            <p style={{ 
              color: '#888', 
              fontSize: '14px'
            }}>请返回 viewer 页面完成分析后，再生成 AI 报告</p>
          </div>
        ) : isGeneratingReport ? (
          <div style={{ 
            background: 'linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)',
            padding: '40px',
            borderRadius: '12px',
            marginTop: '20px',
            textAlign: 'center'
          }}>
            <div style={{ 
              width: '48px', 
              height: '48px', 
              border: '4px solid rgba(255,255,255,0.3)', 
              borderTop: '4px solid white', 
              borderRadius: '50%', 
              animation: 'spin 1s linear infinite',
              margin: '0 auto 16px'
            }} />
            <h3 style={{ 
              color: '#fff', 
              fontSize: '18px',
              marginBottom: '8px'
            }}>正在生成 AI 报告...</h3>
            <p style={{ 
              color: 'rgba(255,255,255,0.8)', 
              fontSize: '14px'
            }}>NeuroMatrix AI 正在分析影像数据</p>
          </div>
        ) : aiReport ? (
          <div className="ai-report-section" style={{ 
            background: '#1a1a1a', 
            borderRadius: '12px', 
            padding: '24px', 
            marginTop: '20px',
            border: '1px solid #333'
          }}>
            <h3 style={{ 
              margin: '0 0 20px 0', 
              color: '#fff', 
              fontSize: '18px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              background: 'linear-gradient(135deg, #60a5fa 0%, #3b82f6 100%)',
              padding: '12px 16px',
              borderRadius: '8px',
              fontWeight: 600
            }}>
              AI 影像诊断报告
            </h3>
            <div 
              className="ai-report-content"
              style={{ 
                lineHeight: '1.8',
                fontSize: '14px',
                color: '#e5e5e5'
              }}
              dangerouslySetInnerHTML={{ __html: parseMarkdown(aiReport) }}
            />
          </div>
        ) : (
          <div style={{ 
            background: '#1a1a1a', 
            borderRadius: '12px', 
            padding: '40px', 
            marginTop: '20px',
            border: '1px solid #333',
            textAlign: 'center'
          }}>
            <div style={{ 
              marginBottom: '16px'
            }}>
              <Star style={{ fontSize: 48, color: '#60a5fa' }} />
            </div>
            <h3 style={{ 
              color: '#fff', 
              fontSize: '18px',
              marginBottom: '12px'
            }}>请生成 AI 报告</h3>
            <p style={{ 
              color: '#888', 
              fontSize: '14px'
            }}>请在脑卒中分析页面点击「手动生成 AI 报告」按钮</p>
          </div>
        )}

        {!isEditing && (
          <div className="report-footer">
            <p>报告生成时间：{new Date().toLocaleString('zh-CN')}</p>
            <p>
              免责声明：此报告中的AI分析仅供临床参考，医生应结合临床情况综合判断。
            </p>
          </div>
        )}
      </div>

      {/* 医疗AI聊天组件 */}
      <MedicalAIChat
        isVisible={showAIChat}
        onClose={() => setShowAIChat(false)}
        sessionId={`session-${patientId || 'default'}`}
        userId={`user-${Date.now()}`}
      />
    </div>
  )
}
