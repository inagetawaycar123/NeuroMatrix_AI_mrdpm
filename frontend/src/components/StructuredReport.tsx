import React, { useEffect, useMemo, useState } from 'react'
import { Star, X } from 'lucide-react'
import { DoctorNotesModule } from './DoctorNotesModule'
import { ImageFindingsModule } from './ImageFindingsModule'
import { MedicalAIChat } from './MedicalAIChat'
import { PatientInfoModule } from './PatientInfoModule'
import '../styles/report.css'

type AnalysisData = {
  core_volume: number | null
  penumbra_volume: number | null
  mismatch_ratio: number | null
  has_mismatch: boolean | null
  hemisphere: string | null
} | null

type SectionMap = Record<string, string>

type CtaSection = {
  title: string
  data: SectionMap
}

type ReportPayload = {
  modalities: string[]
  combo: 'NCCT_ONLY' | 'NCCT_SINGLE_CTA' | 'NCCT_MCTA' | 'NCCT_MCTA_CTP'
  sections: {
    ncct: SectionMap | null
    cta: CtaSection[]
    ctp: {
      enabled: boolean
      core_infarct_volume: number | null
      penumbra_volume: number | null
      mismatch_ratio: number | null
    }
  }
  summary_findings?: string[]
  ctp_enhanced?: string[] | null
  risk_notice?: string[]
}

interface PatientData {
  id: number
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
  analysisData?: AnalysisData
}

const getReportStorageKeys = (fileId?: string) => {
  if (fileId) {
    return {
      report: `ai_report_${fileId}`,
      generating: `ai_report_generating_${fileId}`,
      error: `ai_report_error_${fileId}`,
      payload: `ai_report_payload_${fileId}`,
    }
  }
  return {
    report: 'ai_report',
    generating: 'ai_report_generating',
    error: 'ai_report_error',
    payload: 'ai_report_payload',
  }
}

const escapeHtml = (text: string) =>
  text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

const parseMarkdown = (text: string): string => {
  if (!text) return ''
  const lines = escapeHtml(text).split(/\r?\n/)
  const html: string[] = []
  let inList = false

  const closeList = () => {
    if (!inList) return
    html.push('</ul>')
    inList = false
  }

  for (const rawLine of lines) {
    const line = rawLine.trim()
    if (!line) {
      closeList()
      continue
    }
    if (line.startsWith('## ')) {
      closeList()
      html.push(
        `<h2 style="color:#3b82f6;border-bottom:2px solid #60a5fa;padding-bottom:10px;margin:20px 0 12px 0;font-size:28px;">${line.slice(
          3
        )}</h2>`
      )
      continue
    }
    if (line.startsWith('### ')) {
      closeList()
      html.push(`<h3 style="color:#60a5fa;margin:16px 0 10px 0;font-size:20px;">${line.slice(4)}</h3>`)
      continue
    }
    if (line.startsWith('- ') || /^\d+\.\s/.test(line)) {
      if (!inList) {
        html.push('<ul style="margin:8px 0 12px 0;padding-left:20px;">')
        inList = true
      }
      const body = line.replace(/^(-|\d+\.)\s+/, '')
      html.push(`<li style="margin-bottom:8px;line-height:1.8;">${body}</li>`)
      continue
    }
    closeList()
    html.push(`<p style="margin:8px 0;line-height:1.9;">${line}</p>`)
  }

  closeList()
  return html.join('')
}

const splitMarkdownSections = (markdown: string): Map<string, string[]> => {
  const map = new Map<string, string[]>()
  let current = ''
  for (const rawLine of markdown.split(/\r?\n/)) {
    const line = rawLine.trim()
    if (line.startsWith('## ')) {
      current = line.slice(3).trim()
      map.set(current, [])
      continue
    }
    if (!current || !line) continue
    map.get(current)?.push(line)
  }
  return map
}

