const DEFAULT_UPLOAD_MODE = 'ncct_3phase_cta';

document.addEventListener('DOMContentLoaded', function () {
    const uploadInfo = document.querySelector('.upload-info');
    if (uploadInfo && !uploadInfo.dataset.runtimeHint) {
        uploadInfo.dataset.runtimeHint = '1';
        uploadInfo.innerHTML += '<br>上传成功后将自动进入 StrokeClaw 运行等待页，查看多节点协作过程。';
    }

    const uploadModeSelect = document.getElementById('uploadModeSelect');
    const ctaPhaseSelect = document.getElementById('ctaPhaseSelect');
    const ctaPhaseRow = document.getElementById('ctaPhaseRow');

    const urlParams = new URLSearchParams(window.location.search);
    const patientIdParam = urlParams.get('patient_id');
    if (patientIdParam) {
        setCurrentPatientId(patientIdParam);
    }

    const patientId = getCurrentPatientId();
    if (!patientId) {
        showMsg('缺少 patient_id，正在返回患者列表页。', 'error');
        setTimeout(() => {
            window.location.href = '/patient';
        }, 1000);
        return;
    }

    setPatientInfoVisible(true);
    updatePatientHeader(patientId);

    const mctaInput = document.getElementById('mctaFile');
    const vctaInput = document.getElementById('vctaFile');
    const dctaInput = document.getElementById('dctaFile');
    const ncctInput = document.getElementById('ncctFile');
    const cbfInput = document.getElementById('cbfFile');
    const cbvInput = document.getElementById('cbvFile');
    const tmaxInput = document.getElementById('tmaxFile');
    const questionInput = document.getElementById('agentQuestion');
    const agentToggle = document.getElementById('agentRunToggle');

    function isValidNiftiFile(file) {
        if (!file || !file.name) {
            return false;
        }
        const lowerName = file.name.toLowerCase();
        return lowerName.endsWith('.nii') || lowerName.endsWith('.nii.gz');
    }

    function validateNiftiOrReset(inputEl, label) {
        const file = inputEl && inputEl.files ? inputEl.files[0] : null;
        if (!file) {
            return true;
        }
        if (isValidNiftiFile(file)) {
            return true;
        }
        inputEl.value = '';
        showMsg(`${label} 文件必须是 .nii 或 .nii.gz`, 'error');
        return false;
    }

    function getRowByInputId(id) {
        const el = document.getElementById(id);
        return el ? el.parentElement : null;
    }

    function updateUIByMode() {
        const mode = uploadModeSelect ? uploadModeSelect.value : DEFAULT_UPLOAD_MODE;
        if (ctaPhaseRow) {
            ctaPhaseRow.style.display = mode === 'ncct_single_cta' ? '' : 'none';
        }

        const ncctRow = getRowByInputId('ncctFile');
        const mctaRow = getRowByInputId('mctaFile');
        const vctaRow = getRowByInputId('vctaFile');
        const dctaRow = getRowByInputId('dctaFile');
        const cbfRow = getRowByInputId('cbfFile');
        const cbvRow = getRowByInputId('cbvFile');
        const tmaxRow = getRowByInputId('tmaxFile');
        const sideRow = getRowByInputId('sideSelect');

        if (ncctRow) {
            ncctRow.style.display = '';
        }

        if (mode === 'ncct') {
            if (mctaRow) mctaRow.style.display = 'none';
            if (vctaRow) vctaRow.style.display = 'none';
            if (dctaRow) dctaRow.style.display = 'none';
            if (cbfRow) cbfRow.style.display = 'none';
            if (cbvRow) cbvRow.style.display = 'none';
            if (tmaxRow) tmaxRow.style.display = 'none';
            if (sideRow) sideRow.style.display = '';
        } else if (mode === 'ncct_single_cta') {
            const phase = ctaPhaseSelect ? ctaPhaseSelect.value : 'mcta';
            if (mctaRow) mctaRow.style.display = phase === 'mcta' ? '' : 'none';
            if (vctaRow) vctaRow.style.display = phase === 'vcta' ? '' : 'none';
            if (dctaRow) dctaRow.style.display = phase === 'dcta' ? '' : 'none';
            if (cbfRow) cbfRow.style.display = 'none';
            if (cbvRow) cbvRow.style.display = 'none';
            if (tmaxRow) tmaxRow.style.display = 'none';
            if (sideRow) sideRow.style.display = '';
        } else if (mode === 'ncct_3phase_cta') {
            if (mctaRow) mctaRow.style.display = '';
            if (vctaRow) vctaRow.style.display = '';
            if (dctaRow) dctaRow.style.display = '';
            if (cbfRow) cbfRow.style.display = 'none';
            if (cbvRow) cbvRow.style.display = 'none';
            if (tmaxRow) tmaxRow.style.display = 'none';
            if (sideRow) sideRow.style.display = '';
        } else if (mode === 'ncct_3phase_cta_ctp') {
            if (mctaRow) mctaRow.style.display = '';
            if (vctaRow) vctaRow.style.display = '';
            if (dctaRow) dctaRow.style.display = '';
            if (cbfRow) cbfRow.style.display = '';
            if (cbvRow) cbvRow.style.display = '';
            if (tmaxRow) tmaxRow.style.display = '';
            if (sideRow) sideRow.style.display = '';
        }

        checkFilesReady();
    }

    function bindFileInput(inputEl, buttonId, label) {
        if (!inputEl) {
            return;
        }
        inputEl.addEventListener('change', function (e) {
            if (!e.target.files.length) {
                checkFilesReady();
                return;
            }
            if (!validateNiftiOrReset(e.target, label)) {
                checkFilesReady();
                return;
            }
            const btn = document.getElementById(buttonId);
            if (btn) {
                btn.textContent = e.target.files[0].name;
                btn.classList.add('selected');
            }
            checkFilesReady();
        });
    }

    if (uploadModeSelect) uploadModeSelect.addEventListener('change', updateUIByMode);
    if (ctaPhaseSelect) ctaPhaseSelect.addEventListener('change', updateUIByMode);
    if (questionInput) questionInput.addEventListener('input', checkFilesReady);
    if (agentToggle) agentToggle.addEventListener('change', checkFilesReady);

    bindFileInput(mctaInput, 'mctaBtn', '动脉期CTA');
    bindFileInput(vctaInput, 'vctaBtn', '静脉期CTA');
    bindFileInput(dctaInput, 'dctaBtn', '延迟期CTA');
    bindFileInput(ncctInput, 'ncctBtn', 'NCCT');
    bindFileInput(cbfInput, 'cbfBtn', 'CBF');
    bindFileInput(cbvInput, 'cbvBtn', 'CBV');
    bindFileInput(tmaxInput, 'tmaxBtn', 'Tmax');

    updateUIByMode();
});

