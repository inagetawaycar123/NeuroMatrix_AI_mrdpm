/**
 * NeuroMatrix Chat Components
 * B端集成问答组件库
 */

// 导出主要组件
export { EmbeddedChat } from './components/EmbeddedChat'
export type { default as EmbeddedChatProps } from './components/EmbeddedChat'

// 导出工具函数
export { DataAdapter } from './utils/dataAdapter'
export type {
  BEndMessage,
  ChatMessage,
  MedicalAnalysis,
  BEndAnalysis
} from './utils/dataAdapter'

// 导出UI组件（可选）
export { Button } from './components/ui/button'
export { Input } from './components/ui/input'

// 版本信息
export const VERSION = '1.0.0'
export const COMPONENT_NAME = 'NeuroMatrix Chat Components'