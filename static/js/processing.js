let processingJobId = '';
let processingPatientId = '';
let processingFileId = '';
let processingAgentRunId = '';

let processingPollTimer = null;
let agentPollTimer = null;
let processingStartedAt = Date.now();

let uploadWorkflowCompleted = false;
let viewerRedirectScheduled = false;
let agentResultFetched = false;
let retrySubmitting = false;

let latestJobSnapshot = null;
let latestAgentRun = null;
let latestRetryTarget = null;

const PROCESSING_STEP_ORDER = [
    'archive_ready',
    'modality_detect',
    'ctp_generate',
    'stroke_analysis',
    'pseudocolor',
    'ai_report',
];

const AGENT_TERMINAL_STATUSES = new Set(['succeeded', 'failed', 'cancelled']);

function setTextIfPresent(id, value) {
    const el = document.getElementById(id);
    if (el) {
        el.textContent = value;
    }
}

function getAgentPanelElements() {
    return {
        panel: document.getElementById('agentPanel'),
        runId: document.getElementById('processingAgentRunId'),
        status: document.getElementById('agentRunStatus'),
        stage: document.getElementById('agentRunStage'),
        currentTool: document.getElementById('agentCurrentTool'),
        eventCount: document.getElementById('agentEventCount'),
        reportStatus: document.getElementById('agentReportStatus'),
        lastError: document.getElementById('agentLastError'),
        message: document.getElementById('agentRunMessage'),
        retryStep: document.getElementById('agentRetryStep'),
        retryHint: document.getElementById('agentRetryHint'),
        retryActions: document.getElementById('agentRetryActions'),
        retryBtn: document.getElementById('agentRetryActionBtn'),
    };
}

function startAgentPollingIfNeeded() {
    if (!processingAgentRunId) {
        return;
    }
    const els = getAgentPanelElements();
    if (els.runId) {
        els.runId.textContent = processingAgentRunId;
    }
    if (els.panel) {
        els.panel.style.display = 'block';
    }
    if (!agentPollTimer) {
        pollAgentStatus();
        agentPollTimer = setInterval(pollAgentStatus, 1500);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    document.body.classList.add('processing-page-body');

    const params = new URLSearchParams(window.location.search);
    processingJobId = params.get('job_id') || '';
    processingPatientId = params.get('patient_id') || '';
    processingFileId = params.get('file_id') || '';
    processingAgentRunId = params.get('agent_run_id') || '';

    if (!processingAgentRunId && processingFileId) {
        processingAgentRunId = localStorage.getItem(`latest_agent_run_${processingFileId}`) || '';
    }

    if (processingPatientId) {
        setCurrentPatientId(processingPatientId);
        setPatientInfoVisible(true);
        updatePatientHeader(processingPatientId);
    }

    setTextIfPresent('processingPatientId', processingPatientId || '-');
    setTextIfPresent('processingFileId', processingFileId || '-');
    setTextIfPresent('processingJobId', processingJobId || '-');

    const agentEls = getAgentPanelElements();
    if (agentEls.runId) {
        agentEls.runId.textContent = processingAgentRunId || '-';
    }
    if (processingAgentRunId) {
        if (agentEls.message) {
            agentEls.message.textContent = 'Agent 后置汇总运行中...';
        }
        startAgentPollingIfNeeded();
    } else if (agentEls.message) {
        agentEls.message.textContent = '本次上传未启用 Agent 后置汇总。';
    }

    if (!processingJobId) {
        showProcessingError('缺少 job_id，无法轮询上传处理流程。');
        return;
    }

    renderUploadSteps([]);
    pollProcessingStatus();
    processingPollTimer = setInterval(pollProcessingStatus, 1000);
});

function backToUpload() {
    if (processingPatientId) {
        window.location.href = `/upload?patient_id=${encodeURIComponent(processingPatientId)}`;
    } else {
        window.location.href = '/upload';
    }
}

function goToViewerNow() {
    if (!processingFileId) {
        return;
    }
    window.location.href = `/viewer?file_id=${encodeURIComponent(processingFileId)}`;
}

