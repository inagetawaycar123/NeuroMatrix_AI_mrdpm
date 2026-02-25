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

// Markdown 转 HTML 解析函数
function parseMarkdown(text) {
    if (!text) return '';
    let html = text
        // 处理标题
        .replace(/^## (.+)$/gm, '<div style="margin: 16px 0 12px 0;"><span style="display: inline-flex; align-items: center; gap: 6px; background: linear-gradient(135deg, #60a5fa 0%, #3b82f6 100%); color: white; padding: 8px 16px; border-radius: 6px; font-size: 14px; font-weight: 600;">$1</span></div>')
        // 处理二级标题
        .replace(/^## (.+)$/gm, '<h2 style="color: #3b82f6; font-size: 16px; font-weight: 700; margin: 16px 0 10px 0; padding-bottom: 6px; border-bottom: 2px solid #60a5fa;">$1</h2>')
        // 处理粗体标记 - 直接移除
        .replace(/\*\*(.+?)\*\*/g, '$1')
        // 处理列表
        .replace(/^\d+\. (.+)$/gm, '<div style="margin-left: 16px; margin-bottom: 4px; font-size: 12px; line-height: 1.6;">$1</div>')
        .replace(/^- (.+)$/gm, '<div style="margin-left: 16px; margin-bottom: 4px; font-size: 12px; line-height: 1.6;">$1</div>')
        // 处理换行
        .replace(/\n\n/g, '<br><br>');
    return html;
}

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
    // hemisphere 由后端提供，避免前端手动选择
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

    // 从后端数据库获取 hemisphere（patient_imaging 表）
    currentHemisphere = 'both';
    if (currentFileId) {
        fetch(`/api/get_imaging/${currentFileId}`)
            .then(res => res.json())
            .then(resp => {
                if (resp && resp.success && resp.data && resp.data.hemisphere) {
                    currentHemisphere = resp.data.hemisphere;
                    console.log('从后端获取到 hemisphere:', currentHemisphere);
                } else {
                    console.warn('未从后端找到 hemisphere，使用默认 both');
                }
            }).catch(err => {
                console.warn('获取 hemisphere 失败，使用默认 both:', err);
            });
    }

    // 保存当前文件ID供报告页面使用（localStorage 跨标签页共享）
    sessionStorage.setItem('current_file_id', currentFileId);
    localStorage.setItem('current_file_id', currentFileId);

    // 从localStorage加载分析结果
    if (currentFileId) {
        const savedAnalysis = localStorage.getItem(`stroke_analysis_${currentFileId}`);
        if (savedAnalysis) {
            try {
                analysisResults = JSON.parse(savedAnalysis);
                displayAnalysisResults();
            } catch (e) {
                console.error('加载分析结果失败:', e);
            }
        }
    }

    document.getElementById('sliceSlider').max = totalSlices - 1;

    if (contrastController) {
        contrastController.enableDragAdjust('cta');
        contrastController.enableDragAdjust('ncct');
        contrastController.enableDragAdjust('cta-venous');
        contrastController.enableDragAdjust('cta-delayed');
    }
    // 根据 skip_ai 动态修改 CBF/CBV/Tmax 标签
    if (typeof data.skip_ai !== 'undefined') {
        const labelMap = {
            cbf: document.querySelector('#cell-cbf .cell-label'),
            cbv: document.querySelector('#cell-cbv .cell-label'),
            tmax: document.querySelector('#cell-tmax .cell-label')
        };
        const suffix = data.skip_ai ? '（真实图）' : '（推测图）';
        Object.keys(labelMap).forEach(key => {
            if (labelMap[key]) {
                labelMap[key].textContent = labelMap[key].textContent.replace(/（.*图）$/, '') + suffix;
            }
        });
    }

    // 动态隐藏没有文件的grid-cell卡片
    // 只在首次初始化时做一次（以第一个切片为准）
    if (data.rgb_files && data.rgb_files.length > 0) {
        const firstSlice = data.rgb_files[0];
        const cellMap = {
            ncct: 'cell-ncct',
            mcta: 'cell-cta',
            vcta: 'cell-cta-venous',
            dcta: 'cell-cta-delayed',
            cbf: 'cell-cbf',
            cbv: 'cell-cbv',
            tmax: 'cell-tmax'
            // stroke 不再自动隐藏
        };
        Object.keys(cellMap).forEach(key => {
            let imgUrl = '';
            if (key === 'ncct') imgUrl = firstSlice.ncct_image;
            else if (key === 'mcta') imgUrl = firstSlice.mcta_image;
            else if (key === 'vcta') imgUrl = firstSlice.vcta_url;
            else if (key === 'dcta') imgUrl = firstSlice.dcta_url;
            else if (key === 'cbf') imgUrl = firstSlice.cbf_image;
            else if (key === 'cbv') imgUrl = firstSlice.cbv_image;
            else if (key === 'tmax') imgUrl = firstSlice.tmax_image;
            if (!imgUrl) {
                const cell = document.getElementById(cellMap[key]);
                if (cell) cell.style.display = 'none';
            }
        });
    }

    // 根据当前可见卡片数量优化网格布局
    optimizeGridLayout();
    // 如果尚未有分析结果，显示 stroke 占位提示
    if (!analysisResults || !analysisResults.visualizations || !analysisResults.visualizations.combined) {
        setStrokePlaceholder('未完成分析');
    }
    loadSlice(0);
}

function setStrokePlaceholder(text) {
    const img = document.getElementById('img-stroke');
    const status = document.getElementById('status-stroke');
    if (!img) return;

    try {
        const w = 480; const h = 320;
        const canvas = document.createElement('canvas');
        canvas.width = w; canvas.height = h;
        const ctx = canvas.getContext('2d');
        // 背景
        ctx.fillStyle = '#000000';
        ctx.fillRect(0, 0, w, h);
        // 边框
        ctx.strokeStyle = '#000000'; ctx.lineWidth = 4;
        ctx.strokeRect(0, 0, w, h);
        // 文本
        ctx.fillStyle = '#f3f4f6';
        ctx.font = '20px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(text, w/2, h/2);

        img.src = canvas.toDataURL('image/png');
        // 标记为占位图，避免被全局的 rotate(-90deg) 样式旋转
        img.classList.add('placeholder-image');
        if (status) {
            status.textContent = '未';
            status.className = 'cell-status';
            status.style.display = 'block';
        }
    } catch (e) {
        console.error('设置 stroke 占位图失败:', e);
    }
}

function optimizeGridLayout() {
    const grid = document.querySelector('.image-grid');
    if (!grid) return;

    const allCells = Array.from(grid.querySelectorAll('.grid-cell'));
    const visibleCells = allCells.filter(c => {
        // consider element hidden if display === 'none' or has hidden attribute
        const style = window.getComputedStyle(c);
        return style.display !== 'none' && style.visibility !== 'hidden';
    });

    const count = visibleCells.length;
    if (count <= 0) return;

    let cols = 1;
    if (count <= 3) {
        // 1-3 个图片：一行展示
        cols = count;
    } else if (count <= 8) {
        // 4-8 个图片：两行展示，列数为向上取整(count / 2)
        cols = Math.ceil(count / 2);
    } else {
        // 超过8个：最多 4 列
        cols = 4;
    }

    cols = Math.max(1, Math.min(cols, 4));
    grid.style.gridTemplateColumns = `repeat(${cols}, 1fr)`;

    // 可选：根据列数调整行高，让单元格更接近正方形
    // 这里使用 auto 行高，CSS 中的 .grid-image 已设置为适配容器
}

// 偏侧选择已移除，后端提供 hemisphere 字段

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
    
    // 添加调试信息
    console.log('loadSlice:', sliceIndex);
    console.log('sliceData:', {
        mcta_image: sliceData.mcta_image,
        ncct_image: sliceData.ncct_image,
        vcta_url: sliceData.vcta_url,
        dcta_url: sliceData.dcta_url,
        cbf_image: sliceData.cbf_image,
        cbv_image: sliceData.cbv_image,
        tmax_image: sliceData.tmax_image
    });
    
    // 调整加载顺序以匹配新的布局
    updateImage('ncct', sliceData.ncct_image);
    updateImage('cta', sliceData.mcta_image);
    updateImage('cta-venous', sliceData.vcta_url);
    updateImage('cta-delayed', sliceData.dcta_url);
    
    if (contrastController) {
        contrastController.applyContrastToImage('ncct');
        contrastController.applyContrastToImage('cta');
        contrastController.applyContrastToImage('cta-venous');
        contrastController.applyContrastToImage('cta-delayed');
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
    
    console.log('updateImage:', cellId, 'imageUrl:', imageUrl);
    
    if (imageUrl) {
        img.src = imageUrl;
        img.style.display = 'block';
        if (status) {
            status.textContent = '✓';
            status.className = 'cell-status status-ready';
            status.style.display = 'block';
        }
        
        // 添加图像加载错误处理
        img.onerror = function() {
            console.error('Image load error:', cellId, imageUrl);
            img.style.display = 'none';
            if (status) {
                status.textContent = '✗';
                status.className = 'cell-status status-error';
                status.style.display = 'block';
            }
        };
    } else {
        img.style.display = 'none';
        if (status) {
            status.textContent = '-';
            status.className = 'cell-status';
            status.style.display = 'block';
        }
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

    // 保存分析数据到 localStorage，供报告页面使用（跨标签页共享）
    // 镜像逻辑：前端选择left → 病灶在right（发病侧）
    const hemisphereMap = {
        'left': 'right',
        'right': 'left',
        'both': 'both'
    };
    const lesionHemisphere = hemisphereMap[currentHemisphere] || 'both';
    
    sessionStorage.setItem('analysis_data', JSON.stringify({
        core_infarct_volume: analysisResults.report?.summary?.core_volume_ml || 0,
        penumbra_volume: analysisResults.report?.summary?.penumbra_volume_ml || 0,
        mismatch_ratio: analysisResults.report?.summary?.mismatch_ratio || 0,
        has_mismatch: analysisResults.report?.summary?.has_mismatch || false,
        hemisphere: lesionHemisphere
    }));
    localStorage.setItem('analysis_data', JSON.stringify({
        core_infarct_volume: analysisResults.report?.summary?.core_volume_ml || 0,
        penumbra_volume: analysisResults.report?.summary?.penumbra_volume_ml || 0,
        mismatch_ratio: analysisResults.report?.summary?.mismatch_ratio || 0,
        has_mismatch: analysisResults.report?.summary?.has_mismatch || false,
        hemisphere: lesionHemisphere
    }));

    // 保存完整的分析结果到localStorage，用于页面刷新后恢复
    if (currentFileId) {
        localStorage.setItem(`stroke_analysis_${currentFileId}`, JSON.stringify(analysisResults));
    }

    saveAnalysisToDB();
}

function updateStrokeImage() {
    if (!analysisResults) return;
    const vis = analysisResults.visualizations;
    if (vis) {
        if (vis.penumbra && vis.penumbra[currentSlice]) {
            const ip = document.getElementById('img-penumbra');
            if (ip) { ip.classList.remove('placeholder-image'); ip.src = vis.penumbra[currentSlice]; }
        }
        if (vis.core && vis.core[currentSlice]) {
            const ic = document.getElementById('img-core');
            if (ic) { ic.classList.remove('placeholder-image'); ic.src = vis.core[currentSlice]; }
        }
        if (vis.combined && vis.combined[currentSlice]) {
            const icomb = document.getElementById('img-combined');
            const istroke = document.getElementById('img-stroke');
            if (icomb) { icomb.classList.remove('placeholder-image'); icomb.src = vis.combined[currentSlice]; }
            if (istroke) { istroke.classList.remove('placeholder-image'); istroke.src = vis.combined[currentSlice]; }
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

    // 镜像逻辑：前端选择left → 病灶在right（发病侧）
    const hemisphereMap = {
        'left': 'right',
        'right': 'left',
        'both': 'both'
    };
    const lesionHemisphere = hemisphereMap[currentHemisphere] || 'both';

    const payload = {
        patient_id: currentPatientId,
        core_infarct_volume: analysisResults.report?.summary?.core_volume_ml ? parseFloat(analysisResults.report.summary.core_volume_ml.toFixed(1)) : null,
        penumbra_volume: analysisResults.report?.summary?.penumbra_volume_ml ? parseFloat(analysisResults.report.summary.penumbra_volume_ml.toFixed(1)) : null,
        mismatch_ratio: analysisResults.report?.summary?.mismatch_ratio ? parseFloat(analysisResults.report.summary.mismatch_ratio.toFixed(2)) : null,
        hemisphere: lesionHemisphere,
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
        
        // 注意：已移除自动调用百川 AI，改为手动触发
    } catch (err) {
        showMsg('保存失败: ' + err.message, 'error');
    }
}

// 调用 NeuroMatrix AI 生成报告
async function generateAIReport() {
    if (!currentPatientId) {
        console.warn('没有患者ID，跳过AI报告生成');
        return;
    }

    try {
        console.log('正在调用 NeuroMatrix AI 生成报告...');
        
        // 显示加载动画
        const aiReportSection = document.getElementById('aiReportSection');
        const aiReportContent = document.getElementById('aiReportContent');
        if (aiReportSection && aiReportContent) {
            aiReportSection.style.display = 'block';
            aiReportContent.innerHTML = `
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px; border-radius: 12px; text-align: center;">
                    <div style="border: 4px solid rgba(255,255,255,0.3); border-top: 4px solid white; border-radius: 50%; width: 48px; height: 48px; animation: spin 1s linear infinite; margin: 0 auto 16px;"></div>
                    <p style="color: white; font-size: 16px; font-weight: 600; margin: 0;">NeuroMatrix AI 正在生成诊断意见...</p>
                    <p style="color: rgba(255,255,255,0.8); font-size: 13px; margin-top: 8px;">正在分析患者影像数据，请稍候...</p>
                </div>
            `;
        }
        
        const response = await fetch(`/api/generate_report/${currentPatientId}?format=markdown`);
        const data = await response.json();
        
        console.log('NeuroMatrix API 响应:', data);
        
        if (data.status === 'success') {
            // 将 NeuroMatrix 报告保存到 localStorage（跨标签页共享）
            localStorage.setItem('ai_report', data.report);
            
            // 在分析面板中显示 NeuroMatrix 报告
            displayAIReport(data.report, data.is_mock);
            
            showMsg('AI 报告已生成' + (data.is_mock ? '（模拟模式）' : ''), 'success');
        } else {
            console.warn('AI 报告生成失败：' + data.message);
            // 显示错误信息
            if (aiReportContent) {
                aiReportContent.innerHTML = `
                    <div style="background: #fee2e2; padding: 16px; border-radius: 8px; border-left: 4px solid #ef4444;">
                        <p style="color: #dc2626; font-weight: 600; margin: 0 0 8px 0;">❌ AI 报告生成失败</p>
                        <p style="color: #991b1b; margin: 0;">${data.message || '未知错误'}</p>
                    </div>
                `;
            }
        }
    } catch (err) {
        console.error('AI 报告生成错误：' + err.message);
        // 显示错误信息
        const aiReportContent = document.getElementById('aiReportContent');
        if (aiReportContent) {
            aiReportContent.innerHTML = `
                <div style="background: #fee2e2; padding: 16px; border-radius: 8px; border-left: 4px solid #ef4444;">
                    <p style="color: #dc2626; font-weight: 600; margin: 0 0 8px 0;">❌ 网络错误</p>
                    <p style="color: #991b1b; margin: 0;">${err.message}</p>
                </div>
            `;
        }
    }
}

// 在分析面板中显示 NeuroMatrix 报告
function displayAIReport(report, isMock) {
    const aiReportSection = document.getElementById('aiReportSection');
    const aiReportContent = document.getElementById('aiReportContent');
    
    if (aiReportSection && aiReportContent) {
        aiReportSection.style.display = 'block';
        aiReportContent.innerHTML = `
            <div style="background: #eff6ff; padding: 12px; border-radius: 6px; border-left: 3px solid #2563eb; margin-bottom: 8px;">
                <div style="font-size: 11px; font-weight: 600; color: #2563eb; margin-bottom: 8px;">
                    NeuroMatrix AI 专业诊断报告 ${isMock ? '<span style="background: #ffd700; padding: 1px 6px; border-radius: 8px; font-size: 10px;">模拟</span>' : ''}
                </div>
                <div style="font-size: 12px; line-height: 1.8; color: #333;">${parseMarkdown(report)}</div>
            </div>
        `;
    }
}

// 手动触发 AI 报告生成（由用户点击按钮调用）
function manualGenerateAIReport() {
    const analysisData = localStorage.getItem('analysis_data');
    if (!analysisData) {
        showMsg('请先完成脑卒中分析', 'warning');
        return;
    }
    
    // 设置同步标记（通知其他页面开始生成）
    localStorage.setItem('ai_report_generating', 'true');
    
    // 本地也开始生成
    generateAIReport();
}