function checkFilesReady() {
    const mctaFile = document.getElementById('mctaFile').files[0];
    const vctaFile = document.getElementById('vctaFile').files[0];
    const dctaFile = document.getElementById('dctaFile').files[0];
    const ncctFile = document.getElementById('ncctFile').files[0];
    const cbfFile = document.getElementById('cbfFile').files[0];
    const cbvFile = document.getElementById('cbvFile').files[0];
    const tmaxFile = document.getElementById('tmaxFile').files[0];
    const uploadMode = document.getElementById('uploadModeSelect')
        ? document.getElementById('uploadModeSelect').value
        : DEFAULT_UPLOAD_MODE;
    const questionText = (document.getElementById('agentQuestion')?.value || '').trim();
    const startAgentRun = !document.getElementById('agentRunToggle') || !!document.getElementById('agentRunToggle').checked;

    let ready = !!ncctFile;

    if (uploadMode === 'ncct') {
        ready = !!ncctFile;
    } else if (uploadMode === 'ncct_single_cta') {
        const phase = document.getElementById('ctaPhaseSelect')
            ? document.getElementById('ctaPhaseSelect').value
            : 'mcta';
        if (phase === 'mcta') ready = !!(ncctFile && mctaFile);
        if (phase === 'vcta') ready = !!(ncctFile && vctaFile);
        if (phase === 'dcta') ready = !!(ncctFile && dctaFile);
    } else if (uploadMode === 'ncct_3phase_cta') {
        ready = !!(ncctFile && mctaFile && vctaFile && dctaFile);
    } else if (uploadMode === 'ncct_3phase_cta_ctp') {
        ready = !!(ncctFile && mctaFile && vctaFile && dctaFile && cbfFile && cbvFile && tmaxFile);
    }

    if (ready && startAgentRun && !questionText) {
        ready = false;
    }

    document.getElementById('uploadBtn').disabled = !ready;
}

