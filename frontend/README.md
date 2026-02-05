# NeuroMatrix Chat Components

NeuroMatrix AI问答组件库，支持B端系统集成，提供专业的脑卒中诊疗问答功能。

## 🚀 特性

- ✅ **专业医疗AI** - 专注于脑卒中影像分析和诊疗建议
- ✅ **B端集成友好** - 支持认证、会话管理和数据适配
- ✅ **高度可定制** - 灵活的主题和样式配置
- ✅ **响应式设计** - 适配各种屏幕尺寸
- ✅ **TypeScript支持** - 完整的类型定义
- ✅ **容错性强** - 后端服务不可用时提供降级响应

## 📦 安装

```bash
npm install @neuromatrix/chat-components
# 或
yarn add @neuromatrix/chat-components
```

## 🛠️ 使用方法

### 基础用法

```tsx
import { EmbeddedChat, DataAdapter } from '@neuromatrix/chat-components'
import { useState } from 'react'

function MedicalConsultation() {
  const [userToken, setUserToken] = useState('')
  const [sessionId] = useState(`session_${Date.now()}`)

  // 处理分析完成
  const handleAnalysisComplete = (analysis) => {
    console.log('AI分析结果:', analysis)
    // 将分析结果保存到B端系统
    saveAnalysisToBackend(analysis)
  }

  // 处理消息发送
  const handleMessageSend = (message) => {
    console.log('用户发送消息:', message)
    // 记录用户行为
    logUserAction(message)
  }

  return (
    <div className="consultation-container">
      <EmbeddedChat
        apiEndpoint="https://your-api-endpoint.com/api"
        userToken={userToken}
        sessionId={sessionId}
        userId="doctor_123"
        onAnalysisComplete={handleAnalysisComplete}
        onMessageSend={handleMessageSend}
        placeholder="请描述患者的症状和检查结果..."
        theme="auto"
        className="w-full max-w-2xl mx-auto"
      />
    </div>
  )
}
```

### 高级配置

```tsx
import { EmbeddedChat, DataAdapter } from '@neuromatrix/chat-components'

function AdvancedIntegration() {
  const [isMinimized, setIsMinimized] = useState(false)

  return (
    <EmbeddedChat
      apiEndpoint="https://api.yourcompany.com/neuromatrix"
      userToken={getAuthToken()}
      sessionId={getCurrentSessionId()}
      userId={getCurrentUserId()}
      onAnalysisComplete={(analysis) => {
        // 转换分析结果格式
        const bEndFormat = DataAdapter.convertAnalysisToBEndFormat(analysis)
        // 发送到B端系统
        submitAnalysis(bEndFormat)
      }}
      onMessageSend={(message) => {
        // 记录消息到B端
        logMessage({
          content: message,
          session_id: getCurrentSessionId(),
          user_id: getCurrentUserId(),
          timestamp: new Date().toISOString()
        })
      }}
      onClose={() => setIsMinimized(true)}
      showCloseButton={true}
      theme="light"
      className="fixed bottom-4 right-4 w-96 h-[500px] shadow-xl"
    />
  )
}
```

## 🔧 API 参考

### EmbeddedChat Props

| 属性 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `apiEndpoint` | `string` | `'/api/chat'` | API端点URL |
| `userToken` | `string?` | - | 用户认证token |
| `sessionId` | `string?` | - | 会话ID |
| `userId` | `string?` | - | 用户ID |
| `onAnalysisComplete` | `(analysis: MedicalAnalysis) => void` | - | 分析完成回调 |
| `onMessageSend` | `(message: string) => void` | - | 消息发送回调 |
| `className` | `string?` | - | 自定义CSS类名 |
| `placeholder` | `string` | `'输入您的医疗问题...'` | 输入框占位符 |
| `showCloseButton` | `boolean` | `false` | 是否显示关闭按钮 |
| `onClose` | `() => void` | - | 关闭回调 |
| `theme` | `'light' \| 'dark' \| 'auto'` | `'auto'` | 主题设置 |

### DataAdapter 工具类

```typescript
// 转换消息格式
const chatMessages = DataAdapter.convertMessagesToChatFormat(bEndMessages)
const bEndMessages = DataAdapter.convertMessagesToBEndFormat(chatMessages)

// 转换分析结果
const bEndAnalysis = DataAdapter.convertAnalysisToBEndFormat(analysis)
const analysis = DataAdapter.convertAnalysisFromBEndFormat(bEndAnalysis)

// 工具函数
const sessionId = DataAdapter.normalizeSessionId(rawSessionId)
const sanitizedContent = DataAdapter.sanitizeMessage(userInput)
```

## 🎨 样式定制

组件使用Tailwind CSS，您可以通过以下方式定制样式：

```css
/* 自定义组件样式 */
.embedded-chat {
  border-radius: 12px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
}

.embedded-chat .chat-messages {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
```

## 🔐 认证集成

### JWT Token认证

```typescript
// 获取token
const token = await authenticateUser(username, password)

// 使用组件
<EmbeddedChat
  apiEndpoint="https://api.company.com"
  userToken={token}
  // ... 其他props
/>
```

### 自定义认证头

组件会自动将`userToken`作为`Authorization: Bearer {token}`发送给API。

## 📊 数据格式

### 输入消息格式
```typescript
interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  id?: string
  timestamp?: string
}
```

### 分析结果格式
```typescript
interface MedicalAnalysis {
  risks: Array<{
    level: 'high' | 'medium' | 'low'
    description: string
    suggestion: string
  }>
  keypoints: string[]
  recommendations?: string[]
  timestamp: string
}
```

## 🚨 错误处理

组件内置了完善的错误处理机制：

- **网络错误**: 自动重试，后端不可用时提供降级响应
- **认证错误**: 触发重新认证流程
- **数据错误**: 验证输入数据格式，提供友好的错误提示

## 🔧 开发和构建

```bash
# 安装依赖
npm install

# 开发模式
npm run dev

# 构建组件库
npm run build:lib

# 发布到npm
npm publish
```

## 📋 兼容性

- React 18+
- TypeScript 4.5+
- 现代浏览器 (Chrome, Firefox, Safari, Edge)

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📞 支持

如有问题，请联系技术支持团队或查看[完整文档](https://docs.neuromatrix.ai)。