const stripMarkdownSections = (markdown: string, sectionTitles: string[]): string => {
  if (!markdown) return ''
  const lines = markdown.split(/\r?\n/)
  const kept: string[] = []
  let skip = false

  for (const rawLine of lines) {
    const line = rawLine.trim()
    if (line.startsWith('## ')) {
      const title = line.slice(3).trim()
      skip = sectionTitles.includes(title)
      if (!skip) kept.push(rawLine)
      continue
    }
    if (!skip) kept.push(rawLine)
  }

  return kept.join('\n').trim()
}

const toFloat = (value: unknown): number | null => {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string') {
    const n = Number(value.replace(/[^\d.-]/g, ''))
    return Number.isFinite(n) ? n : null
  }
  return null
}

const parseKeyValueSection = (lines: string[]): SectionMap => {
  const output: SectionMap = {}
  let index = 1

  for (const line of lines) {
    const text = line.replace(/^[-*]\s*/, '').trim()
    if (!text) continue
    const parts = text.split(/[：:]/)
    if (parts.length >= 2) {
      const key = parts.shift()?.trim() || `要点${index}`
      const value = parts.join('：').trim()
      output[key] = value || '未提供'
    } else {
      output[`要点${index}`] = text
    }
    index += 1
  }

  return output
}

const parsePayloadFromMarkdown = (report: string): ReportPayload | null => {
  if (!report) return null
  const sectionMap = splitMarkdownSections(report)

  const ncctLines = sectionMap.get('NCCT 影像学表现') || []
  const arterial = sectionMap.get('CTA（动脉期）') || []
  const venous = sectionMap.get('CTA（静脉期）') || []
  const delayed = sectionMap.get('CTA（延迟期）') || []
  const ctpLines = sectionMap.get('CTP灌注分析') || sectionMap.get('CTP 量化分析') || []
  const riskLines = sectionMap.get('AI风险提示') || []

  const cta: CtaSection[] = []
  if (arterial.length) cta.push({ title: 'CTA（动脉期）', data: parseKeyValueSection(arterial) })
  if (venous.length) cta.push({ title: 'CTA（静脉期）', data: parseKeyValueSection(venous) })
  if (delayed.length) cta.push({ title: 'CTA（延迟期）', data: parseKeyValueSection(delayed) })

  const joinedCTP = ctpLines.join(' ')
  const core = toFloat(joinedCTP.match(/核心梗死体积\s*([0-9.]+)/)?.[1] ?? null)
  const penumbra = toFloat(joinedCTP.match(/半暗带体积\s*([0-9.]+)/)?.[1] ?? null)
  const mismatch = toFloat(joinedCTP.match(/不匹配(?:比值|比例)\s*([0-9.]+)/)?.[1] ?? null)
  const ctpEnabled = ctpLines.length > 0

  const modalities = new Set<string>()
  if (ncctLines.length || cta.length > 0) modalities.add('ncct')
  if (arterial.length) modalities.add('mcta')
  if (venous.length) modalities.add('vcta')
  if (delayed.length) modalities.add('dcta')
  if (ctpEnabled) {
    modalities.add('cbf')
    modalities.add('cbv')
    modalities.add('tmax')
  }

  let combo: ReportPayload['combo'] = 'NCCT_ONLY'
  const hasMCTA = arterial.length > 0 && venous.length > 0 && delayed.length > 0
  const hasAnyCTA = arterial.length > 0 || venous.length > 0 || delayed.length > 0
  if (hasMCTA) combo = ctpEnabled ? 'NCCT_MCTA_CTP' : 'NCCT_MCTA'
  else if (hasAnyCTA) combo = 'NCCT_SINGLE_CTA'

  const summary: string[] = []
  const ncctFirst = ncctLines.find((x) => x.startsWith('- ')) || ncctLines[0]
  if (ncctFirst) summary.push(`NCCT要点：${ncctFirst.replace(/^-\s*/, '')}`)
  const ctaFirstMap: Array<[string, string[]]> = [
    ['CTA（动脉期）', arterial],
    ['CTA（静脉期）', venous],
    ['CTA（延迟期）', delayed],
  ]
  ctaFirstMap.forEach(([title, lines]) => {
    const first = lines.find((x) => x.startsWith('- ')) || lines[0]
    if (first) summary.push(`${title}要点：${first.replace(/^-\s*/, '')}`)
  })
  if (ctpLines.length) {
    const first = ctpLines.find((x) => x.includes('量化结果')) || ctpLines[0]
    if (first) summary.push(`CTP要点：${first.replace(/^-\s*/, '')}`)
  }

  if (!ncctLines.length && !cta.length && !ctpEnabled) return null

  return {
    modalities: Array.from(modalities),
    combo,
    sections: {
      ncct: ncctLines.length ? parseKeyValueSection(ncctLines) : null,
      cta,
      ctp: {
        enabled: ctpEnabled,
        core_infarct_volume: core,
        penumbra_volume: penumbra,
        mismatch_ratio: mismatch,
      },
    },
    summary_findings: summary,
    ctp_enhanced: ctpLines.length ? ctpLines.map((x) => x.replace(/^-\s*/, '').trim()) : null,
    risk_notice: riskLines.length ? riskLines.map((x) => x.replace(/^-\s*/, '').trim()) : [],
  }
}

