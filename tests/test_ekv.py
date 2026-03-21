from backend.ekv import evaluate_ekv


def _base_inputs():
    planner_output = {
        "path_decision": {
            "canonical_modalities": ["ncct", "mcta", "cbf", "cbv", "tmax"],
            "imaging_path": "ncct_mcta_ctp",
        }
    }
    patient_context = {
        "hemisphere": "left",
        "onset_to_admission_hours": 3.5,
        "admission_nihss": 10,
    }
    analysis_result = {
        "hemisphere": "left",
        "core_infarct_volume": 15.0,
        "penumbra_volume": 45.0,
        "mismatch_ratio": 3.0,
    }
    report_result = {
        "report_payload": {
            "hemisphere": "left",
            "core_infarct_volume": 15.5,
            "penumbra_volume": 44.8,
            "mismatch_ratio": 3.02,
        }
    }
    return planner_output, patient_context, analysis_result, report_result


def test_ekv_available_with_supported_claims():
    planner_output, patient_context, analysis_result, report_result = _base_inputs()
    out = evaluate_ekv(
        planner_output=planner_output,
        tool_results=[],
        patient_context=patient_context,
        analysis_result=analysis_result,
        report_result=report_result,
    )
    assert out["success"] is True
    ekv = out["ekv"]
    assert ekv["status"] == "available"
    assert isinstance(ekv["claims"], list)
    assert len(ekv["claims"]) == 6
    assert ekv["score"] > 0.6


def test_ekv_ctp_claim_unavailable_for_ncct_only():
    planner_output, patient_context, analysis_result, report_result = _base_inputs()
    planner_output["path_decision"]["canonical_modalities"] = ["ncct"]

    out = evaluate_ekv(
        planner_output=planner_output,
        tool_results=[],
        patient_context=patient_context,
        analysis_result=analysis_result,
        report_result=report_result,
    )
    claims = out["ekv"]["claims"]
    mismatch_claim = next(c for c in claims if c["claim_id"] == "significant_mismatch_present")
    assert mismatch_claim["verdict"] == "unavailable"


def test_ekv_detects_not_supported_when_metrics_conflict():
    planner_output, patient_context, analysis_result, report_result = _base_inputs()
    report_result["report_payload"]["core_infarct_volume"] = 40.0
    report_result["report_payload"]["mismatch_ratio"] = 1.0

    out = evaluate_ekv(
        planner_output=planner_output,
        tool_results=[],
        patient_context=patient_context,
        analysis_result=analysis_result,
        report_result=report_result,
    )
    claims = out["ekv"]["claims"]
    not_supported = [c for c in claims if c["verdict"] == "not_supported"]
    assert len(not_supported) >= 1
    assert out["ekv"]["finding_count"] >= 1
