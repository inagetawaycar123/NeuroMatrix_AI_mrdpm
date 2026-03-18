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
let pseudocolorLutStats = {};
let contrastController = null;
let reportStatusState = 'idle';
let reportStatusDismissed = false;
let autoReportBootstrapped = false;
let viewerLayoutMode = 'full';

// Markdown 杞?HTML 瑙ｆ瀽鍑芥暟
function parseMarkdown(text) {
    if (!text) return '';
    let html = text
        // 澶勭悊鏍囬
        .replace(/^## (.+)$/gm, '<div style="margin: 16px 0 12px 0;"><span style="display: inline-flex; align-items: center; gap: 6px; background: linear-gradient(135deg, #60a5fa 0%, #3b82f6 100%); color: white; padding: 8px 16px; border-radius: 6px; font-size: 14px; font-weight: 600;">$1</span></div>')
        // 澶勭悊浜岀骇鏍囬
        .replace(/^## (.+)$/gm, '<h2 style="color: #3b82f6; font-size: 16px; font-weight: 700; margin: 16px 0 10px 0; padding-bottom: 6px; border-bottom: 2px solid #60a5fa;">$1</h2>')
        // 澶勭悊绮椾綋鏍囪 - 鐩存帴绉婚櫎
        .replace(/\*\*(.+?)\*\*/g, '$1')
        // 澶勭悊鍒楄〃
        .replace(/^\d+\. (.+)$/gm, '<div style="margin-left: 16px; margin-bottom: 4px; font-size: 12px; line-height: 1.6;">$1</div>')
        .replace(/^- (.+)$/gm, '<div style="margin-left: 16px; margin-bottom: 4px; font-size: 12px; line-height: 1.6;">$1</div>')
        // 澶勭悊鎹㈣
        .replace(/\n\n/g, '<br><br>');
    return html;
}

function hasImageUrl(url) {
    return typeof url === 'string' ? url.trim().length > 0 : !!url;
}

function setCellVisible(cellId, visible) {
    const cell = document.getElementById(cellId);
    if (!cell) return;
    cell.style.display = visible ? 'flex' : 'none';
}

function detectViewerLayoutMode(firstSlice = {}) {
    const hasNcct = hasImageUrl(firstSlice.ncct_image);
    const hasMcta = hasImageUrl(firstSlice.mcta_image);
    const hasVcta = hasImageUrl(firstSlice.vcta_url);
    const hasDcta = hasImageUrl(firstSlice.dcta_url);
    const ctaCount = [hasMcta, hasVcta, hasDcta].filter(Boolean).length;

    // NCCT-only
    if (hasNcct && ctaCount === 0) {
        return 'single';
    }

    // NCCT + single-phase CTA
    if (hasNcct && ctaCount === 1) {
        return 'dual';
    }

    // mCTA / mCTA+CTP / fallback
    return 'full';
}

function applyDynamicViewerLayout(data) {
    const firstSlice = (data.rgb_files && data.rgb_files.length > 0) ? data.rgb_files[0] : {};
    viewerLayoutMode = detectViewerLayoutMode(firstSlice);

    const cellIds = {
        ncct: 'cell-ncct',
        mcta: 'cell-cta',
        vcta: 'cell-cta-venous',
        dcta: 'cell-cta-delayed',
        cbf: 'cell-cbf',
        cbv: 'cell-cbv',
        tmax: 'cell-tmax',
        stroke: 'cell-stroke',
    };

    const hideAll = () => {
        Object.values(cellIds).forEach((id) => setCellVisible(id, false));
    };

    if (viewerLayoutMode === 'single') {
        hideAll();
        setCellVisible(cellIds.ncct, true);
        return;
    }

    if (viewerLayoutMode === 'dual') {
        hideAll();
        setCellVisible(cellIds.ncct, true);
        if (hasImageUrl(firstSlice.mcta_image)) {
            setCellVisible(cellIds.mcta, true);
        } else if (hasImageUrl(firstSlice.vcta_url)) {
            setCellVisible(cellIds.vcta, true);
        } else if (hasImageUrl(firstSlice.dcta_url)) {
            setCellVisible(cellIds.dcta, true);
        }
        return;
    }

    // 8-grid mode remains unchanged for mCTA-related cases.
    Object.values(cellIds).forEach((id) => setCellVisible(id, true));
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
        showMsg('缺少必要的查看数据，请重新上传', 'error');
        setTimeout(() => window.location.href = '/upload', 1000);
        return;
    }

    setPatientInfoVisible(true);
    updatePatientHeader(currentPatientId);
    // hemisphere 鐢卞悗绔彁渚涳紝閬垮厤鍓嶇鎵嬪姩閫夋嫨
    initializeContrastController();

    initializeViewer(viewerData);
    initializeReportAutoFlow();
});

