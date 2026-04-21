export async function fetchOverview({ runId, fileId, patientId }) {
  const params = new URLSearchParams();
  if (runId) params.set("run_id", String(runId));
  if (fileId) params.set("file_id", String(fileId));
  if (patientId) params.set("patient_id", String(patientId));
  const resp = await fetch(`/api/cockpit/overview?${params.toString()}`);
  const data = await resp.json();
  if (!resp.ok || !data.success) {
    throw new Error(data.error || `overview request failed: ${resp.status}`);
  }
  return data;
}

export async function fetchNodeDetail(runId, nodeKey) {
  const resp = await fetch(
    `/api/cockpit/runs/${encodeURIComponent(runId)}/nodes/${encodeURIComponent(nodeKey)}`
  );
  const data = await resp.json();
  if (!resp.ok || !data.success) {
    throw new Error(data.error || `node request failed: ${resp.status}`);
  }
  return data;
}
