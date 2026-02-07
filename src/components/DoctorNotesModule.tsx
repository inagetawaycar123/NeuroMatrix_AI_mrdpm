import React from 'react'
import { RichTextEditor } from './RichTextEditor'

interface DoctorNotesModuleProps {
  notes: string
  isEditing: boolean
  onUpdate: (value: string) => void
}

export const DoctorNotesModule: React.FC<DoctorNotesModuleProps> = ({
  notes,
  isEditing,
  onUpdate
}) => {
  return (
    <div className="report-module">
      <div className="module-header" style={{ background: 'linear-gradient(135deg, #60a5fa 0%, #3b82f6 100%)' }}>医生备注</div>
      <div className="module-content">
        {isEditing ? (
          <RichTextEditor
            value={notes}
            onChange={onUpdate}
            placeholder="请输入临床备注、诊断意见、后续建议..."
          />
        ) : (
          <div className="field-value" style={{ 
            color: notes ? '#333' : '#999',
            fontStyle: notes ? 'normal' : 'italic'
          }}>
            {notes || '无'}
          </div>
        )}
      </div>
    </div>
  )
}