function initializeViewer(data) {
    currentFileId = data.file_id;
    currentRgbFiles = data.rgb_files;
    totalSlices = data.total_slices;
    hasAI = data.has_ai || false;
    availableModels = data.available_models || [];
    currentSlice = 0;
    pseudocolorMode = {};
    pseudocolorGenerated = false;
    isPseudocolorActive = false;
    pseudocolorLutStats = {};

    // 浠庡悗绔暟鎹簱鑾峰彇 hemisphere锛坧atient_imaging 琛級
    currentHemisphere = 'both';
    if (currentFileId) {
        fetch(`/api/get_imaging/${currentFileId}`)
            .then(res => res.json())
            .then(resp => {
                if (resp && resp.success && resp.data && resp.data.hemisphere) {
                    currentHemisphere = resp.data.hemisphere;
                    console.log('浠庡悗绔幏鍙栧埌 hemisphere:', currentHemisphere);
                } else {
                    console.warn('鏈粠鍚庣鎵惧埌 hemisphere锛屼娇鐢ㄩ粯璁?both');
                }
            }).catch(err => {
                console.warn('鑾峰彇 hemisphere 澶辫触锛屼娇鐢ㄩ粯璁?both:', err);
            });
    }

    // 淇濆瓨褰撳墠鏂囦欢ID渚涙姤鍛婇〉闈娇鐢紙localStorage 璺ㄦ爣绛鹃〉鍏变韩锛?
    sessionStorage.setItem('current_file_id', currentFileId);
    localStorage.setItem('current_file_id', currentFileId);

    // 浠巐ocalStorage鍔犺浇鍒嗘瀽缁撴灉
    if (currentFileId) {
        const savedAnalysis = localStorage.getItem(`stroke_analysis_${currentFileId}`);
        if (savedAnalysis) {
            try {
                analysisResults = JSON.parse(savedAnalysis);
                displayAnalysisResults();
            } catch (e) {
                console.error('鍔犺浇鍒嗘瀽缁撴灉澶辫触:', e);
            }
        }
        
        // 妫€鏌ユ暟鎹簱涓殑鍒嗘瀽鐘舵€侊紙鐢ㄤ簬鑷姩鍒嗘瀽锛?
        checkAnalysisStatus();
    }

    // 妫€娴婥TP鐏屾敞鍥炬暟鎹槸鍚﹀瓨鍦?
    function hasCTPData() {
        if (data.rgb_files && data.rgb_files.length > 0) {
            const firstSlice = data.rgb_files[0];
            // 妫€鏌ユ槸鍚﹀瓨鍦–BF銆丆BV銆乀max鍥惧儚鏁版嵁
            return !!(firstSlice.cbf_image || firstSlice.cbv_image || firstSlice.tmax_image);
        }
        return false;
    }

    document.getElementById('sliceSlider').max = totalSlices - 1;

    if (contrastController) {
        contrastController.enableDragAdjust('cta');
        contrastController.enableDragAdjust('ncct');
        contrastController.enableDragAdjust('cta-venous');
        contrastController.enableDragAdjust('cta-delayed');
    }
    // 鏍规嵁 skip_ai 鍔ㄦ€佷慨鏀?CBF/CBV/Tmax 鏍囩
    if (typeof data.skip_ai !== 'undefined') {
        const labelMap = {
            cbf: document.querySelector('#cell-cbf .cell-label'),
            cbv: document.querySelector('#cell-cbv .cell-label'),
            tmax: document.querySelector('#cell-tmax .cell-label')
        };
        const suffix = data.skip_ai ? '（跳过AI）' : '（推测图）';
        Object.keys(labelMap).forEach(key => {
            if (labelMap[key]) {
                labelMap[key].textContent = labelMap[key].textContent.replace(/（.*）$/, '') + suffix;
            }
        });
    }

    // 鏍规嵁褰卞儚妯℃€佹暟閲忓姩鎬佸垏鎹㈠竷灞€锛?1 鏍?2 鏍?/8 鏍?
    applyDynamicViewerLayout(data);

    // 鏍规嵁褰撳墠妗ｄ綅浼樺寲缃戞牸甯冨眬
    optimizeGridLayout();
    ensureLutScaleElements();
    refreshAllLutScales();
    // 1 鏍?/2 鏍煎竷灞€涓嶅啀鏄剧ず stroke 鍗犱綅鎻愮ず
    if (viewerLayoutMode === 'full' && (!analysisResults || !analysisResults.visualizations || !analysisResults.visualizations.combined)) {
        setStrokePlaceholder('暂无脑卒中分析结果');
    }

    // 鑷姩灞曠ず浼僵鍥撅紙濡傛灉瀛樺湪CTP鐏屾敞鍥炬暟鎹級
    if (hasCTPData() && !pseudocolorGenerated) {
        console.log('检测到CTP数据，自动生成伪彩图');
        togglePseudocolor();
    }

    loadSlice(0);
    // 尝试在页面加载时直接从 localStorage 渲染 ICV（如果存在且报告文本未生成）
    tryRenderIcvFromStoredPayload();
}

function extractIcvPayload(payload) {
    if (!payload || typeof payload !== 'object') return null;
    if (payload.icv && typeof payload.icv === 'object') return payload.icv;
    if (payload.success && payload.icv && typeof payload.icv === 'object') return payload.icv;
    if (payload.status && (Array.isArray(payload.findings) || payload.findings)) return payload;
    if (payload.result && payload.result.icv && typeof payload.result.icv === 'object') return payload.result.icv;
    return null;
}

