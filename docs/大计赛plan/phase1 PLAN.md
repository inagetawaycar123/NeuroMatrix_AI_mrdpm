## Phase1（W2-W3）前端惊艳骨架细化计划（含Phase0核查结论）

### 1) 摘要结论
1. `Phase0` 文档产物层面已完成：`docs/phase0` 的 9 份文件齐全，内容可执行。  
2. `Phase0` 流程签署层面未完成：`09_week1_execution_board.md` 的 Gate 勾选仍为未完成状态。  
3. 决策：按“可开工”标准，进入 `Phase1`；但必须在 `W2-D1` 先做 `0.5天 Gate 补签`（不做代码改动，只做团队确认与记录）。  
4. 前端基线判断：现有 `processing` 页已具备“动态叙事骨架”（节点卡片、动画、审阅流），`cockpit` 页缺少真正的 DAG 主舞台与节点详情交互，这是 Phase1 的主攻点。  

核查依据（关键文件）：
- [PLAN_all.md](g:/NeuroMatrix_AI_mrdpm/docs/大计赛plan/PLAN_all.md)
- [README.md](g:/NeuroMatrix_AI_mrdpm/docs/phase0/README.md)
- [09_week1_execution_board.md](g:/NeuroMatrix_AI_mrdpm/docs/phase0/09_week1_execution_board.md)
- [cockpit/index.html](g:/NeuroMatrix_AI_mrdpm/backend/templates/patient/upload/cockpit/index.html)

---

### 2) Phase0核查表（完成判定）
| 核查项 | 结果 | 说明 |
|---|---|---|
| 文档包完整性（01-09） | 完成 | 文件齐全且内容有效 |
| 核心对象/API冻结文本 | 完成 | 已定义 AgentRun/Step/ToolCall/TraceEvent 等 |
| 前端IA与DoD文档 | 完成 | 已定义 Upload→Cockpit→Imaging→Report→Evidence |
| 周执行看板 Gate 勾选 | 未完成 | 所有勾选仍是 `[ ]` |
| Phase0退出条件（README定义） | 未满足 | 需先完成 Gate 通过记录 |

---

### 3) Phase1执行策略（前端惊艳优先，后端最小配套）

#### 3.1 范围与原则（锁定）
1. 不做大重构，不迁移前端技术栈（继续 `HTML + Vanilla JS + 现有React报告页`）。  
2. 优先做“评委第一眼可感知”的界面能力：DAG、步骤状态、证据链、人工复核闭环。  
3. 后端接口采用“双轨”：  
   - 优先复用现有 `/api/agent/runs/*`、`/api/validation/context`。  
   - 缺失接口由前端 Adapter 推导，不阻塞演示。  
4. 强制展示 `source_tag`（real/mock/hybrid），避免“演示造假”质疑。  

#### 3.2 W2-W3日程细化（可直接执行）
| 时间 | 目标 | 核心任务 | 负责人 | 交付物 | 验收标准 |
|---|---|---|---|---|---|
| W2-D1(上午) | Gate补签 | 逐项确认 Phase0 Gate1/2/3，形成 Go 记录 | 敬 + 全员 | Gate评审记录 | `09` 看板全部可追溯 |
| W2-D1(下午) | 视觉冻结 | 锁定 cockpit 视觉规范（状态色、source_tag 徽章、动画节奏） | 康 + 雷 | UI规范v1 | 所有人按同一规范开发 |
| W2-D2 | DAG主舞台骨架 | cockpit 中央区域加入 DAG 视图（节点+连线+状态） | 康 | DAG可渲染静态图 | 可显示 8-12 节点与状态色 |
| W2-D3 | 节点详情卡片 | 点击节点弹出详情：输入/输出/置信度/耗时/风险/source_tag/证据refs | 康 + 朱 | Node Detail Drawer | 任意节点可展开完整信息 |
| W2-D4 | 时间线升级 | 统一 Step Timeline + Event Timeline 过滤与高亮联动 | 康 | 时间线联动 | 点事件可反查节点 |
| W2-D5 | 上传到Cockpit闭环 | 上传页增加“路径预览+运行模式提示+跳转动画” | 康 + 朱 | Upload→Cockpit 连贯链路 | 启动后 1 次跳转即可进入主舞台 |
| W3-D1 | 跨页上下文一致 | `run_id/patient_id/file_id` 在 processing/cockpit/viewer/report/validation 全链路保持 | 朱 + 康 | 上下文适配层 | 页面切换不丢上下文 |
| W3-D2 | 场景驱动演示 | A/B/C 一键启动（优先复用 mock run 机制），生成稳定演示流 | 雷 + 朱 + 敬 | 场景控制板 | 3 条场景可重复演示 |
| W3-D3 | 证据与报告联动 | 节点结论可跳转到验证页/报告段落并定位证据 | 刘 + 康 | Evidence Jump 交互 | “结论→证据”一跳到位 |
| W3-D4 | 动效与移动端打磨 | 进入动效、节点 reveal、状态过渡、移动端布局修复 | 康 + 雷 | 动效与响应式包 | 手机/投屏均可读可演示 |
| W3-D5 | Freeze & 彩排 | A/B/C 三场景全链路彩排、录屏与故障预案 | 敬 + 雷 + 全员 | Phase1封版 | 连续演示 15-18 分钟稳定 |

