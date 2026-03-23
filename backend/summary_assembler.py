import datetime as _dt
import math
import uuid
from typing import Any, Dict, List, Optional, Tuple


KEY_CLAIM_IDS: List[str] = [
    "hemisphere",
    "core_infarct_volume",
    "penumbra_volume",
    "mismatch_ratio",
    "significant_mismatch",
    "treatment_window_notice",
]

HIGH_RISK_CLAIM_IDS = {
    "core_infarct_volume",
    "penumbra_volume",
    "mismatch_ratio",
    "significant_mismatch",
}

CLAIM_TITLES = {
    "hemisphere": "Lesion laterality",
    "core_infarct_volume": "Core infarct volume",
    "penumbra_volume": "Penumbra volume",
    "mismatch_ratio": "Mismatch ratio",
    "significant_mismatch": "Significant mismatch",
    "treatment_window_notice": "Treatment window notice",
}


def _now_iso() -> str:
    return _dt.datetime.utcnow().isoformat() + "Z"


def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        v = float(value)
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    except Exception:
        return None


def _normalize_verdict(value: Any) -> str:
    token = str(value or "").strip().lower()
    if token in {"supported", "partially_supported", "not_supported", "unavailable"}:
        return token
    return "unavailable"


def _risk_level_from_findings(
    key_findings: List[Dict[str, Any]],
    consensus: Dict[str, Any],
) -> str:
    decision = str(consensus.get("decision") or "").strip().lower()
    if decision == "escalate":
        return "high"
    has_not_supported = any(
        str(item.get("verdict") or "").lower() == "not_supported" for item in key_findings
    )
    if has_not_supported:
        return "high"
    has_warn = any(
        str(item.get("verdict") or "").lower() in {"partially_supported", "unavailable"}
        for item in key_findings
    )
    if has_warn:
        return "medium"
    return "low"


def _collect_uncertainties(
    key_findings: List[Dict[str, Any]],
    icv: Dict[str, Any],
    ekv: Dict[str, Any],
    consensus: Dict[str, Any],
) -> List[str]:
    out: List[str] = []
    for item in key_findings:
        verdict = str(item.get("verdict") or "").lower()
        if verdict in {"not_supported", "unavailable"}:
            text = str(item.get("message") or "").strip()
            reason = str(item.get("unavailable_reason") or "").strip()
            claim_id = str(item.get("claim_id") or "unknown")
            if reason:
                out.append(f"{claim_id}: {reason}")
            elif text:
                out.append(f"{claim_id}: {text}")
            else:
                out.append(f"{claim_id}: unresolved")

    for payload, name in (
        (icv, "ICV"),
        (ekv, "EKV"),
        (consensus, "Consensus"),
    ):
        status = str(payload.get("status") or "").lower()
        if status in {"failed", "unavailable", "fail"}:
            err = str(payload.get("error_message") or "").strip()
            if err:
                out.append(f"{name} unavailable: {err}")

    # Deduplicate while preserving order.
    seen = set()
    deduped: List[str] = []
    for item in out:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


def _collect_next_actions(
    key_findings: List[Dict[str, Any]],
    consensus: Dict[str, Any],
) -> List[str]:
    actions: List[str] = []
    for item in _as_list(consensus.get("next_actions")):
        text = str(item or "").strip()
        if text:
            actions.append(text)

    for finding in key_findings:
        verdict = str(finding.get("verdict") or "").lower()
        if verdict in {"not_supported", "unavailable"}:
            suggested = str(finding.get("suggested_action") or "").strip()
            if suggested:
                actions.append(suggested)

    seen = set()
    deduped: List[str] = []
    for item in actions:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


