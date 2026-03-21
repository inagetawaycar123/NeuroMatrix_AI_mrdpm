from typing import Any, Dict, List, Optional


HIGH_RISK_CLAIMS = {
    "core_volume_ml",
    "penumbra_volume_ml",
    "mismatch_ratio",
    "significant_mismatch_present",
}


def _safe_obj(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _extract_claims(ekv_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    claims = ekv_payload.get("claims")
    if not isinstance(claims, list):
        return []
    return [c for c in claims if isinstance(c, dict)]


def _default_actions(decision: str) -> List[str]:
    if decision == "accept":
        return ["Proceed with standard reporting workflow."]
    if decision == "review_required":
        return [
            "Flag this case for clinician review.",
            "Validate key quantitative claims against source images.",
        ]
    if decision == "escalate":
        return [
            "Escalate to senior reviewer before sign-off.",
            "Re-run critical tools and verify data integrity.",
        ]
    return ["No consensus action required."]


def evaluate_consensus(
    icv_payload: Optional[Dict[str, Any]] = None,
    ekv_payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Evaluate whether conflicts require a consensus decision.

    Trigger rules (any one):
    1) EKV has not_supported claim
    2) EKV has >=2 partially_supported claims
    3) ICV status == fail
    4) EKV unavailable and high-risk claims exist
    """
    icv = _safe_obj(icv_payload)
    ekv = _safe_obj(ekv_payload)

    icv_status = str(icv.get("status") or "").strip().lower()
    ekv_status = str(ekv.get("status") or "").strip().lower()

    claims = _extract_claims(ekv)
    not_supported_claims = [c for c in claims if str(c.get("verdict") or "").lower() == "not_supported"]
    partial_claims = [c for c in claims if str(c.get("verdict") or "").lower() == "partially_supported"]

    high_risk_present = any(
        str(c.get("claim_id") or "").strip() in HIGH_RISK_CLAIMS for c in claims
    )

    conflicts: List[Dict[str, Any]] = []

    if not_supported_claims:
        conflicts.append(
            {
                "code": "CONSENSUS_NOT_SUPPORTED",
                "message": "EKV includes not_supported claims",
                "count": len(not_supported_claims),
            }
        )

    if len(partial_claims) >= 2:
        conflicts.append(
            {
                "code": "CONSENSUS_PARTIAL_ACCUMULATION",
                "message": "EKV has multiple partially_supported claims",
                "count": len(partial_claims),
            }
        )

    if icv_status == "fail":
        conflicts.append(
            {
                "code": "CONSENSUS_ICV_FAIL",
                "message": "ICV status is fail",
                "count": 1,
            }
        )

    if ekv_status == "unavailable" and high_risk_present:
        conflicts.append(
            {
                "code": "CONSENSUS_EKV_UNAVAILABLE_HIGH_RISK",
                "message": "EKV unavailable while high-risk claims exist",
                "count": 1,
            }
        )

    if not conflicts:
        payload = {
            "status": "completed",
            "decision": "skipped",
            "conflict_count": 0,
            "summary": "No material conflict. Consensus step skipped.",
            "conflicts": [],
            "next_actions": _default_actions("skipped"),
        }
        return {"success": True, "consensus": payload}

    decision = "review_required"
    if icv_status == "fail" or len(not_supported_claims) >= 2:
        decision = "escalate"
    elif not_supported_claims or len(partial_claims) >= 2:
        decision = "review_required"
    else:
        decision = "accept"

    payload = {
        "status": "completed",
        "decision": decision,
        "conflict_count": len(conflicts),
        "summary": "Consensus decision generated due to detected conflicts.",
        "conflicts": conflicts,
        "next_actions": _default_actions(decision),
    }
    return {"success": True, "consensus": payload}
