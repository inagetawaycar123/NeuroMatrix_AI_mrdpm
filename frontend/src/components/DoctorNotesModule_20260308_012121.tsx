import React from 'react'
import { RichTextEditor } from './RichTextEditor'

interface DoctorNotesModuleProps {
  notes: string
  isEditing: boolean
  onUpdate: (value: string) => void
}

const ALLOWED_TAGS = new Set(['p', 'ul', 'ol', 'li', 'strong', 'em', 's', 'br'])

const sanitizeNotesHtml = (input: string): string => {
  if (!input) return ''
  if (typeof window === 'undefined' || typeof DOMParser === 'undefined') return input

  const parser = new DOMParser()
  const doc = parser.parseFromString(`<div>${input}</div>`, 'text/html')
  const root = doc.body.firstElementChild
  if (!root) return ''

  const blockedTags = new Set(['script', 'style', 'iframe', 'object', 'embed'])
  const allElements = Array.from(root.querySelectorAll('*'))

  for (const element of allElements) {
    const tag = element.tagName.toLowerCase()

    if (blockedTags.has(tag)) {
      element.remove()
      continue
    }

    if (!ALLOWED_TAGS.has(tag)) {
      const parent = element.parentNode
      if (!parent) continue
      while (element.firstChild) {
        parent.insertBefore(element.firstChild, element)
      }
      parent.removeChild(element)
      continue
    }

    for (const attr of Array.from(element.attributes)) {
      element.removeAttribute(attr.name)
    }
  }

  return root.innerHTML.trim()
}

export const DoctorNotesModule: React.FC<DoctorNotesModuleProps> = ({
  notes,
  isEditing,
  onUpdate
}) => {
  const sanitizedNotes = sanitizeNotesHtml(notes)

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
          sanitizedNotes ? (
            <div
              className="field-value doctor-notes-view"
              dangerouslySetInnerHTML={{ __html: sanitizedNotes }}
            />
          ) : (
            <div className="field-value doctor-notes-view doctor-notes-empty">无</div>
          )
        )}
      </div>
    </div>
  )
}
