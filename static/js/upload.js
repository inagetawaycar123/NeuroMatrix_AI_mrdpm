document.addEventListener('DOMContentLoaded', function() {
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

    mctaInput.addEventListener('change', function(e) {
        if (e.target.files.length > 0) {
            const mctaFile = e.target.files[0];
            const btn = document.getElementById('mctaBtn');
            btn.textContent = mctaFile.name;
            btn.classList.add('selected');
            checkFilesReady();
        }
    });

    vctaInput.addEventListener('change', function(e) {
        if (e.target.files.length > 0) {
            const vctaFile = e.target.files[0];
            const btn = document.getElementById('vctaBtn');
            btn.textContent = vctaFile.name;
            btn.classList.add('selected');
            checkFilesReady();
        }
    });

    dctaInput.addEventListener('change', function(e) {
        if (e.target.files.length > 0) {
            const dctaFile = e.target.files[0];
            const btn = document.getElementById('dctaBtn');
            btn.textContent = dctaFile.name;
            btn.classList.add('selected');
            checkFilesReady();
        }
    });

    ncctInput.addEventListener('change', function(e) {
        if (e.target.files.length > 0) {
            const ncctFile = e.target.files[0];
            const btn = document.getElementById('ncctBtn');
            btn.textContent = ncctFile.name;
            btn.classList.add('selected');
            checkFilesReady();
        }
    });

    cbfInput.addEventListener('change', function(e) {
        if (e.target.files.length > 0) {
            const cbfFile = e.target.files[0];
            const btn = document.getElementById('cbfBtn');
            btn.textContent = cbfFile.name;
            btn.classList.add('selected');
            checkFilesReady();
        }
    });
    cbvInput.addEventListener('change', function(e) {
        if (e.target.files.length > 0) {
            const cbvFile = e.target.files[0];
            const btn = document.getElementById('cbvBtn');
            btn.textContent = cbvFile.name;
            btn.classList.add('selected');
            checkFilesReady();
        }
    });
    tmaxInput.addEventListener('change', function(e) {
        if (e.target.files.length > 0) {
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
    document.getElementById('uploadBtn').disabled = !ncctFile;
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

    // 如果三者均上传，则标记跳过AI分析
    if (cbfFile && cbvFile && tmaxFile) {
        formData.append('skip_ai', 'true');
    }

    showLoading(true, '正在上传文件...');
    fetch('/upload', { method: 'POST', body: formData })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                setViewerData({
                    file_id: data.file_id,
                    rgb_files: data.rgb_files,
                    total_slices: data.total_slices,
                    has_ai: data.has_ai || false,
                    available_models: data.available_models || []
                });
                window.location.href = '/viewer?file_id=' + data.file_id;
            } else {
                showMsg('处理失败: ' + data.error, 'error');
            }
        })
        .catch(error => showMsg('处理失败: ' + error.message, 'error'))
        .finally(() => showLoading(false));
}
