document.addEventListener('DOMContentLoaded', function() {
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
        showMsg('缺少患者ID，请先录入患者信息', 'error');
        setTimeout(() => window.location.href = '/patient', 1000);
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

    function isValidNiftiFile(file) {
        if (!file || !file.name) return false;
        const lowerName = file.name.toLowerCase();
        return lowerName.endsWith('.nii') || lowerName.endsWith('.nii.gz');
    }

    function validateNiftiOrReset(inputEl, label) {
        const file = inputEl && inputEl.files ? inputEl.files[0] : null;
        if (!file) return true;
        if (isValidNiftiFile(file)) return true;
        inputEl.value = '';
        showMsg(`${label} 仅支持 .nii 或 .nii.gz 文件`, 'error');
        return false;
    }

    function getRowByInputId(id) {
        const el = document.getElementById(id);
        return el ? el.parentElement : null;
    }

    function updateUIByMode() {
        const mode = uploadModeSelect ? uploadModeSelect.value : 'ncct';
        // show/hide CTA phase selector for single-phase mode
        if (ctaPhaseRow) ctaPhaseRow.style.display = (mode === 'ncct_single_cta') ? '' : 'none';

        // Always show NCCT
        const ncctRow = getRowByInputId('ncctFile'); if (ncctRow) ncctRow.style.display = '';

        const mctaRow = getRowByInputId('mctaFile');
        const vctaRow = getRowByInputId('vctaFile');
        const dctaRow = getRowByInputId('dctaFile');
        const cbfRow = getRowByInputId('cbfFile');
        const cbvRow = getRowByInputId('cbvFile');
        const tmaxRow = getRowByInputId('tmaxFile');
        const sideRow = getRowByInputId('sideSelect');

        if (mode === 'ncct') {
            if (mctaRow) mctaRow.style.display = 'none';
            if (vctaRow) vctaRow.style.display = 'none';
            if (dctaRow) dctaRow.style.display = 'none';
            if (cbfRow) cbfRow.style.display = 'none';
            if (cbvRow) cbvRow.style.display = 'none';
            if (tmaxRow) tmaxRow.style.display = 'none';
            if (sideRow) sideRow.style.display = '';
        } else if (mode === 'ncct_single_cta') {
            // show only selected CTA phase
            const phase = ctaPhaseSelect ? ctaPhaseSelect.value : 'mcta';
            if (mctaRow) mctaRow.style.display = (phase === 'mcta') ? '' : 'none';
            if (vctaRow) vctaRow.style.display = (phase === 'vcta') ? '' : 'none';
            if (dctaRow) dctaRow.style.display = (phase === 'dcta') ? '' : 'none';
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

    if (uploadModeSelect) uploadModeSelect.addEventListener('change', updateUIByMode);
    if (ctaPhaseSelect) ctaPhaseSelect.addEventListener('change', updateUIByMode);
    // initialize UI based on default mode
    updateUIByMode();

    mctaInput.addEventListener('change', function(e) {
        if (e.target.files.length > 0) {
            if (!validateNiftiOrReset(e.target, '动脉期CTA')) {
                checkFilesReady();
                return;
            }
            const mctaFile = e.target.files[0];
            const btn = document.getElementById('mctaBtn');
            btn.textContent = mctaFile.name;
            btn.classList.add('selected');
            checkFilesReady();
        }
    });

    vctaInput.addEventListener('change', function(e) {
        if (e.target.files.length > 0) {
            if (!validateNiftiOrReset(e.target, '静脉期CTA')) {
                checkFilesReady();
                return;
            }
            const vctaFile = e.target.files[0];
            const btn = document.getElementById('vctaBtn');
            btn.textContent = vctaFile.name;
            btn.classList.add('selected');
            checkFilesReady();
        }
    });

    dctaInput.addEventListener('change', function(e) {
        if (e.target.files.length > 0) {
            if (!validateNiftiOrReset(e.target, '延迟期CTA')) {
                checkFilesReady();
                return;
            }
            const dctaFile = e.target.files[0];
            const btn = document.getElementById('dctaBtn');
            btn.textContent = dctaFile.name;
            btn.classList.add('selected');
            checkFilesReady();
        }
    });

    ncctInput.addEventListener('change', function(e) {
        if (e.target.files.length > 0) {
            if (!validateNiftiOrReset(e.target, 'NCCT')) {
                checkFilesReady();
                return;
            }
            const ncctFile = e.target.files[0];
            const btn = document.getElementById('ncctBtn');
            btn.textContent = ncctFile.name;
            btn.classList.add('selected');
            checkFilesReady();
        }
    });

    cbfInput.addEventListener('change', function(e) {
        if (e.target.files.length > 0) {
            if (!validateNiftiOrReset(e.target, 'CBF')) {
                checkFilesReady();
                return;
            }
            const cbfFile = e.target.files[0];
            const btn = document.getElementById('cbfBtn');
            btn.textContent = cbfFile.name;
            btn.classList.add('selected');
            checkFilesReady();
        }
    });
    cbvInput.addEventListener('change', function(e) {
        if (e.target.files.length > 0) {
            if (!validateNiftiOrReset(e.target, 'CBV')) {
                checkFilesReady();
                return;
            }
            const cbvFile = e.target.files[0];
            const btn = document.getElementById('cbvBtn');
            btn.textContent = cbvFile.name;
            btn.classList.add('selected');
            checkFilesReady();
        }
    });
    tmaxInput.addEventListener('change', function(e) {
        if (e.target.files.length > 0) {
            if (!validateNiftiOrReset(e.target, 'Tmax')) {
                checkFilesReady();
                return;
            }
            const tmaxFile = e.target.files[0];
            const btn = document.getElementById('tmaxBtn');
            btn.textContent = tmaxFile.name;
            btn.classList.add('selected');
            checkFilesReady();
        }
    });
});

function checkFilesReady() {
    const mctaFile = document.getElementById('mctaFile').files[0];
    const vctaFile = document.getElementById('vctaFile').files[0];
    const dctaFile = document.getElementById('dctaFile').files[0];
    const ncctFile = document.getElementById('ncctFile').files[0];
    const cbfFile = document.getElementById('cbfFile').files[0];
    const cbvFile = document.getElementById('cbvFile').files[0];
    const tmaxFile = document.getElementById('tmaxFile').files[0];
    const uploadMode = document.getElementById('uploadModeSelect') ? document.getElementById('uploadModeSelect').value : 'ncct';
    let ready = !!ncctFile;
    if (uploadMode === 'ncct') {
        // only NCCT required
        ready = !!ncctFile;
    } else if (uploadMode === 'ncct_single_cta') {
        const phase = document.getElementById('ctaPhaseSelect') ? document.getElementById('ctaPhaseSelect').value : 'mcta';
        if (phase === 'mcta') ready = !!(ncctFile && mctaFile);
        if (phase === 'vcta') ready = !!(ncctFile && vctaFile);
        if (phase === 'dcta') ready = !!(ncctFile && dctaFile);
    } else if (uploadMode === 'ncct_3phase_cta') {
        ready = !!(ncctFile && mctaFile && vctaFile && dctaFile);
    } else if (uploadMode === 'ncct_3phase_cta_ctp') {
        ready = !!(ncctFile && mctaFile && vctaFile && dctaFile && cbfFile && cbvFile && tmaxFile);
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
    if (!ncctFile || !patientId) return;

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
    // 上传模式和 CTA 期数
    const uploadMode = document.getElementById('uploadModeSelect') ? document.getElementById('uploadModeSelect').value : 'ncct';
    formData.append('upload_mode', uploadMode);
    if (uploadMode === 'ncct_single_cta') {
        const ctaPhase = document.getElementById('ctaPhaseSelect') ? document.getElementById('ctaPhaseSelect').value : 'mcta';
        formData.append('cta_phase', ctaPhase);
    }
    // 添加偏侧选择到表单，后端将保存到 patient_imaging.hemisphere
    const hemisphere = document.getElementById('sideSelect') ? document.getElementById('sideSelect').value : 'both';
    formData.append('hemisphere', hemisphere);

    // 如果三者均上传，则标记跳过AI分析
    if (cbfFile && cbvFile && tmaxFile) {
        formData.append('skip_ai', 'true');
    }

    showLoading(true, 'Processing upload workflow...');
    fetch('/api/upload/start', { method: 'POST', body: formData })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const processingUrl =
                    '/processing?job_id=' + encodeURIComponent(data.job_id) +
                    '&patient_id=' + encodeURIComponent(patientId) +
                    '&file_id=' + encodeURIComponent(data.file_id);
                window.location.href = processingUrl;
            } else {
                showMsg('处理失败: ' + data.error, 'error');
            }
        })
        .catch(error => showMsg('处理失败: ' + error.message, 'error'))
        .finally(() => showLoading(false));
}
