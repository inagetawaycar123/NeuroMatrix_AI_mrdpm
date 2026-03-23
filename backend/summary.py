"""
Week6 汇总与证据链模块

本模块实现 build_final_report 汇总函数，负责从 tool_results + report_payload + ekv/consensus
生成 FinalReport + EvidenceMap + Trace，满足 Week6 可审计要求。
"""

import uuid
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

# ==================== 数据结构定义 ====================

class EvidenceItem:
    """证据项数据结构（Week6 冻结契约）"""
    
    def __init__(
        self,
        evidence_id: str,
        source_type: str,  # "ekv", "icv", "consensus", "analysis", "report"
        source_ref: str,   # 源引用，如 "ekv_claim_hemisphere"
        claim: str,        # 关联的 claim_id
        support_level: str,  # "supported", "partially_supported", "not_supported", "unavailable"
        timestamp: str,
        snippet: str,      # 证据文本片段
        doc_name: Optional[str] = None,
        page: Optional[int] = None,
        run_id: Optional[str] = None,
        file_id: Optional[str] = None,
    ):
        self.evidence_id = evidence_id
        self.source_type = source_type
        self.source_ref = source_ref
        self.claim = claim
        self.support_level = support_level
        self.timestamp = timestamp
        self.snippet = snippet
        self.doc_name = doc_name
        self.page = page
        self.run_id = run_id
        self.file_id = file_id
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "source_type": self.source_type,
            "source_ref": self.source_ref,
            "claim": self.claim,
            "support_level": self.support_level,
            "timestamp": self.timestamp,
            "snippet": self.snippet,
            "doc_name": self.doc_name,
            "page": self.page,
            "run_id": self.run_id,
            "file_id": self.file_id,
        }


class FinalReport:
    """最终报告数据结构（Week6 冻结契约）"""
    
    def __init__(
        self,
        summary: str,
        key_findings: List[Dict[str, Any]],
        risk_level: str,  # "low", "medium", "high"
        confidence: float,  # 0.0-1.0
        citations: List[str],
        uncertainties: List[Dict[str, Any]],
        next_actions: List[str],
        traceability: Dict[str, Any],
    ):
        self.summary = summary
        self.key_findings = key_findings
        self.risk_level = risk_level
        self.confidence = confidence
        self.citations = citations
        self.uncertainties = uncertainties
        self.next_actions = next_actions
        self.traceability = traceability
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary,
            "key_findings": self.key_findings,
            "risk_level": self.risk_level,
            "confidence": self.confidence,
            "citations": self.citations,
            "uncertainties": self.uncertainties,
            "next_actions": self.next_actions,
            "traceability": self.traceability,
        }


# ==================== 核心汇总函数 ====================

def build_final_report(run: Dict[str, Any]) -> Dict[str, Any]:
    """
    从 Agent Run 生成 FinalReport + EvidenceMap + Trace
    
    Args:
        run: Agent Run 对象，包含 tool_results、report_payload 等
        
    Returns:
        包含 final_report、evidence_items、evidence_map、trace 的字典
    """
    print(f"[SUMMARY] 开始构建最终报告 for run_id={run.get('run_id')}")
    
    # 1. 提取关键数据
    tool_results = run.get("tool_results", [])
    report_result = run.get("result", {}).get("report_result") or {}
    report_payload = report_result.get("report_payload") or {}
    
    # 提取 ICV/EKV/Consensus 结果
    icv_result = _extract_tool_result(tool_results, "icv")
    ekv_result = _extract_tool_result(tool_results, "ekv")
    consensus_result = _extract_tool_result(tool_results, "consensus_lite")
    
    # 2. 构建证据项
    evidence_items = _build_evidence_items(
        run_id=run.get("run_id"),
        file_id=run.get("file_id"),
        icv_result=icv_result,
        ekv_result=ekv_result,
        consensus_result=consensus_result,
        report_payload=report_payload,
    )
    
    # 3. 构建关键结论（Week5 的 6 类 claim + ICV 高风险项）
    key_findings = _build_key_findings(
        icv_result=icv_result,
        ekv_result=ekv_result,
        consensus_result=consensus_result,
        report_payload=report_payload,
    )
    
    # 4. 构建证据映射
    evidence_map = _build_evidence_map(key_findings, evidence_items)
    
    # 5. 计算可追溯性指标
    traceability = _calculate_traceability(key_findings, evidence_map)
    
    # 6. 构建最终报告
    final_report = _build_final_report_object(
        run=run,
        key_findings=key_findings,
        evidence_map=evidence_map,
        traceability=traceability,
        icv_result=icv_result,
        ekv_result=ekv_result,
        consensus_result=consensus_result,
    )
    
    # 7. 返回完整结果
    result = {
        "final_report": final_report.to_dict(),
        "evidence_items": [item.to_dict() for item in evidence_items],
        "evidence_map": evidence_map,
        "trace": {
            "run_id": run.get("run_id"),
            "file_id": run.get("file_id"),
            "patient_id": run.get("patient_id"),
            "generated_at": datetime.now().isoformat(),
            "traceability": traceability,
        },
    }
    
    print(f"[SUMMARY] 最终报告构建完成 for run_id={run.get('run_id')}")
    print(f"[SUMMARY] 关键结论数: {len(key_findings)}")
    print(f"[SUMMARY] 证据项数: {len(evidence_items)}")
    print(f"[SUMMARY] 可追溯覆盖率: {traceability.get('coverage', 0.0):.2%}")
    
    return result