def _normalize_evidence_item(
    raw_item: Dict[str, Any],
    *,
    run_id: str,
    file_id: str,
    claim_lookup: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    claim_id = str(raw_item.get("claim_id") or "").strip()
    claim_data = claim_lookup.get(claim_id, {})
    evidence_id = str(raw_item.get("evidence_id") or "").strip() or str(uuid.uuid4())

    source_ref = str(raw_item.get("source_ref") or "").strip()
    doc_name = str(raw_item.get("doc_name") or "").strip()
    page = raw_item.get("page")
    snippet = str(raw_item.get("snippet") or "").strip()
    support_level = str(raw_item.get("support_level") or "").strip() or str(
        claim_data.get("verdict") or "unavailable"
    )
    claim_text = str(raw_item.get("claim") or "").strip() or str(
        claim_data.get("claim_text") or ""
    )
    if not claim_text and claim_id:
        claim_text = CLAIM_TITLES.get(claim_id, claim_id)

    return {
        "evidence_id": evidence_id,
        "source_type": str(raw_item.get("source_type") or "guideline"),
        "source_ref": source_ref,
        "claim": claim_text,
        "claim_id": claim_id,
        "support_level": support_level,
        "timestamp": str(raw_item.get("timestamp") or _now_iso()),
        "snippet": snippet,
        "doc_name": doc_name,
        "page": page,
        "run_id": run_id,
        "file_id": file_id,
    }


def _build_evidence_items(
    ekv: Dict[str, Any],
    *,
    run_id: str,
    file_id: str,
) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]], Dict[str, List[str]]]:
    claims = _as_list(ekv.get("claims"))
    claim_lookup: Dict[str, Dict[str, Any]] = {}
    for item in claims:
        if not isinstance(item, dict):
            continue
        cid = str(item.get("claim_id") or "").strip()
        if cid:
            claim_lookup[cid] = item

    citations = _as_list(ekv.get("citations"))
    evidence_items: List[Dict[str, Any]] = []
    evidence_lookup: Dict[str, Dict[str, Any]] = {}
    claim_to_evidence_ids: Dict[str, List[str]] = {}

    for item in citations:
        if not isinstance(item, dict):
            continue
        normalized = _normalize_evidence_item(
            item,
            run_id=run_id,
            file_id=file_id,
            claim_lookup=claim_lookup,
        )
        evidence_items.append(normalized)
        evidence_lookup[normalized["evidence_id"]] = normalized
        cid = normalized.get("claim_id")
        if cid:
            claim_to_evidence_ids.setdefault(cid, []).append(normalized["evidence_id"])

    return evidence_items, evidence_lookup, claim_to_evidence_ids


def _resolve_claim_finding(
    claim_id: str,
    claim_data: Optional[Dict[str, Any]],
    claim_to_evidence_ids: Dict[str, List[str]],
) -> Dict[str, Any]:
    title = CLAIM_TITLES.get(claim_id, claim_id)
    if not isinstance(claim_data, dict):
        return {
            "finding_id": claim_id,
            "claim_id": claim_id,
            "title": title,
            "claim_text": title,
            "verdict": "unavailable",
            "message": "Claim is missing from EKV output.",
            "evidence_ids": [],
            "unavailable_reason": "Claim not produced by EKV.",
            "severity": "medium",
            "suggested_action": "Review source outputs and regenerate EKV claims.",
        }

    verdict = _normalize_verdict(claim_data.get("verdict"))
    message = str(claim_data.get("message") or "").strip()
    evidence_ids = [
        str(x).strip()
        for x in _as_list(claim_data.get("evidence_refs"))
        if str(x).strip()
    ]
    if not evidence_ids:
        evidence_ids = list(claim_to_evidence_ids.get(claim_id, []))

    unavailable_reason = ""
    if not evidence_ids:
        unavailable_reason = (
            message
            or "No evidence reference is mapped for this claim."
            if verdict == "unavailable"
            else "No evidence reference is mapped for this claim."
        )
    elif verdict == "unavailable":
        unavailable_reason = message or "Claim marked unavailable by EKV."

    return {
        "finding_id": claim_id,
        "claim_id": claim_id,
        "title": title,
        "claim_text": str(claim_data.get("claim_text") or title),
        "verdict": verdict,
        "message": message,
        "evidence_ids": evidence_ids,
        "unavailable_reason": unavailable_reason or None,
        "severity": str(claim_data.get("severity") or ""),
        "suggested_action": str(claim_data.get("suggested_action") or ""),
    }


def _resolve_icv_high_risk_findings(
    icv: Dict[str, Any],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    findings = _as_list(icv.get("findings"))
    for item in findings:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or "").lower()
        severity = str(item.get("severity") or "").lower()
        if status not in {"warn", "fail"} and severity not in {"high"}:
            continue
        fid = str(item.get("id") or "").strip()
        if not fid:
            continue
        out.append(
            {
                "finding_id": f"icv::{fid}",
                "claim_id": f"icv::{fid}",
                "title": f"ICV {fid}",
                "claim_text": f"ICV finding {fid}",
                "verdict": "unavailable",
                "message": str(item.get("message") or ""),
                "evidence_ids": [],
                "unavailable_reason": str(item.get("suggested_action") or "")
                or str(item.get("message") or "")
                or "ICV finding has no direct external citation.",
                "severity": severity or ("high" if status == "fail" else "medium"),
                "suggested_action": str(item.get("suggested_action") or ""),
            }
        )
    return out


