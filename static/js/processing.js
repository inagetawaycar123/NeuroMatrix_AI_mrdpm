let processingJobId = '';
let processingPatientId = '';
let processingFileId = '';
let processingPollTimer = null;
let processingStartedAt = Date.now();
let processingCompleted = false;

const PROCESSING_STEP_ORDER = [
    'archive_ready',
    'modality_detect',
    'ctp_generate',
    'stroke_analysis',
    'pseudocolor',
    'ai_report',
];

document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    processingJobId = params.get('job_id') || '';
    processingPatientId = params.get('patient_id') || '';
    processingFileId = params.get('file_id') || '';

    if (processingPatientId) {
        setCurrentPatientId(processingPatientId);
        setPatientInfoVisible(true);
        updatePatientHeader(processingPatientId);
    }

    document.getElementById('processingPatientId').textContent = processingPatientId || '-';
    document.getElementById('processingFileId').textContent = processingFileId || '-';
    document.getElementById('processingJobId').textContent = processingJobId || '-';

    if (!processingJobId) {
        showProcessingError('缺少 job_id，无法查询处理进度。');
        return;
    }

    renderSteps([]);
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
    if (!processingFileId) return;
    window.location.href = `/viewer?file_id=${encodeURIComponent(processingFileId)}`;
}

function showProcessingError(message) {
    const errorEl = document.getElementById('processingError');
    errorEl.textContent = message || '处理失败';
    errorEl.style.display = 'block';
    document.getElementById('processingRetryBtn').style.display = 'inline-block';
    clearPolling();
}

function clearPolling() {
    if (processingPollTimer) {
        clearInterval(processingPollTimer);
        processingPollTimer = null;
    }
}

function formatElapsed() {
    const sec = Math.max(0, Math.floor((Date.now() - processingStartedAt) / 1000));
    return `${sec}s`;
}

function renderSteps(steps) {
    const container = document.getElementById('processingSteps');
    container.innerHTML = '';

    const stepMap = {};
    (steps || []).forEach((s) => {
        stepMap[s.key] = s;
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

function defaultStepMessage(status) {
    if (status === 'pending') return '等待执行';
    if (status === 'running') return '正在处理';
    if (status === 'completed') return '已完成';
    if (status === 'skipped') return '已跳过';
    if (status === 'failed') return '执行失败';
    return '-';
}

function statusText(status) {
    if (status === 'pending') return '待执行';
    if (status === 'running') return '进行中';
    if (status === 'completed') return '完成';
    if (status === 'skipped') return '跳过';
    if (status === 'failed') return '失败';
    return status || '-';
}

function updateMeta(job) {
    document.getElementById('processingStatus').textContent = job.status || '-';
    document.getElementById('processingStepName').textContent = job.current_step || '-';
    document.getElementById('processingElapsed').textContent = formatElapsed();
    const modalities = (job.modalities || []).length ? job.modalities.join('、') : '-';
    document.getElementById('processingModalities').textContent = modalities;
}

function updateProgress(progress) {
    const p = Math.max(0, Math.min(100, Number(progress || 0)));
    document.getElementById('processingProgressFill').style.width = `${p}%`;
    document.getElementById('processingPercent').textContent = `${p}%`;
}

function updateCurrentText(job) {
    const currentEl = document.getElementById('processingCurrent');
    const runningStep = (job.steps || []).find((s) => s.status === 'running');
    if (runningStep) {
        currentEl.textContent = `正在执行：${runningStep.title}。${runningStep.message || ''}`;
        return;
    }

    if (job.status === 'completed') {
        const warnings = job.warnings || [];
        currentEl.textContent = warnings.length
            ? `处理完成（含告警）：${warnings.join('；')}`
            : '处理完成，正在准备进入 Viewer...';
        return;
    }

    if (job.status === 'failed') {
        currentEl.textContent = `任务失败：${job.error || '未知错误'}`;
        return;
    }

    currentEl.textContent = '任务已创建，等待系统开始处理...';
}

function persistResultToStorage(job) {
    const result = job.result || {};
    const fileId = result.file_id || processingFileId || job.file_id;
    if (!fileId) return;
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

function handleJobCompleted(job) {
    if (processingCompleted) return;
    processingCompleted = true;
    clearPolling();
    persistResultToStorage(job);

    document.getElementById('processingViewerBtn').style.display = 'inline-block';
    document.getElementById('processingCurrent').textContent = '全部任务已完成，1.2 秒后自动进入 Viewer。';

    setTimeout(() => {
        if (!processingFileId) return;
        window.location.href = `/viewer?file_id=${encodeURIComponent(processingFileId)}`;
    }, 1200);
}

async function pollProcessingStatus() {
    try {
        const resp = await fetch(`/api/upload/progress/${encodeURIComponent(processingJobId)}`);
        const data = await resp.json();
        if (!resp.ok || !data.success) {
            showProcessingError(data.error || `进度接口错误: ${resp.status}`);
            return;
        }

        const job = data.job || {};
        updateProgress(job.progress || 0);
        renderSteps(job.steps || []);
        updateMeta(job);
        updateCurrentText(job);

        if (job.status === 'failed') {
            showProcessingError(job.error || '任务执行失败');
            return;
        }

        if (job.status === 'completed') {
            handleJobCompleted(job);
        }
    } catch (err) {
        showProcessingError(`轮询失败：${err.message}`);
    }
}
