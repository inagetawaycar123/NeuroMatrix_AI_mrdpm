import React, { useState, useEffect } from 'react'
import { PatientInfoModule } from './PatientInfoModule'
import { ImageFindingsModule } from './ImageFindingsModule'
import { DoctorNotesModule } from './DoctorNotesModule'
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

  // 初始化：加载患者信息和自动生成影像描述
  useEffect(() => {
    if (!patientId) {
      setError('缺少患者ID')
      setLoading(false)
      return
    }
    loadPatientInfo()
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
        <div className="error">❌ {error}</div>
      </div>
    )
  }

  return (
    <div className="report-container">
      <div className="report-header">
        <h2>脑卒中临床诊断报告</h2>
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
              📄 导出PDF
            </button>
          )}
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

        {!isEditing && (
          <div className="report-footer">
            <p>报告生成时间：{new Date().toLocaleString('zh-CN')}</p>
            <p>
              免责声明：此报告中的AI分析仅供临床参考，医生应结合临床情况综合判断。
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
