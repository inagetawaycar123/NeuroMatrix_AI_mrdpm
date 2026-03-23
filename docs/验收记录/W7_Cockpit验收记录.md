# W7_Cockpit验收记录

## 1. 验收说明
- 验收范围：Week7 前端可视化（独立 Cockpit 页 + 入口打通）
- 不在本次范围：Week8 性能/上线建议

## 2. 用例记录模板
> 每条用例请填：`run_id/job_id/file_id`、关键请求/响应摘要、日志片段、截图路径、结论。

### Case 1：主链成功轨迹可视化（NCCT+mCTA）
- run_id:
- job_id:
- file_id:
- 入口页面（processing/viewer/report/validation）:
- 关键请求摘要:
  - `GET /api/agent/runs/{run_id}`:
  - `GET /api/agent/runs/{run_id}/events`:
  - `GET /api/agent/runs/{run_id}/result`:
- 关键日志片段:
- 截图路径:
- 结论（PASS/FAIL）:

### Case 2：非阻断失败场景（EKV/Consensus soft-fail）
- run_id:
- job_id:
- file_id:
- 关键现象:
  - run 终态:
  - Cockpit 错误/提示:
- 关键请求摘要:
- 关键日志片段:
- 截图路径:
- 结论（PASS/FAIL）:

### Case 3：入口与上下文连续性
- 来源入口:
  - processing -> cockpit:
  - viewer -> cockpit:
  - report -> cockpit:
  - validation -> cockpit:
- `run_id/file_id/patient_id` 是否连续:
- 无 run_id 空态引导是否正确:
- 截图路径:
- 结论（PASS/FAIL）:

## 3. 回归检查
- viewer 关键流程正常（PASS/FAIL）:
- report 关键流程正常（PASS/FAIL）:
- chat 关键流程正常（PASS/FAIL）:
- processing 主时间线正常（PASS/FAIL）:

## 4. 总结
- 是否满足 Week7 DoD（可查看一次完整运行轨迹）:
- 遗留问题:
- 建议:

