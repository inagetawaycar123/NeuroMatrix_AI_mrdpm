import { useEffect, useMemo, useRef, useState } from "react";
import { fetchBootstrap, fetchNodeDetail, fetchOverview, startUploadRun } from "./api";

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

function inferUploadMode(files) {
  const has = (key) => files[key] instanceof File;
  const hasNcct = has("ncct_file");
  const hasMcta = has("mcta_file");
  const hasVcta = has("vcta_file");
  const hasDcta = has("dcta_file");
  const hasCtp = has("cbf_file") && has("cbv_file") && has("tmax_file");

  if (hasNcct && hasMcta && hasVcta && hasDcta && hasCtp) {
    return { uploadMode: "ncct_3phase_cta_ctp", ctaPhase: "" };
  }
  if (hasNcct && hasMcta && hasVcta && hasDcta) {
    return { uploadMode: "ncct_3phase_cta", ctaPhase: "" };
  }
  if (hasNcct && (hasMcta || hasVcta || hasDcta)) {
    return {
      uploadMode: "ncct_single_cta",
      ctaPhase: hasMcta ? "mcta" : hasVcta ? "vcta" : "dcta",
    };
  }
  return { uploadMode: "ncct", ctaPhase: "" };
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
  const [bootstrapping, setBootstrapping] = useState(false);
  const [bootstrapData, setBootstrapData] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [nodeDetail, setNodeDetail] = useState(null);
  const [nodeLoading, setNodeLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [uploadForm, setUploadForm] = useState({
    patientId: "",
    fileId: "",
    hemisphere: "both",
    question: "",
    modelType: "mrdpm",
    files: {
      ncct_file: null,
      mcta_file: null,
      vcta_file: null,
      dcta_file: null,
      cbf_file: null,
      cbv_file: null,
      tmax_file: null,
    },
  });
  const autoEntryAttemptedRef = useRef(false);

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

  async function refresh(manual = false, overrideCtx = null) {
    const activeCtx = overrideCtx || ctx;
    if (!activeCtx.runId && !activeCtx.fileId && !activeCtx.patientId) return;
    if (manual) setLoading(true);
    setError("");
    try {
      const next = await fetchOverview(activeCtx);
      setOverview(next);
      const resolvedRunId = String(next?.run?.run_id || "").trim();
      if (resolvedRunId && resolvedRunId !== activeCtx.runId) {
        const updated = { ...activeCtx, runId: resolvedRunId };
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

  async function loadBootstrap(autoEnter = true) {
    setBootstrapping(true);
    setError("");
    try {
      const data = await fetchBootstrap();
      setBootstrapData(data);
      const latest = data?.latest_candidate || null;
      if (autoEnter && latest && !autoEntryAttemptedRef.current) {
        autoEntryAttemptedRef.current = true;
        const nextCtx = {
          runId: String(latest.run_id || "").trim(),
          fileId: String(latest.file_id || "").trim(),
          patientId: String(latest.patient_id || "").trim(),
        };
        setCtx(nextCtx);
        const params = new URLSearchParams();
        if (nextCtx.runId) params.set("run_id", nextCtx.runId);
        if (nextCtx.fileId) params.set("file_id", nextCtx.fileId);
        if (nextCtx.patientId) params.set("patient_id", nextCtx.patientId);
        window.history.replaceState({}, "", `${window.location.pathname}?${params.toString()}`);
        await refresh(true, nextCtx);
      }
    } catch (err) {
      setError(err.message || "无法加载最近运行列表");
    } finally {
      setBootstrapping(false);
    }
  }

  useEffect(() => {
    if (ctx.runId || ctx.fileId || ctx.patientId) {
      refresh(true);
    } else {
      loadBootstrap(true);
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

  async function enterCandidate(candidate) {
    if (!candidate) return;
    const nextCtx = {
      runId: String(candidate.run_id || "").trim(),
      fileId: String(candidate.file_id || "").trim(),
      patientId: String(candidate.patient_id || "").trim(),
    };
    setCtx(nextCtx);
    const params = new URLSearchParams();
    if (nextCtx.runId) params.set("run_id", nextCtx.runId);
    if (nextCtx.fileId) params.set("file_id", nextCtx.fileId);
    if (nextCtx.patientId) params.set("patient_id", nextCtx.patientId);
    window.history.replaceState({}, "", `${window.location.pathname}?${params.toString()}`);
    autoEntryAttemptedRef.current = true;
    await refresh(true, nextCtx);
  }

  function updateUploadField(name, value) {
    setUploadForm((prev) => ({ ...prev, [name]: value }));
  }

  function updateUploadFile(name, file) {
    setUploadForm((prev) => ({
      ...prev,
      files: {
        ...prev.files,
        [name]: file || null,
      },
    }));
  }

  async function submitUpload(e) {
    e.preventDefault();
    setUploadError("");

    const patientId = String(uploadForm.patientId || "").trim();
    if (!patientId || !/^\d+$/.test(patientId)) {
      setUploadError("请填写合法 patient_id（数字）。");
      return;
    }
    if (!(uploadForm.files.ncct_file instanceof File)) {
      setUploadError("请至少上传 NCCT 文件。");
      return;
    }

    const infer = inferUploadMode(uploadForm.files);
    const skipAi =
      uploadForm.files.cbf_file instanceof File &&
      uploadForm.files.cbv_file instanceof File &&
      uploadForm.files.tmax_file instanceof File;

    setUploading(true);
    try {
      const resp = await startUploadRun({
        patientId,
        fileId: String(uploadForm.fileId || "").trim(),
        hemisphere: uploadForm.hemisphere,
        question: String(uploadForm.question || "").trim(),
        modelType: uploadForm.modelType,
        uploadMode: infer.uploadMode,
        ctaPhase: infer.ctaPhase,
        skipAi,
        files: uploadForm.files,
      });

      const runId = String(resp?.agent_run_id || "").trim();
      if (!runId) {
        throw new Error("后端未返回 agent_run_id，无法直接进入主页面。");
      }

      const nextCtx = {
        runId,
        fileId: String(resp?.file_id || uploadForm.fileId || "").trim(),
        patientId,
      };
      setCtx(nextCtx);
      autoEntryAttemptedRef.current = true;

      const params = new URLSearchParams();
      params.set("run_id", nextCtx.runId);
      if (nextCtx.fileId) params.set("file_id", nextCtx.fileId);
      params.set("patient_id", nextCtx.patientId);
      window.history.replaceState({}, "", `${window.location.pathname}?${params.toString()}`);

      await refresh(true, nextCtx);
    } catch (err) {
      setUploadError(err.message || "上传失败");
    } finally {
      setUploading(false);
    }
  }

  if (!hasLoadedRun) {
    return (
      <div className="page launcher-page">
        <section className="launcher-hero glass">
          <p className="eyebrow">NeuroMatrix Agent Cockpit</p>
          <h1>运行入口</h1>
          <p className="launcher-subtitle">
            系统会直接读取最近的病例和运行记录，自动定位最新 run 并进入 Cockpit。
          </p>
          <div className="launcher-meta">
            <span className="chip">recent cases {bootstrapData?.candidates?.length || 0}</span>
            <span className="chip">source {bootstrapData?.latest_candidate?.source || "-"}</span>
            <span className="chip">status {bootstrapping ? "loading" : "ready"}</span>
          </div>
          <div className="launcher-actions">
            <button
              className="primary-btn"
              onClick={() => enterCandidate(bootstrapData?.latest_candidate)}
              disabled={loading || bootstrapping || !bootstrapData?.latest_candidate}
            >
              {bootstrapping ? "定位中..." : "进入最近一次运行"}
            </button>
            <button
              onClick={() => loadBootstrap(false)}
              disabled={bootstrapping}
            >
              刷新最近列表
            </button>
          </div>
          {error ? <div className="error-box">{error}</div> : null}
          <form className="upload-card" onSubmit={submitUpload}>
            <div className="upload-card-head">
              <h3>新病例上传</h3>
              <span className="chip">提交后自动进入 Cockpit</span>
            </div>
            <div className="upload-grid">
              <label>
                patient_id *
                <input
                  value={uploadForm.patientId}
                  onChange={(e) => updateUploadField("patientId", e.target.value)}
                  placeholder="例如 727"
                />
              </label>
              <label>
                file_id（可选）
                <input
                  value={uploadForm.fileId}
                  onChange={(e) => updateUploadField("fileId", e.target.value)}
                  placeholder="留空自动生成"
                />
              </label>
              <label>
                病灶半球
                <select
                  value={uploadForm.hemisphere}
                  onChange={(e) => updateUploadField("hemisphere", e.target.value)}
                >
                  <option value="both">both</option>
                  <option value="left">left</option>
                  <option value="right">right</option>
                </select>
              </label>
              <label>
                模型
                <select
                  value={uploadForm.modelType}
                  onChange={(e) => updateUploadField("modelType", e.target.value)}
                >
                  <option value="mrdpm">mrdpm</option>
                  <option value="medgemma">medgemma</option>
                </select>
              </label>
              <label className="span-2">
                Agent 问题（可选）
                <input
                  value={uploadForm.question}
                  onChange={(e) => updateUploadField("question", e.target.value)}
                  placeholder="例如：请给出取栓相关风险评估"
                />
              </label>
            </div>

            <div className="upload-files">
              <label>NCCT *<input type="file" accept=".nii,.nii.gz" onChange={(e) => updateUploadFile("ncct_file", e.target.files?.[0] || null)} /></label>
              <label>MCTA<input type="file" accept=".nii,.nii.gz" onChange={(e) => updateUploadFile("mcta_file", e.target.files?.[0] || null)} /></label>
              <label>VCTA<input type="file" accept=".nii,.nii.gz" onChange={(e) => updateUploadFile("vcta_file", e.target.files?.[0] || null)} /></label>
              <label>DCTA<input type="file" accept=".nii,.nii.gz" onChange={(e) => updateUploadFile("dcta_file", e.target.files?.[0] || null)} /></label>
              <label>CBF<input type="file" accept=".nii,.nii.gz" onChange={(e) => updateUploadFile("cbf_file", e.target.files?.[0] || null)} /></label>
              <label>CBV<input type="file" accept=".nii,.nii.gz" onChange={(e) => updateUploadFile("cbv_file", e.target.files?.[0] || null)} /></label>
              <label>TMAX<input type="file" accept=".nii,.nii.gz" onChange={(e) => updateUploadFile("tmax_file", e.target.files?.[0] || null)} /></label>
            </div>

            <div className="launcher-actions">
              <button className="primary-btn" type="submit" disabled={uploading}>
                {uploading ? "上传并启动中..." : "上传并进入主页面"}
              </button>
            </div>
            {uploadError ? <div className="error-box">{uploadError}</div> : null}
          </form>
          <div className="recent-cases">
            {(bootstrapData?.candidates || []).map((candidate) => (
              <button key={`${candidate.patient_id || "-"}:${candidate.file_id || "-"}:${candidate.run_id || "-"}`} className="recent-case-card" onClick={() => enterCandidate(candidate)}>
                <div className="recent-case-head">
                  <strong>{candidate.label || `patient ${candidate.patient_id || "-"}`}</strong>
                  <span className="chip">{candidate.source || "-"}</span>
                </div>
                <div className="recent-case-meta">
                  <span>patient_id {fmt(candidate.patient_id)}</span>
                  <span>file_id {fmt(candidate.file_id)}</span>
                  <span>run_id {fmt(candidate.run_id)}</span>
                </div>
              </button>
            ))}
          </div>
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
          <span className="chip">run_id {fmt(run.run_id)}</span>
          <span className="chip">patient_id {fmt(run.patient_id || left?.patient?.patient_id)}</span>
          <span className="chip">file_id {fmt(run.file_id)}</span>
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