function buildIcvSummaryHtml(icv) {
    if (!icv || typeof icv !== 'object') return '';
    const status = (icv.status || '').toLowerCase();
    const color = status === 'pass' ? '#10b981' : status === 'warn' ? '#f59e0b' : '#ef4444';
    if (status === 'unavailable') {
        const reason = icv.error_message || icv.error_code || 'unknown';
        return `
            <div style="background:#fff7ed;border:1px solid rgba(0,0,0,0.04);padding:12px;border-radius:8px;margin-bottom:10px;">
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
                    <div style="font-weight:700;color:#f59e0b;">ICV 检查：UNAVAILABLE</div>
                    <div style="font-size:12px;color:#666">自动质量门检测</div>
                </div>
                <div style="font-size:13px;color:#333;">ICV result unavailable: ${reason}</div>
            </div>
        `;
    }
    const findings = Array.isArray(icv.findings) ? icv.findings : [];
    const findingsListHtml = findings.map(f => `
        <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #eee;">
            <div style="color:#333">${(f.id||'').replace(/_/g,' ')}</div>
            <div style="color:${(f.status==='pass'? '#10b981' : f.status==='warn'? '#f59e0b' : '#ef4444')};font-weight:600">${f.status}</div>
        </div>
    `).join('');

    const severitySetHigh = new Set(['fail','error','critical','high']);
    const severitySetMedium = new Set(['warn','medium']);
    const problemFindings = findings.filter(f => (f.status || '').toLowerCase() !== 'pass');
    const warningCount = problemFindings.length;
    const warningDetailsHtml = problemFindings.map(f => `
        <div style="padding:8px;border-bottom:1px dashed #eee;margin-bottom:6px;">
            <div style="display:flex;justify-content:space-between;gap:8px;align-items:center;">
                <div style="font-weight:700;color:${(severitySetHigh.has((f.status||'').toLowerCase())? '#ef4444' : severitySetMedium.has((f.status||'').toLowerCase()) ? '#f59e0b' : '#6b7280')}">${(f.id||'').replace(/_/g,' ')}</div>
                <div style="font-size:12px;font-weight:600;color:${(severitySetHigh.has((f.status||'').toLowerCase())? '#ef4444' : severitySetMedium.has((f.status||'').toLowerCase()) ? '#f59e0b' : '#6b7280')}">${f.status || 'unknown'}</div>
            </div>
            <div style="color:#333;margin-top:4px;">${f.message || ''}</div>
            ${f.suggested_action ? `<div style="color:#2563eb;margin-top:6px;">建议: ${f.suggested_action}</div>` : ''}
        </div>
    `).join('');

    return `
        <div style="background:#fff7ed;border:1px solid rgba(0,0,0,0.04);padding:12px;border-radius:8px;margin-bottom:10px;">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
                <div style="font-weight:700;color:${color};">ICV 检查：${(icv.status||'').toUpperCase()}</div>
                <div style="font-size:12px;color:#666">自动质量门检测</div>
            </div>
            <div style="font-size:13px;color:#333">${findingsListHtml || '<div style="color:#666">无详细发现</div>'}</div>
            ${warningCount > 0 ? `
                <div style="margin-top:10px;border-top:1px solid rgba(0,0,0,0.03);padding-top:8px;">
                    <div id="icvDetails" style="display:block;margin-top:8px;padding:8px;border-radius:6px;background:#fff;border:1px solid #fee2e2;">
                        <div style="font-weight:700;color:#ef4444;margin-bottom:8px;">ICV 具体问题 (${warningCount})</div>
                        ${warningDetailsHtml}
                    </div>
                </div>
            ` : `<div style="margin-top:10px;padding-top:8px;color:#10b981;font-weight:600;">未发现 ICV 问题</div>`}
        </div>
    `;
}

// 如果存在 `ai_report_payload_<fileId>`，且没有完整报告文本，直接渲染 ICV 区块
function tryRenderIcvFromStoredPayload() {
    try {
        if (!currentFileId) return;
        const keys = getReportStorageKeys(currentFileId);
        const payloadRaw = localStorage.getItem(keys.payload);
        const reportText = localStorage.getItem(keys.report);
        if (!payloadRaw) return; // nothing to render

        const payload = JSON.parse(payloadRaw || '{}');
        const icv = extractIcvPayload(payload);
        if (!icv) return;

        // 无论是否已有全文报告，先更新静态 ICV 状态/问题面板
        renderIcvStaticFields(icv);

        // 如果已经有全文报告，避免覆盖由 displayAIReport 渲染的报告正文
        if (reportText) return;

        const aiReportSection = document.getElementById('aiReportSection');
        const aiReportContent = document.getElementById('aiReportContent');
        if (!aiReportSection || !aiReportContent) return;
        aiReportSection.style.display = 'block';

        const icvHtml = buildIcvSummaryHtml(icv);

        aiReportContent.innerHTML = icvHtml + `<div style="color:#666;margin-top:8px">报告文本尚未生成。</div>`;
    } catch (e) {
        console.warn('tryRenderIcvFromStoredPayload failed', e);
    }
}

function renderIcvStaticFields(icv) {
    try {
        const statusEl = document.getElementById('icvStaticStatus');
        const issuesEl = document.getElementById('icvStaticIssues');
        if (!statusEl || !issuesEl) return;

        const status = (icv && icv.status) ? String(icv.status).toUpperCase() : '等待';
        statusEl.textContent = status;
        statusEl.style.color = status === 'PASS' ? '#10b981' : status === 'WARN' ? '#f59e0b' : status === 'UNAVAILABLE' ? '#f59e0b' : '#ef4444';

        if (status === 'UNAVAILABLE') {
            const reason = (icv && (icv.error_message || icv.error_code)) ? String(icv.error_message || icv.error_code) : 'unknown';
            issuesEl.innerHTML = `<div style="color:#b45309;font-weight:600;">ICV result unavailable: ${reason}</div>`;
            return;
        }

        const findings = Array.isArray(icv && icv.findings) ? icv.findings : [];
        const problems = findings.filter(f => String((f && f.status) || '').toLowerCase() !== 'pass');
        if (!problems.length) {
            issuesEl.innerHTML = '<div style="color:#10b981;font-weight:600;">未发现 ICV 问题</div>';
            return;
        }

        issuesEl.innerHTML = problems.map((f) => `
            <div style="padding:6px 0;border-bottom:1px dashed #eee;">
                <div style="display:flex;justify-content:space-between;gap:8px;align-items:center;">
                    <div style="font-weight:700;color:#ef4444;">${String((f.id||'unknown')).replace(/_/g,' ')}</div>
                    <div style="font-size:12px;font-weight:700;color:#ef4444;">${f.status || 'unknown'}</div>
                </div>
                <div style="margin-top:4px;color:#333;">${f.message || ''}</div>
                ${f.suggested_action ? `<div style="margin-top:4px;color:#2563eb;">建议: ${f.suggested_action}</div>` : ''}
            </div>
        `).join('');
    } catch (e) {
        // ignore
    }
}

function setStrokePlaceholder(text) {
    const strokeCell = document.getElementById('cell-stroke');
    if (!strokeCell || window.getComputedStyle(strokeCell).display === 'none') return;

    const img = document.getElementById('img-stroke');
    const status = document.getElementById('status-stroke');
    if (!img) return;

    try {
        const w = 480; const h = 320;
        const canvas = document.createElement('canvas');
        canvas.width = w; canvas.height = h;
        const ctx = canvas.getContext('2d');
        // 鑳屾櫙
        ctx.fillStyle = '#000000';
        ctx.fillRect(0, 0, w, h);
        // 杈规
        ctx.strokeStyle = '#000000'; ctx.lineWidth = 4;
        ctx.strokeRect(0, 0, w, h);
        // 鏂囨湰
        ctx.fillStyle = '#f3f4f6';
        ctx.font = '20px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(text, w/2, h/2);

        img.src = canvas.toDataURL('image/png');
        // 鏍囪涓哄崰浣嶅浘锛岄伩鍏嶈鍏ㄥ眬鐨?rotate(-90deg) 鏍峰紡鏃嬭浆
        img.classList.add('placeholder-image');
        if (status) {
            status.textContent = '-';
            status.className = 'cell-status';
            status.style.display = 'block';
        }
    } catch (e) {
        console.error('璁剧疆 stroke 鍗犱綅鍥惧け璐?', e);
    }
}