function showProcessingError(message) {
    const errorEl = document.getElementById('processingError');
    errorEl.textContent = message || '上传流程失败';
    errorEl.style.display = 'block';
    document.getElementById('processingRetryBtn').style.display = 'inline-block';
    clearUploadPolling();
}

function clearUploadPolling() {
    if (processingPollTimer) {
        clearInterval(processingPollTimer);
        processingPollTimer = null;
    }
}

function clearAgentPolling() {
    if (agentPollTimer) {
        clearInterval(agentPollTimer);
        agentPollTimer = null;
    }
}

function formatElapsed() {
    const sec = Math.max(0, Math.floor((Date.now() - processingStartedAt) / 1000));
    return `${sec}s`;
}

function defaultStepMessage(status) {
    if (status === 'pending') return '等待执行';
    if (status === 'running') return '执行中';
    if (status === 'completed') return '已完成';
    if (status === 'skipped') return '已跳过';
    if (status === 'failed') return '执行失败';
    return '-';
}

function statusText(status) {
    if (status === 'pending') return '待执行';
    if (status === 'running') return '执行中';
    if (status === 'completed') return '已完成';
    if (status === 'skipped') return '已跳过';
    if (status === 'failed') return '失败';
    return status || '-';
}

function stringifyRunError(errorValue) {
    if (!errorValue) {
        return '-';
    }
    if (typeof errorValue === 'string') {
        return errorValue;
    }
    if (typeof errorValue === 'object') {
        return errorValue.error_message || errorValue.error_code || JSON.stringify(errorValue);
    }
    return String(errorValue);
}

function getDisplayStepsForTimeline(job, run) {
    const originalSteps = Array.isArray(job?.steps) ? job.steps : [];
    const steps = originalSteps.map((step) => ({ ...step }));
    const aiStep = steps.find((step) => step.key === 'ai_report');
    if (!aiStep) {
        return steps;
    }

    aiStep.title = '自动生成结构化报告';

    const agentEnabled = Boolean(job?.agent_run_id || processingAgentRunId);
    if (!agentEnabled || aiStep.status !== 'skipped') {
        return steps;
    }

    if (!run || !run.status) {
        aiStep.status = 'running';
        aiStep.message = '等待 Agent 状态同步';
        return steps;
    }

    if (run.status === 'queued' || run.status === 'running') {
        aiStep.status = 'running';
        aiStep.message = 'Agent 后置汇总正在生成结构化报告...';
        return steps;
    }

    if (run.status === 'succeeded') {
        aiStep.status = 'completed';
        aiStep.message = '结构化报告已由 Agent 生成完成';
        return steps;
    }

    if (run.status === 'failed' || run.status === 'cancelled') {
        aiStep.status = 'failed';
        aiStep.message = `结构化报告生成失败: ${stringifyRunError(run.error)}`;
        return steps;
    }

    aiStep.status = 'running';
    aiStep.message = '等待 Agent 状态同步';
    return steps;
}

function renderUploadSteps(steps) {
    const container = document.getElementById('processingSteps');
    if (!container) {
        return;
    }
    container.innerHTML = '';

    const stepMap = {};
    (steps || []).forEach((step) => {
        stepMap[step.key] = step;
    });

    PROCESSING_STEP_ORDER.forEach((key, index) => {
        const step = stepMap[key] || { key, title: key, status: 'pending', message: '' };
        const card = document.createElement('div');
        card.className = `processing-step step-${step.status || 'pending'}`;
        card.innerHTML = `
            <div class="processing-step-head">
                <span class="processing-step-index">${index + 1}</span>
                <span class="processing-step-title">${step.title || key}</span>
                <span class="processing-step-status">${statusText(step.status)}</span>
            </div>
            <div class="processing-step-msg">${step.message || defaultStepMessage(step.status)}</div>
        `;
        container.appendChild(card);
    });
}

function rerenderTimelineFromSnapshot() {
    if (!latestJobSnapshot) {
        return;
    }
    const displaySteps = getDisplayStepsForTimeline(latestJobSnapshot, latestAgentRun);
    renderUploadSteps(displaySteps);
}

