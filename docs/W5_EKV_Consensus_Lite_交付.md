# Week5 交付文档：EKV + Consensus Lite（实现版）

文档状态：Delivered (Week5)
更新日期：2026-03-19
负责人：第五周交付（执行实现）

## 1. 交付目标

根据 `docs/week5_PLAN.md`，完成 Week5 关键能力落地：

1. 在 Agent 主链中接入 `EKV`（外部知识校验）与 `Consensus Lite`（轻量裁决）。
2. 保持非阻断语义：`icv/ekv/consensus_lite` 失败时不阻断报告生成。
3. 在 Processing/Viewer 提供可见化摘要。
4. 增加测试并完成回归验证。

## 2. 分步骤实施记录

### Step 1：新增规则模块（后端）

新增文件：

1. `backend/ekv.py`
2. `backend/consensus.py`

实现内容：

1. `evaluate_ekv(...)`：
   - 固定 6 类关键结论（侧别、核心体积、半暗带体积、不匹配比、显著不匹配、时窗提示）。
   - 输出结构：`status/finding_count/score/confidence_delta/claims/findings/citations`。
   - 结论标签：`supported | partially_supported | not_supported | unavailable`。
2. `evaluate_consensus(...)`：
   - 触发条件：
     - EKV 存在 `not_supported`
     - `partially_supported >= 2`
     - ICV 为 `fail`
     - EKV `unavailable` 且存在高风险结论
   - 输出结构：`status/decision/conflict_count/summary/conflicts/next_actions`
   - 决策枚举：`accept | review_required | escalate | skipped`

### Step 2：接入 Agent Runtime（主链）

修改文件：`backend/app.py`

实现内容：

1. 工具序列接入：
   - 各路径均加入：`icv -> ekv -> consensus_lite -> generate_medgemma_report`
2. 阶段映射补齐：
   - `ekv -> ekv`
   - `consensus_lite -> consensus`
3. 工具执行分发补齐：
   - 新增 `_tool_ekv(run)`
   - 新增 `_tool_consensus_lite(run)`
4. 非阻断策略扩展：
   - `icv/ekv/consensus_lite` 失败均写日志并继续主链
5. 报告 payload 扩展：
   - `report_payload.icv`
   - `report_payload.ekv`
   - `report_payload.consensus`
6. 最终结果扩展：
   - `result.ekv_result`
   - `result.consensus_result`

### Step 3：前端摘要可见化

修改文件：

1. `backend/templates/patient/upload/processing/index.html`
2. `static/js/processing.js`
3. `static/js/viewer.js`

实现内容：

1. Processing 右侧 Agent 卡新增：
   - EKV 状态
   - EKV 发现数
   - Consensus 决策
   - 冲突数
2. Processing 落盘增强：
   - `ai_report_payload_<file_id>` 同步保存 `icv/ekv/consensus`
3. Viewer 报告区增强：
   - 在现有 ICV 摘要基础上追加 EKV 摘要与 Consensus 摘要卡

### Step 4：回归修复（稳定性）

修改文件：`backend/icv.py`

修复内容：

1. 修复 `report.summary` 数值提取，恢复 ICV 规则测试语义。
2. 修复 CTP 可用性判定语义：不再因体积数值自动认定 CTP，保持与既有测试一致。

## 3. 测试与结果

执行命令：

```bash
/Users/yuanji/Desktop/PyProject/Neuro-latest/.venv/bin/python -m pytest -q \
  tests/test_icv.py \
  tests/test_icv_rules.py \
  tests/test_icv_more.py \
  tests/test_ekv.py \
  tests/test_consensus.py
```

结果：

```text
................                                                         [100%]
```

说明：

1. ICV 历史回归测试通过。
2. Week5 新增 EKV/Consensus 单测通过。
3. 本轮目标范围内后端与前端静态检查无新增错误。

## 4. 新增测试用例

新增文件：

1. `tests/test_ekv.py`
2. `tests/test_consensus.py`

覆盖点：

1. EKV 可用场景与支持标签输出
2. NCCT-only 下 CTP 结论 `unavailable`
3. 量化冲突触发 `not_supported`
4. 无冲突时 Consensus `skipped`
5. 冲突触发 Consensus `review_required/escalate`
6. ICV fail 时 Consensus 升级策略

## 5. 与 Week5 计划对照

已完成：

1. EKV/Consensus 后端主链接入
2. 非阻断语义落地
3. Processing/Viewer 摘要可见化
4. 测试补齐并通过

未在本次扩展范围内单独新增：

1. 新路由（按计划保持 API 向后兼容，不新增路由）
2. 外部新服务依赖（保持现有体系）

## 6. 交付结论

Week5 核心目标已实现并通过目标测试：

1. Agent 主链具备 `ICV + EKV + Consensus Lite` 连续校验能力。
2. 关键校验结果可在 Processing/Viewer 直接查看。
3. 失败具备可见化与可追踪性，且不阻断报告主流程。

可进入下一阶段（Week6）进行更深的报告证据结构与临床验收留痕扩展。
