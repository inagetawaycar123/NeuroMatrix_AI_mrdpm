document.addEventListener('DOMContentLoaded', function() {
    const onset = document.getElementById('onset_exact_time');
    const admission = document.getElementById('admission_time');
    const diff = document.getElementById('surgery_time');

    [onset, admission].forEach(el => el.addEventListener('change', () => {
        if (onset.value && admission.value) {
            const d1 = new Date(onset.value);
            const d2 = new Date(admission.value);
            const ms = d2 - d1;
            const h = Math.floor(ms / 3600000);
            const m = Math.floor((ms % 3600000) / 60000);
            diff.value = `${h}小时 ${m}分钟`;
        }
    }));
});

async function submitPatientBasicInfo() {
    const form = document.getElementById('patientForm');
    if (!form.checkValidity()) {
        showMsg('请填写完整必填项', 'error');
        return;
    }

    showLoading(true, '正在提交患者信息...');

    try {
        const data = {
            patient_name: document.getElementById('patient_name').value.trim(),
            patient_age: parseInt(document.getElementById('patient_age').value),
            patient_sex: document.getElementById('patient_sex').value,
            onset_exact_time: new Date(document.getElementById('onset_exact_time').value).toISOString(),
            admission_time: new Date(document.getElementById('admission_time').value).toISOString(),
            surgery_time: document.getElementById('surgery_time').value,
            admission_nihss: parseInt(document.getElementById('admission_nihss').value),
            create_time: new Date().toISOString()
        };

        const res = await $.ajax({
            url: '/api/insert_patient',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(data)
        });

        setCurrentPatientId(res.data.id);
        showMsg(`提交成功！患者ID: ${res.data.id}`, 'success');
        window.location.href = '/upload?patient_id=' + res.data.id;
    } catch (err) {
        showMsg(err.message || '服务器连接失败', 'error');
    } finally {
        showLoading(false);
    }
}

function resetForm() {
    const form = document.getElementById('patientForm');
    if (form) form.reset();
}
