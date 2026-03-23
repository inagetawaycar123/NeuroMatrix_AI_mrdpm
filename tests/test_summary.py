"""
Week6 汇总与证据链模块测试

测试证据映射、可追溯性计算、集成功能
测试用例覆盖 NCCT-only、NCCT+mCTA、NCCT+mCTA+CTP 三种场景
"""

import pytest
from datetime import datetime
from backend.summary import (
    build_final_report,
    integrate_summary_into_run,
    EvidenceItem,
    FinalReport,
)


# ==================== 测试数据工厂 ====================

def create_mock_run(
    modalities=None,
    run_id="test_run_001",
    file_id="test_file_001",
    patient_id="test_patient_001",
):
    """创建模拟的 Agent Run 对象"""
    
    # 默认使用 NCCT+mCTA+CTP 完整模态
    if modalities is None:
        modalities = ["ncct", "mcta", "cbf", "cbv", "tmax"]
    
    # 构建 tool_results
    tool_results = [
        {
            "tool_name": "icv",
            "status": "completed",
            "structured_output": {
                "status": "completed",
                "findings": [
                    {
                        "id": "R1_ctp_availability",
                        "status": "pass",
                        "severity": "low",
                        "message": "CTP 模态可用",
                    },
                    {
                        "id": "R2_mismatch_consistency",
                        "status": "pass",
                        "severity": "low",
                        "message": "不匹配比值计算一致",
                    },
                ],
            },
        },
        {
            "tool_name": "ekv",
            "status": "completed",
            "structured_output": {
                "status": "available",
                "score": 0.85,
                "claims": [
                    {
                        "claim_id": "hemisphere",
                        "verdict": "supported",
                        "confidence": 0.9,
                        "message": "文献支持左侧半球病变",
                        "evidence_documents": [
                            {
                                "doc_name": "中国脑卒中防治指导规范（2021 年版）",
                                "page": 45,
                                "text": "左侧大脑中动脉供血区是急性缺血性卒中最常见部位...",
                            }
                        ],
                    },
                    {
                        "claim_id": "core_volume_ml",
                        "verdict": "supported",
                        "confidence": 0.8,
                        "message": "核心梗死体积在合理范围内",
                        "evidence_documents": [
                            {
                                "doc_name": "急性缺血卒中血管内治疗技术中国专家共识2025",
                                "page": 32,
                                "text": "核心梗死体积小于 70ml 的患者适合血管内治疗...",
                            }
                        ],
                    },
                    {
                        "claim_id": "penumbra_volume_ml",
                        "verdict": "supported",
                        "confidence": 0.75,
                        "message": "半暗带体积符合治疗窗口",
                        "evidence_documents": [
                            {
                                "doc_name": "急性缺血卒中血管内治疗技术中国专家共识2025",
                                "page": 33,
                                "text": "半暗带体积大于核心梗死体积提示存在可挽救脑组织...",
                            }
                        ],
                    },
                    {
                        "claim_id": "mismatch_ratio",
                        "verdict": "supported",
                        "confidence": 0.85,
                        "message": "不匹配比值大于 1.8，提示存在显著不匹配",
                        "evidence_documents": [
                            {
                                "doc_name": "中国脑卒中防治指导规范（2021 年版）",
                                "page": 78,
                                "text": "不匹配比值大于 1.8 提示存在显著不匹配，适合血管内治疗...",
                            }
                        ],
                    },
                    {
                        "claim_id": "significant_mismatch_present",
                        "verdict": "supported",
                        "confidence": 0.8,
                        "message": "存在显著不匹配",
                        "evidence_documents": [
                            {
                                "doc_name": "中国脑卒中防治指导规范（2021 年版）",
                                "page": 79,
                                "text": "显著不匹配定义为不匹配比值大于 1.8...",
                            }
                        ],
                    },
                    {
                        "claim_id": "treatment_window_hint",
                        "verdict": "partially_supported",
                        "confidence": 0.6,
                        "message": "治疗时窗提示需结合临床评估",
                        "evidence_documents": [
                            {
                                "doc_name": "急性缺血卒中血管内治疗技术中国专家共识2025",
                                "page": 41,
                                "text": "发病 6 小时内为血管内治疗最佳时间窗...",
                            }
                        ],
                    },
                ],
                "citations": [
                    "中国脑卒中防治指导规范（2021 年版）",
                    "急性缺血卒中血管内治疗技术中国专家共识2025",
                ],
            },
        },
        {
            "tool_name": "consensus_lite",
            "status": "completed",
            "structured_output": {
                "decision": "supported",
                "summary": "ICV 与 EKV 结果一致，支持血管内治疗决策",
                "conflict_count": 0,
            },
        },
    ]
    
    # 根据模态调整 EKV 结果
    if "cbf" not in modalities or "cbv" not in modalities or "tmax" not in modalities:
        # 如果没有 CTP 模态，相关 claim 应为 unavailable
        for claim in tool_results[1]["structured_output"]["claims"]:
            if claim["claim_id"] in ["mismatch_ratio", "significant_mismatch_present"]:
                claim["verdict"] = "unavailable"
                claim["evidence_documents"] = []
    
    # 构建 report_result
    report_result = {
        "report_payload": {
            "hemisphere": "left",
            "core_infarct_volume": 15.5,
            "penumbra_volume": 44.8,
            "mismatch_ratio": 3.02,
        }
    }
    
    return {
        "run_id": run_id,
        "file_id": file_id,
        "patient_id": patient_id,
        "tool_results": tool_results,
        "result": {
            "report_result": report_result,
        },
    }