const parsePayloadFromStorage = (raw: string | null): ReportPayload | null => {
  if (!raw) return null
  try {
    const parsed = JSON.parse(raw)
    const sections = parsed?.sections || {}
    const combo: ReportPayload['combo'] =
      parsed?.combo === 'NCCT_ONLY' ||
      parsed?.combo === 'NCCT_SINGLE_CTA' ||
      parsed?.combo === 'NCCT_MCTA' ||
      parsed?.combo === 'NCCT_MCTA_CTP'
        ? parsed.combo
        : 'NCCT_ONLY'

    return {
      modalities: Array.isArray(parsed?.modalities) ? parsed.modalities : [],
      combo,
      sections: {
        ncct: sections?.ncct || null,
        cta: Array.isArray(sections?.cta) ? sections.cta : [],
        ctp: {
          enabled: sections?.ctp?.enabled === true,
          core_infarct_volume: toFloat(sections?.ctp?.core_infarct_volume),
          penumbra_volume: toFloat(sections?.ctp?.penumbra_volume),
          mismatch_ratio: toFloat(sections?.ctp?.mismatch_ratio),
        },
      },
      summary_findings: Array.isArray(parsed?.summary_findings) ? parsed.summary_findings : [],
      ctp_enhanced: Array.isArray(parsed?.ctp_enhanced) ? parsed.ctp_enhanced : null,
      risk_notice: Array.isArray(parsed?.risk_notice) ? parsed.risk_notice : [],
    }
  } catch {
    return null
  }
}

