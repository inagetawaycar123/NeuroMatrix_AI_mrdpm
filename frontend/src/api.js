function getApiBaseUrl() {
  const configured = (import.meta.env.VITE_API_BASE_URL || "").trim();
  if (configured) return configured.replace(/\/$/, "");
  if (typeof window !== "undefined" && window.location && window.location.origin) {
    return window.location.origin;
  }
  return "";
}

function buildApiUrl(path) {
  const base = getApiBaseUrl();
  if (!base) return path;
  return `${base}${path.startsWith("/") ? path : `/${path}`}`;
}

async function requestJson(path) {
  const resp = await fetch(buildApiUrl(path), {
    headers: {
      Accept: "application/json",
    },
  });
  const contentType = (resp.headers.get("content-type") || "").toLowerCase();
  const rawText = await resp.text();
  if (!contentType.includes("application/json")) {
    const preview = rawText.trim().slice(0, 120);
    throw new Error(
      `API returned non-JSON response (${resp.status}). ` +
        `Check backend URL/proxy. Response preview: ${preview || "<empty>"}`
    );
  }
  let data;
  try {
    data = JSON.parse(rawText);
  } catch (err) {
    throw new Error(
      `API returned invalid JSON (${resp.status}). ` +
        `Response preview: ${rawText.trim().slice(0, 120) || "<empty>"}`
    );
  }
  if (!resp.ok || !data.success) {
    throw new Error(data.error || `request failed: ${resp.status}`);
  }
  return data;
}

export async function fetchOverview({ runId, fileId, patientId }) {
  const params = new URLSearchParams();
  if (runId) params.set("run_id", String(runId));
  if (fileId) params.set("file_id", String(fileId));
  if (patientId) params.set("patient_id", String(patientId));
  return requestJson(`/api/cockpit/overview?${params.toString()}`);
}

export async function fetchBootstrap(limit = 6) {
  const normalizeTask = (task) => {
    const lastRun = task?.last_run || {};
    return {
      patient_id: task?.patient_id ?? null,
      file_id: String(task?.file_id || "").trim(),
      run_id: String(lastRun?.run_id || "").trim(),
      source: task?.source || "task_center",
      timestamp: String(task?.updated_at || "").trim(),
      available_modalities: Array.isArray(task?.available_modalities)
        ? task.available_modalities
        : [],
      hemisphere: String(task?.hemisphere || "").trim() || "both",
      status: String(task?.status || "").trim(),
      stage: String(lastRun?.stage || "").trim(),
      label: task?.patient_name
        ? `${task.patient_name} · ${String(task?.file_id || "").trim()}`
        : `patient ${task?.patient_id || "-"} · ${String(task?.file_id || "").trim()}`,
    };
  };

  const normalizeCockpitCandidate = (candidate) => ({
    patient_id: candidate?.patient_id ?? null,
    file_id: String(candidate?.file_id || "").trim(),
    run_id: String(candidate?.run_id || "").trim(),
    source: candidate?.source || "cockpit",
    timestamp: String(candidate?.timestamp || "").trim(),
    available_modalities: Array.isArray(candidate?.available_modalities)
      ? candidate.available_modalities
      : [],
    hemisphere: String(candidate?.hemisphere || "").trim() || "both",
    status: String(candidate?.status || "").trim(),
    stage: String(candidate?.stage || "").trim(),
    label: candidate?.label || `patient ${candidate?.patient_id || "-"} · ${String(candidate?.file_id || "").trim()}`,
  });

  const mergeCandidates = (items) => {
    const merged = [];
    const seen = new Set();
    for (const item of items) {
      const key = `${String(item?.run_id || "").trim()}|${String(item?.file_id || "").trim()}|${String(item?.patient_id || "").trim()}`;
      if (!key || seen.has(key)) continue;
      seen.add(key);
      merged.push(item);
    }
    merged.sort((a, b) => String(b.timestamp || "").localeCompare(String(a.timestamp || "")));
    return merged;
  };

  const tasksResp = await requestJson(`/api/strokeclaw/tasks?limit=${encodeURIComponent(String(limit))}`);
  const tasks = Array.isArray(tasksResp.tasks) ? tasksResp.tasks : [];
  let candidates = tasks
    .map((task) => {
      return normalizeTask(task);
    })
    .filter((item) => item.file_id || item.run_id || item.patient_id);

  if (candidates.length === 0) {
    try {
      const cockpitResp = await requestJson(`/api/cockpit/bootstrap?limit=${encodeURIComponent(String(limit))}`);
      const cockpitCandidates = Array.isArray(cockpitResp.candidates) ? cockpitResp.candidates.map(normalizeCockpitCandidate) : [];
      candidates = mergeCandidates(cockpitCandidates);
    } catch (_err) {
      candidates = [];
    }
  } else {
    try {
      const cockpitResp = await requestJson(`/api/cockpit/bootstrap?limit=${encodeURIComponent(String(limit))}`);
      const cockpitCandidates = Array.isArray(cockpitResp.candidates) ? cockpitResp.candidates.map(normalizeCockpitCandidate) : [];
      candidates = mergeCandidates([...candidates, ...cockpitCandidates]);
    } catch (_err) {
      candidates = mergeCandidates(candidates);
    }
  }

  return {
    success: true,
    candidates,
    latest_candidate: candidates[0] || null,
    latest_run: candidates[0] || null,
    has_ready_target: candidates.length > 0,
    source: tasksResp.source || "task_center",
    count: tasksResp.count ?? candidates.length,
  };
}

export async function fetchNodeDetail(runId, nodeKey) {
  return requestJson(
    `/api/cockpit/runs/${encodeURIComponent(runId)}/nodes/${encodeURIComponent(nodeKey)}`
  );
}
