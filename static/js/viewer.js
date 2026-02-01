let currentPatientId = '';
let currentFileId = null;
let currentSlice = 0;
let totalSlices = 0;
let currentRgbFiles = [];
let hasAI = false;
let availableModels = [];
let currentHemisphere = 'both';
let analysisResults = null;
let pseudocolorMode = {};
let pseudocolorGenerated = false;
let isPseudocolorActive = false;
let contrastController = null;

document.addEventListener('DOMContentLoaded', function() {
    const urlParams = new URLSearchParams(window.location.search);
    const fileIdParam = urlParams.get('file_id');
    if (fileIdParam) {
        currentFileId = fileIdParam;
    }

    currentPatientId = getCurrentPatientId();
    const viewerData = getViewerData();

    if (!currentPatientId || !currentFileId || !viewerData) {
        showMsg('缺少影像信息，请先上传文件', 'error');
        setTimeout(() => window.location.href = '/upload', 1000);
        return;
    }

    setPatientInfoVisible(true);
    updatePatientHeader(currentPatientId);

    initializeHemisphereButtons();
    initializeContrastController();

    initializeViewer(viewerData);
});

function initializeViewer(data) {
    currentFileId = data.file_id;
    currentRgbFiles = data.rgb_files;
    totalSlices = data.total_slices;
    hasAI = data.has_ai || false;
    availableModels = data.available_models || [];
    currentSlice = 0;

    // 保存当前文件ID供报告页面使用
    sessionStorage.setItem('current_file_id', currentFileId);

    document.getElementById('sliceSlider').max = totalSlices - 1;

    if (contrastController) {
        contrastController.enableDragAdjust('cta');
        contrastController.enableDragAdjust('ncct');
    }
    loadSlice(0);
}

function initializeHemisphereButtons() {
    document.querySelectorAll('.hemisphere-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.hemisphere-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            currentHemisphere = this.dataset.hemisphere;
        });
    });
}

function initializeContrastController() {
    contrastController = new ContrastController({
        containerId: 'contrast-panel-container',
        onUpdate: function(imageId, settings) {
            updateContrastIndicator(imageId, settings);
        }
    });
}

function updateContrastIndicator(imageId, settings) {
    const indicator = document.getElementById(`contrast-indicator-${imageId}`);
    if (indicator) indicator.textContent = `W:${Math.round(settings.windowWidth)} L:${Math.round(settings.windowLevel)}`;
}

function toggleContrastPanel() {
    if (contrastController) {
        contrastController.togglePanel();
        const btn = document.getElementById('contrastBtn');
        const panel = document.getElementById('contrast-panel-container');
        if (btn && panel) btn.classList.toggle('active', !panel.classList.contains('hidden'));
    }
}

function loadSlice(sliceIndex) {
    if (sliceIndex < 0 || sliceIndex >= totalSlices) return;
    currentSlice = sliceIndex;
    const sliceData = currentRgbFiles[currentSlice];
    updateImage('cta', sliceData.mcta_image);
    updateImage('ncct', sliceData.ncct_image);
    if (contrastController) {
        contrastController.applyContrastToImage('cta');
        contrastController.applyContrastToImage('ncct');
    }
    updateAIImage('cbf', sliceData);
    updateAIImage('cbv', sliceData);
    updateAIImage('tmax', sliceData);
    updateStrokeImage();
    updateSliceInfo();
}

function updateImage(cellId, imageUrl) {
    const img = document.getElementById('img-' + cellId);
    const status = document.getElementById('status-' + cellId);
    if (imageUrl) {
        img.src = imageUrl;
        img.style.display = 'block';
        if (status) {
            status.textContent = '✓';
            status.className = 'cell-status status-ready';
            status.style.display = 'block';
        }
    } else {
        img.style.display = 'none';
        if (status) status.style.display = 'none';
    }
}