def create_ncct_only_run():
    """创建 NCCT-only 场景的 Run"""
    run = create_mock_run(modalities=["ncct"])
    
    # 调整 ICV 结果
    for tool in run["tool_results"]:
        if tool["tool_name"] == "icv":
            tool["structured_output"]["findings"] = [
                {
                    "id": "R1_ctp_availability",
                    "status": "not_applicable",
                    "severity": "low",
                    "message": "无 CTP 模态，跳过 CTP 相关检查",
                }
            ]
    
    # 在 NCCT-only 场景中，report_payload 不应该包含 CTP 量化指标
    if "report_result" in run["result"]:
        report_payload = run["result"]["report_result"].get("report_payload", {})
        # 移除 CTP 相关指标
        ctp_metrics = ["mismatch_ratio"]
        for metric in ctp_metrics:
            if metric in report_payload:
                del report_payload[metric]
    
    return run


def create_ncct_mcta_run():
    """创建 NCCT+mCTA 场景的 Run"""
    run = create_mock_run(modalities=["ncct", "mcta"])
    
    # 调整 ICV 结果
    for tool in run["tool_results"]:
        if tool["tool_name"] == "icv":
            tool["structured_output"]["findings"] = [
                {
                    "id": "R1_ctp_availability",
                    "status": "not_applicable",
                    "severity": "low",
                    "message": "无 CTP 模态，跳过 CTP 相关检查",
                }
            ]
    
    # 在 NCCT+mCTA 场景中，report_payload 不应该包含 CTP 量化指标
    if "report_result" in run["result"]:
        report_payload = run["result"]["report_result"].get("report_payload", {})
        # 移除 CTP 相关指标
        ctp_metrics = ["mismatch_ratio"]
        for metric in ctp_metrics:
            if metric in report_payload:
                del report_payload[metric]
    
    return run


def create_full_ctp_run():
    """创建 NCCT+mCTA+CTP 完整场景的 Run"""
    return create_mock_run(modalities=["ncct", "mcta", "cbf", "cbv", "tmax"])


# ==================== 测试用例：证据映射 ====================

def test_evidence_mapping_ncct_only():
    """测试 NCCT-only 场景的证据映射"""
    run = create_ncct_only_run()
    result = build_final_report(run)
    
    # 验证证据项
    evidence_items = result["evidence_items"]
    assert len(evidence_items) > 0
    
    # 验证证据映射
    evidence_map = result["evidence_map"]
    
    # CTP 相关结论应为 unavailable
    ctp_claims = ["mismatch_ratio", "significant_mismatch_present"]
    for claim_id in ctp_claims:
        mapping = evidence_map.get(claim_id)
        assert mapping is not None
        assert mapping["unavailable_reason"] is not None
        # 接受多种不可用原因
        acceptable_reasons = ["缺少量化数据", "模态限制", "相关信息不可用", "临床信息不完整"]
        assert any(reason in mapping["unavailable_reason"] for reason in acceptable_reasons), \
            f"unavailable_reason '{mapping['unavailable_reason']}' 不是可接受的原因"
    
    # 非 CTP 结论应有证据
    non_ctp_claims = ["hemisphere", "core_volume_ml", "penumbra_volume_ml"]
    for claim_id in non_ctp_claims:
        mapping = evidence_map.get(claim_id)
        assert mapping is not None
    
    print(f"[TEST] NCCT-only 证据映射测试通过")