function optimizeGridLayout() {
    const grid = document.querySelector('.image-grid');
    if (!grid) return;

    grid.classList.remove('layout-compact', 'layout-single', 'layout-dual', 'layout-full');

    if (viewerLayoutMode === 'single') {
        grid.style.gridTemplateColumns = '1fr';
        grid.style.gridTemplateRows = '1fr';
        grid.classList.add('layout-compact', 'layout-single');
        return;
    }

    if (viewerLayoutMode === 'dual') {
        grid.style.gridTemplateColumns = 'repeat(2, minmax(0, 1fr))';
        grid.style.gridTemplateRows = '1fr';
        grid.classList.add('layout-compact', 'layout-dual');
        return;
    }

    // 8-grid mode
    grid.style.gridTemplateColumns = 'repeat(4, 1fr)';
    grid.style.gridTemplateRows = 'repeat(2, 1fr)';
    grid.classList.add('layout-full');
}

// 鍋忎晶閫夋嫨宸茬Щ闄わ紝鍚庣鎻愪緵 hemisphere 瀛楁


const LUT_MODELS = ['cbf', 'cbv', 'tmax'];

function formatLutValue(value) {
    const n = Number(value);
    if (!Number.isFinite(n)) return '--';
    const abs = Math.abs(n);
    if (abs >= 100) return n.toFixed(0);
    if (abs >= 10) return n.toFixed(1);
    return n.toFixed(2);
}

function getLutCell(modelKey) {
    return document.getElementById(`cell-${modelKey}`);
}

function ensureLutScaleElements() {
    LUT_MODELS.forEach((modelKey) => {
        const cell = getLutCell(modelKey);
        if (!cell) return;

        let scale = document.getElementById(`lut-scale-${modelKey}`);
        if (scale) return;

        scale = document.createElement('div');
        scale.id = `lut-scale-${modelKey}`;
        scale.className = 'lut-scale';
        scale.innerHTML = `
            <div class="lut-scale-value lut-scale-max" id="lut-max-${modelKey}">--</div>
            <div class="lut-scale-bar-wrap">
                <div class="lut-scale-bar"></div>
                <div class="lut-scale-mid-tick"></div>
                <div class="lut-scale-value lut-scale-mid" id="lut-mid-${modelKey}">--</div>
            </div>
            <div class="lut-scale-value lut-scale-min" id="lut-min-${modelKey}">--</div>
        `;
        cell.appendChild(scale);
    });
}

function cachePseudocolorLutStats(generateResult) {
    if (!generateResult || !generateResult.results) return;
    Object.entries(generateResult.results).forEach(([sliceKey, modelMap]) => {
        const sliceIndex = Number(sliceKey);
        if (!Number.isInteger(sliceIndex) || !modelMap) return;

        Object.entries(modelMap).forEach(([modelKey, modelResult]) => {
            if (!LUT_MODELS.includes(modelKey)) return;
            if (!modelResult || !modelResult.success || !modelResult.lut_stats) return;
            if (!pseudocolorLutStats[modelKey]) pseudocolorLutStats[modelKey] = {};
            pseudocolorLutStats[modelKey][sliceIndex] = modelResult.lut_stats;
        });
    });
}

function updateLutScale(modelKey, sliceIndex = currentSlice) {
    const scale = document.getElementById(`lut-scale-${modelKey}`);
    const cell = getLutCell(modelKey);
    const img = document.getElementById(`img-${modelKey}`);
    if (!scale || !cell || !img) return;

    const cellVisible = window.getComputedStyle(cell).display !== 'none';
    const showScale = !!pseudocolorMode[modelKey] && cellVisible && img.style.display !== 'none';
    if (!showScale) {
        scale.style.display = 'none';
        return;
    }

    const stats = pseudocolorLutStats[modelKey] ? pseudocolorLutStats[modelKey][sliceIndex] : null;
    const maxEl = document.getElementById(`lut-max-${modelKey}`);
    const midEl = document.getElementById(`lut-mid-${modelKey}`);
    const minEl = document.getElementById(`lut-min-${modelKey}`);

    if (stats) {
        const minVal = stats.min_value;
        const maxVal = stats.max_value;
        const midVal = Number.isFinite(Number(minVal)) && Number.isFinite(Number(maxVal))
            ? (Number(minVal) + Number(maxVal)) / 2
            : null;
        if (maxEl) maxEl.textContent = formatLutValue(maxVal);
        if (midEl) midEl.textContent = formatLutValue(midVal);
        if (minEl) minEl.textContent = formatLutValue(minVal);
    } else {
        if (maxEl) maxEl.textContent = '--';
        if (midEl) midEl.textContent = '--';
        if (minEl) minEl.textContent = '--';
    }

    scale.style.display = 'flex';
}