---

### 4) Phase1接口与数据决策（实现时无需再讨论）

#### 4.1 前端统一 ViewModel（新增约定）
1. `RunMetaVM`: `run_id,status,stage,current_step,source_tag,updated_at`  
2. `NodeVM`: `step_key,title,status,confidence,latency_ms,risk_level,source_tag`  
3. `NodeDetailVM`: `input_summary,output_summary,evidence_refs,error_code,retryable`  
4. `EventVM`: `event_seq,event_type,tool_name,status,timestamp,latency_ms,message`  

#### 4.2 数据来源优先级（锁定）
1. 优先：现有接口 `/api/agent/runs/{run_id}` + `/events` + `/result` + `/review` + `/api/validation/context`。  
2. 兼容：若未来上线 `/graph`、`/decision-bundle`、`/api/demo/scenarios/*`，前端自动切换使用。  
3. 回退：缺字段时由 Adapter 从 run/events 推导，不阻塞 UI 展示。  

#### 4.3 代码改动主战场（Phase1限定）
- [cockpit/index.html](g:/NeuroMatrix_AI_mrdpm/backend/templates/patient/upload/cockpit/index.html)
- [cockpit.js](g:/NeuroMatrix_AI_mrdpm/static/js/cockpit.js)
- [cockpit.css](g:/NeuroMatrix_AI_mrdpm/static/css/cockpit.css)

---

### 5) Phase1验收（DoD，比赛导向）
1. 评委在 10 秒内看到“这是智能体流程而非单次推理”。  
2. Cockpit 可展示 DAG、当前节点、节点状态动画、步骤时间线、事件流。  
3. 任意节点可展开详情（含置信度、耗时、风险、source_tag、证据引用）。  
4. A/B/C 三场景均可一键启动并可稳定复现。  
5. `source_tag` 全程可见，mock/hybrid 时有明显提示条。  
6. Report Review 闭环可演示（确认/编辑/继续），并可回到证据页反查。  
7. 跨页上下文不丢失（Upload→Processing→Cockpit→Validation→Report）。  

---

### 6) 6人 Phase1 分工（W2-W3）
| 成员 | Phase1职责 | 关键交付 |
|---|---|---|
| 敬 | Gate补签、演示叙事、里程碑验收 | Phase1 Go记录、答辩话术v1、场景主讲脚本 |
| 朱 | 接口适配与上下文链路 | FE Adapter、跨页上下文稳定、场景启动后端配合 |
| 袁 | 模型节点语义与风险字段规范 | NCCT/血管分类节点字段定义、mock→real映射规则 |
| 康 | Cockpit视觉与交互主开发 | DAG主舞台、节点详情卡、动效系统、响应式适配 |
| 刘 | 报告与证据联动 | 报告段落定位、证据映射展示、审阅交互对齐 |
| 雷 | QA与彩排资产 | A/B/C 彩排清单、录屏素材、故障切换预案 |

---

### 7) Assumptions & Defaults
1. 默认认定：Phase0“文档完成但Gate未签署”，W2-D1先补签后继续。  
2. Phase1 不引入重型新框架，不改现有页面路由结构。  
3. 缺失后端新接口时，前端先用 Adapter 推导 + mock 场景保演示连续性。  
4. 比赛优先目标为“可演示、可解释、可追溯”，非一次性工程化终态。  