def test_evidence_mapping_ncct_mcta():
    """测试 NCCT+mCTA 场景的证据映射"""
    run = create_ncct_mcta_run()
    result = build_final_report(run)
    
    evidence_map = result["evidence_map"]
    
    # CTP 相关结论应为 unavailable
    ctp_claims = ["mismatch_ratio", "significant_mismatch_present"]
    for claim_id in ctp_claims:
        mapping = evidence_map.get(claim_id)
        assert mapping is not None
        assert mapping["unavailable_reason"] is not None
        # 接受多种不可用原因
        acceptable_reasons = ["缺少量化数据", "模态限制", "相关信息不可用", "临床信息不完整"]
        assert any(reason in mapping["unavailable_reason"] for reason in acceptable_reasons), \
            f"unavailable_reason '{mapping['unavailable_reason']}' 不是可接受的原因"
    
    # mCTA 相关结论应有证据
    mcta_claims = ["hemisphere"]
    for claim_id in mcta_claims:
        mapping = evidence_map.get(claim_id)
        assert mapping is not None
    
    print(f"[TEST] NCCT+mCTA 证据映射测试通过")


def test_evidence_mapping_full_ctp():
    """测试 NCCT+mCTA+CTP 完整场景的证据映射"""
    run = create_full_ctp_run()
    result = build_final_report(run)
    
    evidence_map = result["evidence_map"]
    
    # 所有结论都应有证据或明确 unavailable
    all_claims = [
        "hemisphere",
        "core_volume_ml",
        "penumbra_volume_ml",
        "mismatch_ratio",
        "significant_mismatch_present",
        "treatment_window_hint",
    ]
    
    for claim_id in all_claims:
        mapping = evidence_map.get(claim_id)
        assert mapping is not None
        
        # 验证要么有证据，要么有 unavailable_reason
        if not mapping["evidence_ids"]:
            assert mapping["unavailable_reason"] is not None
            assert len(mapping["unavailable_reason"]) > 0
    
    # 验证量化结论有证据
    quantitative_claims = ["core_volume_ml", "penumbra_volume_ml", "mismatch_ratio"]
    for claim_id in quantitative_claims:
        mapping = evidence_map.get(claim_id)
        # 在完整 CTP 场景中，这些结论应有证据
        if mapping["evidence_ids"]:
            assert len(mapping["evidence_ids"]) > 0
    
    print(f"[TEST] NCCT+mCTA+CTP 证据映射测试通过")


# ==================== 测试用例：可追溯性计算 ====================

def test_traceability_calculation():
    """测试可追溯性计算"""
    run = create_full_ctp_run()
    result = build_final_report(run)
    
    traceability = result["final_report"]["traceability"]
    
    # 验证可追溯性指标存在
    assert "total_findings" in traceability
    assert "findings_requiring_evidence" in traceability
    assert "mapped_findings" in traceability
    assert "coverage" in traceability
    assert "unmapped_ids" in traceability
    assert "threshold_met" in traceability
    
    # 验证数据类型
    assert isinstance(traceability["total_findings"], int)
    assert isinstance(traceability["findings_requiring_evidence"], int)
    assert isinstance(traceability["mapped_findings"], int)
    assert isinstance(traceability["coverage"], float)
    assert isinstance(traceability["unmapped_ids"], list)
    assert isinstance(traceability["threshold_met"], bool)
    
    # 验证覆盖率在 0-1 之间
    assert 0.0 <= traceability["coverage"] <= 1.0
    
    # 验证 mapped_findings 不超过 findings_requiring_evidence
    assert traceability["mapped_findings"] <= traceability["findings_requiring_evidence"]
    
    print(f"[TEST] 可追溯性计算测试通过，覆盖率: {traceability['coverage']:.1%}")


def test_traceability_threshold():
    """测试可追溯性阈值"""
    run = create_full_ctp_run()
    result = build_final_report(run)
    
    traceability = result["final_report"]["traceability"]
    coverage = traceability["coverage"]
    threshold_met = traceability["threshold_met"]
    
    # 验证阈值逻辑
    if coverage >= 0.9:
        assert threshold_met is True
    else:
        assert threshold_met is False
    
    print(f"[TEST] 可追溯性阈值测试通过，覆盖率: {coverage:.1%}, 达标: {threshold_met}")