function refreshAllLutScales() {
    ensureLutScaleElements();
    LUT_MODELS.forEach((modelKey) => updateLutScale(modelKey, currentSlice));
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
    
    // 娣诲姞璋冭瘯淇℃伅
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
    
    // 璋冩暣鍔犺浇椤哄簭浠ュ尮閰嶆柊鐨勫竷灞€
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
    refreshAllLutScales();
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
        
        // 娣诲姞鍥惧儚鍔犺浇閿欒澶勭悊
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
    updateLutScale(modelKey, currentSlice);
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
        showLoading(true, '姝ｅ湪涓烘墍鏈夊垏鐗囩敓鎴愪吉褰╁浘...');
        btn.disabled = true;
        fetch(`/generate_all_pseudocolors/${currentFileId}`)
            .then(res => res.json()).then(data => {
                if (data.success) {
                    pseudocolorGenerated = true;
                    isPseudocolorActive = true;
                    cachePseudocolorLutStats(data);
                    ensureLutScaleElements();
                    ['cbf', 'cbv', 'tmax'].forEach(model => {
                        pseudocolorMode[model] = true;
                        document.getElementById('toggle-' + model).classList.add('active');
                    });
                    btn.textContent = '关闭伪彩图模式';
                    btn.disabled = false;
                    loadSlice(currentSlice);
                    showMessage(`浼僵鍥剧敓鎴愬畬鎴?(${data.total_success}/${data.total_attempts})`, 'success');
                } else {
                    btn.disabled = false;
                    showMessage('鐢熸垚澶辫触: ' + data.error, 'error');
                }
            }).catch(err => {
                btn.disabled = false;
                showMessage('鐢熸垚澶辫触: ' + err.message, 'error');
            }).finally(() => showLoading(false));
    } else {
        isPseudocolorActive = !isPseudocolorActive;
        ['cbf', 'cbv', 'tmax'].forEach(model => {
            pseudocolorMode[model] = isPseudocolorActive;
            document.getElementById('toggle-' + model).classList.toggle('active', isPseudocolorActive);
        });
        btn.textContent = isPseudocolorActive ? '关闭伪彩图模式' : '开启伪彩图模式';
        loadSlice(currentSlice);
    }
}

function toggleCellPseudocolor(modelKey) {
    pseudocolorMode[modelKey] = !pseudocolorMode[modelKey];
    document.getElementById('toggle-' + modelKey).classList.toggle('active');
    updateAIImage(modelKey, currentRgbFiles[currentSlice]);
    updateLutScale(modelKey, currentSlice);
}

function toggleAnalysisPanel() { document.getElementById('analysisPanel').classList.toggle('open'); }

function startStrokeAnalysis() {
    showLoading(true, '姝ｅ湪杩涜鑴戝崚涓垎鏋?..');
    fetch(`/analyze_stroke/${currentFileId}?hemisphere=${currentHemisphere}`)
        .then(res => res.json()).then(data => {
            if (data.success || data.analysis_results) {
                analysisResults = data.analysis_results || data;
                displayAnalysisResults();
                showMessage('鍒嗘瀽瀹屾垚', 'success');
            } else { showMessage('鍒嗘瀽澶辫触: ' + data.error, 'error'); }
        }).catch(err => showMessage('鍒嗘瀽澶辫触: ' + err.message, 'error')).finally(() => showLoading(false));
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
            statusEl.textContent = '存在显著不匹配';
            statusEl.className = 'metric-value alert';
            mismatchContainer.classList.add('warning');
        } else {
            statusEl.textContent = '鏃犳樉钁椾笉鍖归厤';
            statusEl.className = 'metric-value good';
            mismatchContainer.classList.remove('warning');
        }
    }

    // 淇濆瓨鍒嗘瀽鏁版嵁鍒?localStorage锛屼緵鎶ュ憡椤甸潰浣跨敤锛堣法鏍囩椤靛叡浜級
    // 闀滃儚閫昏緫锛氬墠绔€夋嫨left 鈫?鐥呯伓鍦╮ight锛堝彂鐥呬晶锛?
    const hemisphereMap = {
        'left': 'right',
        'right': 'left',
        'both': 'both'
    };
    const lesionHemisphere = hemisphereMap[currentHemisphere] || 'both';
    
    sessionStorage.setItem('analysis_data', JSON.stringify({
        file_id: currentFileId,
        core_infarct_volume: analysisResults.report?.summary?.core_volume_ml || 0,
        penumbra_volume: analysisResults.report?.summary?.penumbra_volume_ml || 0,
        mismatch_ratio: analysisResults.report?.summary?.mismatch_ratio || 0,
        has_mismatch: analysisResults.report?.summary?.has_mismatch || false,
        hemisphere: lesionHemisphere
    }));
    localStorage.setItem('analysis_data', JSON.stringify({
        file_id: currentFileId,
        core_infarct_volume: analysisResults.report?.summary?.core_volume_ml || 0,
        penumbra_volume: analysisResults.report?.summary?.penumbra_volume_ml || 0,
        mismatch_ratio: analysisResults.report?.summary?.mismatch_ratio || 0,
        has_mismatch: analysisResults.report?.summary?.has_mismatch || false,
        hemisphere: lesionHemisphere
    }));

    // 淇濆瓨瀹屾暣鐨勫垎鏋愮粨鏋滃埌localStorage锛岀敤浜庨〉闈㈠埛鏂板悗鎭㈠
    if (currentFileId) {
        localStorage.setItem(`stroke_analysis_${currentFileId}`, JSON.stringify(analysisResults));
    }

    saveAnalysisToDB();
}

function updateStrokeImage() {
    if (!analysisResults) return;
    const strokeCell = document.getElementById('cell-stroke');
    if (!strokeCell || window.getComputedStyle(strokeCell).display === 'none') return;
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

    // 闀滃儚閫昏緫锛氬墠绔€夋嫨left 鈫?鐥呯伓鍦╮ight锛堝彂鐥呬晶锛?
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
        
        // 娉ㄦ剰锛氬凡绉婚櫎鑷姩璋冪敤鐧惧窛 AI锛屾敼涓烘墜鍔ㄨЕ鍙?
    } catch (err) {
        showMsg('保存失败: ' + err.message, 'error');
    }
}

// 璋冪敤 NeuroMatrix AI 鐢熸垚鎶ュ憡
function getReportStorageKeys(fileId = currentFileId) {
    const normalized = fileId || '';
    return {
        report: `ai_report_${normalized}`,
        generating: `ai_report_generating_${normalized}`,
        error: `ai_report_error_${normalized}`,
        payload: `ai_report_payload_${normalized}`,
    };
}

function getReportUrl() {
    return `/report/${currentPatientId}?file_id=${encodeURIComponent(currentFileId)}`;
}

