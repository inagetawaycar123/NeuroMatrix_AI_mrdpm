const { useState, useEffect } = React;
const PatientInfoModule = ({ data, isEditing, onUpdate }) => {
    if (!data)
        return React.createElement("div", { className: "module-empty" }, "\u52A0\u8F7D\u60A3\u8005\u4FE1\u606F\u4E2D...");
    const formatDateTime = (dateStr) => {
        if (!dateStr)
            return '--';
        return new Date(dateStr).toLocaleString('zh-CN');
    };
    return (React.createElement("div", { className: "report-module" },
        React.createElement("div", { className: "module-header" }, "\uD83D\uDCCB \u60A3\u8005\u57FA\u672C\u4FE1\u606F"),
        React.createElement("div", { className: "module-content" },
            React.createElement("div", { className: "report-field" },
                React.createElement("span", { className: "field-label" }, "\u59D3\u540D"),
                isEditing ? (React.createElement("input", { type: "text", className: "field-edit", value: data.patient_name, onChange: (e) => onUpdate('patient_name', e.target.value) })) : (React.createElement("span", { className: "field-value" }, data.patient_name || '--'))),
            React.createElement("div", { className: "report-field" },
                React.createElement("span", { className: "field-label" }, "\u5E74\u9F84"),
                isEditing ? (React.createElement("input", { type: "number", className: "field-edit", value: data.patient_age, onChange: (e) => onUpdate('patient_age', parseInt(e.target.value)) })) : (React.createElement("span", { className: "field-value" },
                    data.patient_age,
                    "\u5C81"))),
            React.createElement("div", { className: "report-field" },
                React.createElement("span", { className: "field-label" }, "\u6027\u522B"),
                isEditing ? (React.createElement("input", { type: "text", className: "field-edit", value: data.patient_sex, onChange: (e) => onUpdate('patient_sex', e.target.value) })) : (React.createElement("span", { className: "field-value" }, data.patient_sex || '--'))),
            React.createElement("div", { className: "report-field" },
                React.createElement("span", { className: "field-label" }, "\u53D1\u75C5\u65F6\u95F4"),
                isEditing ? (React.createElement("input", { type: "datetime-local", className: "field-edit", defaultValue: data.onset_exact_time?.slice(0, 16), onChange: (e) => onUpdate('onset_exact_time', e.target.value) })) : (React.createElement("span", { className: "field-value" }, formatDateTime(data.onset_exact_time)))),
            React.createElement("div", { className: "report-field" },
                React.createElement("span", { className: "field-label" }, "\u5165\u9662\u65F6\u95F4"),
                isEditing ? (React.createElement("input", { type: "datetime-local", className: "field-edit", defaultValue: data.admission_time?.slice(0, 16), onChange: (e) => onUpdate('admission_time', e.target.value) })) : (React.createElement("span", { className: "field-value" }, formatDateTime(data.admission_time)))),
            React.createElement("div", { className: "report-field" },
                React.createElement("span", { className: "field-label" }, "\u5165\u9662NIHSS\u8BC4\u5206"),
                isEditing ? (React.createElement("input", { type: "number", className: "field-edit", min: "0", max: "42", value: data.admission_nihss, onChange: (e) => onUpdate('admission_nihss', parseInt(e.target.value)) })) : (React.createElement("span", { className: "field-value" },
                    data.admission_nihss,
                    " \u5206"))),
            React.createElement("div", { className: "report-field" },
                React.createElement("span", { className: "field-label" }, "\u53D1\u75C5\u81F3\u5165\u9662"),
                isEditing ? (React.createElement("input", { type: "text", className: "field-edit", defaultValue: data.surgery_time, onChange: (e) => onUpdate('surgery_time', e.target.value) })) : (React.createElement("span", { className: "field-value" }, data.surgery_time || '--'))))));
};
const ImageFindingsModule = ({ data, findings, isEditing, onUpdate, }) => {
    if (!data)
        return React.createElement("div", { className: "module-empty" }, "\u52A0\u8F7D\u5F71\u50CF\u5206\u6790\u6570\u636E\u4E2D...");
    return (React.createElement("div", { className: "report-module" },
        React.createElement("div", { className: "module-header" }, "\uD83D\uDD2C \u5F71\u50CF\u53D1\u73B0"),
        React.createElement("div", { className: "module-content" },
            React.createElement("div", { className: "report-field full-width" },
                React.createElement("span", { className: "field-label" }, "\u6838\u5FC3\u6897\u6B7B\u533A"),
                isEditing ? (React.createElement("textarea", { className: "field-edit-area", rows: 2, value: findings.core, onChange: (e) => onUpdate('core', e.target.value) })) : (React.createElement("div", { className: "field-value" }, findings.core || '--'))),
            React.createElement("div", { className: "report-field full-width" },
                React.createElement("span", { className: "field-label" }, "\u534A\u6697\u5E26\u533A\u57DF"),
                isEditing ? (React.createElement("textarea", { className: "field-edit-area", rows: 2, value: findings.penumbra, onChange: (e) => onUpdate('penumbra', e.target.value) })) : (React.createElement("div", { className: "field-value" }, findings.penumbra || '--'))),
            React.createElement("div", { className: "report-field full-width" },
                React.createElement("span", { className: "field-label" }, "\u8840\u7BA1\u8BC4\u4F30"),
                isEditing ? (React.createElement("textarea", { className: "field-edit-area", rows: 2, value: findings.vessel, onChange: (e) => onUpdate('vessel', e.target.value) })) : (React.createElement("div", { className: "field-value" }, findings.vessel || '--'))),
            React.createElement("div", { className: "report-field full-width" },
                React.createElement("span", { className: "field-label" }, "\u704C\u6CE8\u5206\u6790"),
                isEditing ? (React.createElement("textarea", { className: "field-edit-area", rows: 3, value: findings.perfusion, onChange: (e) => onUpdate('perfusion', e.target.value) })) : (React.createElement("div", { className: "field-value", style: { whiteSpace: 'pre-wrap' } }, findings.perfusion || '--'))),
            React.createElement("div", { className: "analysis-summary" },
                React.createElement("h4", null, "AI\u5206\u6790\u6307\u6807"),
                React.createElement("div", { className: "metric" },
                    React.createElement("span", null, "\u6838\u5FC3\u6897\u6B7B\u4F53\u79EF\uFF1A"),
                    React.createElement("strong", null,
                        data.core_volume?.toFixed(1) || '--',
                        " ml")),
                React.createElement("div", { className: "metric" },
                    React.createElement("span", null, "\u534A\u6697\u5E26\u4F53\u79EF\uFF1A"),
                    React.createElement("strong", null,
                        data.penumbra_volume?.toFixed(1) || '--',
                        " ml")),
                React.createElement("div", { className: "metric" },
                    React.createElement("span", null, "\u4E0D\u5339\u914D\u6BD4\u4F8B\uFF1A"),
                    React.createElement("strong", null, data.mismatch_ratio?.toFixed(2) || '--')),
                React.createElement("div", { className: "metric" },
                    React.createElement("span", null, "\u4E0D\u5339\u914D\u72B6\u6001\uFF1A"),
                    React.createElement("strong", { style: { color: data.has_mismatch ? '#ff6b6b' : '#51cf66' } }, data.has_mismatch ? '存在显著不匹配' : '无显著不匹配'))))));
};
const DoctorNotesModule = ({ notes, isEditing, onUpdate }) => {
    return (React.createElement("div", { className: "report-module" },
        React.createElement("div", { className: "module-header" }, "\uD83D\uDCAC \u533B\u751F\u5907\u6CE8"),
        React.createElement("div", { className: "module-content" }, isEditing ? (React.createElement("textarea", { className: "field-edit-area", rows: 4, value: notes, onChange: (e) => onUpdate(e.target.value), placeholder: "\u8BF7\u8F93\u5165\u4E34\u5E8A\u5907\u6CE8\u3001\u8BCA\u65AD\u610F\u89C1\u3001\u540E\u7EED\u5EFA\u8BAE..." })) : (React.createElement("div", { className: "field-value", style: { whiteSpace: 'pre-wrap', minHeight: '60px' } }, notes || '暂无备注')))));
};
const StructuredReport = ({ patientId, fileId, analysisData, }) => {
    const [isEditing, setIsEditing] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const [patient, setPatient] = useState(null);
    const [findings, setFindings] = useState({
        core: '',
        penumbra: '',
        vessel: '',
        perfusion: '',
    });
    const [notes, setNotes] = useState('');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    // 初始化：加载患者信息和自动生成影像描述
    useEffect(() => {
        if (!patientId) {
            setError('缺少患者ID');
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
            }
            else {
                setError(data.message || '加载患者信息失败');
            }
        }
        catch (err) {
            setError('网络错误：' + err.message);
        }
        finally {
            setLoading(false);
        }
    };
    const generateImageFindings = (patientData) => {
        if (!analysisData)
            return;
        const hemName = {
            left: '左侧',
            right: '右侧',
            both: '双侧',
        }[analysisData.hemisphere] || '双侧';
        const coreText = `核心梗死区位于${hemName}大脑半球，体积约 ${analysisData.core_volume?.toFixed(1) || '--'} ml。病灶界限清晰，灌注信号明显降低。`;
        const penumbraText = `半暗带（缺血半影）范围广泛，体积约 ${analysisData.penumbra_volume?.toFixed(1) || '--'} ml，较核心梗死区明显扩大，提示存在大量可挽救脑组织。`;
        const vesselText = '需根据CTA序列进一步评估脑血管通畅性，判断是否存在大血管闭塞，为血管内治疗提供依据。';
        const perfusionText = `灌注参数分析：
- CBF（脑血流量）：核心梗死区显著降低，半暗带区域相对保留
- CBV（脑血容量）：与梗死灶分布相符，周围相对升高
- Tmax（平均通过时间）：延迟区域远大于核心区，不匹配比例 ${analysisData.mismatch_ratio?.toFixed(2) || '--'}
- 不匹配评估：${analysisData.has_mismatch ? '存在显著核心-半暗带不匹配，提示可能存在可挽救脑组织，需评估血管内治疗适应证' : '无显著不匹配'}`;
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
    const handleNotesUpdate = (value) => {
        setNotes(value);
    };
    const saveReport = async () => {
        if (!patientId || !fileId)
            return;
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
                alert('报告保存成功');
            }
            else {
                alert('保存失败：' + data.message);
            }
        }
        catch (err) {
            alert('保存失败：' + err.message);
        }
        finally {
            setIsSaving(false);
        }
    };
    const exportPDF = async () => {
        alert('PDF导出功能开发中...');
    };
    if (loading)
        return React.createElement("div", { className: "report-container" },
            React.createElement("div", { className: "loading" }, "\u52A0\u8F7D\u4E2D..."));
    if (error)
        return React.createElement("div", { className: "report-container" },
            React.createElement("div", { className: "error" },
                "\u274C ",
                error));
    return (React.createElement("div", { className: "report-container" },
        React.createElement("div", { className: "report-header" },
            React.createElement("h2", null, "\u8111\u5352\u4E2D\u4E34\u5E8A\u8BCA\u65AD\u62A5\u544A"),
            React.createElement("div", { className: "report-actions" },
                React.createElement("button", { className: `action-btn ${isEditing ? 'cancel' : 'primary'}`, onClick: () => setIsEditing(!isEditing) }, isEditing ? '取消编辑' : '编辑报告'),
                isEditing && (React.createElement(React.Fragment, null,
                    React.createElement("button", { className: "action-btn primary", onClick: saveReport, disabled: isSaving }, isSaving ? '保存中...' : '保存报告'))),
                !isEditing && (React.createElement(React.Fragment, null,
                    React.createElement("button", { className: "action-btn", onClick: exportPDF }, "\uD83D\uDCC4 \u5BFC\u51FAPDF"))))),
        React.createElement("div", { className: "report-body" },
            React.createElement(PatientInfoModule, { data: patient, isEditing: isEditing, onUpdate: handlePatientUpdate }),
            React.createElement(ImageFindingsModule, { data: analysisData || null, findings: findings, isEditing: isEditing, onUpdate: handleFindingsUpdate }),
            React.createElement(DoctorNotesModule, { notes: notes, isEditing: isEditing, onUpdate: handleNotesUpdate }),
            !isEditing && (React.createElement("div", { className: "report-footer" },
                React.createElement("p", null,
                    "\u62A5\u544A\u751F\u6210\u65F6\u95F4\uFF1A",
                    new Date().toLocaleString('zh-CN')),
                React.createElement("p", null, "\u514D\u8D23\u58F0\u660E\uFF1A\u6B64\u62A5\u544A\u4E2D\u7684AI\u5206\u6790\u4EC5\u4F9B\u4E34\u5E8A\u53C2\u8003\uFF0C\u533B\u751F\u5E94\u7ED3\u5408\u4E34\u5E8A\u60C5\u51B5\u7EFC\u5408\u5224\u65AD\u3002"))))));
};

// 导出到全局命名空间供 HTML 调用
window.StructuredReport = StructuredReport;