function updateUploadMeta(job) {
    const modalities = (job.modalities || []).length ? job.modalities.join(', ') : '-';
    setTextIfPresent('processingModalities', modalities);
    setTextIfPresent('processingStatus', job.status || '-');
    setTextIfPresent('processingStepName', job.current_step || '-');
    setTextIfPresent('processingElapsed', formatElapsed());
    if (!processingAgentRunId && job.agent_run_id) {
        processingAgentRunId = job.agent_run_id;
        setTextIfPresent('processingAgentRunId', processingAgentRunId);
        startAgentPollingIfNeeded();
    }
}

function updateProgress(progress) {
    const percent = Math.max(0, Math.min(100, Number(progress || 0)));
    document.getElementById('processingProgressFill').style.width = `${percent}%`;
    document.getElementById('processingPercent').textContent = `${percent}%`;
}

function updateCurrentText(job) {
    const currentEl = document.getElementById('processingCurrent');
    const runningStep = (job.steps || []).find((step) => step.status === 'running');
    if (runningStep) {
        currentEl.textContent = `正在执行 ${runningStep.title}: ${runningStep.message || ''}`;
        return;
    }

    if (job.status === 'completed') {
        const warnings = job.warnings || [];
        currentEl.textContent = warnings.length
            ? `上传完成（含告警）: ${warnings.join(' | ')}`
            : '上传主流程已完成。';
        return;
    }

    if (job.status === 'failed') {
        currentEl.textContent = `上传失败: ${job.error || '未知错误'}`;
        return;
    }

    currentEl.textContent = '正在等待上传处理流程...';
}

function persistResultToStorage(job) {
    const result = job.result || {};
    const fileId = result.file_id || processingFileId || job.file_id;
    if (!fileId) {
        return;
    }

    processingFileId = fileId;

    const viewerData = {
        file_id: fileId,
        rgb_files: result.rgb_files || [],
        total_slices: result.total_slices || 0,
        has_ai: result.has_ai || false,
        available_models: result.available_models || [],
        model_configs: result.model_configs || {},
        skip_ai: result.skip_ai || false,
    };

    setViewerData(viewerData);
    sessionStorage.setItem('current_file_id', fileId);
    localStorage.setItem('current_file_id', fileId);

    if (result.report) {
        localStorage.setItem(`ai_report_${fileId}`, result.report);
        localStorage.setItem('ai_report', result.report);
    }
    if (result.report_payload) {
        localStorage.setItem(`ai_report_payload_${fileId}`, JSON.stringify(result.report_payload));
    }
    if (result.json_path) {
        localStorage.setItem(`ai_report_json_path_${fileId}`, result.json_path);
    }

    localStorage.removeItem(`ai_report_generating_${fileId}`);
    localStorage.removeItem(`ai_report_error_${fileId}`);
}

function maybeAutoRedirectToViewer() {
    if (viewerRedirectScheduled) {
        return;
    }
    viewerRedirectScheduled = true;
    setTimeout(() => {
        if (!processingFileId) {
            return;
        }
        window.location.href = `/viewer?file_id=${encodeURIComponent(processingFileId)}`;
    }, 1200);
}

function handleJobCompleted(job) {
    if (uploadWorkflowCompleted) {
        return;
    }

    uploadWorkflowCompleted = true;
    clearUploadPolling();
    persistResultToStorage(job);

    document.getElementById('processingViewerBtn').style.display = 'inline-block';

    if (processingAgentRunId) {
        document.getElementById('processingCurrent').textContent =
            '上传主流程已完成，正在等待 Agent 后置汇总...';
        return;
    }

    document.getElementById('processingCurrent').textContent =
        '上传主流程已完成，正在跳转到 Viewer...';
    maybeAutoRedirectToViewer();
}