export const StructuredReport: React.FC<StructuredReportProps> = ({ patientId, fileId, analysisData }) => {
  const [isEditing, setIsEditing] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [patient, setPatient] = useState<PatientData | null>(null)
  const [findings, setFindings] = useState({
    core: '',
    penumbra: '',
    vessel: '',
    perfusion: '',
  })
  const [notes, setNotes] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [aiReport, setAiReport] = useState<string | null>(null)
  const [isGeneratingReport, setIsGeneratingReport] = useState(false)
  const [showAIChat, setShowAIChat] = useState(false)
  const [reportPayload, setReportPayload] = useState<ReportPayload | null>(null)

  const filteredAiReport = useMemo(
    () => stripMarkdownSections(aiReport || '', ['AI风险提示']),
    [aiReport]
  )
  const reportHtml = useMemo(() => parseMarkdown(filteredAiReport), [filteredAiReport])

  const riskNotices = useMemo(() => {
    if (Array.isArray(reportPayload?.risk_notice) && reportPayload.risk_notice.length > 0) {
      return reportPayload.risk_notice.filter((x) => x && x.trim())
    }
    if (aiReport) {
      const lines = splitMarkdownSections(aiReport).get('AI风险提示') || []
      const normalized = lines.map((x) => x.replace(/^-\s*/, '').trim()).filter(Boolean)
      if (normalized.length > 0) return normalized
    }
    return [
      '本报告由 AI 自动生成，仅用于辅助参考，不能替代执业医师诊断。',
      '关键结论需结合完整影像序列、临床表现与实验室结果综合判读。',
    ]
  }, [reportPayload, aiReport])

  useEffect(() => {
    if (!patientId) {
      setError('缺少患者ID')
      setLoading(false)
      return
    }

    const loadPatientInfo = async () => {
      try {
        const res = await fetch(`/api/get_patient/${patientId}`)
        const data = await res.json()
        if (data.status === 'success') {
          setPatient(data.data)
        } else {
          setError(data.message || '获取患者信息失败')
        }
      } catch (err) {
        setError(`获取患者信息失败：${(err as Error).message}`)
      } finally {
        setLoading(false)
      }
    }

    loadPatientInfo()
  }, [patientId])

  useEffect(() => {
    const keys = getReportStorageKeys(fileId)

    const applyStorageState = () => {
      const savedReport = localStorage.getItem(keys.report)
      const savedGenerating = localStorage.getItem(keys.generating)
      const savedPayload = localStorage.getItem(keys.payload)

      setAiReport(savedReport || null)
      setIsGeneratingReport(savedGenerating === 'true')

      const payloadFromStorage = parsePayloadFromStorage(savedPayload)
      if (payloadFromStorage) {
        setReportPayload(payloadFromStorage)
      } else {
        setReportPayload(savedReport ? parsePayloadFromMarkdown(savedReport) : null)
      }
    }

    applyStorageState()

    const handleStorage = (e: StorageEvent) => {
      if (e.key === keys.generating) {
        setIsGeneratingReport(e.newValue === 'true')
        if (e.newValue === 'true') {
          setAiReport(null)
          setReportPayload(null)
        }
      }

      if (e.key === keys.report) {
        const report = e.newValue || null
        setAiReport(report)
        setIsGeneratingReport(false)
        if (!localStorage.getItem(keys.payload)) {
          setReportPayload(report ? parsePayloadFromMarkdown(report) : null)
        }
      }

      if (e.key === keys.payload) {
        setReportPayload(parsePayloadFromStorage(e.newValue))
      }

      if (e.key === keys.error && e.newValue) {
        setIsGeneratingReport(false)
      }
    }

    window.addEventListener('storage', handleStorage)
    return () => window.removeEventListener('storage', handleStorage)
  }, [fileId])

  const handlePatientUpdate = (field: string, value: unknown) => {
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
          patient,
          findings,
          notes,
          saved_at: new Date().toISOString(),
        }),
      })

      const data = await res.json()
      if (data.status === 'success') {
        setIsEditing(false)
        alert('报告保存成功')
      } else {
        alert(`报告保存失败：${data.message}`)
      }
    } catch (err) {
      alert(`报告保存失败：${(err as Error).message}`)
    } finally {
      setIsSaving(false)
    }
  }

  const exportPDF = async () => {
    alert('PDF 导出功能开发中')
  }

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
        <div className="error">
          <X className="inline w-4 h-4 mr-1" /> {error}
        </div>
      </div>
    )
  }

  return (
    <div className="report-container">
      <div className="report-header">
        <h2
          style={{
            background: 'linear-gradient(135deg, #60a5fa 0%, #3b82f6 100%)',
            color: 'white',
            padding: '16px 24px',
            borderRadius: '12px',
            margin: 0,
            fontSize: '20px',
            fontWeight: 600,
            boxShadow: '0 4px 12px rgba(59, 130, 246, 0.4)',
          }}
        >
          脑卒中临床诊断报告
        </h2>
        <div className="report-actions">
          <button className={`action-btn ${isEditing ? 'cancel' : 'primary'}`} onClick={() => setIsEditing(!isEditing)}>
            {isEditing ? '取消编辑' : '编辑报告'}
          </button>
          {isEditing && (
            <button className="action-btn primary" onClick={saveReport} disabled={isSaving}>
              {isSaving ? '保存中...' : '保存报告'}
            </button>
          )}
          {!isEditing && (
            <button className="action-btn" onClick={exportPDF}>
              导出PDF
            </button>
          )}
          <button className="action-btn ai-consult-btn" onClick={() => setShowAIChat(!showAIChat)}>
            AI问诊
          </button>
        </div>
      </div>

      <div className="report-body">
        <PatientInfoModule data={patient} isEditing={isEditing} onUpdate={handlePatientUpdate} />

        <ImageFindingsModule
          data={analysisData || null}
          reportPayload={reportPayload}
          findings={findings}
          isEditing={isEditing}
          onUpdate={handleFindingsUpdate}
        />

        {isGeneratingReport ? (
          <div
            style={{
              background: 'linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)',
              padding: '40px',
              borderRadius: '12px',
              marginTop: '20px',
              textAlign: 'center',
            }}
          >
            <div
              style={{
                width: '48px',
                height: '48px',
                border: '4px solid rgba(255,255,255,0.3)',
                borderTop: '4px solid white',
                borderRadius: '50%',
                animation: 'spin 1s linear infinite',
                margin: '0 auto 16px',
              }}
            />
            <h3 style={{ color: '#fff', fontSize: '18px', marginBottom: '8px' }}>正在生成 AI 影像诊断报告...</h3>
            <p style={{ color: 'rgba(255,255,255,0.8)', fontSize: '14px' }}>NeuroMatrix AI 正在分析影像并汇总结果</p>
          </div>
        ) : aiReport ? (
          <div
            className="ai-report-section"
            style={{
              background: '#1a1a1a',
              borderRadius: '12px',
              padding: '24px',
              marginTop: '20px',
              border: '1px solid #333',
            }}
          >
            <h3
              style={{
                margin: '0 0 20px 0',
                color: '#fff',
                fontSize: '18px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                background: 'linear-gradient(135deg, #60a5fa 0%, #3b82f6 100%)',
                padding: '12px 16px',
                borderRadius: '8px',
                fontWeight: 600,
              }}
            >
              AI影像诊断报告（详细）
            </h3>
            <div
              className="ai-report-content"
              style={{ lineHeight: '1.8', fontSize: '14px', color: '#e5e5e5' }}
              dangerouslySetInnerHTML={{ __html: reportHtml }}
            />
          </div>
        ) : (
          <div
            style={{
              background: '#1a1a1a',
              borderRadius: '12px',
              padding: '40px',
              marginTop: '20px',
              border: '1px solid #333',
              textAlign: 'center',
            }}
          >
            <div style={{ marginBottom: '16px' }}>
              <Star style={{ fontSize: 48, color: '#60a5fa' }} />
            </div>
            <h3 style={{ color: '#fff', fontSize: '18px', marginBottom: '12px' }}>请在 Viewer 页面点击“生成报告”</h3>
            <p style={{ color: '#888', fontSize: '14px' }}>系统将调用 MedGemma 生成 NCCT/CTA 分析与动态报告内容。</p>
          </div>
        )}

        <div className="report-module">
          <div className="module-header" style={{ background: 'linear-gradient(135deg, #60a5fa 0%, #3b82f6 100%)' }}>
            AI风险提示
          </div>
          <div className="module-content">
            <div className="field-value">
              <ul style={{ margin: 0, paddingLeft: 18 }}>
                {riskNotices.map((item, idx) => (
                  <li key={`risk-${idx}`} style={{ marginBottom: 8, lineHeight: 1.7 }}>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>

        <DoctorNotesModule notes={notes} isEditing={isEditing} onUpdate={setNotes} />

        {!isEditing && (
          <div className="report-footer">
            <p>报告生成时间：{new Date().toLocaleString('zh-CN')}</p>
            <p>免责声明：本报告中的AI分析仅供临床参考，医生应结合临床情况综合判断。</p>
          </div>
        )}
      </div>

      <MedicalAIChat
        isVisible={showAIChat}
        onClose={() => setShowAIChat(false)}
        sessionId={`session-${patientId || 'default'}`}
        userId={`user-${Date.now()}`}
      />
    </div>
  )
}
