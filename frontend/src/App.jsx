import { useEffect, useMemo, useState } from "react";
import { fetchNodeDetail, fetchOverview } from "./api";

const TERMINAL = new Set(["succeeded", "failed", "cancelled", "paused_review_required"]);

function fmt(value) {
  if (!value && value !== 0) return "-";
  return String(value);
}

function prettyJson(value) {
  if (value === null || value === undefined) return "-";
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch (_err) {
    return String(value);
  }
}

function statusClass(status) {
  return `status-${String(status || "pending").toLowerCase().replace(/\s+/g, "-")}`;
}

function parseInitialContext() {
  const q = new URLSearchParams(window.location.search);
  return {
    runId: (q.get("run_id") || "").trim(),
    fileId: (q.get("file_id") || "").trim(),
    patientId: (q.get("patient_id") || "").trim(),
  };
}

export default function App() {
  const [ctx, setCtx] = useState(parseInitialContext);
  const [overview, setOverview] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [selectedNode, setSelectedNode] = useState(null);
  const [nodeDetail, setNodeDetail] = useState(null);
  const [nodeLoading, setNodeLoading] = useState(false);

  const run = overview?.run || {};
  const dag = overview?.dag || { nodes: [], edges: [] };
  const validation = overview?.validation || {};
  const left = overview?.panels?.left || {};
  const right = overview?.panels?.right || {};
  const bottom = overview?.panels?.bottom || {};

  const riskItems = right.risks || [];
  const logs = bottom.timeline || [];
  const runStatus = String(run.status || "").toLowerCase();
  const isTerminal = TERMINAL.has(runStatus) || runStatus === "completed";
  const hasLoadedRun = Boolean(run.run_id);

  async function refresh(manual = false) {
    if (!ctx.runId && !ctx.fileId && !ctx.patientId) return;
    if (manual) setLoading(true);
    setError("");
    try {
      const next = await fetchOverview(ctx);
      setOverview(next);
      const resolvedRunId = String(next?.run?.run_id || "").trim();
      if (resolvedRunId && resolvedRunId !== ctx.runId) {
        const updated = { ...ctx, runId: resolvedRunId };
        setCtx(updated);
        const params = new URLSearchParams();
        if (updated.runId) params.set("run_id", updated.runId);
        if (updated.fileId) params.set("file_id", updated.fileId);
        if (updated.patientId) params.set("patient_id", updated.patientId);
        window.history.replaceState({}, "", `${window.location.pathname}?${params.toString()}`);
      }
    } catch (err) {
      setError(err.message || "加载失败");
    } finally {
      if (manual) setLoading(false);
    }
  }

  useEffect(() => {
    if (ctx.runId || ctx.fileId || ctx.patientId) {
      refresh(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!overview || isTerminal) return;
    const timer = setInterval(() => refresh(false), 1500);
    return () => clearInterval(timer);
  }, [overview, isTerminal]);

  async function openNode(node) {
    setSelectedNode(node);
    setNodeDetail(null);
    if (!run.run_id || !node?.step_key) return;
    setNodeLoading(true);
    try {
      const detail = await fetchNodeDetail(run.run_id, node.step_key);
      setNodeDetail(detail);
    } catch (err) {
      setNodeDetail({ error: err.message || "节点详情加载失败" });
    } finally {
      setNodeLoading(false);
    }
  }

  const laneGroups = useMemo(() => {
    const groups = {};
    for (const node of dag.nodes || []) {
      const lane = node.lane_title || node.lane || "未分组";
      if (!groups[lane]) groups[lane] = [];
      groups[lane].push(node);
    }
    return groups;
  }, [dag.nodes]);

  async function handleLauncherEnter() {
    setOverview(null);
    await refresh(true);
  }

  if (!hasLoadedRun) {
    return (
      <div className="page launcher-page">
        <section className="launcher-hero glass">
          <p className="eyebrow">NeuroMatrix Agent Cockpit</p>
          <h1>运行入口</h1>
          <p className="launcher-subtitle">
            输入 patient_id 或 file_id，系统会自动匹配最新 run，并一键进入 Cockpit 总览。
          </p>
          <div className="launcher-grid">
            <label>
              <span>patient_id</span>
              <input
                placeholder="例如 500"
                value={ctx.patientId}
                onChange={(e) => setCtx((s) => ({ ...s, patientId: e.target.value.trim() }))}
              />
            </label>
            <label>
              <span>file_id</span>
              <input
                placeholder="例如 case_20260421_001"
                value={ctx.fileId}
                onChange={(e) => setCtx((s) => ({ ...s, fileId: e.target.value.trim() }))}
              />
            </label>
            <label>
              <span>run_id（可选）</span>
              <input
                placeholder="如已知可直接填"
                value={ctx.runId}
                onChange={(e) => setCtx((s) => ({ ...s, runId: e.target.value.trim() }))}
              />
            </label>
          </div>
          <div className="launcher-actions">
            <button
              className="primary-btn"
              onClick={handleLauncherEnter}
              disabled={loading || (!ctx.runId && !ctx.fileId && !ctx.patientId)}
            >
              {loading ? "定位中..." : "自动查找最新 run 并进入 Cockpit"}
            </button>
            <button
              onClick={() => {
                setError("");
                setCtx({ runId: "", fileId: "", patientId: "" });
              }}
              disabled={loading}
            >
              清空
            </button>
          </div>
          {error ? <div className="error-box">{error}</div> : null}
        </section>
      </div>
    );
  }

  return (
    <div className="page">
      <header className="topbar glass">
        <div>
          <p className="eyebrow">NeuroMatrix Agent Cockpit</p>
          <h1>实时总览驾驶舱</h1>
        </div>
        <div className="toolbar">
          <input
            placeholder="run_id"
            value={ctx.runId}
            onChange={(e) => setCtx((s) => ({ ...s, runId: e.target.value.trim() }))}
          />
          <input
            placeholder="file_id"
            value={ctx.fileId}
            onChange={(e) => setCtx((s) => ({ ...s, fileId: e.target.value.trim() }))}
          />
          <input
            placeholder="patient_id"
            value={ctx.patientId}
            onChange={(e) => setCtx((s) => ({ ...s, patientId: e.target.value.trim() }))}
          />
          <button onClick={() => refresh(true)} disabled={loading}>
            {loading ? "刷新中..." : "刷新"}
          </button>
        </div>
      </header>

      {error ? <div className="error-box">{error}</div> : null}

      <main className="cockpit-grid">
        <section className="panel glass left-panel">
          <h2>病例与输入</h2>
          <div className="kv"><span>patient_id</span><strong>{fmt(run.patient_id || left?.patient?.patient_id)}</strong></div>
          <div className="kv"><span>file_id</span><strong>{fmt(run.file_id)}</strong></div>
          <div className="kv"><span>模态</span><strong>{(left.available_modalities || []).join(" + ") || "-"}</strong></div>
          <div className="kv"><span>半球</span><strong>{fmt(left.hemisphere)}</strong></div>
          <div className="kv"><span>性别</span><strong>{fmt(left?.patient?.sex)}</strong></div>
          <div className="kv"><span>年龄</span><strong>{fmt(left?.patient?.age)}</strong></div>
          <div className="kv"><span>NIHSS</span><strong>{fmt(left?.patient?.admission_nihss)}</strong></div>
          <div className="kv"><span>run_id</span><strong>{fmt(run.run_id)}</strong></div>
          <div className="kv"><span>状态</span><strong className={statusClass(run.status)}>{fmt(run.status)}</strong></div>
        </section>

        <section className="panel glass dag-panel">
          <div className="panel-head">
            <h2>DAG 处理监控</h2>
            <div className="chip-wrap">
              <span className="chip">nodes {dag.node_count || 0}</span>
              <span className="chip">edges {dag.edge_count || 0}</span>
              <span className="chip">path {fmt(dag.imaging_path)}</span>
            </div>
          </div>
          <div className="dag-scroll">
            {Object.entries(laneGroups).map(([lane, nodes]) => (
              <div key={lane} className="lane">
                <h3>{lane}</h3>
                <div className="lane-row">
                  {nodes.map((node) => (
                    <button
                      key={node.id}
                      className={`node-card ${statusClass(node.status)}`}
                      onClick={() => openNode(node)}
                    >
                      <span className="node-title">{node.title || node.step_key}</span>
                      <span className="node-key">{node.step_key}</span>
                      <span className="node-meta">{fmt(node.status)}</span>
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="panel glass right-panel">
          <h2>结论 / 证据 / 风险</h2>
          <div className="kv"><span>Consensus</span><strong>{fmt(right.consensus)}</strong></div>
          <div className="kv"><span>ICV</span><strong>{fmt(validation?.icv?.status)}</strong></div>
          <div className="kv"><span>EKV</span><strong>{fmt(validation?.ekv?.status)}</strong></div>
          <div className="kv"><span>Support Rate</span><strong>{validation?.ekv?.support_rate == null ? "-" : `${(Number(validation.ekv.support_rate) * 100).toFixed(1)}%`}</strong></div>
          <div className="kv"><span>Traceability</span><strong>{fmt(validation?.traceability?.status)}</strong></div>
          <h3>风险提示</h3>
          <div className="risk-list">
            {riskItems.length === 0 ? <p className="muted">暂无高风险提示</p> : null}
            {riskItems.map((item) => (
              <article key={`${item.event_seq}_${item.tool}`} className={`risk-item level-${item.level}`}>
                <p>{item.message || "-"}</p>
                <small>{item.tool} #{item.event_seq}</small>
              </article>
            ))}
          </div>
        </section>

        <section className="panel glass bottom-panel">
          <h2>运行日志与时间线</h2>
          <div className="timeline">
            {logs.length === 0 ? <p className="muted">暂无日志</p> : null}
            {logs.map((evt) => (
              <div key={evt.event_id || `${evt.tool_name}_${evt.event_seq}`} className="timeline-row">
                <div className="dot" />
                <div className="timeline-main">
                  <div className="timeline-title">
                    <strong>{evt.tool_name || "-"}</strong>
                    <span className={statusClass(evt.status)}>{fmt(evt.status)}</span>
                  </div>
                  <p>{evt.result_summary || evt.message || "-"}</p>
                </div>
                <div className="timeline-side">
                  <small>#{fmt(evt.event_seq)}</small>
                  <small>{fmt(evt.timestamp)}</small>
                </div>
              </div>
            ))}
          </div>
        </section>
      </main>

      {selectedNode ? (
        <div className="modal-wrap" onClick={() => setSelectedNode(null)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <h3>{selectedNode.title || selectedNode.step_key}</h3>
              <button onClick={() => setSelectedNode(null)}>关闭</button>
            </div>
            <div className="modal-kv">
              <div className="kv"><span>step_key</span><strong>{fmt(selectedNode.step_key)}</strong></div>
              <div className="kv"><span>status</span><strong>{fmt(selectedNode.status)}</strong></div>
              <div className="kv"><span>latency_ms</span><strong>{fmt(selectedNode.latency_ms)}</strong></div>
              <div className="kv"><span>retryable</span><strong>{String(Boolean(selectedNode.retryable))}</strong></div>
            </div>
            {nodeLoading ? <p className="muted">节点详情加载中...</p> : null}
            {nodeDetail?.error ? <p className="error-box">{nodeDetail.error}</p> : null}
            <div className="io-grid">
              <section>
                <h4>输入</h4>
                <pre>{prettyJson(nodeDetail?.input_payload || selectedNode.input_payload)}</pre>
              </section>
              <section>
                <h4>输出</h4>
                <pre>{prettyJson(nodeDetail?.output_payload || selectedNode.output_payload)}</pre>
              </section>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