def _build_traceability(
    key_findings: List[Dict[str, Any]],
) -> Dict[str, Any]:
    total = len(key_findings)
    mapped = sum(
        1
        for item in key_findings
        if isinstance(item.get("evidence_ids"), list) and len(item.get("evidence_ids")) > 0
    )
    unmapped_ids = [
        str(item.get("finding_id"))
        for item in key_findings
        if not (isinstance(item.get("evidence_ids"), list) and len(item.get("evidence_ids")) > 0)
    ]
    coverage = round((mapped / total), 4) if total > 0 else 1.0

    high_risk_unmapped = 0
    for item in key_findings:
        claim_id = str(item.get("claim_id") or "")
        if claim_id not in HIGH_RISK_CLAIM_IDS:
            continue
        evidence_ids = item.get("evidence_ids")
        if not isinstance(evidence_ids, list) or not evidence_ids:
            high_risk_unmapped += 1

    return {
        "total_findings": total,
        "mapped_findings": mapped,
        "coverage": coverage,
        "unmapped_ids": unmapped_ids,
        "high_risk_unmapped_count": high_risk_unmapped,
    }


def build_summary_artifacts(
    *,
    run_id: str,
    file_id: str,
    report_payload: Optional[Dict[str, Any]],
    icv: Optional[Dict[str, Any]],
    ekv: Optional[Dict[str, Any]],
    consensus: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Build Week6 summary artifacts from Week5 outputs.
    Single source of truth: report_payload.
    """
    payload = _as_dict(report_payload).copy()
    icv_payload = _as_dict(icv) if isinstance(icv, dict) else _as_dict(payload.get("icv"))
    ekv_payload = _as_dict(ekv) if isinstance(ekv, dict) else _as_dict(payload.get("ekv"))
    consensus_payload = (
        _as_dict(consensus) if isinstance(consensus, dict) else _as_dict(payload.get("consensus"))
    )

    claims = _as_list(ekv_payload.get("claims"))
    claim_lookup = {
        str(item.get("claim_id") or "").strip(): item
        for item in claims
        if isinstance(item, dict) and str(item.get("claim_id") or "").strip()
    }

    evidence_items, evidence_lookup, claim_to_evidence_ids = _build_evidence_items(
        ekv_payload,
        run_id=run_id,
        file_id=file_id,
    )

    key_findings: List[Dict[str, Any]] = []
    for claim_id in KEY_CLAIM_IDS:
        key_findings.append(
            _resolve_claim_finding(
                claim_id,
                claim_lookup.get(claim_id),
                claim_to_evidence_ids,
            )
        )
    key_findings.extend(_resolve_icv_high_risk_findings(icv_payload))

    evidence_map: Dict[str, Dict[str, Any]] = {}
    for item in key_findings:
        finding_id = str(item.get("finding_id") or "")
        evidence_map[finding_id] = {
            "evidence_ids": list(item.get("evidence_ids") or []),
            "unavailable_reason": item.get("unavailable_reason"),
        }

    traceability = _build_traceability(key_findings)

    confidence = _safe_float(ekv_payload.get("score"))
    if confidence is None:
        confidence = 0.0

    uncertainties = _collect_uncertainties(
        key_findings=key_findings,
        icv=icv_payload,
        ekv=ekv_payload,
        consensus=consensus_payload,
    )
    next_actions = _collect_next_actions(
        key_findings=key_findings,
        consensus=consensus_payload,
    )
    risk_level = _risk_level_from_findings(key_findings, consensus_payload)

    final_citations = []
    for item in evidence_items:
        final_citations.append(
            {
                "evidence_id": item.get("evidence_id"),
                "source_ref": item.get("source_ref"),
                "doc_name": item.get("doc_name"),
                "page": item.get("page"),
                "snippet": item.get("snippet"),
            }
        )

    mapped = traceability.get("mapped_findings", 0)
    total = traceability.get("total_findings", 0)
    summary_text = (
        f"Summary generated from Week5 outputs. "
        f"Evidence mapped for {mapped}/{total} findings."
    )

    final_report = {
        "summary": summary_text,
        "key_findings": key_findings,
        "risk_level": risk_level,
        "confidence": confidence,
        "citations": final_citations,
        "uncertainties": uncertainties,
        "next_actions": next_actions,
    }

    payload["final_report"] = final_report
    payload["evidence_items"] = evidence_items
    payload["evidence_map"] = evidence_map
    payload["traceability"] = traceability

    try:
        print(
            f"[SUMMARY] run_id={run_id} file_id={file_id} "
            f"risk={risk_level} confidence={confidence} findings={total}"
        )
        print(
            f"[EVIDENCE] run_id={run_id} file_id={file_id} "
            f"items={len(evidence_items)} mapped={mapped}/{total} "
            f"coverage={traceability.get('coverage')} "
            f"high_risk_unmapped={traceability.get('high_risk_unmapped_count')}"
        )
    except Exception:
        pass

    return payload