async function pollProcessingStatus() {
    try {
        const resp = await fetch(`/api/upload/progress/${encodeURIComponent(processingJobId)}`);
        const data = await resp.json();
        if (!resp.ok || !data.success) {
            showProcessingError(data.error || `无法获取上传进度: ${resp.status}`);
            return;
        }

        const job = data.job || {};
        latestJobSnapshot = job;
        updateProgress(job.progress || 0);
        updateUploadMeta(job);
        rerenderTimelineFromSnapshot();
        updateCurrentText(job);

        if (job.status === 'failed') {
            showProcessingError(job.error || '上传流程失败');
            return;
        }

        if (job.status === 'completed') {
            handleJobCompleted(job);
        }
    } catch (err) {
        showProcessingError(`上传轮询失败: ${err.message}`);
    }
}

function getStepByKey(run, stepKey) {
    return (run.steps || []).find((step) => step.key === stepKey) || null;
}

function getReportStatusText(run) {
    const reportStep = getStepByKey(run, 'generate_medgemma_report');
    const status = reportStep ? reportStep.status : '';
    if (status === 'completed') return '已完成';
    if (status === 'running') return '生成中';
    if (status === 'failed') return '失败';
    if (status === 'skipped') return '已跳过';
    if (run.status === 'succeeded') return '已完成';
    if (run.status === 'failed') return '失败';
    return '未开始';
}

function getLastErrorText(run) {
    if (run.error) {
        return stringifyRunError(run.error);
    }
    const failedStep = [...(run.steps || [])].reverse().find((step) => step.status === 'failed');
    if (failedStep && failedStep.message) {
        return failedStep.message;
    }
    return '-';
}

function getLatestRetryableFailedStep(run) {
    if (!run || !Array.isArray(run.steps)) {
        return null;
    }
    for (let i = run.steps.length - 1; i >= 0; i -= 1) {
        const step = run.steps[i];
        if (step && step.status === 'failed' && step.retryable === true) {
            return step;
        }
    }
    return null;
}

function updateRetryControls(run) {
    const els = getAgentPanelElements();
    if (!els.retryStep || !els.retryHint || !els.retryActions || !els.retryBtn) {
        return;
    }

    latestRetryTarget = getLatestRetryableFailedStep(run);
    const canRetryNow = Boolean(run && run.status === 'failed' && latestRetryTarget);

    if (!canRetryNow) {
        els.retryStep.textContent = '-';
        if (run && run.status === 'failed') {
            els.retryHint.textContent = '当前失败步骤不可重试。';
        } else {
            els.retryHint.textContent = '当前无需重试。';
        }
        els.retryActions.style.display = 'none';
        els.retryBtn.disabled = false;
        els.retryBtn.textContent = '重试失败步骤';
        return;
    }

    const attempts = Number(latestRetryTarget.attempts || 0);
    const title = latestRetryTarget.title || latestRetryTarget.key || '-';
    els.retryStep.textContent = `${title} (${latestRetryTarget.key || '-'})`;
    els.retryHint.textContent = `可重试失败步骤（当前 attempt=${attempts}）。`;
    els.retryActions.style.display = 'flex';
    els.retryBtn.disabled = retrySubmitting;
    els.retryBtn.textContent = retrySubmitting ? '重试提交中...' : '重试失败步骤';
}

async function retryAgentFailedStep() {
    if (retrySubmitting || !processingAgentRunId) {
        return;
    }

    const run = latestAgentRun || {};
    const target = getLatestRetryableFailedStep(run);
    const els = getAgentPanelElements();
    if (!target || run.status !== 'failed') {
        if (els.retryHint) {
            els.retryHint.textContent = '当前没有可重试的失败步骤。';
        }
        updateRetryControls(run);
        return;
    }

    retrySubmitting = true;
    updateRetryControls(run);

    try {
        const resp = await fetch(`/api/agent/runs/${encodeURIComponent(processingAgentRunId)}/retry`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                step_key: target.key,
                reason: 'processing_page_manual_retry',
            }),
        });
        const data = await resp.json();
        if (!resp.ok || !data.success) {
            const errText = data.error || `重试提交失败 (${resp.status})`;
            if (els.retryHint) {
                els.retryHint.textContent = errText;
            }
            return;
        }

        if (els.retryHint) {
            els.retryHint.textContent = `已提交重试：${target.key}`;
        }

        if (latestAgentRun) {
            latestAgentRun.status = 'running';
            latestAgentRun.stage = 'tooling';
            latestAgentRun.current_tool = target.key;
        }
        startAgentPollingIfNeeded();
        await pollAgentStatus();
    } catch (err) {
        if (els.retryHint) {
            els.retryHint.textContent = `重试提交异常: ${err.message}`;
        }
    } finally {
        retrySubmitting = false;
        updateRetryControls(latestAgentRun || run);
    }
}