def _extract_tool_result(tool_results: List[Dict[str, Any]], tool_name: str) -> Optional[Dict[str, Any]]:
    """从 tool_results 中提取指定工具的结果"""
    for result in reversed(tool_results):
        if result.get("tool_name") == tool_name and result.get("status") == "completed":
            return result.get("structured_output") or {}
    return None


def _build_evidence_items(
    run_id: str,
    file_id: str,
    icv_result: Optional[Dict[str, Any]],
    ekv_result: Optional[Dict[str, Any]],
    consensus_result: Optional[Dict[str, Any]],
    report_payload: Dict[str, Any],
) -> List[EvidenceItem]:
    """构建证据项列表"""
    evidence_items = []
    timestamp = datetime.now().isoformat()
    
    # 1. 从 EKV 提取证据
    if ekv_result:
        claims = ekv_result.get("claims", [])
        for claim in claims:
            claim_id = claim.get("claim_id")
            verdict = claim.get("verdict")
            evidence_docs = claim.get("evidence_documents", [])
            
            for doc in evidence_docs:
                evidence_id = f"ekv_{claim_id}_{uuid.uuid4().hex[:8]}"
                item = EvidenceItem(
                    evidence_id=evidence_id,
                    source_type="ekv",
                    source_ref=f"ekv_claim_{claim_id}",
                    claim=claim_id,
                    support_level=verdict,
                    timestamp=timestamp,
                    snippet=doc.get("text", "")[:500],  # 截取前500字符
                    doc_name=doc.get("doc_name"),
                    page=doc.get("page"),
                    run_id=run_id,
                    file_id=file_id,
                )
                evidence_items.append(item)
    
    # 2. 从 ICV 提取证据
    if icv_result:
        findings = icv_result.get("findings", [])
        for finding in findings:
            finding_id = finding.get("id", "")
            status = finding.get("status", "")
            evidence_id = f"icv_{finding_id}_{uuid.uuid4().hex[:8]}"
            item = EvidenceItem(
                evidence_id=evidence_id,
                source_type="icv",
                source_ref=f"icv_finding_{finding_id}",
                claim=_map_icv_finding_to_claim(finding_id),
                support_level=_map_icv_status_to_support_level(status),
                timestamp=timestamp,
                snippet=finding.get("message", "")[:500],
                run_id=run_id,
                file_id=file_id,
            )
            evidence_items.append(item)
    
    # 3. 从 Consensus 提取证据
    if consensus_result:
        decision = consensus_result.get("decision", "")
        summary = consensus_result.get("summary", "")
        evidence_id = f"consensus_{uuid.uuid4().hex[:8]}"
        item = EvidenceItem(
            evidence_id=evidence_id,
            source_type="consensus",
            source_ref="consensus_decision",
            claim="consensus_overall",
            support_level=_map_consensus_decision_to_support_level(decision),
            timestamp=timestamp,
            snippet=summary[:500],
            run_id=run_id,
            file_id=file_id,
        )
        evidence_items.append(item)
    
    # 4. 从 Report Payload 提取量化证据
    if report_payload:
        # 提取核心量化指标
        metrics = ["core_infarct_volume", "penumbra_volume", "mismatch_ratio"]
        for metric in metrics:
            value = report_payload.get(metric)
            if value is not None:
                evidence_id = f"report_{metric}_{uuid.uuid4().hex[:8]}"
                item = EvidenceItem(
                    evidence_id=evidence_id,
                    source_type="report",
                    source_ref=f"report_metric_{metric}",
                    claim=metric,
                    support_level="supported",  # 报告数据默认为支持
                    timestamp=timestamp,
                    snippet=f"{metric}: {value}",
                    run_id=run_id,
                    file_id=file_id,
                )
                evidence_items.append(item)
    
    return evidence_items


