let cockpitRunId = '';
let cockpitFileId = '';
let cockpitPatientId = '';

let cockpitRun = null;
let cockpitEvents = [];
let cockpitResult = null;
let cockpitValidation = null;

let cockpitPollTimer = null;
const COCKPIT_TERMINAL = new Set(['succeeded', 'failed', 'cancelled']);

const STATUS_TEXT_MAP = {
    queued: '排队中',
    running: '执行中',
    succeeded: '成功',
    failed: '失败',
    cancelled: '已取消',
    pending: '待执行',
    completed: '已完成',
    skipped: '已跳过',
    pass: '通过',
    warn: '警告',
    fail: '失败',
    unavailable: '不可用',
};

const STAGE_TEXT_MAP = {
    triage: '分诊',
    tooling: '工具执行',
    icv: '内在一致性校验',
    ekv: '外部证据校验',
    consensus: '一致性裁决',
    summary: '汇总',
    done: '完成',
};

const CONSENSUS_TEXT_MAP = {
    accept: '接受',
    review_required: '需复核',
    escalate: '需升级处理',
    unavailable: '不可用',
    skipped: '已跳过',
};

const SOURCE_CHAIN_TEXT_MAP = {
    none: '无',
    case_latest_result_json: '病例最新结果',
    run_result: '运行结果',
    run_result_by_id: '指定运行结果',
    agent_run_result: '智能体运行结果',
    report_payload: '报告载荷',
    local_storage_fallback: '本地缓存兜底',
};

function setText(id, value) {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = value ?? '-';
}

function mapTokenText(value, map) {
    const raw = String(value || '').trim();
    if (!raw) return '-';
    const key = raw.toLowerCase();
    return map[key] || raw;
}

function statusText(value) {
    return mapTokenText(value, STATUS_TEXT_MAP);
}

function stageText(value) {
    return mapTokenText(value, STAGE_TEXT_MAP);
}

function consensusText(value) {
    return mapTokenText(value, CONSENSUS_TEXT_MAP);
}

function sourceChainText(value) {
    return mapTokenText(value, SOURCE_CHAIN_TEXT_MAP);
}

function hasChinese(text) {
    return /[\u4e00-\u9fff]/.test(String(text || ''));
}

function statusClass(value) {
    const token = String(value || '').toLowerCase().replace(/\s+/g, '_');
    return token ? `status-${token}` : '';
}

function formatTime(value) {
    if (!value) return '-';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return date.toLocaleString();
}

function formatLatency(ms) {
    const n = Number(ms);
    if (!Number.isFinite(n) || n < 0) return '-';
    return `${Math.round(n)}ms`;
}

function formatPercentFromFraction(value) {
    const n = Number(value);
    if (!Number.isFinite(n)) return '-';
    return `${(n * 100).toFixed(1)}%`;
}

function getQueryParamsWithContext(extra = {}) {
    const params = new URLSearchParams();
    const runId = extra.run_id || cockpitRunId;
    const fileId = extra.file_id || cockpitFileId;
    const patientId = extra.patient_id || cockpitPatientId;
    if (runId) params.set('run_id', runId);
    if (fileId) params.set('file_id', fileId);
    if (patientId) params.set('patient_id', String(patientId));
    Object.entries(extra).forEach(([k, v]) => {
        if (!v || ['run_id', 'file_id', 'patient_id'].includes(k)) return;
        params.set(k, String(v));
    });
    return params;
}

function getViewerUrl() {
    if (!cockpitFileId) return '/viewer';
    const params = getQueryParamsWithContext();
    return `/viewer?${params.toString()}`;
}

function getReportUrl() {
    if (!cockpitPatientId) return '/';
    const params = getQueryParamsWithContext();
    return `/report/${encodeURIComponent(cockpitPatientId)}?${params.toString()}`;
}

function getValidationUrl(tab = 'ekv') {
    const params = getQueryParamsWithContext({ tab });
    return `/validation?${params.toString()}`;
}

function goBackViewer() {
    window.location.href = getViewerUrl();
}

