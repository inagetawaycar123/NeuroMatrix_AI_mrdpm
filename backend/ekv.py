from typing import Any, Dict, List, Optional


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _safe_int(value: Any) -> Optional[int]:
    try:
        if value is None:
            return None
        return int(value)
    except Exception:
        return None


def _normalize_verdict(verdict: str) -> str:
    token = str(verdict or "").strip().lower()
    if token in {"supported", "partially_supported", "not_supported", "unavailable"}:
        return token
    return "unavailable"


def _collect_modalities(planner_output: Optional[Dict[str, Any]]) -> List[str]:
    path_decision = (planner_output or {}).get("path_decision") or {}
    mods = path_decision.get("canonical_modalities") or []
    normalized = []
    for item in mods:
        key = str(item or "").strip().lower()
        if key and key not in normalized:
            normalized.append(key)
    return normalized


def _extract_analysis_metrics(analysis_result: Optional[Dict[str, Any]]) -> Dict[str, Optional[float]]:
    data = analysis_result if isinstance(analysis_result, dict) else {}
    core = _safe_float(data.get("core_infarct_volume") or data.get("core_volume_ml"))
    penumbra = _safe_float(data.get("penumbra_volume") or data.get("penumbra_volume_ml"))
    mismatch = _safe_float(data.get("mismatch_ratio"))

    report = data.get("report")
    if not isinstance(report, dict):
        report = {}
    summary = report.get("summary")
    if not isinstance(summary, dict):
        summary = {}

    if core is None:
        core = _safe_float(summary.get("core_volume_ml") or summary.get("core_infarct_volume"))
    if penumbra is None:
        penumbra = _safe_float(summary.get("penumbra_volume_ml") or summary.get("penumbra_volume"))
    if mismatch is None:
        mismatch = _safe_float(summary.get("mismatch_ratio"))

    return {
        "core_infarct_volume": core,
        "penumbra_volume": penumbra,
        "mismatch_ratio": mismatch,
    }


def _extract_report_metrics(report_payload: Optional[Dict[str, Any]]) -> Dict[str, Optional[float]]:
    payload = report_payload if isinstance(report_payload, dict) else {}
    ctp = payload.get("ctp")
    if not isinstance(ctp, dict):
        ctp = {}
    return {
        "core_infarct_volume": _safe_float(
            payload.get("core_infarct_volume") or payload.get("core_volume_ml") or ctp.get("core_infarct_volume")
        ),
        "penumbra_volume": _safe_float(
            payload.get("penumbra_volume") or payload.get("penumbra_volume_ml") or ctp.get("penumbra_volume")
        ),
        "mismatch_ratio": _safe_float(payload.get("mismatch_ratio") or ctp.get("mismatch_ratio")),
    }


def _verdict_from_pair(analysis_value: Optional[float], report_value: Optional[float], tolerance: float = 0.1) -> str:
    if analysis_value is None and report_value is None:
        return "unavailable"
    if analysis_value is None or report_value is None:
        return "partially_supported"

    base = abs(analysis_value) if abs(analysis_value) > 1e-6 else 1.0
    rel_err = abs(report_value - analysis_value) / base
    if rel_err <= tolerance:
        return "supported"
    if rel_err <= 0.35:
        return "partially_supported"
    return "not_supported"


def _claim(
    claim_id: str,
    claim_text: str,
    verdict: str,
    message: str,
    evidence_refs: Optional[List[str]] = None,
    confidence: Optional[float] = None,
) -> Dict[str, Any]:
    v = _normalize_verdict(verdict)
    return {
        "claim_id": claim_id,
        "claim_text": claim_text,
        "verdict": v,
        "evidence_refs": evidence_refs or [],
        "message": message,
        "confidence": float(confidence if confidence is not None else _confidence_from_verdict(v)),
    }


def _confidence_from_verdict(verdict: str) -> float:
    if verdict == "supported":
        return 0.9
    if verdict == "partially_supported":
        return 0.6
    if verdict == "not_supported":
        return 0.2
    return 0.0


def _score_from_claims(claims: List[Dict[str, Any]]) -> float:
    weights = {
        "supported": 1.0,
        "partially_supported": 0.6,
        "not_supported": 0.0,
        "unavailable": 0.0,
    }
    if not claims:
        return 0.0
    total = 0.0
    for item in claims:
        verdict = str(item.get("verdict") or "")
        total += weights.get(verdict, 0.0)
    return round(total / float(len(claims)), 4)


def _confidence_delta_from_claims(claims: List[Dict[str, Any]]) -> float:
    not_supported_count = sum(1 for c in claims if c.get("verdict") == "not_supported")
    partial_count = sum(1 for c in claims if c.get("verdict") == "partially_supported")
    unavailable_count = sum(1 for c in claims if c.get("verdict") == "unavailable")
    delta = -(not_supported_count * 0.25 + partial_count * 0.08 + unavailable_count * 0.05)
    if delta < -1.0:
        delta = -1.0
    return round(delta, 4)