function getReportCacheState(fileId = currentFileId) {
    const keys = getReportStorageKeys(fileId);
    const reportText = localStorage.getItem(keys.report) || '';
    const hasReport = !!reportText;
    const isGenerating = localStorage.getItem(keys.generating) === 'true';
    const errorMessage = localStorage.getItem(keys.error) || '';

    if (isGenerating) {
        return { status: 'generating', errorMessage, hasReport, isGenerating, reportText };
    }
    if (hasReport) {
        return { status: 'ready', errorMessage: '', hasReport, isGenerating: false, reportText };
    }
    if (errorMessage) {
        return { status: 'error', errorMessage, hasReport: false, isGenerating: false, reportText: '' };
    }
    return { status: 'idle', errorMessage: '', hasReport: false, isGenerating: false, reportText: '' };
}

function getTopbarReportButton() {
    return document.getElementById('topbarReportBtn');
}

function setTopbarReportButtonState(state) {
    const btn = getTopbarReportButton();
    if (!btn) return;

    btn.classList.remove('report-ready', 'report-generating', 'report-error');
    if (state === 'ready') {
        btn.textContent = '\u67e5\u770b\u62a5\u544a';
        btn.classList.add('report-ready');
        return;
    }
    if (state === 'generating') {
        btn.textContent = '\u751f\u6210\u4e2d...';
        btn.classList.add('report-generating');
        return;
    }
    if (state === 'error') {
        btn.textContent = '\u91cd\u8bd5\u751f\u6210';
        btn.classList.add('report-error');
        return;
    }
    btn.textContent = '\u751f\u6210\u62a5\u544a';
}

function renderReportStatusBanner(state, message = '', errorMessage = '') {
    const banner = document.getElementById('reportStatusBanner');
    const text = document.getElementById('reportStatusText');
    const primaryBtn = document.getElementById('reportStatusPrimaryBtn');
    if (!banner || !text || !primaryBtn) return;

    if (reportStatusDismissed && state !== 'generating') {
        banner.style.display = 'none';
        return;
    }

    if (state === 'idle') {
        banner.style.display = 'none';
        return;
    }

    if (state === 'generating') {
        text.textContent = message || '\u7cfb\u7edf\u6b63\u5728\u81ea\u52a8\u751f\u6210\u62a5\u544a\uff0c\u4f60\u53ef\u4ee5\u7ee7\u7eed\u9605\u7247\u3002';
        primaryBtn.textContent = '\u67e5\u770b\u8fdb\u5ea6';
    } else if (state === 'ready') {
        text.textContent = message || '\u62a5\u544a\u5df2\u5c31\u7eea\uff0c\u53ef\u968f\u65f6\u67e5\u770b\u3002';
        primaryBtn.textContent = '\u67e5\u770b\u62a5\u544a';
    } else {
        text.textContent = message || `\u81ea\u52a8\u751f\u6210\u5931\u8d25\uff1a${errorMessage || '\u672a\u77e5\u9519\u8bef'}`;
        primaryBtn.textContent = '\u91cd\u8bd5\u751f\u6210';
    }

    banner.style.display = 'flex';
}

function setReportStatus(state, message = '', errorMessage = '') {
    if (reportStatusState !== state) {
        reportStatusDismissed = false;
    }
    reportStatusState = state;
    setTopbarReportButtonState(state);
    renderReportStatusBanner(state, message, errorMessage);
}

function refreshReportStatusFromCache() {
    const cache = getReportCacheState(currentFileId);
    if (cache.status === 'generating') {
        setReportStatus('generating');
        return cache;
    }
    if (cache.status === 'ready') {
        setReportStatus('ready');
        return cache;
    }
    if (cache.status === 'error') {
        setReportStatus('error', '', cache.errorMessage);
        return cache;
    }
    setReportStatus('idle');
    return cache;
}

function handleReportStatusPrimaryAction() {
    if (reportStatusState === 'ready' || reportStatusState === 'generating') {
        openReportPage();
        return;
    }
    triggerGenerateReportFromTopBar();
}

function bindReportStatusBannerEvents() {
    const primaryBtn = document.getElementById('reportStatusPrimaryBtn');
    const closeBtn = document.getElementById('reportStatusCloseBtn');
    if (primaryBtn && !primaryBtn.dataset.bound) {
        primaryBtn.addEventListener('click', handleReportStatusPrimaryAction);
        primaryBtn.dataset.bound = '1';
    }
    if (closeBtn && !closeBtn.dataset.bound) {
        closeBtn.addEventListener('click', () => {
            reportStatusDismissed = true;
            const banner = document.getElementById('reportStatusBanner');
            if (banner) banner.style.display = 'none';
        });
        closeBtn.dataset.bound = '1';
    }
}

function initializeReportAutoFlow() {
    bindReportStatusBannerEvents();
    refreshReportStatusFromCache();

    if (autoReportBootstrapped) {
        return;
    }
    autoReportBootstrapped = true;

    const cache = getReportCacheState(currentFileId);
    // 如果已有报告，直接在侧边面板显示
    if (cache.status === 'ready' && cache.reportText) {
        displayAIReport(cache.reportText, false);
        return;
    }
    if (cache.status === 'generating') {
        return;
    }

    autoGenerateReportIfNeeded();
}

async function autoGenerateReportIfNeeded() {
    if (!currentPatientId || !currentFileId) return;
    const cache = getReportCacheState(currentFileId);
    if (cache.hasReport || cache.isGenerating) {
        refreshReportStatusFromCache();
        // 如果已有报告，尝试在侧边面板显示
        if (cache.hasReport && cache.reportText) {
            displayAIReport(cache.reportText, false);
        }
        return;
    }

    setReportStatus('generating', '\u7cfb\u7edf\u6b63\u5728\u81ea\u52a8\u751f\u6210\u62a5\u544a\uff0c\u8bf7\u7ee7\u7eed\u9605\u7247\u3002');
    const result = await generateAIReport({
        openAfterGenerate: false,
        showInline: true,
        source: 'auto',
    });

    if (!result.success) {
        setReportStatus('error', `\u81ea\u52a8\u751f\u6210\u5931\u8d25\uff1a${result.message || '\u672a\u77e5\u9519\u8bef'}`, result.message || '');
    }
}

