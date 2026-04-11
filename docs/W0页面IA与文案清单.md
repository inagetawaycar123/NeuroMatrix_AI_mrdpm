# W0 页面 IA 与文案清单

## 1. 页面列表（W0）
- 页面 1：`StrokeClaw W0 Workbench`（`/strokeclaw/w0`）
- 页面 2：`Cockpit`（`/cockpit`，作为 Runtime 占位页）

## 2. 页面 1 信息架构
### 顶部区
- 主标题：`StrokeClaw W0 任务入口`
- 副标题：`W0 骨架联调：任务入口 + Orchestration 计划面板 + Runtime 占位。`

### 输入区
- `patient_id`
- `file_id`
- `goal_question`（可选）
- `available_modalities`（多选）

### 动作区
- 按钮：`启动 StrokeClaw W0 Run`
- 按钮：`进入 Runtime（Cockpit）`
- Hint 文案：
  - 默认：`请输入 patient_id 与 file_id 后启动。`
  - 运行中：`Run 进行中：{status} / {stage}`
  - 结束：`Run 已结束：{status}`

### 运行状态区
- `run_id`
- `status`
- `stage`
- `current_tool`
- `termination_reason`
- `replan_count`

### 计划面板区
- 标题：`Stroke Orchestration（计划面板）`
- 渲染优先级：
  1. `plan_frames[-1].next_tools`
  2. `planner_output.tool_sequence`
  3. `steps[].key`
  4. 占位文案：`计划尚未生成，等待 triage_planner 完成。`

### 事件区
- 标题：`Runtime 事件占位`
- 行内容：`event_seq + event_type + status + tool_name + timestamp`

## 3. 页面 2（Cockpit）在 W0 的定位
- 继续作为 Runtime 主查看页。
- W0 只要求可跳转与可读，不做结构重构。

## 4. 文案冻结规则
- W0 期间冻结区块层级和主标题，不变更页面结构。
- 允许微调：
  - 提示文案
  - 错误文案
  - 字段显示顺序的微调