function goBackReport() {
    if (!cockpitPatientId) {
        window.location.href = '/';
        return;
    }
    window.location.href = getReportUrl();
}

function goBackValidation() {
    window.location.href = getValidationUrl('ekv');
}

function parseCockpitParams() {
    const params = new URLSearchParams(window.location.search);
    cockpitRunId = (params.get('run_id') || '').trim();
    cockpitFileId = (params.get('file_id') || sessionStorage.getItem('current_file_id') || '').trim();
    cockpitPatientId = (params.get('patient_id') || getCurrentPatientId() || '').trim();

    if (!cockpitRunId && cockpitFileId) {
        cockpitRunId = (localStorage.getItem(`latest_agent_run_${cockpitFileId}`) || '').trim();
    }

    if (typeof setCurrentPatientId === 'function' && cockpitPatientId) {
        setCurrentPatientId(cockpitPatientId);
    }
    if (typeof setPatientInfoVisible === 'function') {
        setPatientInfoVisible(Boolean(cockpitPatientId));
    }
    if (typeof updatePatientHeader === 'function' && cockpitPatientId) {
        updatePatientHeader(cockpitPatientId);
    }
}

function persistRunContext() {
    if (cockpitFileId && cockpitRunId) {
        localStorage.setItem(`latest_agent_run_${cockpitFileId}`, cockpitRunId);
    }
}

function updateMeta(run = {}, events = []) {
    const runId = run.run_id || cockpitRunId || '-';
    const patientId = run.patient_id || cockpitPatientId || '-';
    const fileId = run.file_id || cockpitFileId || '-';
    const stage = stageText(run.stage || '-');
    const status = statusText(run.status || '-');

    setText('metaRunId', runId);
    setText('metaPatientId', patientId);
    setText('metaFileId', fileId);
    setText('metaRunStatus', status);
    setText('metaRunStage', stage);
    setText('metaCurrentTool', run.current_tool || '-');
    setText('metaEventCount', String(events.length || 0));
    setText('metaUpdatedAt', formatTime(run.updated_at || run.created_at));
}

function computeLastError(run) {
    if (!run || typeof run !== 'object') return '-';
    if (run.error) {
        if (typeof run.error === 'string') return run.error;
        return run.error.error_message || run.error.error_code || JSON.stringify(run.error);
    }
    const failedStep = [...(run.steps || [])].reverse().find((s) => s && s.status === 'failed');
    if (failedStep && failedStep.message) return failedStep.message;
    const status = String(run.status || '').toLowerCase();
    if (['queued', 'running', 'succeeded', 'cancelled'].includes(status)) return '无';
    return '-';
}

function computeRetryableStep(run) {
    if (!run || !Array.isArray(run.steps)) return '-';
    const step = [...run.steps].reverse().find((s) => s && s.status === 'failed' && s.retryable === true);
    if (!step) return '无';
    const title = step.title || step.key || '-';
    const attempts = Number(step.attempts || 0);
    return `${title} (${step.key || '-'}, attempt=${attempts})`;
}

function toSummaryCount(status, count, listLike) {
    const statusToken = String(status || '').toLowerCase();
    if (statusToken !== 'unavailable') {
        return String(Number.isFinite(Number(count)) ? Number(count) : 0);
    }
    if (Array.isArray(listLike) && listLike.length > 0) {
        return String(Number.isFinite(Number(count)) ? Number(count) : listLike.length);
    }
    return '-';
}

