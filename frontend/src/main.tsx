import React from 'react'
import ReactDOM from 'react-dom/client'
import { StructuredReport } from './components/StructuredReport'
import './styles/global.css'

type AnalysisData = {
  file_id?: string
  core_volume: number | null
  penumbra_volume: number | null
  mismatch_ratio: number | null
  has_mismatch: boolean | null
  hemisphere: string | null
}

const toNumberOrNull = (value: unknown): number | null => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value
  }
  return null
}

const parseAnalysisData = (fileId: string): AnalysisData | null => {
  const raw = sessionStorage.getItem('analysis_data')
  if (!raw) return null

  try {
    const parsed = JSON.parse(raw) || {}
    const dataFileId = typeof parsed.file_id === 'string' ? parsed.file_id : ''

    if (fileId && dataFileId !== fileId) {
      return null
    }

    const hasAnyValue =
      parsed.core_infarct_volume != null ||
      parsed.penumbra_volume != null ||
      parsed.mismatch_ratio != null ||
      typeof parsed.has_mismatch === 'boolean'

    if (!hasAnyValue) {
      return null
    }

    return {
      file_id: dataFileId || undefined,
      core_volume: toNumberOrNull(parsed.core_infarct_volume),
      penumbra_volume: toNumberOrNull(parsed.penumbra_volume),
      mismatch_ratio: toNumberOrNull(parsed.mismatch_ratio),
      has_mismatch: typeof parsed.has_mismatch === 'boolean' ? parsed.has_mismatch : null,
      hemisphere: typeof parsed.hemisphere === 'string' ? parsed.hemisphere : null,
    }
  } catch {
    return null
  }
}

const urlParams = new URLSearchParams(window.location.search)
const pathParts = window.location.pathname.split('/')
const patientId = parseInt(pathParts[pathParts.length - 1]) || null
const fileId = urlParams.get('file_id') || ''
const analysisData = parseAnalysisData(fileId)

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <StructuredReport
      patientId={patientId}
      fileId={fileId}
      analysisData={analysisData}
    />
  </React.StrictMode>
)