function updateAgentPanel(run, events) {
    const els = getAgentPanelElements();
    if (els.status) els.status.textContent = run.status || '-';
    if (els.stage) els.stage.textContent = run.stage || '-';
    if (els.currentTool) els.currentTool.textContent = run.current_tool || '-';
    if (els.eventCount) els.eventCount.textContent = String((events || []).length);
    if (els.reportStatus) els.reportStatus.textContent = getReportStatusText(run);
    if (els.lastError) els.lastError.textContent = getLastErrorText(run);
    updateRetryControls(run);

    if (!els.message) {
        return;
    }
    if (run.status === 'running' || run.status === 'queued') {
        els.message.textContent = `Agent 后置汇总运行中: ${run.current_tool || run.stage || '-'}`;
        return;
    }
    if (run.status === 'succeeded') {
        els.message.textContent = 'Agent 后置汇总已完成。';
        return;
    }
    if (run.status === 'failed') {
        els.message.textContent = `Agent 后置汇总失败（不影响影像处理）: ${getLastErrorText(run)}`;
        return;
    }
    if (run.status === 'cancelled') {
        els.message.textContent = 'Agent 后置汇总已取消。';
        return;
    }
    els.message.textContent = `Agent 状态: ${run.status || '-'}`;
}

async function pollAgentStatus() {
    if (!processingAgentRunId) {
        return;
    }

    const els = getAgentPanelElements();

    try {
        const [runResp, eventsResp] = await Promise.all([
            fetch(`/api/agent/runs/${encodeURIComponent(processingAgentRunId)}`),
            fetch(`/api/agent/runs/${encodeURIComponent(processingAgentRunId)}/events`),
        ]);

        const runData = await runResp.json();
        const eventsData = await eventsResp.json();

        if (!runResp.ok || !runData.success) {
            if (els.message) {
                els.message.textContent = runData.error || `获取 run 状态失败 (${runResp.status})`;
            }
            return;
        }
        if (!eventsResp.ok || !eventsData.success) {
            if (els.message) {
                els.message.textContent = eventsData.error || `获取 events 失败 (${eventsResp.status})`;
            }
            return;
        }

        const run = runData.run || {};
        const events = eventsData.events || [];
        latestAgentRun = run;
        updateAgentPanel(run, events);
        rerenderTimelineFromSnapshot();

        if (run.status === 'succeeded' && !agentResultFetched) {
            const resultResp = await fetch(`/api/agent/runs/${encodeURIComponent(processingAgentRunId)}/result`);
            if (resultResp.ok) {
                const resultData = await resultResp.json();
                const reportResult = (((resultData || {}).result || {}).report_result || {});
                if (resultData.success && reportResult.report && processingFileId) {
                    localStorage.setItem(`ai_report_${processingFileId}`, reportResult.report);
                }
            }
            agentResultFetched = true;
        }

        if (AGENT_TERMINAL_STATUSES.has(run.status)) {
            clearAgentPolling();
            if (run.status === 'succeeded' && uploadWorkflowCompleted) {
                document.getElementById('processingCurrent').textContent =
                    '上传主流程 + Agent 后置汇总已完成，正在跳转到 Viewer...';
                maybeAutoRedirectToViewer();
            }
            if (run.status === 'failed' && uploadWorkflowCompleted) {
                document.getElementById('processingCurrent').textContent =
                    '上传主流程已完成，但 Agent 后置汇总失败。可直接进入 Viewer。';
                document.getElementById('processingViewerBtn').style.display = 'inline-block';
            }
        }
    } catch (err) {
        if (els.message) {
            els.message.textContent = `Agent 轮询失败: ${err.message}`;
        }
    }
}
