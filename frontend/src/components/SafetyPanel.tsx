'use client'

import { useState, useEffect } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'

interface Analysis {
  id: string
  risks: Array<{ level: 'high' | 'medium', description: string, suggestion: string }>
  keypoints: string[]
  triggerMessage?: {
    id: string
    content: string
    timestamp: string
  }
  timestamp: string
}

interface SafetyPanelProps {
  analysisHistory?: Analysis[]
}

export function SafetyPanel({ analysisHistory }: SafetyPanelProps) {
  // 调试日志
  console.log('SafetyPanel received analysisHistory:', analysisHistory)
  console.log('Analysis history length:', analysisHistory?.length || 0)
  if (analysisHistory && analysisHistory.length > 0) {
    console.log('Latest analysis:', analysisHistory[analysisHistory.length - 1])
  }

  return (
      <div className="w-80 bg-gray-900 border-l border-gray-700 flex flex-col max-h-screen">
        {/* 标题 */}
        <div className="p-4 border-b border-gray-700 flex-shrink-0">
          <h2 className="text-lg font-semibold text-white">安全卡</h2>
        </div>

        {/* 安全提示模块 */}
        <div className="flex-1 overflow-y-auto min-h-0">
          {analysisHistory && analysisHistory.length > 0 ? (
            <div className="p-4 space-y-6">
              {analysisHistory.map((analysis, analysisIndex) => (
                <div key={analysis.id || analysisIndex} className="space-y-4">
                  {/* 时间戳 */}
                  <div className="text-center">
                    <span className="text-xs text-gray-500">
                      {new Date(analysis.timestamp).toLocaleString()}
                    </span>
                  </div>

                  {/* 触发消息引用 */}
                  {analysis.triggerMessage && (
                    <div className="bg-blue-900 border border-blue-700 rounded-lg p-3">
                      <div className="flex items-center gap-2 mb-2">
                        <div className="w-4 h-4 bg-blue-500 rounded-full flex items-center justify-center">
                          <span className="text-white text-xs">💬</span>
                        </div>
                        <span className="text-blue-300 text-xs font-medium">相关消息</span>
                      </div>
                      <p className="text-blue-200 text-sm leading-relaxed line-clamp-2">
                        "{analysis.triggerMessage.content.length > 100
                          ? analysis.triggerMessage.content.substring(0, 100) + '...'
                          : analysis.triggerMessage.content}"
                      </p>
                    </div>
                  )}

                  {/* 动态风险提示 */}
                  {analysis.risks.map((risk: any, riskIndex: number) => (
                    <div
                      key={riskIndex}
                      className={`border rounded-lg p-4 ${
                        risk.level === 'high'
                          ? 'bg-red-900 border-red-700'
                          : 'bg-orange-900 border-orange-700'
                      }`}
                    >
                      <div className="flex items-center gap-2 mb-2">
                        <div className={`w-3 h-3 rounded-full ${
                          risk.level === 'high' ? 'bg-red-500' : 'bg-orange-500'
                        }`}></div>
                        <h3 className={`font-medium ${
                          risk.level === 'high' ? 'text-red-300' : 'text-orange-300'
                        }`}>
                          {risk.level === 'high' ? '紧急警报' : '临床提醒'}
                        </h3>
                      </div>
                      <div className="space-y-2">
                        <p className={`text-sm ${
                          risk.level === 'high' ? 'text-red-200' : 'text-orange-200'
                        }`}>
                          <strong>风险描述：</strong> {risk.description}
                        </p>
                        <p className={`text-sm ${
                          risk.level === 'high' ? 'text-red-200' : 'text-orange-200'
                        }`}>
                          <strong>处置建议：</strong> {risk.suggestion}
                        </p>
                      </div>
                    </div>
                  ))}

                  {/* 治疗要点 */}
                  <div className="bg-gray-800 border border-gray-600 rounded-lg p-4">
                    <h3 className="font-medium text-gray-300 mb-2">治疗要点</h3>
                    <ul className="text-gray-400 text-sm space-y-1">
                      {analysis.keypoints.map((point: string, pointIndex: number) => (
                        <li key={pointIndex}>• {point}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-4 space-y-4">
              {/* 默认安全提示 */}
              <div className="bg-blue-900 border border-blue-700 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-4 h-4 bg-blue-500 rounded-full flex items-center justify-center">
                    <span className="text-white text-xs">ℹ️</span>
                  </div>
                  <h3 className="text-blue-300 text-sm font-medium">安全使用指南</h3>
                </div>
                <div className="text-blue-200 text-xs space-y-2">
                  <p>• 本AI助手仅供临床参考，不替代医生诊断</p>
                  <p>• 所有分析结果需经专业医师确认</p>
                  <p>• 紧急情况请立即就医</p>
                  <p>• 输入医疗相关问题将触发智能分析</p>
                </div>
              </div>

              {/* 等待提示 */}
              <div className="text-center">
                <span className="text-xs text-gray-500">
                  暂无安全提示 - 开始医疗对话即可生成
                </span>
              </div>

              {/* 显示接收到的数据用于调试 */}
              <div className="bg-gray-800 p-3 rounded text-xs text-gray-400">
                <div>历史记录数量: {(analysisHistory?.length ?? 0)}</div>
                <div>状态: {(analysisHistory && analysisHistory.length > 0) ? '有数据' : '空数组'}</div>
                {analysisHistory && analysisHistory.length > 0 && (
                  <div>最新记录: {analysisHistory[analysisHistory.length - 1]?.timestamp}</div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    )
}