function renderRunSummary(run, validation, resultResp) {
    const reportReady = resultResp?.ok || String(run?.status || '').toLowerCase() === 'succeeded';
    setText('summaryResultStatus', reportReady ? '可读取' : '待完成');
    setText('summaryLastError', computeLastError(run));
    setText('summaryRetryStep', computeRetryableStep(run));

    const meta = validation?.meta || {};
    setText('summarySourceChain', sourceChainText(meta.source_chain || '-'));

    const icv = validation?.icv || {};
    const ekv = validation?.ekv || {};
    const consensus = validation?.consensus || {};
    const traceability = validation?.traceability || {};

    setText('summaryIcvStatus', statusText(icv.status || '-'));
    const icvCount = Number.isFinite(Number(icv.finding_count))
        ? Number(icv.finding_count)
        : (Array.isArray(icv.findings) ? icv.findings.length : 0);
    setText('summaryIcvFindings', toSummaryCount(icv.status, icvCount, icv.findings));

    setText('summaryEkvStatus', statusText(ekv.status || '-'));
    const ekvCount = Number.isFinite(Number(ekv.finding_count))
        ? Number(ekv.finding_count)
        : (Array.isArray(ekv.findings) ? ekv.findings.length : 0);
    setText('summaryEkvFindings', toSummaryCount(ekv.status, ekvCount, ekv.findings || ekv.claims));
    if (String(ekv.status || '').toLowerCase() === 'unavailable') {
        setText('summaryEkvSupportRate', '-');
    } else {
        setText('summaryEkvSupportRate', formatPercentFromFraction(ekv.support_rate));
    }

    setText('summaryConsensusStatus', statusText(consensus.status || '-'));
    const decisionRaw = String(consensus.decision || '').toLowerCase();
    if (decisionRaw) {
        setText('summaryConsensusDecision', consensusText(decisionRaw));
    } else if (String(consensus.status || '').toLowerCase() === 'skipped') {
        setText('summaryConsensusDecision', consensusText('accept'));
    } else {
        setText('summaryConsensusDecision', '-');
    }
    const conflictCount = Number.isFinite(Number(consensus.conflict_count))
        ? Number(consensus.conflict_count)
        : (Array.isArray(consensus.conflicts) ? consensus.conflicts.length : 0);
    setText('summaryConsensusConflicts', toSummaryCount(consensus.status, conflictCount, consensus.conflicts));

    setText('summaryTraceStatus', statusText(traceability.status || '-'));
    if (String(traceability.status || '').toLowerCase() === 'unavailable') {
        setText('summaryTraceCoverage', '-');
    } else {
        setText('summaryTraceCoverage', formatPercentFromFraction(traceability.coverage));
    }
    const mapped = Number.isFinite(Number(traceability.mapped_findings)) ? Number(traceability.mapped_findings) : '-';
    const total = Number.isFinite(Number(traceability.total_findings)) ? Number(traceability.total_findings) : '-';
    setText('summaryTraceMapped', `${mapped}/${total}`);
    setText(
        'summaryTraceUnmapped',
        Number.isFinite(Number(traceability.unmapped_count))
            ? Number(traceability.unmapped_count)
            : (Array.isArray(traceability.unmapped_ids) ? traceability.unmapped_ids.length : '-')
    );
    setText(
        'summaryTraceHighRisk',
        Number.isFinite(Number(traceability.high_risk_unmapped_count))
            ? Number(traceability.high_risk_unmapped_count)
            : '-'
    );
}

function renderStepTimeline(run) {
    const wrap = document.getElementById('stepTimeline');
    if (!wrap) return;
    wrap.innerHTML = '';
    const steps = Array.isArray(run?.steps) ? run.steps : [];
    if (steps.length === 0) {
        wrap.innerHTML = '<div class="empty-block">当前运行还没有步骤轨迹。</div>';
        return;
    }
    steps.forEach((step, idx) => {
        const item = document.createElement('div');
        item.className = 'step-item';
        const status = String(step.status || 'pending');
        item.innerHTML = `
            <div class="step-item-head">
                <div class="step-item-title">${idx + 1}. ${step.title || step.key || '-'}</div>
                <div class="badge ${statusClass(status)}">${statusText(status)}</div>
            </div>
            <div class="step-item-meta">
                <div>key: ${step.key || '-'}</div>
                <div>attempt: ${step.attempts || 0} | retryable: ${step.retryable === true ? 'true' : 'false'}</div>
                <div>message: ${step.message || '-'}</div>
                <div>started: ${formatTime(step.started_at)} | ended: ${formatTime(step.ended_at)}</div>
            </div>
        `;
        wrap.appendChild(item);
    });
}