function updateAIImage(modelKey, sliceData) {
    const img = document.getElementById('img-' + modelKey);
    const status = document.getElementById('status-' + modelKey);
    const hasModel = sliceData['has_' + modelKey];
    const imageUrl = sliceData[modelKey + '_image'];
    const usePseudocolor = pseudocolorMode[modelKey];
    let finalUrl = imageUrl;

    if (usePseudocolor && currentFileId) {
        finalUrl = `/get_image/${currentFileId}/slice_${String(currentSlice).padStart(3, '0')}_${modelKey}_pseudocolor.png`;
    }
    if (hasModel && finalUrl) {
        img.src = finalUrl;
        img.style.display = 'block';
        if (status) {
            status.textContent = '✓';
            status.className = 'cell-status status-ready';
            status.style.display = 'block';
        }
    } else {
        img.style.display = 'none';
        if (status) {
            status.textContent = '-';
            status.className = 'cell-status';
            status.style.display = 'block';
        }
    }
}

function updateSliceInfo() {
    const info = `${currentSlice + 1} / ${totalSlices}`;
    document.getElementById('sliceInfo').textContent = info;
    document.getElementById('topSliceInfo').textContent = info;
    document.getElementById('sliceSlider').value = currentSlice;
    document.getElementById('prevBtn').disabled = currentSlice === 0;
    document.getElementById('nextBtn').disabled = currentSlice === totalSlices - 1;
}

function changeSlice(delta) { loadSlice(currentSlice + delta); }
function updateSlice(value) { loadSlice(parseInt(value)); }

function togglePseudocolor() {
    const btn = document.getElementById('pseudocolorBtn');
    if (!pseudocolorGenerated) {
        showLoading(true, '正在为所有切片生成伪彩图...');
        btn.disabled = true;
        fetch(`/generate_all_pseudocolors/${currentFileId}`)
            .then(res => res.json()).then(data => {
                if (data.success) {
                    pseudocolorGenerated = true;
                    isPseudocolorActive = true;
                    ['cbf', 'cbv', 'tmax'].forEach(model => {
                        pseudocolorMode[model] = true;
                        document.getElementById('toggle-' + model).classList.add('active');
                    });
                    btn.textContent = '取消伪彩图';
                    btn.disabled = false;
                    loadSlice(currentSlice);
                    showMessage(`伪彩图生成完成 (${data.total_success}/${data.total_attempts})`, 'success');
                } else {
                    btn.disabled = false;
                    showMessage('生成失败: ' + data.error, 'error');
                }
            }).catch(err => {
                btn.disabled = false;
                showMessage('生成失败: ' + err.message, 'error');
            }).finally(() => showLoading(false));
    } else {
        isPseudocolorActive = !isPseudocolorActive;
        ['cbf', 'cbv', 'tmax'].forEach(model => {
            pseudocolorMode[model] = isPseudocolorActive;
            document.getElementById('toggle-' + model).classList.toggle('active', isPseudocolorActive);
        });
        btn.textContent = isPseudocolorActive ? '取消伪彩图' : '显示伪彩图';
        loadSlice(currentSlice);
    }
}

function toggleCellPseudocolor(modelKey) {
    pseudocolorMode[modelKey] = !pseudocolorMode[modelKey];
    document.getElementById('toggle-' + modelKey).classList.toggle('active');
    updateAIImage(modelKey, currentRgbFiles[currentSlice]);
}

function toggleAnalysisPanel() { document.getElementById('analysisPanel').classList.toggle('open'); }

function startStrokeAnalysis() {
    showLoading(true, '正在进行脑卒中分析...');
    fetch(`/analyze_stroke/${currentFileId}?hemisphere=${currentHemisphere}`)
        .then(res => res.json()).then(data => {
            if (data.success || data.analysis_results) {
                analysisResults = data.analysis_results || data;
                displayAnalysisResults();
                showMessage('分析完成', 'success');
            } else { showMessage('分析失败: ' + data.error, 'error'); }
        }).catch(err => showMessage('分析失败: ' + err.message, 'error')).finally(() => showLoading(false));
}