function processFiles() {
    const patientId = getCurrentPatientId();
    const mctaFile = document.getElementById('mctaFile').files[0];
    const vctaFile = document.getElementById('vctaFile').files[0];
    const dctaFile = document.getElementById('dctaFile').files[0];
    const ncctFile = document.getElementById('ncctFile').files[0];
    const cbfFile = document.getElementById('cbfFile').files[0];
    const cbvFile = document.getElementById('cbvFile').files[0];
    const tmaxFile = document.getElementById('tmaxFile').files[0];

    if (!ncctFile || !patientId) {
        return;
    }

    const formData = new FormData();
    if (mctaFile) formData.append('mcta_file', mctaFile);
    if (vctaFile) formData.append('vcta_file', vctaFile);
    if (dctaFile) formData.append('dcta_file', dctaFile);
    formData.append('ncct_file', ncctFile);
    if (cbfFile) formData.append('cbf_file', cbfFile);
    if (cbvFile) formData.append('cbv_file', cbvFile);
    if (tmaxFile) formData.append('tmax_file', tmaxFile);
    formData.append('patient_id', patientId);

    const modelType = document.getElementById('modelSelect').value;
    formData.append('model_type', modelType);

    const uploadMode = document.getElementById('uploadModeSelect')
        ? document.getElementById('uploadModeSelect').value
        : DEFAULT_UPLOAD_MODE;
    formData.append('upload_mode', uploadMode);

    if (uploadMode === 'ncct_single_cta') {
        const ctaPhase = document.getElementById('ctaPhaseSelect')
            ? document.getElementById('ctaPhaseSelect').value
            : 'mcta';
        formData.append('cta_phase', ctaPhase);
    }

    const hemisphere = document.getElementById('sideSelect')
        ? document.getElementById('sideSelect').value
        : 'both';
    formData.append('hemisphere', hemisphere);

    const question = (document.getElementById('agentQuestion')?.value || '').trim();

    if (cbfFile && cbvFile && tmaxFile) {
        formData.append('skip_ai', 'true');
    }

    const agentToggle = document.getElementById('agentRunToggle');
    const startAgentRun = !agentToggle || !!agentToggle.checked;
    if (startAgentRun && !question) {
        showMsg('启用 Agent 时请填写任务问题。', 'error');
        return;
    }
    if (question) {
        formData.append('question', question);
    }
    if (startAgentRun) {
        formData.append('start_agent_run', 'true');
    }

    showLoading(true, '正在处理上传流程...');

    fetch('/api/upload/start', { method: 'POST', body: formData })
        .then((response) => response.json())
        .then((data) => {
            if (!data.success) {
                showMsg(`上传失败: ${data.error}`, 'error');
                return;
            }

            const runInfoEl = document.getElementById('agentRunInfo');
            if (data.agent_run_id) {
                if (runInfoEl) {
                    runInfoEl.style.display = 'block';
                    runInfoEl.textContent = `已创建 Agent run: ${data.agent_run_id}`;
                }
                localStorage.setItem(`latest_agent_run_${data.file_id}`, data.agent_run_id);
            } else if (runInfoEl) {
                runInfoEl.style.display = 'block';
                runInfoEl.textContent = '本次上传未启用 Agent 主链。';
            }

            let processingUrl =
                '/processing?job_id=' + encodeURIComponent(data.job_id) +
                '&patient_id=' + encodeURIComponent(patientId) +
                '&file_id=' + encodeURIComponent(data.file_id);

            if (data.agent_run_id) {
                processingUrl += '&agent_run_id=' + encodeURIComponent(data.agent_run_id);
            }

            window.location.href = processingUrl;
        })
        .catch((error) => {
            showMsg(`上传失败: ${error.message}`, 'error');
        })
        .finally(() => showLoading(false));
}