function uniqueValues(items, getter) {
    const set = new Set();
    items.forEach((item) => {
        const value = getter(item);
        if (value) set.add(value);
    });
    return Array.from(set.values());
}

function updateEventFilterOptions(events) {
    const stageSel = document.getElementById('eventStageFilter');
    const statusSel = document.getElementById('eventStatusFilter');
    const toolSel = document.getElementById('eventToolFilter');
    if (!stageSel || !statusSel || !toolSel) return;

    const preserve = {
        stage: stageSel.value || 'all',
        status: statusSel.value || 'all',
        tool: toolSel.value || 'all',
    };

    const stages = uniqueValues(events, (e) => String(e.stage || '').trim().toLowerCase()).sort();
    const statuses = uniqueValues(events, (e) => String(e.status || '').trim().toLowerCase()).sort();
    const tools = uniqueValues(events, (e) => String(e.tool_name || '').trim()).sort();

    const fill = (el, options, labelMapper) => {
        const old = el.value || 'all';
        el.innerHTML = '<option value="all">全部</option>';
        options.forEach((opt) => {
            const node = document.createElement('option');
            node.value = opt;
            node.textContent = labelMapper(opt);
            el.appendChild(node);
        });
        if (options.includes(old)) {
            el.value = old;
        } else if (options.includes(preserve[el.id.includes('Stage') ? 'stage' : el.id.includes('Status') ? 'status' : 'tool'])) {
            el.value = preserve[el.id.includes('Stage') ? 'stage' : el.id.includes('Status') ? 'status' : 'tool'];
        } else {
            el.value = 'all';
        }
    };

    fill(stageSel, stages, (x) => stageText(x));
    fill(statusSel, statuses, (x) => statusText(x));
    fill(toolSel, tools, (x) => x);
}

function getFilteredEvents(events) {
    const stageFilter = (document.getElementById('eventStageFilter')?.value || 'all').toLowerCase();
    const statusFilter = (document.getElementById('eventStatusFilter')?.value || 'all').toLowerCase();
    const toolFilter = (document.getElementById('eventToolFilter')?.value || 'all');

    return [...events]
        .sort((a, b) => Number(a.event_seq || 0) - Number(b.event_seq || 0))
        .filter((event) => {
            const stage = String(event.stage || '').toLowerCase();
            const status = String(event.status || '').toLowerCase();
            const tool = String(event.tool_name || '');
            if (stageFilter !== 'all' && stage !== stageFilter) return false;
            if (statusFilter !== 'all' && status !== statusFilter) return false;
            if (toolFilter !== 'all' && tool !== toolFilter) return false;
            return true;
        });
}

function renderEventTimeline(events) {
    const wrap = document.getElementById('eventTimeline');
    if (!wrap) return;
    wrap.innerHTML = '';
    const filtered = getFilteredEvents(events);
    if (filtered.length === 0) {
        wrap.innerHTML = '<div class="empty-block">当前筛选条件下无事件。</div>';
        return;
    }

    filtered.forEach((event) => {
        const status = String(event.status || '');
        const item = document.createElement('div');
        item.className = 'event-item';
        const toolName = event.tool_name || '-';
        const title = `#${event.event_seq || '-'} | ${toolName}`;
        const errorCode = event.error_code || '-';
        item.innerHTML = `
            <div class="event-item-head">
                <div class="event-item-title">${title}</div>
                <div class="badge ${statusClass(status)}">${statusText(status)}</div>
            </div>
            <div class="event-item-meta">
                <div>stage: ${stageText(event.stage || '-')} | attempt: ${event.attempt || 0} | retryable: ${event.retryable === true ? 'true' : 'false'}</div>
                <div>latency: ${formatLatency(event.latency_ms)} | error_code: ${errorCode}</div>
                <div>timestamp: ${formatTime(event.timestamp)}</div>
            </div>
        `;
        wrap.appendChild(item);
    });
}

