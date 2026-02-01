import React from 'react'
import ReactDOM from 'react-dom/client'
import { StructuredReport } from './components/StructuredReport'
import './styles/global.css'

// 从 URL 获取参数
const urlParams = new URLSearchParams(window.location.search)
const pathParts = window.location.pathname.split('/')
const patientId = parseInt(pathParts[pathParts.length - 1]) || null
const fileId = urlParams.get('file_id') || ''

// 从 sessionStorage 获取分析数据
const viewerData = JSON.parse(sessionStorage.getItem('analysis_data') || '{}')
const analysisData = {
  core_volume: viewerData.core_infarct_volume || 0,
  penumbra_volume: viewerData.penumbra_volume || 0,
  mismatch_ratio: viewerData.mismatch_ratio || 0,
  has_mismatch: viewerData.has_mismatch || false,
  hemisphere: viewerData.hemisphere || 'both'
}

// 挂载 React 应用
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <StructuredReport
      patientId={patientId}
      fileId={fileId}
      analysisData={analysisData}
    />
  </React.StrictMode>
)