function setReportGenerating(fileId, generating) {
    const keys = getReportStorageKeys(fileId);
    if (generating) {
        localStorage.setItem(keys.generating, 'true');
        // 兼容旧版 /report 页面（读取全局键）
        localStorage.setItem('ai_report_generating', 'true');
    } else {
        localStorage.removeItem(keys.generating);
        localStorage.removeItem('ai_report_generating');
    }

    if (fileId === currentFileId) {
        refreshReportStatusFromCache();
    }
}

function clearReportCache(fileId) {
    const keys = getReportStorageKeys(fileId);
    localStorage.removeItem(keys.report);
    localStorage.removeItem(keys.error);
    localStorage.removeItem(keys.generating);
    localStorage.removeItem(keys.payload);
    // 清理历史全局键，避免旧页面串病例
    localStorage.removeItem('ai_report');
    localStorage.removeItem('ai_report_generating');

    if (fileId === currentFileId) {
        refreshReportStatusFromCache();
    }
}

function openReportPage(reportWindow = null) {
    const reportUrl = getReportUrl();
    if (reportWindow && !reportWindow.closed) {
        reportWindow.location.href = reportUrl;
        return;
    }
    const win = window.open(reportUrl, '_blank');
    if (!win) {
        // 弹窗被拦截时兜底在当前窗口打开
        window.location.href = reportUrl;
    }
}

async function generateAIReport(options = {}) {
    const {
        openAfterGenerate = false,
        reportWindow = null,
        showInline = true,
        source = 'manual',
    } = options;

    if (!currentPatientId) {
        console.warn('missing patient_id, skip AI report generation');
        return { success: false, message: 'missing patient_id' };
    }
    if (!currentFileId) {
        console.warn('missing file_id, skip AI report generation');
        return { success: false, message: 'missing file_id' };
    }

    const keys = getReportStorageKeys(currentFileId);
    setReportGenerating(currentFileId, true);
    localStorage.removeItem(keys.error);
    setReportStatus('generating');

    try {
        console.log(`[MedGemma][Viewer] start generate source=${source} patient_id=${currentPatientId} file_id=${currentFileId}`);

        const aiReportSection = document.getElementById('aiReportSection');
        const aiReportContent = document.getElementById('aiReportContent');
        if (showInline && aiReportSection && aiReportContent) {
            aiReportSection.style.display = 'block';
            aiReportContent.innerHTML = `
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px; border-radius: 12px; text-align: center;">
                    <div style="border: 4px solid rgba(255,255,255,0.3); border-top: 4px solid white; border-radius: 50%; width: 48px; height: 48px; animation: spin 1s linear infinite; margin: 0 auto 16px;"></div>
                    <p style="color: white; font-size: 16px; font-weight: 600; margin: 0;">NeuroMatrix AI 正在生成报告...</p>
                    <p style="color: rgba(255,255,255,0.8); font-size: 13px; margin-top: 8px;">请稍候，模型推理时间可能较长</p>
                </div>
            `;
        }

        const endpoint = `/api/generate_report/${currentPatientId}?format=markdown&file_id=${encodeURIComponent(currentFileId)}&source=${encodeURIComponent(source)}`;
        const response = await fetch(endpoint);
        let data = {};
        try {
            data = await response.json();
        } catch (parseErr) {
            data = { status: 'error', message: `Invalid JSON response: ${parseErr.message}` };
        }

        console.log('[MedGemma][Viewer] API response:', data);
        if (data.json_path) {
            console.log(`[MedGemma][Viewer] report json path: ${data.json_path}`);
        }

        if (response.ok && data.status === 'success') {
            localStorage.setItem(keys.report, data.report || '');
            if (data.report_payload) {
                localStorage.setItem(keys.payload, JSON.stringify(data.report_payload));
            } else {
                localStorage.removeItem(keys.payload);
            }
            // 兼容旧版 /report 页面（读取全局键）
            localStorage.setItem('ai_report', data.report || '');
            setReportGenerating(currentFileId, false);
            localStorage.removeItem(keys.error);
            setReportStatus('ready');

            if (showInline) {
                displayAIReport(data.report, data.is_mock);
            }

            if (openAfterGenerate) {
                openReportPage(reportWindow);
            }

            showMsg(
                'AI 报告生成成功' + (data.is_mock ? '（模拟）' : ''),
                'success'
            );
            return { success: true, data };
        }

        const errorMessage = data.message || `HTTP ${response.status}`;
        console.warn(`[MedGemma][Viewer] generate failed: ${errorMessage}`);
        localStorage.setItem(keys.error, errorMessage);
        setReportGenerating(currentFileId, false);
        setReportStatus('error', `自动生成失败：${errorMessage}`, errorMessage);

        if (showInline && aiReportContent) {
            aiReportContent.innerHTML = `
                <div style="background: #fee2e2; padding: 16px; border-radius: 8px; border-left: 4px solid #ef4444;">
                    <p style="color: #dc2626; font-weight: 600; margin: 0 0 8px 0;">AI 报告生成失败</p>
                    <p style="color: #991b1b; margin: 0;">${errorMessage}</p>
                </div>
            `;
        }
        return { success: false, message: errorMessage, data };
    } catch (err) {
        const errorMessage = err.message || 'Unknown error';
        console.error(`[MedGemma][Viewer] generate exception: ${errorMessage}`);
        localStorage.setItem(keys.error, errorMessage);
        setReportGenerating(currentFileId, false);
        setReportStatus('error', `自动生成失败：${errorMessage}`, errorMessage);

        const aiReportContent = document.getElementById('aiReportContent');
        if (showInline && aiReportContent) {
            aiReportContent.innerHTML = `
                <div style="background: #fee2e2; padding: 16px; border-radius: 8px; border-left: 4px solid #ef4444;">
                    <p style="color: #dc2626; font-weight: 600; margin: 0 0 8px 0;">网络或服务异常</p>
                    <p style="color: #991b1b; margin: 0;">${errorMessage}</p>
                </div>
            `;
        }
        return { success: false, message: errorMessage };
    }
}