function updateHint(message, isError = false) {
    const hint = document.getElementById('cockpitHint');
    if (!hint) return;
    hint.textContent = message;
    hint.style.color = isError ? '#fca5a5' : '#9fb4d6';
}

function bindEntryButtons() {
    const viewerBtn = document.getElementById('gotoViewerBtn');
    const reportBtn = document.getElementById('gotoReportBtn');
    const validationBtn = document.getElementById('gotoValidationBtn');

    if (viewerBtn) {
        viewerBtn.onclick = () => {
            window.location.href = getViewerUrl();
        };
    }
    if (reportBtn) {
        reportBtn.onclick = () => {
            window.location.href = getReportUrl();
        };
    }
    if (validationBtn) {
        validationBtn.onclick = () => {
            window.location.href = getValidationUrl('ekv');
        };
    }
}

function bindActions() {
    document.getElementById('refreshCockpitBtn')?.addEventListener('click', () => {
        fetchCockpitData(true);
    });

    document.getElementById('copyRunIdBtn')?.addEventListener('click', async () => {
        if (!cockpitRunId) {
            updateHint('当前没有可复制的 run_id。');
            return;
        }
        try {
            await navigator.clipboard.writeText(cockpitRunId);
            updateHint(`已复制 run_id: ${cockpitRunId}`);
        } catch (err) {
            updateHint(`复制失败: ${err.message}`, true);
        }
    });

    document.getElementById('exportTraceBtn')?.addEventListener('click', () => {
        exportTraceText();
    });

    ['eventStageFilter', 'eventStatusFilter', 'eventToolFilter'].forEach((id) => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('change', () => renderEventTimeline(cockpitEvents));
        }
    });
}

function exportTraceText() {
    if (!cockpitRunId && !cockpitFileId) {
        updateHint('没有可导出的轨迹上下文。');
        return;
    }
    const lines = [];
    lines.push(`run_id: ${cockpitRunId || '-'}`);
    lines.push(`patient_id: ${cockpitPatientId || '-'}`);
    lines.push(`file_id: ${cockpitFileId || '-'}`);
    lines.push(`status: ${cockpitRun?.status || '-'}`);
    lines.push(`stage: ${cockpitRun?.stage || '-'}`);
    lines.push(`current_tool: ${cockpitRun?.current_tool || '-'}`);
    lines.push('');
    lines.push('[steps]');
    (cockpitRun?.steps || []).forEach((step, idx) => {
        lines.push(
            `${idx + 1}. key=${step.key || '-'} title=${step.title || '-'} status=${step.status || '-'} attempts=${step.attempts || 0} retryable=${step.retryable === true}`
        );
        lines.push(`   message=${step.message || '-'}`);
    });
    lines.push('');
    lines.push('[events]');
    cockpitEvents
        .slice()
        .sort((a, b) => Number(a.event_seq || 0) - Number(b.event_seq || 0))
        .forEach((event) => {
            lines.push(
                `#${event.event_seq || '-'} stage=${event.stage || '-'} tool=${event.tool_name || '-'} status=${event.status || '-'} attempt=${event.attempt || 0} latency=${event.latency_ms || 0}ms error_code=${event.error_code || '-'}`
            );
        });

    const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' });
    const anchor = document.createElement('a');
    const ts = new Date().toISOString().replace(/[:.]/g, '-');
    const fileName = `cockpit_trace_${cockpitRunId || cockpitFileId || 'unknown'}_${ts}.txt`;
    anchor.href = URL.createObjectURL(blob);
    anchor.download = fileName;
    anchor.click();
    URL.revokeObjectURL(anchor.href);
    updateHint(`轨迹导出成功: ${fileName}`);
}

function parseResultPayload(resultResp) {
    if (!resultResp || typeof resultResp !== 'object') return null;
    const resultObj = resultResp.data?.result || cockpitRun?.result || null;
    if (!resultObj || typeof resultObj !== 'object') return null;
    return (resultObj.report_result || {}).report_payload || null;
}

