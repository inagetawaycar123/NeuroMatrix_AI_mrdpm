const { useState, useEffect } = React;

const PatientInfoModule = ({ data, isEditing, onUpdate }) => {
    if (!data) {
        return React.createElement("div", { className: "module-empty" }, "鍔犺浇鎮ｈ€呬俊鎭腑...");
    }
    const formatDateTime = (dateStr) => {
        if (!dateStr) {
            return '--';
        }
        return new Date(dateStr).toLocaleString('zh-CN');
    };
    return React.createElement("div", { className: "report-module" },
        React.createElement("div", { className: "module-header", style: { background: 'linear-gradient(135deg, #60a5fa 0%, #3b82f6 100%)' } }, "鎮ｈ€呭熀鏈俊鎭?),
        React.createElement("div", { className: "module-content" },
            React.createElement("div", { className: "report-field" },
                React.createElement("span", { className: "field-label" }, "ID"),
                React.createElement("span", { className: "field-value" }, data.id || '--')
            ),
            React.createElement("div", { className: "report-field" },
                React.createElement("span", { className: "field-label" }, "濮撳悕"),
                isEditing
                    ? React.createElement("input", { type: "text", className: "field-edit", value: data.patient_name, onChange: (e) => onUpdate('patient_name', e.target.value) })
                    : React.createElement("span", { className: "field-value" }, data.patient_name || '--')
            ),
            React.createElement("div", { className: "report-field" },
                React.createElement("span", { className: "field-label" }, "骞撮緞"),
                isEditings
                    ? React.createElement("input", { type: "number", className: "field-edit", value: data.patient_age, onChange: (e) => onUpdate('patient_age', parseInt(e.target.value)) })
                    : React.createElement("span", { className: "field-value" }, data.patient_age, "宀?)
            ),
            React.createElement("div", { className: "report-field" },
                React.createElement("span", { className: "field-label" }, "鎬у埆"),
                isEditing
                    ? React.createElement("input", { type: "text", className: "field-edit", value: data.patient_sex, onChange: (e) => onUpdate('patient_sex', e.target.value) })
                    : React.createElement("span", { className: "field-value" }, data.patient_sex || '--')
            ),
            React.createElement("div", { className: "report-field" },
                React.createElement("span", { className: "field-label" }, "鍙戠梾鏃堕棿"),
                isEditing
                    ? React.createElement("input", { type: "datetime-local", className: "field-edit", defaultValue: data.onset_exact_time?.slice(0, 16), onChange: (e) => onUpdate('onset_exact_time', e.target.value) })
                    : React.createElement("span", { className: "field-value" }, formatDateTime(data.onset_exact_time))
            ),
            React.createElement("div", { className: "report-field" },
                React.createElement("span", { className: "field-label" }, "鍏ラ櫌鏃堕棿"),
                isEditing
                    ? React.createElement("input", { type: "datetime-local", className: "field-edit", defaultValue: data.admission_time?.slice(0, 16), onChange: (e) => onUpdate('admission_time', e.target.value) })
                    : React.createElement("span", { className: "field-value" }, formatDateTime(data.admission_time))
            ),
            React.createElement("div", { className: "report-field" },
                React.createElement("span", { className: "field-label" }, "鍏ラ櫌NIHSS璇勫垎"),
                isEditing
                    ? React.createElement("input", { type: "number", className: "field-edit", min: "0", max: "42", value: data.admission_nihss, onChange: (e) => onUpdate('admission_nihss', parseInt(e.target.value)) })
                    : React.createElement("span", { className: "field-value" }, data.admission_nihss, " 鍒?)
            ),
            React.createElement("div", { className: "report-field" },
                React.createElement("span", { className: "field-label" }, "鍙戠梾鑷冲叆闄?),
                isEditing
                    ? React.createElement("input", { type: "text", className: "field-edit", defaultValue: data.surgery_time, onChange: (e) => onUpdate('surgery_time', e.target.value) })
                    : React.createElement("span", { className: "field-value" }, data.surgery_time || '--')
            )
        )
    );
};

const ImageFindingsModule = ({ data, findings, isEditing, onUpdate }) => {
    if (!data) {
        return React.createElement("div", { className: "module-empty" }, "鍔犺浇褰卞儚鍒嗘瀽鏁版嵁涓?..");
    }
    return React.createElement("div", { className: "report-module" },
        React.createElement("div", { className: "module-header", style: { background: 'linear-gradient(135deg, #60a5fa 0%, #3b82f6 100%)' } }, "褰卞儚鍙戠幇"),
        React.createElement("div", { className: "module-content" },
            React.createElement("div", { className: "report-field full-width" },
                React.createElement("span", { className: "field-label" }, "鏍稿績姊楁鍖?),
                isEditing
                    ? React.createElement("textarea", { className: "field-edit-area", rows: 2, value: findings.core, onChange: (e) => onUpdate('core', e.target.value) })
                    : React.createElement("div", { className: "field-value" }, findings.core || '--')
            ),
            React.createElement("div", { className: "report-field full-width" },
                React.createElement("span", { className: "field-label" }, "鍗婃殫甯﹀尯鍩?),
                isEditing
                    ? React.createElement("textarea", { className: "field-edit-area", rows: 2, value: findings.penumbra, onChange: (e) => onUpdate('penumbra', e.target.value) })
                    : React.createElement("div", { className: "field-value" }, findings.penumbra || '--')
            ),
            React.createElement("div", { className: "report-field full-width" },
                React.createElement("span", { className: "field-label" }, "琛€绠¤瘎浼?),
                isEditing
                    ? React.createElement("textarea", { className: "field-edit-area", rows: 2, value: findings.vessel, onChange: (e) => onUpdate('vessel', e.target.value) })
                    : React.createElement("div", { className: "field-value" }, findings.vessel || '--')
            ),
            React.createElement("div", { className: "report-field full-width" },
                React.createElement("span", { className: "field-label" }, "鐏屾敞鍒嗘瀽"),
                isEditing
                    ? React.createElement("textarea", { className: "field-edit-area", rows: 3, value: findings.perfusion, onChange: (e) => onUpdate('perfusion', e.target.value) })
                    : React.createElement("div", { className: "field-value", style: { whiteSpace: 'pre-wrap' } }, findings.perfusion || '--')
            ),
            React.createElement("div", { className: "analysis-summary" },
                React.createElement("h4", null, "AI鍒嗘瀽鎸囨爣"),
                React.createElement("div", { className: "metric" },
                    React.createElement("span", null, "鏍稿績姊楁浣撶Н锛?),
                    React.createElement("strong", null, data.core_volume?.toFixed(1) || '--', " ml")
                ),
                React.createElement("div", { className: "metric" },
                    React.createElement("span", null, "鍗婃殫甯︿綋绉細"),
                    React.createElement("strong", null, data.penumbra_volume?.toFixed(1) || '--', " ml")
                ),
                React.createElement("div", { className: "metric" },
                    React.createElement("span", null, "涓嶅尮閰嶆瘮渚嬶細"),
                    React.createElement("strong", null, data.mismatch_ratio?.toFixed(2) || '--')
                ),
                React.createElement("div", { className: "metric" },
                    React.createElement("span", null, "涓嶅尮閰嶇姸鎬侊細"),
                    React.createElement("strong", { style: { color: data.has_mismatch ? '#ff6b6b' : '#51cf66' } }, data.has_mismatch ? '瀛樺湪鏄捐憲涓嶅尮閰? : '鏃犳樉钁椾笉鍖归厤')
                )
            )
        )
    );
};

const DoctorNotesModule = ({ notes, isEditing, onUpdate }) => {
    return React.createElement("div", { className: "report-module" },
        React.createElement("div", { className: "module-header", style: { background: 'linear-gradient(135deg, #60a5fa 0%, #3b82f6 100%)' } }, "鍖荤敓澶囨敞"),
        React.createElement("div", { className: "module-content" },
            isEditing
                ? React.createElement("textarea", { className: "field-edit-area", rows: 4, value: notes, onChange: (e) => onUpdate(e.target.value), placeholder: "璇疯緭鍏ヤ复搴婂娉ㄣ€佽瘖鏂剰瑙併€佸悗缁缓璁?.." })
                : React.createElement("div", { className: "field-value", style: { whiteSpace: 'pre-wrap', minHeight: '60px' } }, notes || '鏃?)
        )
    );
};

function renderMarkdownToHtml(markdown) {
    if (!markdown) {
        return '';
    }
    let html = markdown
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
    // 澶勭悊鏍囬 - 绠€娲佹牱寮忥紙妫€鏌ユ柟娉曘€佸奖鍍忓琛ㄧ幇銆佽绠¤瘎浼般€佽瘖鏂剰瑙併€佹不鐤楀缓璁級
    html = html.replace(/^## (妫€鏌ユ柟娉晐褰卞儚瀛﹁〃鐜皘琛€绠¤瘎浼皘璇婃柇鎰忚|娌荤枟寤鸿|褰卞儚璇婃柇鎶ュ憡)$/gm, 
        '<div style="margin: 20px 0 12px 0; padding-bottom: 8px; border-bottom: 2px solid #3b82f6; color: #3b82f6; font-size: 18px; font-weight: 600;">$1</div>');
    // 澶勭悊鏅€氫簩绾ф爣棰?
    html = html.replace(/^## (.+)$/gm, '<h2 style="color: #3b82f6; border-bottom: 3px solid #60a5fa; padding-bottom: 10px; margin: 24px 0 16px 0; font-size: 20px; font-weight: 700;">$1</h2>');
    // 澶勭悊鏅€氫笁绾ф爣棰?
    html = html.replace(/^### (.+)$/gm, '<h3 style="color: #60a5fa; margin: 20px 0 12px 0; font-size: 17px; font-weight: 600; padding-left: 12px; border-left: 4px solid #93c5fd;">$1</h3>');
    // 澶勭悊绮椾綋鏍囪 - 鐩存帴淇濈暀鏅€氭枃瀛?
    html = html.replace(/\*\*(.+?)\*\*/g, '$1');
    html = html.replace(/^\d+\. (.+)$/gm, '<li style="margin-left: 24px; margin-bottom: 8px; color: #e5e7eb;">$1</li>');
    html = html.replace(/^- (.+)$/gm, '<li style="margin-left: 24px; margin-bottom: 8px; color: #e5e7eb;">$1</li>');
    html = html.replace(/\n\n/g, '</p><p style="margin: 10px 0; line-height: 1.9; color: #d1d5db;">');
    return '<p style="margin: 10px 0; line-height: 1.9; color: #d1d5db;">' + html + '</p>';
}

const getReportStorageKeys = (fileId) => {
    if (fileId) {
        return {
            report: `ai_report_${fileId}`,
            generating: `ai_report_generating_${fileId}`,
            error: `ai_report_error_${fileId}`
        };
    }
    return {
        report: 'ai_report',
        generating: 'ai_report_generating',
        error: 'ai_report_error'
    };
};
const StructuredReport = ({ patientId, fileId, analysisData }) => {
    const [isEditing, setIsEditing] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const [aiReport, setAiReport] = useState(null);
    const [isGeneratingReport, setIsGeneratingReport] = useState(false);
    const [patient, setPatient] = useState(null);
    const [findings, setFindings] = useState({
        core: '',
        penumbra: '',
        vessel: '',
        perfusion: '',
    });
    const [notes, setNotes] = useState('');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);    // 报告缓存按 file_id 隔离，避免跨病例串数据
    useEffect(() => {
        const keys = getReportStorageKeys(fileId);

        const applyStorageState = () => {
            const savedReport = localStorage.getItem(keys.report);
            const savedGenerating = localStorage.getItem(keys.generating);
            setAiReport(savedReport || null);
            setIsGeneratingReport(savedGenerating === 'true');
        };

        applyStorageState();

        const handleStorage = (e) => {
            if (e.key === keys.generating) {
                setIsGeneratingReport(e.newValue === 'true');
                if (e.newValue === 'true') {
                    setAiReport(null);
                }
            }
            if (e.key === keys.report) {
                setAiReport(e.newValue || null);
                setIsGeneratingReport(false);
            }
            if (e.key === keys.error && e.newValue) {
                setIsGeneratingReport(false);
            }
        };

        window.addEventListener('storage', handleStorage);
        return () => window.removeEventListener('storage', handleStorage);
    }, [fileId]);
    
    useEffect(() => {
        if (!patientId) {
            setError('缂哄皯鎮ｈ€匢D');
            setLoading(false);
            return;
        }
        loadPatientInfo();
    }, [patientId]);
    
    const loadPatientInfo = async () => {
        try {
            const res = await fetch(`/api/get_patient/${patientId}`);
            const data = await res.json();
            if (data.status === 'success') {
                setPatient(data.data);
                generateImageFindings(data.data);
            } else {
                setError(data.message || '鍔犺浇鎮ｈ€呬俊鎭け璐?);
            }
        } catch (err) {
            setError('缃戠粶閿欒锛? + err.message);
        } finally {
            setLoading(false);
        }
    };
    
    const generateImageFindings = (patientData) => {
        if (!analysisData) {
            return;
        }
        const hemName = {
            left: '宸︿晶',
            right: '鍙充晶',
            both: '鍙屼晶',
        }[analysisData.hemisphere] || '鍙屼晶';
        const coreText = `鏍稿績姊楁鍖轰綅浜?{hemName}澶ц剳鍗婄悆锛屼綋绉害 ${analysisData.core_volume?.toFixed(1) || '--'} ml銆傜梾鐏剁晫闄愭竻鏅帮紝鐏屾敞淇″彿鏄庢樉闄嶄綆銆俙;
        const penumbraText = `鍗婃殫甯︼紙缂鸿鍗婂奖锛夎寖鍥村箍娉涳紝浣撶Н绾?${analysisData.penumbra_volume?.toFixed(1) || '--'} ml锛岃緝鏍稿績姊楁鍖烘槑鏄炬墿澶э紝鎻愮ず瀛樺湪澶ч噺鍙尳鏁戣剳缁勭粐銆俙;
        const vesselText = '闇€鏍规嵁CTA搴忓垪杩涗竴姝ヨ瘎浼拌剳琛€绠￠€氱晠鎬э紝鍒ゆ柇鏄惁瀛樺湪澶ц绠￠棴濉烇紝涓鸿绠″唴娌荤枟鎻愪緵渚濇嵁銆?;
        const perfusionText = `鐏屾敞鍙傛暟鍒嗘瀽锛?
- CBF锛堣剳琛€娴侀噺锛夛細鏍稿績姊楁鍖烘樉钁楅檷浣庯紝鍗婃殫甯﹀尯鍩熺浉瀵逛繚鐣?
- CBV锛堣剳琛€瀹归噺锛夛細涓庢姝荤伓鍒嗗竷鐩哥锛屽懆鍥寸浉瀵瑰崌楂?
- Tmax锛堝钩鍧囬€氳繃鏃堕棿锛夛細寤惰繜鍖哄煙杩滃ぇ浜庢牳蹇冨尯锛屼笉鍖归厤姣斾緥 ${analysisData.mismatch_ratio?.toFixed(2) || '--'}
- 涓嶅尮閰嶈瘎浼帮細${analysisData.has_mismatch ? '瀛樺湪鏄捐憲鏍稿績-鍗婃殫甯︿笉鍖归厤锛屾彁绀哄彲鑳藉瓨鍦ㄥ彲鎸芥晳鑴戠粍缁囷紝闇€璇勪及琛€绠″唴娌荤枟閫傚簲璇? : '鏃犳樉钁椾笉鍖归厤'}`;
        setFindings({
            core: coreText,
            penumbra: penumbraText,
            vessel: vesselText,
            perfusion: perfusionText,
        });
    };
    
    const handlePatientUpdate = (field, value) => {
        setPatient((prev) => (prev ? { ...prev, [field]: value } : null));
    };
    
    const handleFindingsUpdate = (field, value) => {
        setFindings((prev) => ({ ...prev, [field]: value }));
    };
    
    const saveReport = async () => {
        if (!patientId || !fileId) {
            return;
        }
        setIsSaving(true);
        try {
            const res = await fetch('/api/save_report', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    patient_id: patientId,
                    file_id: fileId,
                    patient: patient,
                    findings: findings,
                    notes: notes,
                    saved_at: new Date().toISOString(),
                }),
            });
            const data = await res.json();
            if (data.status === 'success') {
                setIsEditing(false);
                alert('鎶ュ憡淇濆瓨鎴愬姛');
            } else {
                alert('淇濆瓨澶辫触锛? + data.message);
            }
        } catch (err) {
            alert('淇濆瓨澶辫触锛? + err.message);
        } finally {
            setIsSaving(false);
        }
    };
    
    const exportPDF = async () => {
        alert('PDF瀵煎嚭鍔熻兘寮€鍙戜腑...');
    };
    
    if (loading) {
        return React.createElement("div", { className: "report-container" },
            React.createElement("div", { className: "loading" }, "鍔犺浇涓?..")
        );
    }
    if (error) {
        return React.createElement("div", { className: "report-container" },
            React.createElement("div", { className: "error" }, "閿欒: ", error)
        );
    }
    
    return React.createElement("div", { className: "report-container" },
        React.createElement("div", { className: "report-header" },
            React.createElement("h2", { style: { 
                background: 'linear-gradient(135deg, #60a5fa 0%, #3b82f6 100%)', 
                color: 'white',
                padding: '16px 24px',
                borderRadius: '12px',
                margin: 0,
                fontSize: '20px',
                fontWeight: 600,
                boxShadow: '0 4px 12px rgba(59, 130, 246, 0.4)'
            } }, "鑴戝崚涓复搴婅瘖鏂姤鍛?),
            React.createElement("div", { className: "report-actions" },
                React.createElement("button", { className: `action-btn ${isEditing ? 'cancel' : 'primary'}`, onClick: () => setIsEditing(!isEditing) }, isEditing ? '鍙栨秷缂栬緫' : '缂栬緫鎶ュ憡'),
                isEditing && React.createElement("button", { className: "action-btn primary", onClick: saveReport, disabled: isSaving }, isSaving ? '淇濆瓨涓?..' : '淇濆瓨鎶ュ憡'),
                !isEditing && React.createElement("button", { className: "action-btn", onClick: exportPDF }, "瀵煎嚭PDF")
            )
        ),
        React.createElement("div", { className: "report-body" },
            React.createElement(PatientInfoModule, { data: patient, isEditing: isEditing, onUpdate: handlePatientUpdate }),
            React.createElement(ImageFindingsModule, { data: analysisData || null, findings: findings, isEditing: isEditing, onUpdate: handleFindingsUpdate }),
            
            // 鐧惧窛 AI 璇婃柇鎰忚妯″潡 - 鍥涚鐘舵€佹樉绀?
            !analysisData || analysisData.core_volume === 0 ?
                React.createElement("div", { className: "report-module", style: { background: '#1a1a1a', borderRadius: '12px', padding: '40px', marginTop: '20px', border: '1px solid #333', textAlign: 'center' } },
                    React.createElement("div", { style: { fontSize: '48px', marginBottom: '16px', color: '#60a5fa' } }, "鉁?),
                    React.createElement("h3", { style: { color: '#fff', fontSize: '18px', marginBottom: '12px' } }, "璇峰厛瀹屾垚鑴戝崚涓垎鏋?),
                    React.createElement("p", { style: { color: '#888', fontSize: '14px' } }, "璇疯繑鍥?viewer 椤甸潰瀹屾垚鍒嗘瀽鍚庯紝鍐嶇敓鎴?AI 鎶ュ憡")
                )
            : isGeneratingReport ?
                React.createElement("div", { className: "report-module", style: { background: 'linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)', padding: '40px', borderRadius: '12px', marginTop: '20px', textAlign: 'center' } },
                    React.createElement("div", { 
                        style: { 
                            width: '48px', 
                            height: '48px', 
                            border: '4px solid rgba(255,255,255,0.3)', 
                            borderTop: '4px solid white', 
                            borderRadius: '50%', 
                            animation: 'spin 1s linear infinite',
                            margin: '0 auto 16px'
                        } 
                    }),
                    React.createElement("h3", { style: { color: '#fff', fontSize: '18px', marginBottom: '8px' } }, "姝ｅ湪鐢熸垚 AI 鎶ュ憡..."),
                    React.createElement("p", { style: { color: 'rgba(255,255,255,0.8)', fontSize: '14px' } }, "NeuroMatrix AI 姝ｅ湪鍒嗘瀽褰卞儚鏁版嵁")
                )
            : aiReport ?
                React.createElement("div", { className: "report-module" },
                    React.createElement("div", { className: "module-header", style: { background: 'linear-gradient(135deg, #60a5fa 0%, #3b82f6 100%)' } }, "NeuroMatrix AI 璇婃柇鎰忚"),
                    React.createElement("div", {
                        className: "ai-report-content",
                        style: {
                            background: '#1a1a1a',
                            padding: '24px',
                            borderRadius: '12px',
                            lineHeight: '1.8',
                            marginTop: '20px',
                            border: '1px solid #333'
                        },
                        dangerouslySetInnerHTML: { __html: renderMarkdownToHtml(aiReport) }
                    })
                )
            :
                React.createElement("div", { className: "report-module", style: { background: '#1a1a1a', borderRadius: '12px', padding: '40px', marginTop: '20px', border: '1px solid #333', textAlign: 'center' } },
                    React.createElement("div", { style: { fontSize: '48px', marginBottom: '16px', color: '#60a5fa' } }, "鉁?),
                    React.createElement("h3", { style: { color: '#fff', fontSize: '18px', marginBottom: '12px' } }, "璇风敓鎴?AI 鎶ュ憡"),
                    React.createElement("p", { style: { color: '#888', fontSize: '14px' } }, "璇峰湪鑴戝崚涓垎鏋愰〉闈㈢偣鍑汇€屾墜鍔ㄧ敓鎴?AI 鎶ュ憡銆嶆寜閽?)
                ),
            
            // 鍖荤敓澶囨敞妯″潡
            React.createElement(DoctorNotesModule, { notes: notes, isEditing: isEditing, onUpdate: setNotes }),
            
            !isEditing && React.createElement("div", { className: "report-footer" },
                React.createElement("p", null, "鎶ュ憡鐢熸垚鏃堕棿锛?, new Date().toLocaleString('zh-CN')),
                React.createElement("p", null, "鍏嶈矗澹版槑锛氭鎶ュ憡涓殑AI鍒嗘瀽浠呬緵涓村簥鍙傝€冿紝鍖荤敓搴旂粨鍚堜复搴婃儏鍐电患鍚堝垽鏂€?)
            )
        )
    );
};

window.StructuredReport = StructuredReport;