def evaluate_ekv(
    planner_output: Optional[Dict[str, Any]] = None,
    tool_results: Optional[List[Dict[str, Any]]] = None,
    patient_context: Optional[Dict[str, Any]] = None,
    analysis_result: Optional[Dict[str, Any]] = None,
    report_result: Optional[Dict[str, Any]] = None,
    kb_citations: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Evaluate external-knowledge consistency for key claims.

    The function uses deterministic rule checks so it can run without external services.
    """
    del tool_results  # reserved for future use

    modalities = _collect_modalities(planner_output)
    has_ctp = any(x in {"cbf", "cbv", "tmax", "ctp"} for x in modalities)

    analysis_metrics = _extract_analysis_metrics(analysis_result)
    report_payload = (report_result or {}).get("report_payload") if isinstance(report_result, dict) else {}
    if not isinstance(report_payload, dict):
        report_payload = {}
    report_metrics = _extract_report_metrics(report_payload)

    patient_struct = patient_context if isinstance(patient_context, dict) else {}
    hemisphere_registry = str(patient_struct.get("hemisphere") or "").strip().lower()
    hemisphere_report = str(
        report_payload.get("hemisphere")
        or report_payload.get("affected_side")
        or analysis_result.get("hemisphere") if isinstance(analysis_result, dict) else ""
    ).strip().lower()

    claims: List[Dict[str, Any]] = []

    # C1 hemisphere
    if hemisphere_registry and hemisphere_report:
        if hemisphere_registry == hemisphere_report:
            verdict = "supported"
            message = "病变侧别与结构化结果一致"
        elif "both" in {hemisphere_registry, hemisphere_report}:
            verdict = "partially_supported"
            message = "病变侧别存在保守合并表述（both）"
        else:
            verdict = "not_supported"
            message = "病变侧别在注册信息与报告结构化字段之间不一致"
    elif hemisphere_registry or hemisphere_report:
        verdict = "partially_supported"
        message = "病变侧别信息仅在单一来源可用"
    else:
        verdict = "unavailable"
        message = "病变侧别信息不可用"
    claims.append(_claim("hemisphere", "病变侧别", verdict, message, ["rule:hemisphere_consistency"]))

    # C2-C4 quantitative claims
    core_verdict = _verdict_from_pair(
        analysis_metrics.get("core_infarct_volume"), report_metrics.get("core_infarct_volume"), tolerance=0.1
    )
    claims.append(
        _claim(
            "core_volume_ml",
            "核心体积（ml）",
            core_verdict,
            "核心体积与结构化结果的一致性校验",
            ["rule:core_volume_consistency"],
        )
    )

    penumbra_verdict = _verdict_from_pair(
        analysis_metrics.get("penumbra_volume"), report_metrics.get("penumbra_volume"), tolerance=0.1
    )
    claims.append(
        _claim(
            "penumbra_volume_ml",
            "半暗带体积（ml）",
            penumbra_verdict,
            "半暗带体积与结构化结果的一致性校验",
            ["rule:penumbra_volume_consistency"],
        )
    )

    mismatch_verdict = _verdict_from_pair(
        analysis_metrics.get("mismatch_ratio"), report_metrics.get("mismatch_ratio"), tolerance=0.12
    )
    claims.append(
        _claim(
            "mismatch_ratio",
            "不匹配比值",
            mismatch_verdict,
            "不匹配比值与结构化结果的一致性校验",
            ["rule:mismatch_consistency"],
        )
    )

    # C5 significant mismatch present
    mismatch = analysis_metrics.get("mismatch_ratio")
    if mismatch is None:
        verdict = "unavailable"
        message = "缺少不匹配比值，无法判断是否显著不匹配"
    else:
        if mismatch >= 1.8:
            verdict = "supported"
            message = "存在显著灌注不匹配"
        elif mismatch >= 1.2:
            verdict = "partially_supported"
            message = "存在边界不匹配，需结合临床复核"
        else:
            verdict = "not_supported"
            message = "未见显著灌注不匹配"
    if not has_ctp:
        verdict = "unavailable"
        message = "当前模态缺少 CTP，显著不匹配结论不可判定"
    claims.append(
        _claim(
            "significant_mismatch_present",
            "是否存在显著不匹配",
            verdict,
            message,
            ["rule:significant_mismatch"],
        )
    )

    # C6 treatment window hint
    onset_hours = _safe_float(patient_struct.get("onset_to_admission_hours"))
    nihss = _safe_int(patient_struct.get("admission_nihss"))
    if onset_hours is None:
        verdict = "unavailable"
        message = "缺少发病到入院时长，无法做时窗提示校验"
    elif onset_hours <= 6:
        verdict = "supported"
        message = "时间窗处于早期，再灌注提示与常见指南一致"
    elif onset_hours <= 24 and (nihss is None or nihss >= 6):
        verdict = "partially_supported"
        message = "时间窗延长，需结合梗死核心与症状严重度综合判定"
    else:
        verdict = "partially_supported"
        message = "时间窗偏长，建议强化人工复核"
    claims.append(
        _claim(
            "treatment_window_hint",
            "治疗时窗相关提示",
            verdict,
            message,
            ["rule:treatment_window_hint"],
        )
    )

    findings: List[Dict[str, Any]] = []
    for item in claims:
        verdict = item.get("verdict")
        if verdict == "supported":
            continue
        severity = "medium"
        if verdict == "not_supported":
            severity = "high"
        elif verdict == "unavailable":
            severity = "info"
        findings.append(
            {
                "id": f"EKV_{item.get('claim_id')}",
                "status": verdict,
                "severity": severity,
                "message": item.get("message", ""),
                "suggested_action": "Review this claim against source imaging and guideline evidence.",
            }
        )

    unavailable_count = sum(1 for c in claims if c.get("verdict") == "unavailable")
    status = "available"
    if unavailable_count == len(claims):
        status = "unavailable"

    citations = list(kb_citations or [])
    if not citations:
        citations = [
            "guideline:defuse3-mismatch",
            "guideline:acute-ischemic-stroke-imaging",
        ]

    ekv_payload = {
        "status": status,
        "finding_count": len(findings),
        "score": _score_from_claims(claims),
        "confidence_delta": _confidence_delta_from_claims(claims),
        "claims": claims,
        "findings": findings,
        "citations": citations,
    }

    return {"success": True, "ekv": ekv_payload}