async function fetchCockpitData(isManual = false) {
    parseCockpitParams();
    bindEntryButtons();
    persistRunContext();

    if (!cockpitRunId) {
        updateMeta({}, []);
        renderStepTimeline(null);
        updateEventFilterOptions([]);
        renderEventTimeline([]);
        updateHint('未提供 run_id，请从 processing/viewer/report 页面进入，或在 URL 追加 run_id。');
        stopPolling();
        return;
    }

    if (isManual) {
        updateHint('正在刷新运行轨迹...');
    }

    const runUrl = `/api/agent/runs/${encodeURIComponent(cockpitRunId)}`;
    const eventsUrl = `/api/agent/runs/${encodeURIComponent(cockpitRunId)}/events`;
    const resultUrl = `/api/agent/runs/${encodeURIComponent(cockpitRunId)}/result`;
    const validationParams = getQueryParamsWithContext();
    const validationUrl = `/api/validation/context?${validationParams.toString()}`;

    try {
        const [runResp, eventsResp, resultRespRaw, validationResp] = await Promise.all([
            fetch(runUrl),
            fetch(eventsUrl),
            fetch(resultUrl),
            fetch(validationUrl),
        ]);

        const runData = await runResp.json();
        const eventsData = await eventsResp.json();
        const resultData = await resultRespRaw.json().catch(() => ({}));
        const validationData = await validationResp.json().catch(() => ({}));

        if (!runResp.ok || !runData.success) {
            throw new Error(runData.error || `获取 run 失败 (${runResp.status})`);
        }
        if (!eventsResp.ok || !eventsData.success) {
            throw new Error(eventsData.error || `获取 events 失败 (${eventsResp.status})`);
        }

        cockpitRun = runData.run || {};
        cockpitEvents = Array.isArray(eventsData.events) ? eventsData.events : [];
        cockpitResult = {
            ok: resultRespRaw.ok && resultData.success,
            status: resultRespRaw.status,
            data: resultData,
        };
        cockpitValidation = validationData && validationData.success ? validationData : null;

        cockpitFileId = String(cockpitRun.file_id || cockpitValidation?.meta?.file_id || cockpitFileId || '').trim();
        cockpitPatientId = String(cockpitRun.patient_id || cockpitValidation?.meta?.patient_id || cockpitPatientId || '').trim();
        persistRunContext();

        updateMeta(cockpitRun, cockpitEvents);
        renderStepTimeline(cockpitRun);
        updateEventFilterOptions(cockpitEvents);
        renderEventTimeline(cockpitEvents);
        renderRunSummary(cockpitRun, cockpitValidation, cockpitResult);

        const payload = parseResultPayload(cockpitResult);
        if (payload && cockpitFileId) {
            localStorage.setItem(`ai_report_payload_${cockpitFileId}`, JSON.stringify(payload));
        }

        if (COCKPIT_TERMINAL.has(String(cockpitRun.status || '').toLowerCase())) {
            stopPolling();
            updateHint(`运行已结束：${statusText(cockpitRun.status || '-')}`);
        } else {
            startPolling();
            updateHint(`运行进行中：${stageText(cockpitRun.stage || '-')} / ${cockpitRun.current_tool || '-'}`);
        }
    } catch (err) {
        updateHint(`加载失败：${err.message}`, true);
        stopPolling();
    }
}

function startPolling() {
    if (cockpitPollTimer) return;
    cockpitPollTimer = setInterval(() => {
        fetchCockpitData(false);
    }, 1500);
}

function stopPolling() {
    if (!cockpitPollTimer) return;
    clearInterval(cockpitPollTimer);
    cockpitPollTimer = null;
}

document.addEventListener('DOMContentLoaded', () => {
    document.body.classList.add('cockpit-page-body');
    bindActions();
    bindEntryButtons();
    fetchCockpitData(true);
});

window.goBackViewer = goBackViewer;
window.goBackReport = goBackReport;
window.goBackValidation = goBackValidation;
