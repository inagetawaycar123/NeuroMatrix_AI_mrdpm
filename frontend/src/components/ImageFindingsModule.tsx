import React, { useMemo } from 'react'

type SectionMap = Record<string, string>

type CtaSection = {
  title: string
  data: SectionMap
}

type ReportPayload = {
  modalities?: string[]
  combo?: 'NCCT_ONLY' | 'NCCT_SINGLE_CTA' | 'NCCT_MCTA' | 'NCCT_MCTA_CTP'
  sections?: {
    ncct?: SectionMap | null
    cta?: CtaSection[]
    ctp?: {
      enabled?: boolean
      core_infarct_volume?: number | null
      penumbra_volume?: number | null
      mismatch_ratio?: number | null
    }
  }
  summary_findings?: string[]
  ctp_enhanced?: string[] | null
}

interface ImageFindingsModuleProps {
  data: any
  reportPayload?: ReportPayload | null
  findings: {
    core: string
    penumbra: string
    vessel: string
    perfusion: string
  }
  isEditing: boolean
  onUpdate: (field: string, value: string) => void
}

const toFiniteNumber = (value: unknown): number | null => {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string') {
    const n = Number(value)
    return Number.isFinite(n) ? n : null
  }
  return null
}

const formatNumeric = (value: unknown, digits: number): string => {
  const n = toFiniteNumber(value)
  return n === null ? '--' : n.toFixed(digits)
}

const pickFirstSentence = (section?: SectionMap | null): string | null => {
  if (!section) return null
  const values = Object.values(section).filter((x) => typeof x === 'string' && x.trim())
  return values.length ? values[0].trim() : null
}

const pickLine = (lines: string[] | null | undefined, keyword: string): string | null => {
  if (!Array.isArray(lines)) return null
  const found = lines.find((x) => x.includes(keyword))
  return found || null
}

export const ImageFindingsModule: React.FC<ImageFindingsModuleProps> = ({ data, reportPayload }) => {
  const combo = reportPayload?.combo || 'NCCT_ONLY'
  const ctpSection = reportPayload?.sections?.ctp
  const showQuantitative =
    (combo === 'NCCT_MCTA' || combo === 'NCCT_MCTA_CTP') && ctpSection?.enabled === true

  const coreVolume = ctpSection?.core_infarct_volume ?? data?.core_volume ?? null
  const penumbraVolume = ctpSection?.penumbra_volume ?? data?.penumbra_volume ?? null
  const mismatchRatio = ctpSection?.mismatch_ratio ?? data?.mismatch_ratio ?? null
  const mismatchNumber = toFiniteNumber(mismatchRatio)
  const hasMismatch =
    typeof data?.has_mismatch === 'boolean'
      ? data.has_mismatch
      : mismatchNumber === null
      ? null
      : mismatchNumber >= 1.8

  const summaryItems = useMemo(() => {
    const directSummary = (reportPayload?.summary_findings || []).filter((x) => x && x.trim())
    if (directSummary.length) return directSummary

    const generated: string[] = []
    const ncctFirst = pickFirstSentence(reportPayload?.sections?.ncct)
    if (ncctFirst) generated.push(`NCCT要点：${ncctFirst}`)

    const ctaSections = Array.isArray(reportPayload?.sections?.cta) ? reportPayload?.sections?.cta : []
    ctaSections.forEach((section) => {
      const first = pickFirstSentence(section.data)
      if (first) generated.push(`${section.title}要点：${first}`)
    })

    if (showQuantitative) {
      generated.push(
        `CTP量化要点：核心梗死体积 ${formatNumeric(coreVolume, 1)} ml，半暗带体积 ${formatNumeric(
          penumbraVolume,
          1
        )} ml，不匹配比值 ${formatNumeric(mismatchRatio, 2)}。`
      )
    }

    return generated
  }, [reportPayload, showQuantitative, coreVolume, penumbraVolume, mismatchRatio])

  const ctpEnhanced = reportPayload?.ctp_enhanced || null
  const ctpInterpretation =
    pickLine(ctpEnhanced, '灌注解读') ||
    (hasMismatch === null
      ? '灌注解读：当前量化结果不完整，请结合原始灌注图及临床信息综合判断。'
      : hasMismatch
      ? '灌注解读：存在核心-半暗带不匹配，提示仍可能存在可挽救脑组织。'
      : '灌注解读：未见显著核心-半暗带不匹配，可挽救脑组织证据相对有限。')

  const ctpWindowHint =
    pickLine(ctpEnhanced, '治疗窗提示') || '治疗窗提示：请结合发病时间窗、神经功能缺损程度与禁忌证综合评估再灌注策略。'

  return (
    <div className="report-module">
      <div className="module-header" style={{ background: 'linear-gradient(135deg, #60a5fa 0%, #3b82f6 100%)' }}>
        影像学摘要
      </div>
      <div className="module-content">
        {summaryItems.length > 0 ? (
          <div className="report-field full-width">
            <span className="field-label">关键要点</span>
            <div className="field-value">
              <ul style={{ margin: 0, paddingLeft: 18 }}>
                {summaryItems.map((item, idx) => (
                  <li key={`summary-${idx}`} style={{ marginBottom: 8, lineHeight: 1.7 }}>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        ) : (
          <div className="module-empty">暂无影像学摘要，请在 Viewer 页面点击“生成报告”后重试。</div>
        )}

        {showQuantitative && (
          <div className="analysis-summary">
            <h4>CTP 灌注分析</h4>
            <div className="metric">
              <span>核心梗死体积</span>
              <strong>{formatNumeric(coreVolume, 1)} ml</strong>
            </div>
            <div className="metric">
              <span>半暗带体积</span>
              <strong>{formatNumeric(penumbraVolume, 1)} ml</strong>
            </div>
            <div className="metric">
              <span>不匹配比值</span>
              <strong>{formatNumeric(mismatchRatio, 2)}</strong>
            </div>
            <div className="metric">
              <span>不匹配状态</span>
              <strong style={{ color: hasMismatch === null ? '#d1d5db' : hasMismatch ? '#ff6b6b' : '#51cf66' }}>
                {hasMismatch === null ? '--' : hasMismatch ? '存在显著不匹配' : '无显著不匹配'}
              </strong>
            </div>
            <div style={{ marginTop: 12, color: '#d1d5db', fontSize: 13, lineHeight: 1.7 }}>{ctpInterpretation}</div>
            <div style={{ marginTop: 8, color: '#d1d5db', fontSize: 13, lineHeight: 1.7 }}>{ctpWindowHint}</div>
          </div>
        )}
      </div>
    </div>
  )
}
