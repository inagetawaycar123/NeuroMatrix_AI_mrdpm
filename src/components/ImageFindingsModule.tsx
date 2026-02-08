import React from 'react'
import { RichTextEditor } from './RichTextEditor'

interface ImageFindingsModuleProps {
  data: any
  findings: {
    core: string
    penumbra: string
    vessel: string
    perfusion: string
  }
  isEditing: boolean
  onUpdate: (field: string, value: string) => void
}

export const ImageFindingsModule: React.FC<ImageFindingsModuleProps> = ({
  data,
  findings,
  isEditing,
  onUpdate
}) => {
  if (!data) {
    return <div className="module-empty">加载影像分析数据中...</div>
  }

  return (
    <div className="report-module">
      <div className="module-header" style={{ background: 'linear-gradient(135deg, #60a5fa 0%, #3b82f6 100%)' }}>影像学发现</div>
      <div className="module-content">
        {/* 核心梗死 */}
        <div className="report-field full-width">
          <span className="field-label">核心梗死区</span>
          {isEditing ? (
            <RichTextEditor
              value={findings.core}
              onChange={(v) => onUpdate('core', v)}
              placeholder="描述核心梗死区的位置、大小、形态等..."
            />
          ) : (
            <div className="field-value" dangerouslySetInnerHTML={{ __html: findings.core }} />
          )}
        </div>

        {/* 半暗带 */}
        <div className="report-field full-width">
          <span className="field-label">半暗带区域</span>
          {isEditing ? (
            <RichTextEditor
              value={findings.penumbra}
              onChange={(v) => onUpdate('penumbra', v)}
              placeholder="描述半暗带的范围、分布等..."
            />
          ) : (
            <div className="field-value" dangerouslySetInnerHTML={{ __html: findings.penumbra }} />
          )}
        </div>

        {/* 血管 */}
        <div className="report-field full-width">
          <span className="field-label">血管评估</span>
          {isEditing ? (
            <RichTextEditor
              value={findings.vessel}
              onChange={(v) => onUpdate('vessel', v)}
              placeholder="描述颅内血管情况..."
            />
          ) : (
            <div className="field-value" dangerouslySetInnerHTML={{ __html: findings.vessel }} />
          )}
        </div>

        {/* 灌注 */}
        <div className="report-field full-width">
          <span className="field-label">灌注参数分析</span>
          {isEditing ? (
            <RichTextEditor
              value={findings.perfusion}
              onChange={(v) => onUpdate('perfusion', v)}
              placeholder="描述灌注参数分析..."
            />
          ) : (
            <div className="field-value" dangerouslySetInnerHTML={{ __html: findings.perfusion }} />
          )}
        </div>

        {/* AI分析指标 */}
        <div className="analysis-summary">
          <h4>AI分析指标</h4>
          <div className="metric">
            <span>核心梗死体积：</span>
            <strong>{data.core_volume?.toFixed(1) || '--'} ml</strong>
          </div>
          <div className="metric">
            <span>半暗带体积：</span>
            <strong>{data.penumbra_volume?.toFixed(1) || '--'} ml</strong>
          </div>
          <div className="metric">
            <span>不匹配比例：</span>
            <strong>{data.mismatch_ratio?.toFixed(2) || '--'}</strong>
          </div>
          <div className="metric">
            <span>不匹配状态：</span>
            <strong style={{ color: data.has_mismatch ? '#ff6b6b' : '#51cf66' }}>
              {data.has_mismatch ? '存在显著不匹配' : '无显著不匹配'}
            </strong>
          </div>
        </div>
      </div>
    </div>
  )
}
