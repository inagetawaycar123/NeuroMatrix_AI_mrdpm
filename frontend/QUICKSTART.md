# 🚀 快速开始指南

## 30 秒快速启动

```bash
# 1. 进入项目目录
cd /Users/yuanji/Desktop/3/frontend

# 2. 启动开发服务器
npm run dev
# 等待 "ready - started server on 0.0.0.0:3000"

# 3. 打开浏览器
open http://localhost:3000

# 4. 开始使用！🎉
```

---

## ✅ 系统就绪检查表

### 已配置 ✅

- [x] 百川 M3 API 密钥
- [x] Supabase 数据库连接
- [x] 前端 React 组件
- [x] 后端 API 路由
- [x] 医学 Prompt 模板
- [x] 图像分析引擎

### 立即可用 ✅

- [x] 文本医学问诊
- [x] 医学影像上传和分析
- [x] 会话管理和历史
- [x] AHA 指南建议
- [x] 医学免责声明
- [x] 多轮对话支持

---

## 📖 使用场景

### 场景 1: 简单医学问诊

**输入**:
```
患者: 68岁男性
NIHSS: 12分
问题: 是否适合IV-tPA溶栓？
```

**输出**:
```
根据患者信息和AHA/ASA指南：

✅ 适合IV-tPA溶栓治疗
  • 年龄在推荐范围内
  • NIHSS评分符合要求
  • 发病时间在4.5小时内

⚠️ 证据等级: IIa级 (应该考虑)

【重要免责声明】
本建议仅供参考，最终诊断由医生决定
```

### 场景 2: 带医学影像的查询

**输入**:
```
患者: 72岁女性
NIHSS: 8分
上传: CT脑血管造影
问题: 影像提示什么? 是否能溶栓?
```

**输出**:
```
【患者提供的医学影像信息】

图像 1（CT）：
【图像类型】: CT脑血管造影
【主要发现】: 左侧MCA起始段血栓，部分血流尚存
【临床相关性】: 符合急性缺血性卒中

基于影像和临床数据：
• 建议进行溶栓或取栓评估
• 证据等级: I级 (强烈推荐)

【医学免责声明】
...
```

### 场景 3: 多轮临床讨论

```
医生: 患者有高血压病史，是否仍可溶栓?
系统: 高血压患者可溶栓，但需...

医生: 如果血压 >185/110 呢?
系统: 血压>185/110需先控制至...

医生: 用什么药物降血压?
系统: 根据AHA指南，推荐用...
```

---

## 🧪 测试 API

### 测试 1: 验证系统正常运行

```bash
# 检查服务器
curl http://localhost:3000/api/chat/clinical/ 2>&1

# 预期响应:
# {"error":"Missing sessionId parameter"}
```

### 测试 2: 简单文本查询

```bash
curl -X POST http://localhost:3000/api/chat/clinical/ \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "test-001",
    "question": "请介绍你的功能",
    "patientContext": {
      "patientId": "p1",
      "name": "Test",
      "age": 65
    }
  }' | python3 -m json.tool
```

### 测试 3: 医学影像查询

```bash
npx ts-node test-image-api.ts
```

**预期输出**:
```
✅ API 响应成功!
📊 响应信息:
   SessionId: image-test-xxx
   AI 回复长度: xxx 字符
   Token 使用: xxx
📝 AI 回复预览: [医学建议...]
```

---

## 📚 关键文件位置

| 功能 | 文件 | 用途 |
|------|------|------|
| AI 医学建议 | `src/lib/prompt-engineer.ts` | 医学提示模板 |
| API 端点 | `src/app/api/chat/clinical/route.ts` | 后端路由 |
| 前端 UI | `src/components/MainChat.tsx` | React 组件 |
| 百川 API | `src/lib/baichuan-client.ts` | AI 调用 |
| 数据库 | `src/lib/session-manager.ts` | Supabase 连接 |
| 图像处理 | `src/lib/image-analyzer.ts` | 医学影像分析 |
| 配置 | `.env.local` | API 密钥 |

---

## 🔧 常见操作

### 查看 API 日志

```bash
# 在开发服务器终端观看实时日志
# 或查看保存的日志
tail -f /tmp/nextjs.log
```

### 重启服务

```bash
# 停止现有的服务
pkill -f "next dev"

# 重新启动
npm run dev
```

### 检查数据库

```bash
# 访问 Supabase 管理面板
# https://supabase.com/dashboard

# 查看表
# → chat_sessions (会话)
# → medical_images (医学影像)
```

### 查看环境变量

```bash
cat .env.local
# 确认所有密钥都已配置
```

---

## ❓ 常见问题

### Q: 如何修改医学提示？
**A**: 编辑 `src/lib/prompt-engineer.ts` 中的模板或 SYSTEM_PROMPT

### Q: 如何添加新的临床评分？
**A**: 更新 `PatientContext` 接口，然后在 prompt 中使用

### Q: 如何支持更多语言？
**A**: 在 prompt-engineer.ts 中添加新的语言模板

### Q: 如何增加响应速度？
**A**: 实现缓存层或使用更小的模型（trade-off 质量）

### Q: 如何保证隐私？
**A**: 系统使用 Supabase RLS 进行行级保护，所有数据加密存储

---

## 📞 获取帮助

### 文档位置

- **系统架构**: `docs/system-complete-guide.md`
- **API 参考**: `docs/api-quickref.md`
- **图像功能**: `docs/image-integration-complete.md`
- **部署指南**: `docs/deployment-checklist.md`
- **完成清单**: `docs/COMPLETION-CHECKLIST.md`

### 联系方式

- **开发者**: Yuan Ji (Backend)
- **技术问题**: 查看源代码注释
- **医学问题**: 咨询医学顾问

---

## 🎯 下一步

### 今天可以做的

1. ✅ 启动系统
2. ✅ 测试基本功能
3. ✅ 上传医学影像
4. ✅ 查看 AI 建议
5. ✅ 检查会话历史

### 本周可以做的

1. 📋 集成到医疗应用
2. 🧪 进行临床验证
3. 📊 收集反馈数据
4. 🔧 优化提示模板
5. 🚀 部署到生产环境

### 本月可以做的

1. 🏥 医学伦理审查
2. 📱 开发移动应用
3. 🌐 多语言支持
4. 📈 性能优化
5. 📚 发布学术论文

---

## ✨ 系统亮点速览

```
┌──────────────────────────────────────────────────┐
│  🖼️ 医学影像分析                                 │
│  实时识别 CT/MRI/X光                            │
└──────────────────────────────────────────────────┘
           ↓ 通过 百川M3 API ↓
┌──────────────────────────────────────────────────┐
│  🧠 AI 医学建议                                  │
│  基于 AHA/ASA 2023 卒中指南                      │
│  含证据等级标注 (I/IIa/IIb/III)                  │
└──────────────────────────────────────────────────┘
           ↓ 存储在 Supabase ↓
┌──────────────────────────────────────────────────┐
│  💾 会话管理                                     │
│  患者信息、对话历史、影像数据                    │
│  支持多轮临床讨论                                │
└──────────────────────────────────────────────────┘
           ↓ 显示给医生 ↓
┌──────────────────────────────────────────────────┐
│  ⚠️ 医学免责声明                                 │
│  "仅供参考，不替代医生诊断"                    │
└──────────────────────────────────────────────────┘
```

---

**🎉 准备好了！现在就开始体验 NeuroMatrix AI 吧！**

```bash
npm run dev
```

**访问**: http://localhost:3000  
**状态**: ✅ 完全就绪  
**版本**: 1.0.0