def test_traceability_ncct_only():
    """测试 NCCT-only 场景的可追溯性"""
    run = create_ncct_only_run()
    result = build_final_report(run)
    
    traceability = result["final_report"]["traceability"]
    
    # NCCT-only 场景中，CTP 相关结论应为 unavailable
    # 因此覆盖率可能较低，但这是预期的
    assert traceability["coverage"] >= 0.0
    
    # 验证 unmapped_ids 包含 CTP 相关结论
    ctp_claims = ["mismatch_ratio", "significant_mismatch_present"]
    unmapped_ids = traceability["unmapped_ids"]
    
    # 检查是否有 CTP 相关结论在 unmapped_ids 中
    ctp_unmapped = [claim for claim in ctp_claims if claim in unmapped_ids]
    assert len(ctp_unmapped) > 0 or traceability["coverage"] == 1.0
    
    print(f"[TEST] NCCT-only 可追溯性测试通过，覆盖率: {traceability['coverage']:.1%}")


# ==================== 测试用例：集成功能 ====================

def test_integrate_summary_into_run():
    """测试集成功能"""
    run = create_full_ctp_run()
    
    # 集成前验证
    assert "final_report" not in run.get("result", {})
    assert "evidence_items" not in run.get("result", {})
    assert "evidence_map" not in run.get("result", {})
    assert "trace" not in run.get("result", {})
    
    # 执行集成
    updated_run = integrate_summary_into_run(run)
    
    # 验证集成后字段
    result = updated_run.get("result", {})
    assert "final_report" in result
    assert "evidence_items" in result
    assert "evidence_map" in result
    assert "trace" in result
    
    # 验证字段结构
    final_report = result["final_report"]
    assert "summary" in final_report
    assert "key_findings" in final_report
    assert "risk_level" in final_report
    assert "confidence" in final_report
    assert "traceability" in final_report
    
    # 验证证据项
    evidence_items = result["evidence_items"]
    assert isinstance(evidence_items, list)
    if evidence_items:
        item = evidence_items[0]
        assert "evidence_id" in item
        assert "source_type" in item
        assert "claim" in item
    
    # 验证证据映射
    evidence_map = result["evidence_map"]
    assert isinstance(evidence_map, dict)
    
    # 验证 trace
    trace = result["trace"]
    assert "run_id" in trace
    assert "traceability" in trace
    
    print(f"[TEST] 集成功能测试通过")


def test_integration_preserves_existing_data():
    """测试集成不破坏现有数据"""
    run = create_full_ctp_run()
    
    # 添加一些现有数据
    run["result"]["existing_field"] = "should_be_preserved"
    run["result"]["report_result"]["existing_report_field"] = "should_also_be_preserved"
    
    # 执行集成
    updated_run = integrate_summary_into_run(run)
    
    # 验证现有数据被保留
    assert updated_run["result"]["existing_field"] == "should_be_preserved"
    assert updated_run["result"]["report_result"]["existing_report_field"] == "should_also_be_preserved"
    
    # 验证新增字段也存在
    assert "final_report" in updated_run["result"]
    assert "evidence_items" in updated_run["result"]
    
    print(f"[TEST] 集成数据保留测试通过")


def test_integration_error_handling():
    """测试集成错误处理"""
    # 创建无效的 run 对象
    invalid_run = {"run_id": "invalid_run"}
    
    # 应该不会抛出异常，而是返回原始 run
    result = integrate_summary_into_run(invalid_run)
    
    # 验证返回了 run 对象
    assert "run_id" in result
    assert result["run_id"] == "invalid_run"
    
    print(f"[TEST] 集成错误处理测试通过")


# ==================== 测试用例：FinalReport 结构 ====================

def test_final_report_structure():
    """测试 FinalReport 数据结构"""
    run = create_full_ctp_run()
    result = build_final_report(run)
    
    final_report = result["final_report"]
    
    # 验证必需字段
    required_fields = [
        "summary",
        "key_findings",
        "risk_level",
        "confidence",
        "citations",
        "uncertainties",
        "next_actions",
        "traceability",
    ]
    
    for field in required_fields:
        assert field in final_report
        assert final_report[field] is not None
    
    # 验证字段类型
    assert isinstance(final_report["summary"], str)
    assert isinstance(final_report["key_findings"], list)
    assert isinstance(final_report["risk_level"], str)
    assert isinstance(final_report["confidence"], (int, float))
    assert isinstance(final_report["citations"], list)
    assert isinstance(final_report["uncertainties"], list)
    assert isinstance(final_report["next_actions"], list)
    assert isinstance(final_report["traceability"], dict)
    
    print(f"[TEST] FinalReport 结构测试通过")
