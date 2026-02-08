import React from 'react'

interface PatientData {
  patient_name: string
  patient_age: number
  patient_sex: string
  onset_exact_time?: string
  admission_time?: string
  admission_nihss: number
  surgery_time?: string
}

interface PatientInfoModuleProps {
  data: PatientData | null
  isEditing: boolean
  onUpdate: (field: string, value: any) => void
}

export const PatientInfoModule: React.FC<PatientInfoModuleProps> = ({
  data,
  isEditing,
  onUpdate
}) => {
  if (!data) {
    return <div className="module-empty">加载患者信息中...</div>
  }

  const formatDateTime = (dateStr?: string) => {
    if (!dateStr) return '--'
    return new Date(dateStr).toLocaleString('zh-CN')
  }

  return (
    <div className="report-module">
      <div className="module-header" style={{ background: 'linear-gradient(135deg, #60a5fa 0%, #3b82f6 100%)' }}>患者基本信息</div>
      <div className="module-content">
        <div className="report-field">
          <span className="field-label">姓名</span>
          {isEditing ? (
            <input
              type="text"
              className="field-edit"
              value={data.patient_name}
              onChange={(e) => onUpdate('patient_name', e.target.value)}
            />
          ) : (
            <span className="field-value">{data.patient_name || '--'}</span>
          )}
        </div>

        <div className="report-field">
          <span className="field-label">年龄</span>
          {isEditing ? (
            <input
              type="number"
              className="field-edit"
              value={data.patient_age}
              onChange={(e) => onUpdate('patient_age', parseInt(e.target.value))}
            />
          ) : (
            <span className="field-value">{data.patient_age}岁</span>
          )}
        </div>

        <div className="report-field">
          <span className="field-label">性别</span>
          {isEditing ? (
            <input
              type="text"
              className="field-edit"
              value={data.patient_sex}
              onChange={(e) => onUpdate('patient_sex', e.target.value)}
            />
          ) : (
            <span className="field-value">{data.patient_sex || '--'}</span>
          )}
        </div>

        <div className="report-field">
          <span className="field-label">发病时间</span>
          {isEditing ? (
            <input
              type="datetime-local"
              className="field-edit"
              defaultValue={data.onset_exact_time?.slice(0, 16)}
              onChange={(e) => onUpdate('onset_exact_time', e.target.value)}
            />
          ) : (
            <span className="field-value">{formatDateTime(data.onset_exact_time)}</span>
          )}
        </div>

        <div className="report-field">
          <span className="field-label">入院时间</span>
          {isEditing ? (
            <input
              type="datetime-local"
              className="field-edit"
              defaultValue={data.admission_time?.slice(0, 16)}
              onChange={(e) => onUpdate('admission_time', e.target.value)}
            />
          ) : (
            <span className="field-value">{formatDateTime(data.admission_time)}</span>
          )}
        </div>

        <div className="report-field">
          <span className="field-label">入院NIHSS评分</span>
          {isEditing ? (
            <input
              type="number"
              className="field-edit"
              min="0"
              max="42"
              value={data.admission_nihss}
              onChange={(e) => onUpdate('admission_nihss', parseInt(e.target.value))}
            />
          ) : (
            <span className="field-value">{data.admission_nihss} 分</span>
          )}
        </div>

        <div className="report-field">
          <span className="field-label">发病至入院</span>
          {isEditing ? (
            <input
              type="text"
              className="field-edit"
              defaultValue={data.surgery_time}
              onChange={(e) => onUpdate('surgery_time', e.target.value)}
            />
          ) : (
            <span className="field-value">{data.surgery_time || '--'}</span>
          )}
        </div>
      </div>
    </div>
  )
}
