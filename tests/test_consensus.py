from backend.consensus import evaluate_consensus


def test_consensus_skips_without_conflicts():
    icv = {"status": "pass", "findings": []}
    ekv = {
        "status": "available",
        "claims": [
            {"claim_id": "hemisphere", "verdict": "supported"},
            {"claim_id": "core_volume_ml", "verdict": "supported"},
        ],
    }
    out = evaluate_consensus(icv_payload=icv, ekv_payload=ekv)
    assert out["success"] is True
    consensus = out["consensus"]
    assert consensus["decision"] == "skipped"
    assert consensus["conflict_count"] == 0


def test_consensus_triggers_review_for_not_supported():
    icv = {"status": "warn", "findings": []}
    ekv = {
        "status": "available",
        "claims": [
            {"claim_id": "mismatch_ratio", "verdict": "not_supported"},
            {"claim_id": "hemisphere", "verdict": "supported"},
        ],
    }
    out = evaluate_consensus(icv_payload=icv, ekv_payload=ekv)
    consensus = out["consensus"]
    assert consensus["decision"] in {"review_required", "escalate"}
    assert consensus["conflict_count"] >= 1


def test_consensus_escalates_on_icv_fail():
    icv = {"status": "fail", "findings": [{"id": "R5", "status": "fail"}]}
    ekv = {
        "status": "available",
        "claims": [
            {"claim_id": "core_volume_ml", "verdict": "partially_supported"},
            {"claim_id": "penumbra_volume_ml", "verdict": "partially_supported"},
        ],
    }
    out = evaluate_consensus(icv_payload=icv, ekv_payload=ekv)
    consensus = out["consensus"]
    assert consensus["decision"] == "escalate"
    assert consensus["conflict_count"] >= 1