function displayAnalysisResults() {
    if (!analysisResults) return;
    document.getElementById('analysisResults').classList.add('show');
    document.getElementById('analysisMetrics').classList.add('show');
    updateStrokeImage();
    const report = analysisResults.report?.summary;
    if (report) {
        const penumbra = report.penumbra_volume_ml?.toFixed(1) || '--';
        const core = report.core_volume_ml?.toFixed(1) || '--';
        const ratio = report.mismatch_ratio?.toFixed(2) || '--';
        document.getElementById('value-penumbra').textContent = penumbra + ' ml';
        document.getElementById('value-core').textContent = core + ' ml';
        document.getElementById('value-ratio').textContent = ratio;
        document.getElementById('metric-penumbra').textContent = penumbra;
        document.getElementById('metric-core').textContent = core;
        document.getElementById('metric-mismatch').textContent = ratio;
        const statusEl = document.getElementById('value-status');
        const mismatchContainer = document.getElementById('metric-mismatch-container');
        if (report.has_mismatch) {
            statusEl.textContent = '存在不匹配';
            statusEl.className = 'metric-value alert';
            mismatchContainer.classList.add('warning');
        } else {
            statusEl.textContent = '无显著不匹配';
            statusEl.className = 'metric-value good';
            mismatchContainer.classList.remove('warning');
        }
    }

    // 保存分析数据到 sessionStorage，供报告页面使用
    sessionStorage.setItem('analysis_data', JSON.stringify({
        core_infarct_volume: analysisResults.report?.summary?.core_volume_ml || 0,
        penumbra_volume: analysisResults.report?.summary?.penumbra_volume_ml || 0,
        mismatch_ratio: analysisResults.report?.summary?.mismatch_ratio || 0,
        has_mismatch: analysisResults.report?.summary?.has_mismatch || false,
        hemisphere: currentHemisphere
    }));

    saveAnalysisToDB();
}

function updateStrokeImage() {
    if (!analysisResults) return;
    const vis = analysisResults.visualizations;
    if (vis) {
        if (vis.penumbra && vis.penumbra[currentSlice]) document.getElementById('img-penumbra').src = vis.penumbra[currentSlice];
        if (vis.core && vis.core[currentSlice]) document.getElementById('img-core').src = vis.core[currentSlice];
        if (vis.combined && vis.combined[currentSlice]) {
            document.getElementById('img-combined').src = vis.combined[currentSlice];
            document.getElementById('img-stroke').src = vis.combined[currentSlice];
            document.getElementById('status-stroke').textContent = '✓';
            document.getElementById('status-stroke').className = 'cell-status status-ready';
            document.getElementById('status-stroke').style.display = 'block';
        }
    }
}

function downloadData() {
    const currentFile = currentRgbFiles[currentSlice];
    if (currentFile) {
        if (currentFile.npy_url) window.open(currentFile.npy_url, '_blank');
        if (currentFile.cbf_npy_url) window.open(currentFile.cbf_npy_url, '_blank');
        if (currentFile.cbv_npy_url) window.open(currentFile.cbv_npy_url, '_blank');
        if (currentFile.tmax_npy_url) window.open(currentFile.tmax_npy_url, '_blank');
    }
}

async function saveAnalysisToDB() {
    if (!analysisResults || !currentPatientId || !currentFileId) return;

    const payload = {
        patient_id: currentPatientId,
        core_infarct_volume: analysisResults.report?.summary?.core_volume_ml ? parseFloat(analysisResults.report.summary.core_volume_ml.toFixed(1)) : null,
        penumbra_volume: analysisResults.report?.summary?.penumbra_volume_ml ? parseFloat(analysisResults.report.summary.penumbra_volume_ml.toFixed(1)) : null,
        mismatch_ratio: analysisResults.report?.summary?.mismatch_ratio ? parseFloat(analysisResults.report.summary.mismatch_ratio.toFixed(2)) : null,
        analysis_status: 'completed'
    };

    try {
        await $.ajax({
            url: '/api/update_analysis',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(payload)
        });
        showMsg('分析结果已保存', 'success');
    } catch (err) {
        showMsg('保存失败: ' + err.message, 'error');
    }
}