def _build_key_findings(
    icv_result: Optional[Dict[str, Any]],
    ekv_result: Optional[Dict[str, Any]],
    consensus_result: Optional[Dict[str, Any]],
    report_payload: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """构建关键结论列表（Week5 的 6 类 claim + ICV 高风险项）"""
    key_findings = []
    
    # Week5 的 6 类 claim
    claim_definitions = [
        {"id": "hemisphere", "title": "病变侧别", "category": "qualitative"},
        {"id": "core_volume_ml", "title": "核心梗死体积 (ml)", "category": "quantitative"},
        {"id": "penumbra_volume_ml", "title": "半暗带体积 (ml)", "category": "quantitative"},
        {"id": "mismatch_ratio", "title": "不匹配比值", "category": "quantitative"},
        {"id": "significant_mismatch_present", "title": "是否存在显著不匹配", "category": "qualitative"},
        {"id": "treatment_window_hint", "title": "治疗时窗相关提示", "category": "clinical"},
    ]
    
    # 从 EKV 获取 claim 状态
    ekv_claims = {}
    if ekv_result:
        for claim in ekv_result.get("claims", []):
            claim_id = claim.get("claim_id")
            ekv_claims[claim_id] = {
                "verdict": claim.get("verdict"),
                "message": claim.get("message", ""),
                "confidence": claim.get("confidence", 0.0),
            }
    
    # 构建关键结论
    for claim_def in claim_definitions:
        claim_id = claim_def["id"]
        ekv_info = ekv_claims.get(claim_id, {})
        
        finding = {
            "id": claim_id,
            "title": claim_def["title"],
            "category": claim_def["category"],
            "verdict": ekv_info.get("verdict", "unavailable"),
            "confidence": ekv_info.get("confidence", 0.0),
            "message": ekv_info.get("message", "信息不可用"),
            "risk_level": _determine_risk_level(claim_id, ekv_info.get("verdict")),
            "requires_evidence": claim_def["category"] in ["quantitative", "clinical"],
        }
        key_findings.append(finding)
    
    # 添加 ICV 高风险项
    if icv_result:
        high_risk_findings = [
            f for f in icv_result.get("findings", [])
            if f.get("severity") == "high" and f.get("status") in ["fail", "warn"]
        ]
        for finding in high_risk_findings:
            key_findings.append({
                "id": finding.get("id", ""),
                "title": f"ICV高风险: {finding.get('message', '')[:50]}...",
                "category": "icv_high_risk",
                "verdict": "requires_review",
                "confidence": 0.3,
                "message": finding.get("message", ""),
                "risk_level": "high",
                "requires_evidence": True,
            })
    
    return key_findings


def _build_evidence_map(
    key_findings: List[Dict[str, Any]],
    evidence_items: List[EvidenceItem],
) -> Dict[str, Dict[str, Any]]:
    """构建证据映射：每条关键结论关联的证据ID列表"""
    evidence_map = {}
    
    # 初始化映射
    for finding in key_findings:
        finding_id = finding["id"]
        evidence_map[finding_id] = {
            "finding_id": finding_id,
            "evidence_ids": [],
            "unavailable_reason": None,
        }
    
    # 将证据项关联到对应的结论
    for item in evidence_items:
        claim = item.claim
        if claim in evidence_map:
            evidence_map[claim]["evidence_ids"].append(item.evidence_id)
    
    # 检查无证据的结论
    for finding_id, mapping in evidence_map.items():
        if not mapping["evidence_ids"]:
            # 查找对应的关键结论
            finding = next((f for f in key_findings if f["id"] == finding_id), None)
            if finding:
                # 如果结论需要证据，或者 verdict 为 unavailable，则设置原因
                if finding.get("requires_evidence") or finding.get("verdict") == "unavailable":
                    mapping["unavailable_reason"] = _determine_unavailable_reason(finding)
    
    return evidence_map


def _calculate_traceability(
    key_findings: List[Dict[str, Any]],
    evidence_map: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """计算可追溯性指标"""
    total_findings = len(key_findings)
    
    # 需要证据的结论
    findings_requiring_evidence = [
        f for f in key_findings if f.get("requires_evidence", False)
    ]
    total_requiring_evidence = len(findings_requiring_evidence)
    
    # 有证据的结论
    mapped_findings = 0
    unmapped_ids = []
    
    for finding in findings_requiring_evidence:
        finding_id = finding["id"]
        mapping = evidence_map.get(finding_id, {})
        if mapping.get("evidence_ids"):
            mapped_findings += 1
        else:
            unmapped_ids.append(finding_id)
    
    # 计算覆盖率
    coverage = 0.0
    if total_requiring_evidence > 0:
        coverage = mapped_findings / total_requiring_evidence
    
    return {
        "total_findings": total_findings,
        "findings_requiring_evidence": total_requiring_evidence,
        "mapped_findings": mapped_findings,
        "coverage": coverage,
        "unmapped_ids": unmapped_ids,
        "threshold_met": coverage >= 0.9,  # Week6 签收阈值
    }


def _build_final_report_object(
    run: Dict[str, Any],
    key_findings: List[Dict[str, Any]],
    evidence_map: Dict[str, Dict[str, Any]],
    traceability: Dict[str, Any],
    icv_result: Optional[Dict[str, Any]],
    ekv_result: Optional[Dict[str, Any]],
    consensus_result: Optional[Dict[str, Any]],
) -> FinalReport:
    """构建 FinalReport 对象"""
    
    # 生成摘要
    summary = _generate_summary(
        run=run,
        key_findings=key_findings,
        traceability=traceability,
        icv_result=icv_result,
        ekv_result=ekv_result,
        consensus_result=consensus_result,
    )
    
    # 确定风险等级
    risk_level = _determine_overall_risk_level(key_findings)
    
    # 计算总体置信度
    confidence = _calculate_overall_confidence(key_findings)
    
    # 收集引用
    citations = _collect_citations(ekv_result, icv_result, consensus_result)
    
    # 收集不确定性
    uncertainties = _collect_uncertainties(
        key_findings=key_findings,
        evidence_map=evidence_map,
        icv_result=icv_result,
        ekv_result=ekv_result,
        consensus_result=consensus_result,
    )
    
    # 确定下一步行动
    next_actions = _determine_next_actions(
        key_findings=key_findings,
        traceability=traceability,
        uncertainties=uncertainties,
    )
    
    return FinalReport(
        summary=summary,
        key_findings=key_findings,
        risk_level=risk_level,
        confidence=confidence,
        citations=citations,
        uncertainties=uncertainties,
        next_actions=next_actions,
        traceability=traceability,
    )


# ==================== 辅助函数 ====================

def _map_icv_finding_to_claim(finding_id: str) -> str:
    """将 ICV finding ID 映射到 claim ID"""
    if "hemisphere" in finding_id:
        return "hemisphere"
    elif "core" in finding_id:
        return "core_volume_ml"
    elif "penumbra" in finding_id:
        return "penumbra_volume_ml"
    elif "mismatch" in finding_id:
        return "mismatch_ratio"
    else:
        return "other"


def _map_icv_status_to_support_level(status: str) -> str:
    """将 ICV status 映射到 support_level"""
    status_lower = str(status).lower()
    if status_lower == "pass":
        return "supported"
    elif status_lower == "warn":
        return "partially_supported"
    elif status_lower == "fail":
        return "not_supported"
    else:
        return "unavailable"


def _map_consensus_decision_to_support_level(decision: str) -> str:
    """将 Consensus decision 映射到 support_level"""
    decision_lower = str(decision).lower()
    if decision_lower in ["supported", "consistent"]:
        return "supported"
    elif decision_lower in ["partial", "requires_review"]:
        return "partially_supported"
    elif decision_lower in ["conflict", "not_supported"]:
        return "not_supported"
    else:
        return "unavailable"


def _determine_risk_level(claim_id: str, verdict: str) -> str:
    """确定单个结论的风险等级"""
    # 高风险结论：核心体积、半暗带、不匹配比
    high_risk_claims = ["core_volume_ml", "penumbra_volume_ml", "mismatch_ratio"]
    
    if claim_id in high_risk_claims:
        if verdict == "not_supported":
            return "high"
        elif verdict == "partially_supported":
            return "medium"
        elif verdict == "unavailable":
            return "medium"
        else:
            return "low"
    
    # 其他结论
    if verdict == "not_supported":
        return "medium"
    elif verdict == "partially_supported":
        return "low"
    elif verdict == "unavailable":
        return "low"
    else:
        return "low"


def _determine_unavailable_reason(finding: Dict[str, Any]) -> str:
    """确定证据不可用的原因"""
    category = finding.get("category", "")
    verdict = finding.get("verdict", "")
    
    if verdict == "unavailable":
        if category == "quantitative":
            return "缺少量化数据（可能由于模态限制）"
        elif category == "clinical":
            return "临床信息不完整"
        else:
            return "相关信息不可用"
    else:
        return "未找到匹配的文献证据"


def _generate_summary(
    run: Dict[str, Any],
    key_findings: List[Dict[str, Any]],
    traceability: Dict[str, Any],
    icv_result: Optional[Dict[str, Any]],
    ekv_result: Optional[Dict[str, Any]],
    consensus_result: Optional[Dict[str, Any]],
) -> str:
    """生成报告摘要"""
    run_id = run.get("run_id", "unknown")
    patient_id = run.get("patient_id", "unknown")
    file_id = run.get("file_id", "unknown")
    
    # 统计关键指标
    total_findings = len(key_findings)
    high_risk_count = sum(1 for f in key_findings if f.get("risk_level") == "high")
    medium_risk_count = sum(1 for f in key_findings if f.get("risk_level") == "medium")
    
    # 可追溯性指标
    coverage = traceability.get("coverage", 0.0)
    threshold_met = traceability.get("threshold_met", False)
    
    summary_lines = [
        f"卒中影像分析汇总报告 (Run ID: {run_id})",
        f"患者: {patient_id}, 病例: {file_id}",
        "",
        f"关键结论总数: {total_findings}",
        f"高风险结论: {high_risk_count}, 中风险结论: {medium_risk_count}",
        f"可追溯覆盖率: {coverage:.1%} {'(达标)' if threshold_met else '(未达标)'}",
        "",
    ]
    
    # 添加模块状态
    if icv_result:
        icv_status = icv_result.get("status", "unknown")
        summary_lines.append(f"ICV 内部一致性验证: {icv_status}")
    
    if ekv_result:
        ekv_status = ekv_result.get("status", "unknown")
        ekv_score = ekv_result.get("score", 0.0)
        summary_lines.append(f"EKV 外部知识验证: {ekv_status} (得分: {ekv_score:.2f})")
    
    if consensus_result:
        consensus_decision = consensus_result.get("decision", "unknown")
        summary_lines.append(f"共识决策: {consensus_decision}")
    
    return "\n".join(summary_lines)


def _determine_overall_risk_level(key_findings: List[Dict[str, Any]]) -> str:
    """确定总体风险等级"""
    risk_counts = {"high": 0, "medium": 0, "low": 0}
    
    for finding in key_findings:
        risk = finding.get("risk_level", "low")
        risk_counts[risk] += 1
    
    if risk_counts["high"] > 0:
        return "high"
    elif risk_counts["medium"] > 0:
        return "medium"
    else:
        return "low"


def _calculate_overall_confidence(key_findings: List[Dict[str, Any]]) -> float:
    """计算总体置信度"""
    if not key_findings:
        return 0.0
    
    total_confidence = 0.0
    count = 0
    
    for finding in key_findings:
        confidence = finding.get("confidence", 0.0)
        if confidence is not None:
            total_confidence += confidence
            count += 1
    
    if count == 0:
        return 0.0
    
    return round(total_confidence / count, 3)


def _collect_citations(
    ekv_result: Optional[Dict[str, Any]],
    icv_result: Optional[Dict[str, Any]],
    consensus_result: Optional[Dict[str, Any]],
) -> List[str]:
    """收集所有引用"""
    citations = []
    
    # 从 EKV 收集引用
    if ekv_result:
        ekv_citations = ekv_result.get("citations", [])
        citations.extend(ekv_citations)
    
    # 从 ICV 收集引用（如果有）
    if icv_result:
        # ICV 通常没有外部引用，但可以添加内部引用
        citations.append("内部一致性验证 (ICV)")
    
    # 从 Consensus 收集引用
    if consensus_result:
        citations.append("共识决策模块")
    
    # 去重
    unique_citations = []
    for citation in citations:
        if citation not in unique_citations:
            unique_citations.append(citation)
    
    return unique_citations


def _collect_uncertainties(
    key_findings: List[Dict[str, Any]],
    evidence_map: Dict[str, Dict[str, Any]],
    icv_result: Optional[Dict[str, Any]],
    ekv_result: Optional[Dict[str, Any]],
    consensus_result: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """收集不确定性"""
    uncertainties = []
    
    # 1. 无证据的关键结论
    for finding_id, mapping in evidence_map.items():
        if not mapping.get("evidence_ids") and mapping.get("unavailable_reason"):
            finding = next((f for f in key_findings if f["id"] == finding_id), None)
            if finding:
                uncertainties.append({
                    "type": "missing_evidence",
                    "finding_id": finding_id,
                    "finding_title": finding.get("title", ""),
                    "reason": mapping["unavailable_reason"],
                    "severity": "medium" if finding.get("requires_evidence") else "low",
                })
    
    # 2. ICV 失败或警告
    if icv_result:
        icv_findings = icv_result.get("findings", [])
        for finding in icv_findings:
            status = finding.get("status", "")
            if status in ["fail", "warn"]:
                uncertainties.append({
                    "type": "icv_issue",
                    "finding_id": finding.get("id", ""),
                    "message": finding.get("message", ""),
                    "severity": finding.get("severity", "medium"),
                    "suggested_action": finding.get("suggested_action", "请复核"),
                })
    
    # 3. EKV 不支持或部分支持的结论
    if ekv_result:
        ekv_claims = ekv_result.get("claims", [])
        for claim in ekv_claims:
            verdict = claim.get("verdict", "")
            if verdict in ["not_supported", "partially_supported"]:
                uncertainties.append({
                    "type": "ekv_verdict",
                    "claim_id": claim.get("claim_id", ""),
                    "verdict": verdict,
                    "message": claim.get("message", ""),
                    "severity": "high" if verdict == "not_supported" else "medium",
                })
    
    # 4. Consensus 冲突
    if consensus_result:
        conflict_count = consensus_result.get("conflict_count", 0)
        if conflict_count > 0:
            uncertainties.append({
                "type": "consensus_conflict",
                "conflict_count": conflict_count,
                "message": f"ICV 与 EKV 之间存在 {conflict_count} 处冲突",
                "severity": "medium",
                "suggested_action": "建议人工复核冲突项",
            })
    
    return uncertainties


def _determine_next_actions(
    key_findings: List[Dict[str, Any]],
    traceability: Dict[str, Any],
    uncertainties: List[Dict[str, Any]],
) -> List[str]:
    """确定下一步行动"""
    next_actions = []
    
    # 1. 可追溯性未达标
    if not traceability.get("threshold_met", False):
        coverage = traceability.get("coverage", 0.0)
        next_actions.append(f"可追溯覆盖率 ({coverage:.1%}) 未达 90% 阈值，建议补充证据")
    
    # 2. 高风险结论
    high_risk_findings = [f for f in key_findings if f.get("risk_level") == "high"]
    if high_risk_findings:
        next_actions.append(f"发现 {len(high_risk_findings)} 项高风险结论，建议优先复核")
    
    # 3. 无证据的关键结论
    unmapped_ids = traceability.get("unmapped_ids", [])
    if unmapped_ids:
        next_actions.append(f"{len(unmapped_ids)} 项关键结论缺乏证据支持，建议补充")
    
    # 4. 不确定性处理
    high_severity_uncertainties = [u for u in uncertainties if u.get("severity") == "high"]
    if high_severity_uncertainties:
        next_actions.append(f"发现 {len(high_severity_uncertainties)} 项高严重性不确定项，需紧急处理")
    
    # 5. 默认行动
    if not next_actions:
        next_actions.append("所有关键结论均有证据支持，可进入下一阶段")
    
    return next_actions


# ==================== 集成函数 ====================

def integrate_summary_into_run(run: Dict[str, Any]) -> Dict[str, Any]:
    """
    将汇总结果集成到 Run 对象中
    
    Args:
        run: Agent Run 对象
        
    Returns:
        更新后的 Run 对象
    """
    try:
        # 构建最终报告
        summary_result = build_final_report(run)
        
        # 更新 run.result
        run_result = run.get("result") or {}
        run_result.update({
            "final_report": summary_result["final_report"],
            "evidence_items": summary_result["evidence_items"],
            "evidence_map": summary_result["evidence_map"],
            "trace": summary_result["trace"],
        })
        
        # 保持向后兼容：不删除已有的 report_result
        if "report_result" not in run_result:
            run_result["report_result"] = run.get("result", {}).get("report_result") or {}
        
        # 更新 run 对象
        run["result"] = run_result
        
        print(f"[SUMMARY] 汇总结果已集成到 run_id={run.get('run_id')}")
        return run
        
    except Exception as e:
        print(f"[SUMMARY] 集成汇总结果失败: {e}")
        import traceback
        traceback.print_exc()
        return run