function displayAIReport(report, isMock) {
    const aiReportSection = document.getElementById('aiReportSection');
    const aiReportContent = document.getElementById('aiReportContent');
    
    if (!aiReportSection || !aiReportContent) return;
    aiReportSection.style.display = 'block';

    // build ICV summary (if present in stored report payload)
    let icvHtml = '';
    try {
        const keys = getReportStorageKeys(currentFileId);
        const payloadRaw = localStorage.getItem(keys.payload) || null;
        if (payloadRaw) {
                const payload = JSON.parse(payloadRaw || '{}');
                const icv = extractIcvPayload(payload);
            if (icv) {
                // 同步固定 HTML 字段（状态 + 具体问题）
                renderIcvStaticFields(icv);
                icvHtml = buildIcvSummaryHtml(icv);
            }
        }
    } catch (e) {
        console.warn('Failed to render ICV summary', e);
        icvHtml = '';
    }

    aiReportContent.innerHTML = `
        <div style="background: #eff6ff; padding: 12px; border-radius: 6px; border-left: 3px solid #2563eb; margin-bottom: 8px;">
            <div style="font-size: 11px; font-weight: 600; color: #2563eb; margin-bottom: 8px;">
                NeuroMatrix AI 报告 ${isMock ? '<span style="background: #ffd700; padding: 1px 6px; border-radius: 8px; font-size: 10px;">模拟</span>' : ''}
            </div>
            ${icvHtml}
            <div style="font-size: 12px; line-height: 1.8; color: #333;">${parseMarkdown(report)}</div>
        </div>
    `;

    // bind toggle handler for the ICV details
    try { attachIcvToggleHandlers(); } catch (e) { /* ignore */ }

    // 同步到静态面板或隐藏静态面板
    try {
        const staticPanel = document.getElementById('icvStaticPanel');
        if (staticPanel && icvHtml && icvHtml.length > 0) {
            staticPanel.style.display = 'block';
        }
    } catch (e) { /* ignore */ }
}

function attachIcvToggleHandlers() {
    try {
        const btn = document.getElementById('icvToggleBtn');
        const box = document.getElementById('icvDetails');
        if (!btn || !box) return;
        if (btn.dataset.attach) return;
        btn.dataset.attach = '1';
        btn.addEventListener('click', () => {
            if (box.style.display === 'none' || !box.style.display) {
                box.style.display = 'block';
                btn.textContent = btn.textContent.replace(/▾$/, '▴');
            } else {
                box.style.display = 'none';
                btn.textContent = btn.textContent.replace(/▴$/, '▾');
            }
        });
    } catch (e) {
        // ignore
    }
}

// 鎵嬪姩瑙﹀彂 AI 鎶ュ憡鐢熸垚锛堢敱鐢ㄦ埛鐐瑰嚮鎸夐挳璋冪敤锛?
function manualGenerateAIReport() {
    clearReportCache(currentFileId);
    setReportStatus('generating', '\u6b63\u5728\u91cd\u65b0\u751f\u6210\u62a5\u544a\uff0c\u8bf7\u7a0d\u5019\u3002');
    generateAIReport({ openAfterGenerate: false, showInline: true, source: 'manual_panel' });
}

async function triggerGenerateReportFromTopBar() {
    if (!currentPatientId || !currentFileId) {
        showMsg('\u7f3a\u5c11 patient_id \u6216 file_id\uff0c\u65e0\u6cd5\u751f\u6210\u62a5\u544a', 'warning');
        return;
    }

    console.log(`[MedGemma][Viewer] triggerGenerateReportFromTopBar patient_id=${currentPatientId} file_id=${currentFileId}`);
    const cache = getReportCacheState(currentFileId);

    if (cache.status === 'ready') {
        openReportPage();
        return;
    }

    if (cache.status === 'generating') {
        openReportPage();
        return;
    }

    clearReportCache(currentFileId);
    setReportStatus('generating', '\u7cfb\u7edf\u5df2\u5f00\u59cb\u751f\u6210\u62a5\u544a\uff0c\u4f60\u53ef\u4ee5\u7ee7\u7eed\u9605\u7247\u3002');
    const result = await generateAIReport({
        openAfterGenerate: false,
        showInline: false,
        source: 'manual_topbar',
    });

    if (result.success) {
        showMsg('\u62a5\u544a\u5df2\u751f\u6210\uff0c\u70b9\u51fb\u201c\u67e5\u770b\u62a5\u544a\u201d\u5373\u53ef\u6253\u5f00\u3002', 'success');
        return;
    }

    showMsg(`\u62a5\u544a\u751f\u6210\u5931\u8d25\uff1a${result.message || '\u672a\u77e5\u9519\u8bef'}`, 'error');
}

window.triggerGenerateReportFromTopBar = triggerGenerateReportFromTopBar;

function checkAnalysisStatus() {
    if (!currentFileId) return;
    
    fetch(`/api/get_imaging/${currentFileId}`)
        .then(res => res.json())
        .then(resp => {
            if (resp && resp.success && resp.data && resp.data.analysis_result) {
                const dbAnalysis = resp.data.analysis_result;
                if (dbAnalysis.success) {
                    // 妫€鏌ocalStorage涓槸鍚﹀凡鏈夊垎鏋愮粨鏋?
                    const savedAnalysis = localStorage.getItem(`stroke_analysis_${currentFileId}`);
                    if (!savedAnalysis) {
                        // 濡傛灉localStorage涓病鏈夛紝浣嗘暟鎹簱涓湁锛屾洿鏂板墠绔姸鎬?
                        analysisResults = dbAnalysis;
                        displayAnalysisResults();
                        console.log('浠庢暟鎹簱鍔犺浇鍒嗘瀽缁撴灉');
                    }
                }
            }
        })
        .catch(err => {
            console.warn('妫€鏌ュ垎鏋愮姸鎬佸け璐?', err);
        });
}






