import torch
import json
import base64
import time
import copy
import re
import html
import glob
import threading
import shutil
from .ai_inference import get_ai_model
import os
import requests  # 添加 requests 导入，用于调用百川 M3 API
from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    send_file,
    send_from_directory,
    Response,
    stream_with_context,
)
from extensions import NumpyJSONEncoder
from datetime import datetime
from dotenv import load_dotenv

# ==================== Supabase 客户端内联初始化 ====================
try:
    from supabase import create_client, Client

    SUPABASE_URL = "https://ppyexzqdbsnwqfyugfvc.supabase.co"
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBweWV4enFkYnNud3FmeXVnZnZjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njc1Nzc3ODAsImV4cCI6MjA4MzE1Mzc4MH0.EjDH3eufPKBF8MJiHM6SVzPQlsWvGqhLQPKKhVG5Ffo"
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    SUPABASE_AVAILABLE = True
    print("✓ Supabase 客户端初始化成功")
except ImportError as e:
    print(f"✗ Supabase 导入失败: {e}")
    supabase = None
    SUPABASE_AVAILABLE = False
except Exception as e:
    print(f"✗ Supabase 初始化失败: {e}")
    supabase = None
    SUPABASE_AVAILABLE = False


# ==================== 封装 Supabase 数据库操作函数 ====================
def insert_patient_info(patient_data: dict):
    """
    插入患者信息到 Supabase 的 patient_info 表
    """
    if not SUPABASE_AVAILABLE:
        return (False, "Supabase 不可用")
    try:
        if "create_time" in patient_data:
            del patient_data["create_time"]
        response = supabase.table("patient_info").insert([patient_data]).execute()
        if response.data and len(response.data) > 0:
            return (True, response.data[0])
        else:
            return (False, "写入失败：Supabase 返回空数据")
    except Exception as e:
        return (False, f"写入失败：{str(e)}")


def update_analysis_result(patient_id: int, analysis_data: dict):
    """
    更新患者的分析结果到 patient_info 表
    """
    if not SUPABASE_AVAILABLE:
        return (False, "Supabase 不可用")
    try:
        update_data = {
            "core_infarct_volume": analysis_data.get("core_infarct_volume"),
            "penumbra_volume": analysis_data.get("penumbra_volume"),
            "mismatch_ratio": analysis_data.get("mismatch_ratio"),
            "hemisphere": analysis_data.get("hemisphere"),
            "analysis_status": analysis_data.get("analysis_status", "completed"),
        }
        response = (
            supabase.table("patient_info")
            .update(update_data)
            .eq("id", patient_id)
            .execute()
        )
        if response.data and len(response.data) > 0:
            return (True, response.data[0])
        else:
            return (False, "更新失败：Supabase 返回空数据")
    except Exception as e:
        return (False, f"更新失败：{str(e)}")


def get_patient_by_id(patient_id: int):
    """
    根据 ID 获取患者信息
    """
    if not SUPABASE_AVAILABLE:
        return None
    try:
        response = (
            supabase.table("patient_info").select("*").eq("id", patient_id).execute()
        )
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        print(f"获取患者信息失败: {e}")
        return None


def get_imaging_by_case(patient_id: int, case_id: str):
    """
    æ ¹æ® case_id å’Œ patient_id æŸ¥è¯¢ patient_imaging è®°å½•
    """
    if not SUPABASE_AVAILABLE:
        return None
    try:
        query = supabase.table("patient_imaging").select("*").eq("case_id", case_id)
        if patient_id:
            query = query.eq("patient_id", patient_id)
        response = query.execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        print(f"patient_imaging æŸ¥è¯¢å¤±è´¥: {e}")
        return None


def append_modalities_to_imaging(
    patient_id: int, case_id: str, new_items, hemisphere="both"
):
    """
    Upsert uploaded modalities into patient_imaging.available_modalities (text[])
    using (patient_id, case_id) as the record key.
    Returns (True, data) or (False, error).
    """
    if not SUPABASE_AVAILABLE:
        return (False, "Supabase unavailable")

    items_to_add = new_items if isinstance(new_items, list) else [new_items]
    if not all(isinstance(x, str) for x in items_to_add):
        return (False, "All modality items must be strings")
    if not case_id or not isinstance(case_id, str):
        return (False, f"Invalid case_id: {case_id}")

    alias = {"mcat": "mcta", "vcat": "vcta"}
    normalized_items = []
    for item in items_to_add:
        key = str(item).strip().lower()
        if not key:
            continue
        key = alias.get(key, key)
        if key not in normalized_items:
            normalized_items.append(key)

    if not normalized_items:
        return (False, "No valid modality items")

    try:
        query = (
            supabase.table("patient_imaging")
            .select("id, available_modalities")
            .eq("case_id", case_id)
        )
        if patient_id:
            query = query.eq("patient_id", patient_id)
        sel = query.execute()

        if sel.data and len(sel.data) > 0:
            current_modalities = sel.data[0].get("available_modalities") or []
            normalized_current = []
            for mod in current_modalities:
                mod_key = alias.get(str(mod).strip().lower(), str(mod).strip().lower())
                if mod_key and mod_key not in normalized_current:
                    normalized_current.append(mod_key)

            combined = normalized_current.copy()
            for item in normalized_items:
                if item not in combined:
                    combined.append(item)

            update_data = {"available_modalities": combined}
            if hemisphere:
                update_data["hemisphere"] = hemisphere

            upd = (
                supabase.table("patient_imaging")
                .update(update_data)
                .eq("case_id", case_id)
            )
            if patient_id:
                upd = upd.eq("patient_id", patient_id)
            upd.execute()
        else:
            payload = {
                "patient_id": patient_id,
                "case_id": case_id,
                "available_modalities": normalized_items,
                "hemisphere": hemisphere,
            }
            supabase.table("patient_imaging").insert([payload]).execute()

        verify = (
            supabase.table("patient_imaging")
            .select("id, available_modalities, hemisphere")
            .eq("case_id", case_id)
        )
        if patient_id:
            verify = verify.eq("patient_id", patient_id)
        verify_resp = verify.execute()
        if verify_resp.data and len(verify_resp.data) > 0:
            print(
                f"patient_imaging modalities readback: "
                f"case_id={case_id}, patient_id={patient_id}, "
                f"modalities={verify_resp.data[0].get('available_modalities')}"
            )
            return (True, verify_resp.data[0])

        return (True, {"available_modalities": normalized_items})
    except Exception as e:
        return (False, f"Operation failed: {str(e)}")


def _is_missing_column_error(exc: Exception, column_name: str) -> bool:
    text = str(exc or "")
    token = text.lower()
    col = str(column_name or "").lower()
    return ("pgrst204" in token and col in token) or (
        "could not find" in token and col in token and "schema cache" in token
    )


def _build_report_notes_text(payload: dict) -> str:
    patient = (
        payload.get("patient", {}) if isinstance(payload.get("patient"), dict) else {}
    )
    findings = (
        payload.get("findings", {}) if isinstance(payload.get("findings"), dict) else {}
    )
    notes = payload.get("notes", "")
    return (
        f"患者信息：{patient.get('patient_name', '')}\n"
        f"核心梗死：{findings.get('core', '')}\n"
        f"半暗带：{findings.get('penumbra', '')}\n"
        f"血管评估：{findings.get('vessel', '')}\n"
        f"灌注分析：{findings.get('perfusion', '')}\n"
        f"医生备注：{notes}\n"
    )


def _strip_html_to_text(raw_html: str) -> str:
    if not raw_html:
        return ""
    text = str(raw_html)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</p>", "\n", text)
    text = re.sub(r"(?i)</li>", "\n", text)
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = html.unescape(text)
    lines = []
    for line in text.splitlines():
        normalized = re.sub(r"\s+", " ", line).strip()
        if normalized:
            lines.append(normalized)
    return "\n".join(lines)


def _medgemma_results_dir() -> str:
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(project_root, "MedGemma_Model", "results")


def _sync_notes_to_result_json(
    file_id: str, patient_id: int, notes_html: str, saved_at: str
):
    sync_result = {
        "matched_files": [],
        "updated_files": [],
        "failed_files": [],
    }
    results_dir = _medgemma_results_dir()
    if not os.path.isdir(results_dir):
        return sync_result

    pattern = os.path.join(results_dir, f"medgemma_report_{file_id}_*.json")
    matched_files = sorted(glob.glob(pattern))
    sync_result["matched_files"] = matched_files
    if not matched_files:
        return sync_result

    notes_payload = {
        "html": str(notes_html or ""),
        "text": _strip_html_to_text(notes_html or ""),
        "saved_at": str(saved_at or ""),
        "patient_id": patient_id,
        "file_id": file_id,
    }

    for path in matched_files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            if not isinstance(payload, dict):
                raise ValueError("report json root is not object")

            payload["doctor_notes"] = notes_payload
            report_payload = payload.get("report_payload")
            if not isinstance(report_payload, dict):
                report_payload = {}
            report_payload["doctor_notes"] = notes_payload
            payload["report_payload"] = report_payload

            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            sync_result["updated_files"].append(path)
        except Exception as e:
            sync_result["failed_files"].append({"path": path, "error": str(e)})

    return sync_result


def save_report_notes(patient_id: int, file_id: str, payload: dict):
    """
    Save report notes by case.
    Primary target: patient_imaging.notes
    Compatibility target: patient_info.uncertainty_remark (best-effort)
    """
    result = {
        "success": False,
        "error": None,
        "warnings": [],
        "saved_targets": {
            "patient_imaging_notes": False,
            "patient_info_uncertainty_remark": False,
        },
        "json_sync": {
            "matched_files": [],
            "updated_files": [],
            "failed_files": [],
        },
        "data": None,
    }

    if not SUPABASE_AVAILABLE:
        result["error"] = "Supabase unavailable"
        return result

    notes_text = str(payload.get("notes", "") or "")
    saved_at = str(payload.get("saved_at") or (datetime.utcnow().isoformat() + "Z"))
    report_notes = _build_report_notes_text(payload)

    # Primary path: save case notes in patient_imaging
    try:
        update_query = (
            supabase.table("patient_imaging")
            .update({"notes": notes_text})
            .eq("case_id", file_id)
        )
        if patient_id:
            update_query = update_query.eq("patient_id", patient_id)
        update_resp = update_query.execute()

        if update_resp.data and len(update_resp.data) > 0:
            result["saved_targets"]["patient_imaging_notes"] = True
            result["data"] = update_resp.data[0]
        else:
            insert_payload = {
                "patient_id": patient_id,
                "case_id": file_id,
                "notes": notes_text,
            }
            insert_resp = (
                supabase.table("patient_imaging").insert([insert_payload]).execute()
            )
            if insert_resp.data and len(insert_resp.data) > 0:
                result["saved_targets"]["patient_imaging_notes"] = True
                result["data"] = insert_resp.data[0]
            else:
                result["error"] = "save patient_imaging.notes failed: empty response"
                return result

        print(
            f"[Report Save] notes_saved_target=patient_imaging patient_id={patient_id} case_id={file_id}"
        )
    except Exception as e:
        result["error"] = f"save patient_imaging.notes failed: {e}"
        return result

    # Compatibility path: patient_info.uncertainty_remark
    try:
        compat_resp = (
            supabase.table("patient_info")
            .update({"uncertainty_remark": report_notes})
            .eq("id", patient_id)
            .execute()
        )
        # No exception => treat as compatible success (row may be empty if id not found).
        result["saved_targets"]["patient_info_uncertainty_remark"] = True
        if not compat_resp.data:
            result["warnings"].append(
                "patient_info row not found, skipped uncertainty_remark update"
            )
    except Exception as e:
        if _is_missing_column_error(e, "uncertainty_remark"):
            result["warnings"].append(
                "patient_info.uncertainty_remark missing, skipped compatibility update"
            )
            print(
                "[Report Save] patient_info_uncertainty_remark_skipped_missing_column=true"
            )
        else:
            result["warnings"].append(f"patient_info compatibility update failed: {e}")
            print(f"[Report Save] patient_info compatibility update failed: {e}")

    try:
        json_sync = _sync_notes_to_result_json(
            file_id, patient_id, notes_text, saved_at
        )
        result["json_sync"] = json_sync
        if json_sync.get("failed_files"):
            result["warnings"].append(
                f"report json sync partially failed ({len(json_sync['failed_files'])}/{len(json_sync['matched_files'])})"
            )
        print(
            f"[Report Save] json_sync matched={len(json_sync.get('matched_files', []))} "
            f"updated={len(json_sync.get('updated_files', []))} "
            f"failed={len(json_sync.get('failed_files', []))}"
        )
    except Exception as e:
        result["warnings"].append(f"report json sync failed: {e}")
        print(f"[Report Save] report json sync failed: {e}")

    result["success"] = True
    return result


# ==================== 百川 M3 API 配置 ====================


# ==================== 百川 M3 API 配置 ====================
# 首先尝试从 .env 文件加载环境变量
        
load_dotenv()

# 然后读取环境变量（已从.env加载或系统环境变量）
BAICHUAN_API_URL = os.environ.get(
    "BAICHUAN_API_URL", "https://api.baichuan-ai.com/v1/chat/completions"
)
BAICHUAN_API_KEY = os.environ.get("BAICHUAN_API_KEY", "") or os.environ.get(
    "BAICHUAN_AK", ""
)
BAICHUAN_MODEL = (
    os.environ.get("BAICHUAN_MODEL", "Baichuan-M3") or "Baichuan-M3"
).strip()
BAICHUAN_CHAT_MODEL = (
    os.environ.get("BAICHUAN_CHAT_MODEL", "").strip() or BAICHUAN_MODEL
)
_kb_ids_raw = os.environ.get("BAICHUAN_KB_IDS", "kb-mMSWx8f9GMasTj0gR52k2rdr")
BAICHUAN_KB_IDS = [kb_id.strip() for kb_id in _kb_ids_raw.split(",") if kb_id.strip()]
# 修正路径：__file__ 在 backend/ 下，需要向上一级到项目根目录
KB_PDF_DIR = os.environ.get(
    "KB_PDF_DIR",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "kb"),
)
KB_PDF_URL_PREFIX = "/kb-pdfs"


def _get_baichuan_api_base() -> str:
    env_base = os.environ.get("BAICHUAN_API_BASE")
    if env_base:
        return env_base.rstrip("/")
    if "/v1/" in BAICHUAN_API_URL:
        return BAICHUAN_API_URL.split("/v1/")[0] + "/v1"
    return "https://api.baichuan-ai.com/v1"


print(f"百川 API URL: {BAICHUAN_API_URL}")
print(
    f"百川 API Key: {'***' + BAICHUAN_API_KEY[-4:] if BAICHUAN_API_KEY else '未配置'}"
)
print(f"百川模型: {BAICHUAN_MODEL}")
print(f"百川问诊模型: {BAICHUAN_CHAT_MODEL}")
print(f"知识库ID数量: {len(BAICHUAN_KB_IDS)}")
print(f"知识库PDF目录: {KB_PDF_DIR}")

# 卒中影像报告 Prompt 模板 (Markdown 格式)
REPORT_PROMPT_TEMPLATE = """
你是一位专业的神经放射科医生。AI 系统基于患者 NCCT + 动脉期 CTA + 静脉期 CTA + 延迟期 CTA（4 通道 mCTA）影像，通过 MRDPM 扩散模型生成 CBF/CBV/Tmax 灌注参数图，请综合分析这 4 类影像的灌注特征，生成符合卒中诊疗规范的影像诊断报告。

【患者临床与影像数据】
- 患者ID: {patient_id}
- 姓名: {patient_name}
- 年龄: {patient_age}
- 性别: {patient_sex}
- 入院 NIHSS 评分: {nihss_score}
- 发病至入院时间: {onset_to_admission}
- 基于 NCCT + 动脉期/静脉期/延迟期 mCTA 生成的灌注参数：
  • 核心梗死体积 (Core): {core_volume} ml
  • 半暗带体积 (Penumbra): {penumbra_volume} ml
  • 不匹配比值 (Mismatch Ratio): {mismatch_ratio}
  • 发病侧: {hemisphere}

【重要提示 - 必须严格遵守】
在诊断意见中，你必须逐一分析以下三个临床数据：
1. NIHSS评分分析：入院 NIHSS 评分为 {nihss_score}，请详细分析该评分对应的神经功能缺损严重程度（如轻度、中度、重度）
2. 年龄分析：患者年龄 {patient_age} 岁，请分析年龄对治疗决策的影响
3. 发病时间分析：发病至入院时间为 {onset_to_admission}，请评估是否在治疗时间窗内

【报告要求】
1. 符合《中国急性缺血性脑卒中诊治指南》规范
2. 各章节需详尽描述
3. 使用医学专业术语
4. 输出格式为 Markdown
5. 小标题使用 "##" 前缀标记，如 "## 检查方法"
6. 不要使用粗体标记（**文字**），直接使用普通文字描述

【输出格式】

· 检查方法
头颅 CT 平扫 (NCCT) + 三期 CT 血管成像 (mCTA：动脉期、静脉期、延迟期)

· 影像学表现
基于 NCCT + 动脉期/静脉期/延迟期 mCTA 综合分析：
1. 核心梗死区：[结合 CBF/CBV/Tmax 参数，根据 DEFUSE 3 标准（rCBF<30%、Tmax>6s）详细描述位置、体积、灌注异常情况]
2. 半暗带区：[详细描述范围、与核心梗死区的空间关系、Tmax 延迟程度]
3. 左右脑不对称分析：[比较患侧与健侧的 CBF/CBV 差异，量化不对称指数]
4. 不匹配评估：[不匹配比值及临床意义]

· 血管评估
[根据三期 CTA 的动脉-静脉显影差异，推断责任血管及侧支循环情况]

· 诊断意见
[必须包含以下内容，逐条分析：
1. NIHSS评分分析：入院 NIHSS 评分为 {nihss_score}，请详细分析该评分对应的神经功能缺损严重程度
2. 年龄分析：患者年龄 {patient_age} 岁，请分析年龄对治疗决策的影响
3. 发病时间分析：发病至入院时间为 {onset_to_admission}，请评估是否在治疗时间窗内
4. 急性缺血性卒中诊断
5. 核心梗死体积及位置（基于 rCBF<30% 阈值）
6. 半暗带体积及可挽救脑组织评估（基于 Tmax>6s 阈值）
7. 不匹配比值及 DEFUSE 3 入选标准判断
8. 建议进一步行血管内治疗评估]

· 治疗建议
推荐完善数字减影血管造影 (DSA) 以明确血管闭塞部位及侧支循环情况。综合 NIHSS 评分、患者年龄及发病至入院时间以及核心梗死/半暗带体积比值，判断血管内治疗指征。若符合 DEFUSE 3 标准，建议积极行血管内治疗。

请根据以上患者数据生成报告：
"""

# JSON 结构化输出 Prompt
REPORT_JSON_PROMPT = """
你是一位专业的神经放射科医生。AI 系统基于患者 NCCT + 动脉期 CTA + 静脉期 CTA + 延迟期 CTA（4 通道 mCTA）影像，通过 MRDPM 扩散模型生成 CBF/CBV/Tmax 灌注参数图，请综合分析生成规范的卒中影像诊断报告 JSON。

【患者影像数据】
- 患者ID: {patient_id}
- 基于 NCCT + 动脉期/静脉期/延迟期 mCTA 生成的灌注参数：
  • 核心梗死体积 (Core): {core_volume} ml
  • 半暗带体积 (Penumbra): {penumbra_volume} ml
  • 不匹配比值 (Mismatch Ratio): {mismatch_ratio}
  • 发病侧: {hemisphere}

【临床诊断标准】
- 核心梗死：rCBF < 30%（相对脑血流量）
- 半暗带：Tmax > 6 秒
- DEFUSE 3 标准：不匹配体积 ≥ 15ml 且不匹配比值 ≥ 1.8

【输出要求】
请严格按照以下 JSON 格式输出，**不要包含任何其他文字或代码块标记**：

{{"检查方法": "头颅CT平扫(NCCT)+三期CTA(mCTA:动脉期、静脉期、延迟期)", "核心梗死": {{"体积": "核心梗死体积ml", "位置": "具体脑叶和血管供血区", "CT表现": "NCCT低密度改变情况", "灌注标准": "rCBF<30%"}}, "半暗带": {{"体积": "半暗带体积ml", "位置": "缺血半暗带分布区域", "灌注特征": "Tmax>6s, CBF降低但CBV相对保留", "与核心关系": "空间关系描述"}}, "左右脑不对称分析": {{"患侧": "患侧灌注参数", "健侧": "健侧灌注参数", "不对称指数": "量化值"}}, "血管评估": "根据三期CTA推断责任血管和侧支循环情况", "DEFUSE3评估": {{"不匹配体积": "体积ml", "不匹配比值": "比值", "是否入选": "是/否"}}, "诊断意见": "综合诊断意见", "治疗建议": ["建议1", "建议2", "建议3"]}}

请只输出 JSON 对象，确保所有字符串使用双引号包裹。
"""


def generate_report_with_baichuan(
    structured_data: dict, output_format: str = "markdown"
) -> dict:
    """
    调用百川 M3 API 生成卒中影像报告
    """
    try:
        # 准备 NIHSS 评分显示
        nihss_score = structured_data.get("admission_nihss", None)
        nihss_display = f"{nihss_score} 分" if nihss_score is not None else "未记录"

        # 准备患者信息显示
        patient_id = structured_data.get("id", structured_data.get("ID", "未知"))
        patient_name = structured_data.get("patient_name", "未知")
        patient_age = structured_data.get("patient_age", "未知")
        patient_sex = structured_data.get("patient_sex", "未知")
        onset_to_admission = structured_data.get("onset_to_admission_hours", None)
        onset_display = (
            f"{onset_to_admission} 小时" if onset_to_admission is not None else "未记录"
        )

        # 准备 Prompt
        if output_format == "json":
            prompt = REPORT_JSON_PROMPT.format(
                patient_id=patient_id,
                core_volume=structured_data.get("core_infarct_volume", "N/A"),
                penumbra_volume=structured_data.get("penumbra_volume", "N/A"),
                mismatch_ratio=structured_data.get("mismatch_ratio", "N/A"),
                hemisphere=structured_data.get("hemisphere", "双侧"),
            )
        else:
            from datetime import datetime

            prompt = REPORT_PROMPT_TEMPLATE.format(
                patient_id=patient_id,
                patient_name=patient_name,
                patient_age=patient_age,
                patient_sex=patient_sex,
                nihss_score=nihss_display,
                onset_to_admission=onset_display,
                core_volume=structured_data.get("core_infarct_volume", "N/A"),
                penumbra_volume=structured_data.get("penumbra_volume", "N/A"),
                mismatch_ratio=structured_data.get("mismatch_ratio", "N/A"),
                hemisphere=structured_data.get("hemisphere", "双侧"),
            )

        # 检查 API Key
        if not BAICHUAN_API_KEY:
            print("⚠ 百川 API Key 未配置，返回模拟报告")
            mock_report = generate_mock_report(structured_data, output_format)
            return {
                "success": True,
                "report": mock_report,
                "format": output_format,
                "is_mock": True,
                "warning": "使用模拟报告，请配置 BAICHUAN_API_KEY 环境变量",
            }

        # 调用百川 M3 API
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {BAICHUAN_API_KEY}",
        }

        payload = {
            "model": BAICHUAN_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": "你是一位专业的神经放射科医生，擅长撰写规范的卒中影像诊断报告。",
                },
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 4096,
            "temperature": 0.3,
            "top_p": 0.9,
        }

        print(f"调用百川 M3 API... format={output_format}")
        print(f"Payload: {json.dumps(payload, ensure_ascii=False)[:500]}...")
        response = requests.post(
            BAICHUAN_API_URL, headers=headers, json=payload, timeout=60
        )

        print(f"响应状态码: {response.status_code}")
        print(f"响应内容: {response.text[:1000]}...")

        if response.status_code == 200:
            result = response.json()

            # 百川 M3 API 可能有多种响应格式，尝试多种解析方式
            report_content = ""

            # 方式1: OpenAI 格式 (choices[0].message.content)
            if "choices" in result and len(result["choices"]) > 0:
                choice = result["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    report_content = choice["message"]["content"]
                elif "text" in choice:
                    report_content = choice["text"]

            # 方式2: 直接 content 字段
            if not report_content and "content" in result:
                report_content = result["content"]

            # 方式3: data 字段
            if not report_content and "data" in result:
                data = result["data"]
                if "content" in data:
                    report_content = data["content"]

            print(f"✓ 百川 M3 API 调用成功，报告长度: {len(report_content)}")
            return {
                "success": True,
                "report": report_content,
                "format": output_format,
                "is_mock": False,
            }
        else:
            error_msg = f"API 调用失败: {response.status_code} - {response.text}"
            print(f"✗ {error_msg}")
            return {"success": False, "error": error_msg, "format": output_format}

    except requests.exceptions.Timeout:
        error_msg = "百川 M3 API 调用超时"
        print(f"✗ {error_msg}")
        return {"success": False, "error": error_msg, "format": output_format}
    except Exception as e:
        error_msg = f"生成报告失败: {str(e)}"
        print(f"✗ {error_msg}")
        import traceback

        traceback.print_exc()
        return {"success": False, "error": error_msg, "format": output_format}


def generate_mock_report(structured_data: dict, output_format: str = "markdown") -> str:
    """生成模拟报告（当 API Key 未配置时使用）"""
    patient_id = structured_data.get("id", structured_data.get("ID", "未知"))
    core_volume = structured_data.get("core_infarct_volume", 0)
    penumbra_volume = structured_data.get("penumbra_volume", 0)
    mismatch_ratio = structured_data.get("mismatch_ratio", 0)
    hemisphere = structured_data.get("hemisphere", "双侧")

    mock_report = f"""影像诊断报告

患者ID: {patient_id}

· 检查方法
头颅 CT 平扫 (NCCT) + 三期 CT 血管成像 (mCTA：动脉期、静脉期、延迟期)

· 影像学表现
基于 NCCT + 动脉期/静脉期/延迟期 mCTA 综合分析：
1. 核心梗死区：根据 rCBF<30% 确定，体积约 {core_volume} ml，位于 {hemisphere} 大脑半球
2. 半暗带区：根据 Tmax>6s 确定，体积约 {penumbra_volume} ml
3. 左右脑不对称分析：患侧与健侧 CBF/CBV 差异显著
4. 不匹配评估：不匹配比值约 {mismatch_ratio}

· 诊断意见
{hemisphere} 大脑半球急性缺血性改变，核心梗死体积约 {core_volume} ml，半暗带体积约 {penumbra_volume} ml，不匹配比值约 {mismatch_ratio}

· 治疗建议
1. 建议行血管内介入治疗评估
2. 尽快完善头颈 CTA 检查评估血管情况
3. 监测生命体征，维持血压稳定"""

    if output_format == "json":
        import json

        return json.dumps(
            {
                "ID": patient_id,
                "检查方法": "头颅CT平扫(NCCT)+三期CTA(mCTA:动脉期、静脉期、延迟期)",
                "核心梗死": {
                    "体积": f"{core_volume} ml",
                    "位置": f"{hemisphere}大脑半球",
                    "CT表现": "NCCT未见明显低密度灶",
                    "灌注标准": "rCBF<30%",
                },
                "半暗带": {
                    "体积": f"{penumbra_volume} ml",
                    "位置": f"{hemisphere}大脑半球",
                    "灌注特征": "Tmax>6s, CBF降低但CBV相对保留",
                    "与核心关系": "相邻区域",
                },
                "左右脑不对称分析": {
                    "患侧": "CBF/CBV降低",
                    "健侧": "正常范围",
                    "不对称指数": "显著",
                },
                "血管评估": "根据三期CTA推断责任血管",
                "DEFUSE3评估": {
                    "不匹配体积": f"{penumbra_volume} ml",
                    "不匹配比值": f"{mismatch_ratio}",
                    "是否入选": "是"
                    if penumbra_volume >= 15 and mismatch_ratio >= 1.8
                    else "否",
                },
                "诊断意见": f"{hemisphere}大脑半球急性缺血性改变，核心梗死体积约 {core_volume} ml，半暗带体积约 {penumbra_volume} ml",
                "治疗建议": "建议行血管内介入治疗评估",
            },
            ensure_ascii=False,
            indent=2,
        )

    return mock_report


import os
import numpy as np
from PIL import Image
import uuid
import traceback
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import colorsys
import matplotlib as mpl

# 在app.py的导入部分添加
from stroke_analysis import analyze_stroke_case
from medgemma_report import generate_report_with_medgemma

# 尝试导入 nibabel
try:
    import nibabel as nib

    NIBABEL_AVAILABLE = True
    print("✓ nibabel 导入成功")
except ImportError as e:
    print(f"✗ nibabel 导入失败: {e}")
    NIBABEL_AVAILABLE = False

app = Flask(__name__, static_folder="../static")
app.config["SECRET_KEY"] = "your-secret-key-here"
app.config["UPLOAD_FOLDER"] = "static/uploads"
app.config["PROCESSED_FOLDER"] = "static/processed"
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024
app.config["TEMPLATES_AUTO_RELOAD"] = True  # 禁用HTML缓存，修改立即生效
app.jinja_env.auto_reload = True

# 核心：配置NumpyJSONEncoder用于JSON序列化
app.json_encoder = NumpyJSONEncoder


# 创建必要的目录
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["PROCESSED_FOLDER"], exist_ok=True)

print(f"上传目录: {app.config['UPLOAD_FOLDER']}")
print(f"处理目录: {app.config['PROCESSED_FOLDER']}")

# ==================== Upload Job Center (for /processing) ====================
UPLOAD_JOB_STEP_DEFS = [
    {"key": "archive_ready", "title": "建立患者档案"},
    {"key": "modality_detect", "title": "识别上传模态"},
    {"key": "ctp_generate", "title": "生成CTP灌注图"},
    {"key": "stroke_analysis", "title": "脑卒中自动分析"},
    {"key": "pseudocolor", "title": "生成伪彩图"},
    {"key": "ai_report", "title": "生成AI影像报告"},
]

UPLOAD_JOBS = {}
UPLOAD_JOBS_LOCK = threading.Lock()


def _job_now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _safe_job_copy(job):
    return copy.deepcopy(job) if job else None


def _calc_job_progress(job):
    steps = job.get("steps", [])
    if not steps:
        return 0
    done = sum(
        1 for step in steps if step.get("status") in ("completed", "skipped", "failed")
    )
    running = any(step.get("status") == "running" for step in steps)
    progress = int((done / len(steps)) * 100)
    if running and progress < 99:
        progress = min(99, progress + 8)
    if job.get("status") == "completed":
        progress = 100
    if job.get("status") == "failed":
        progress = min(progress, 99)
    return max(0, min(100, progress))


def _create_upload_job(job_id, patient_id, file_id, modalities):
    steps = []
    for spec in UPLOAD_JOB_STEP_DEFS:
        steps.append(
            {
                "key": spec["key"],
                "title": spec["title"],
                "status": "pending",
                "message": "",
                "started_at": None,
                "ended_at": None,
            }
        )

    job = {
        "job_id": job_id,
        "status": "queued",
        "progress": 0,
        "current_step": None,
        "steps": steps,
        "file_id": file_id,
        "patient_id": patient_id,
        "modalities": modalities or [],
        "result": None,
        "error": None,
        "warnings": [],
        "created_at": _job_now(),
        "updated_at": _job_now(),
    }
    with UPLOAD_JOBS_LOCK:
        UPLOAD_JOBS[job_id] = job
    return _safe_job_copy(job)


def _update_upload_job(job_id, updater):
    with UPLOAD_JOBS_LOCK:
        job = UPLOAD_JOBS.get(job_id)
        if not job:
            return None
        updater(job)
        job["progress"] = _calc_job_progress(job)
        job["updated_at"] = _job_now()
        return _safe_job_copy(job)


def _set_job_status(job_id, status, error=None):
    def _mut(job):
        job["status"] = status
        if error:
            job["error"] = error

    return _update_upload_job(job_id, _mut)


def _update_step(job_id, step_key, status, message=""):
    def _mut(job):
        for step in job["steps"]:
            if step["key"] != step_key:
                continue
            step["status"] = status
            if message:
                step["message"] = message
            now = _job_now()
            if status == "running":
                step["started_at"] = step["started_at"] or now
                step["ended_at"] = None
                job["current_step"] = step_key
            elif status in ("completed", "failed", "skipped"):
                step["started_at"] = step["started_at"] or now
                step["ended_at"] = now
                if job.get("current_step") == step_key:
                    job["current_step"] = None
            break

    return _update_upload_job(job_id, _mut)


def _add_job_warning(job_id, warning):
    def _mut(job):
        if warning and warning not in job["warnings"]:
            job["warnings"].append(warning)

    return _update_upload_job(job_id, _mut)


def _get_upload_job(job_id):
    with UPLOAD_JOBS_LOCK:
        return _safe_job_copy(UPLOAD_JOBS.get(job_id))


def _normalize_uploaded_modalities(modalities):
    alias = {"mcat": "mcta", "vcat": "vcta"}
    normalized = []
    for item in modalities or []:
        key = alias.get(str(item).strip().lower(), str(item).strip().lower())
        if key and key not in normalized:
            normalized.append(key)
    return normalized


def _is_mcta_combo(modalities):
    mod_set = set(_normalize_uploaded_modalities(modalities))
    return all(k in mod_set for k in ("ncct", "mcta", "vcta", "dcta"))


def _has_real_ctp(modalities):
    mod_set = set(_normalize_uploaded_modalities(modalities))
    return all(k in mod_set for k in ("cbf", "cbv", "tmax"))


def _result_has_ctp_images(upload_result):
    rgb_files = (upload_result or {}).get("rgb_files") or []
    if not rgb_files:
        return False
    first_slice = rgb_files[0] or {}
    return bool(
        first_slice.get("cbf_image")
        or first_slice.get("cbv_image")
        or first_slice.get("tmax_image")
    )


def _invoke_internal_upload(payload):
    import contextlib

    form = {
        "patient_id": str(payload["patient_id"]),
        "file_id": payload["file_id"],
        "hemisphere": payload.get("hemisphere", "both"),
        "model_type": payload.get("model_type", "mrdpm"),
        "upload_mode": payload.get("upload_mode", "ncct"),
        "defer_stroke_analysis": "true",
    }
    if payload.get("cta_phase"):
        form["cta_phase"] = payload["cta_phase"]
    if payload.get("skip_ai"):
        form["skip_ai"] = "true"

    with app.test_client() as client:
        with contextlib.ExitStack() as stack:
            for field_name, file_info in payload.get("files", {}).items():
                fp = stack.enter_context(open(file_info["path"], "rb"))
                form[field_name] = (fp, file_info["filename"])

            resp = client.post("/upload", data=form, content_type="multipart/form-data")
            result = resp.get_json(silent=True) or {}
            if resp.status_code != 200:
                return False, f"内部上传接口返回 {resp.status_code}", result
            if not result.get("success"):
                return False, result.get("error", "上传处理失败"), result
            return True, "ok", result


def _invoke_internal_generate_report(patient_id, file_id):
    with app.test_client() as client:
        url = f"/api/generate_report/{patient_id}?format=markdown&file_id={file_id}&source=processing_page"
        resp = client.get(url)
        data = resp.get_json(silent=True) or {}
        if resp.status_code != 200:
            return False, f"报告接口返回 {resp.status_code}", data
        if data.get("status") != "success":
            return False, data.get("message", "报告生成失败"), data
        return True, "ok", data


def _generate_pseudocolor_for_result(file_id, total_slices):
    output_dir = os.path.join(app.config["PROCESSED_FOLDER"], file_id)
    total_success = 0
    total_attempts = 0
    for slice_idx in range(int(total_slices or 0)):
        results = generate_all_pseudocolors(output_dir, file_id, slice_idx)
        for _, item in (results or {}).items():
            total_attempts += 1
            if item.get("success"):
                total_success += 1
    ok = total_success > 0 if total_attempts > 0 else False
    msg = f"伪彩图生成 {total_success}/{total_attempts}"
    return ok, msg


def _run_upload_processing_job(job_id, payload):
    temp_dir = payload.get("temp_dir")
    warnings = []
    try:
        _set_job_status(job_id, "running")

        can_mcta = _is_mcta_combo(payload.get("modalities"))
        has_real_ctp = _has_real_ctp(payload.get("modalities"))
        should_ctp_generate = can_mcta and not has_real_ctp
        should_stroke = can_mcta

        if should_ctp_generate:
            _update_step(
                job_id, "ctp_generate", "running", "正在基于 mCTA 生成 CTP 灌注图"
            )
        else:
            reason = (
                "已上传真实CTP数据，无需生成"
                if has_real_ctp
                else "当前模态不支持CTP生成"
            )
            _update_step(job_id, "ctp_generate", "skipped", reason)

        ok, upload_msg, upload_result = _invoke_internal_upload(payload)
        if not ok:
            if should_ctp_generate:
                _update_step(job_id, "ctp_generate", "failed", upload_msg)
            _set_job_status(job_id, "failed", upload_msg)
            return

        if should_ctp_generate:
            _update_step(job_id, "ctp_generate", "completed", "CTP 灌注图生成完成")

        if should_stroke:
            _update_step(job_id, "stroke_analysis", "running", "正在执行脑卒中自动分析")
            try:
                from stroke_analysis import auto_analyze_stroke

                analysis_result = auto_analyze_stroke(
                    payload["file_id"], payload["patient_id"]
                )
                if analysis_result.get("success"):
                    _update_step(
                        job_id, "stroke_analysis", "completed", "脑卒中自动分析完成"
                    )
                else:
                    err = analysis_result.get("error", "脑卒中自动分析失败")
                    _update_step(job_id, "stroke_analysis", "failed", err)
                    _set_job_status(job_id, "failed", err)
                    return
            except Exception as e:
                err = f"脑卒中自动分析异常: {e}"
                _update_step(job_id, "stroke_analysis", "failed", err)
                _set_job_status(job_id, "failed", err)
                return
        else:
            _update_step(
                job_id, "stroke_analysis", "skipped", "当前模态组合不触发脑卒中自动分析"
            )

        if _result_has_ctp_images(upload_result):
            _update_step(job_id, "pseudocolor", "running", "正在生成医学标准伪彩图")
            try:
                ok, msg = _generate_pseudocolor_for_result(
                    payload["file_id"], upload_result.get("total_slices", 0)
                )
                if ok:
                    _update_step(job_id, "pseudocolor", "completed", msg)
                else:
                    _update_step(job_id, "pseudocolor", "failed", msg)
                    warnings.append(msg)
                    _add_job_warning(job_id, msg)
            except Exception as e:
                msg = f"伪彩图生成异常: {e}"
                _update_step(job_id, "pseudocolor", "failed", msg)
                warnings.append(msg)
                _add_job_warning(job_id, msg)
        else:
            _update_step(
                job_id, "pseudocolor", "skipped", "无可用CTP图像，跳过伪彩图生成"
            )

        _update_step(job_id, "ai_report", "running", "正在生成AI影像报告")
        ok, report_msg, report_result = _invoke_internal_generate_report(
            payload["patient_id"], payload["file_id"]
        )
        if ok:
            upload_result["report"] = report_result.get("report")
            upload_result["report_payload"] = report_result.get("report_payload")
            upload_result["json_path"] = report_result.get("json_path")
            _update_step(job_id, "ai_report", "completed", "AI影像报告生成完成")
        else:
            warn = f"AI影像报告生成失败: {report_msg}"
            warnings.append(warn)
            _add_job_warning(job_id, warn)
            _update_step(job_id, "ai_report", "failed", report_msg)

        def _mut(job):
            job["status"] = "completed"
            job["result"] = upload_result
            job["error"] = None
            job["current_step"] = None
            if warnings:
                job["warnings"] = list({*job.get("warnings", []), *warnings})
            job["progress"] = 100

        _update_upload_job(job_id, _mut)
    except Exception as e:
        _set_job_status(job_id, "failed", f"任务异常: {e}")
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


# 获取项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# AI模型配置 - 扩展为三个模型
AI_CONFIG_BASE = os.path.join(PROJECT_ROOT, "palette", "config")
AI_WEIGHTS_BASE = os.path.join(PROJECT_ROOT, "palette", "weights")

# 三个模型的配置
MODEL_CONFIGS = {
    "cbf": {
        "name": "CBF灌注图",
        "config_path": os.path.join(AI_CONFIG_BASE, "cbf.json"),
        "weight_dir": os.path.join(AI_WEIGHTS_BASE, "cbf"),
        "use_ema": True,
        "color": "#e74c3c",  # 红色
        "description": "脑血流量 (Cerebral Blood Flow)",
    },
    "cbv": {
        "name": "CBV灌注图",
        "config_path": os.path.join(AI_CONFIG_BASE, "cbv.json"),
        "weight_dir": os.path.join(AI_WEIGHTS_BASE, "cbv"),
        "use_ema": True,
        "color": "#3498db",  # 蓝色
        "description": "脑血容量 (Cerebral Blood Volume)",
    },
    "tmax": {
        "name": "Tmax灌注图",
        "config_path": os.path.join(AI_CONFIG_BASE, "tmax.json"),
        "weight_dir": os.path.join(AI_WEIGHTS_BASE, "tmax"),
        "use_ema": True,
        "color": "#27ae60",  # 绿色
        "description": "达峰时间 (Time to Maximum)",
    },
}


def find_weight_file(weight_dir: str, pattern: str) -> str:
    """
    在权重目录中查找匹配的文件

    Args:
        weight_dir: 权重目录路径
        pattern: 文件名模式（如 "200_Network_ema.pth"）

    Returns:
        找到的文件路径，或 None
    """
    if not os.path.exists(weight_dir):
        return None

    # 直接匹配
    direct_path = os.path.join(weight_dir, pattern)
    if os.path.exists(direct_path):
        return direct_path

    # 查找所有 .pth 文件并匹配前缀
    for filename in os.listdir(weight_dir):
        if filename.endswith(".pth") and filename.startswith(pattern.split("_")[0]):
            return os.path.join(weight_dir, filename)

    return None


def get_weight_base_path(weight_dir: str) -> str:
    """
    获取权重文件的基础路径（去掉文件名）
    权重文件名格式: XXX_Network.pth 或 XXX_Network_ema.pth
    """
    if not os.path.exists(weight_dir):
        return None

    # 查找权重文件
    for filename in os.listdir(weight_dir):
        if filename.endswith("_Network.pth") or filename.endswith("_Network_ema.pth"):
            # 提取数字部分（如 200）
            prefix = filename.split("_")[0]
            return os.path.join(weight_dir, prefix)

    return None


# 全局模型字典
ai_models = {}

# 统一的伪彩图配置 - 使用医学标准颜色映射
PSEUDOCOLOR_CONFIG = {
    "colormap": "jet",  # 医学图像标准颜色映射
    "vmin": 0.1,  # 忽略过低的值
    "vmax": 0.9,  # 避免过饱和
}


def init_ai_models():
    """初始化所有AI模型"""
    global ai_models
    ai_models = {}

    print("=" * 50)
    print("开始初始化AI模型...")
    print("=" * 50)

    models_initialized = 0

    # 自动检测设备，优先使用CUDA，如果不可用则使用CPU
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"使用设备: {device}")

    for model_key, config in MODEL_CONFIGS.items():
        print(f"\n初始化 {config['name']} 模型:")
        print(f"  配置路径: {config['config_path']}")
        print(f"  权重目录: {config['weight_dir']}")

        # 使用新的权重检测逻辑
        weight_base = get_weight_base_path(config["weight_dir"])

        # 检查文件是否存在
        config_exists = os.path.exists(config["config_path"])
        ema_exists = (
            find_weight_file(config["weight_dir"], "_Network_ema.pth") is not None
        )
        normal_exists = (
            find_weight_file(config["weight_dir"], "_Network.pth") is not None
        )

        print(f"  配置文件: {'✓' if config_exists else '✗'}")
        print(f"  权重基础路径: {weight_base}")
        print(f"  EMA权重: {'✓' if ema_exists else '✗'}")
        print(f"  普通权重: {'✓' if normal_exists else '✗'}")

        if config_exists and weight_base:
            try:
                # 这里需要根据您的ai_inference模块调整初始化方式
                model = init_single_ai_model(
                    config["config_path"], weight_base, config["use_ema"], device=device
                )
                if model:
                    ai_models[model_key] = {
                        "model": model,
                        "config": config,
                        "available": True,
                    }
                    models_initialized += 1
                    print(f"  ✓ {config['name']} 模型初始化成功")
                else:
                    ai_models[model_key] = {
                        "model": None,
                        "config": config,
                        "available": False,
                    }
                    print(f"  ✗ {config['name']} 模型初始化失败")
            except Exception as e:
                ai_models[model_key] = {
                    "model": None,
                    "config": config,
                    "available": False,
                }
                print(f"  ✗ {config['name']} 模型初始化异常: {e}")
        else:
            ai_models[model_key] = {"model": None, "config": config, "available": False}
            print(f"  ✗ {config['name']} 模型文件不完整")

    print(
        f"\n模型初始化统计: {models_initialized}/{len(MODEL_CONFIGS)} 个模型成功初始化"
    )
    print("=" * 50)

    return models_initialized > 0


def init_single_ai_model(config_path, weight_base, use_ema=True, device="cpu"):
    """初始化单个AI模型"""
    try:
        # 这里需要根据您的ai_inference模块调整初始化方式
        from ai_inference import MedicalAIModel

        model = MedicalAIModel(config_path, weight_base, use_ema=use_ema, device=device)
        return model
    except Exception as e:
        print(f"初始化单个模型失败: {e}")
        return None


def get_ai_model(model_key="cbf"):
    """获取指定的AI模型"""
    global ai_models
    if model_key in ai_models and ai_models[model_key]["available"]:
        return ai_models[model_key]["model"]
    return None


def are_any_models_available():
    """检查是否有任何模型可用"""
    global ai_models
    return any(model_info["available"] for model_info in ai_models.values())


def get_available_models():
    """获取可用的模型列表"""
    global ai_models
    # 从palette模型配置中获取可用模型
    available = [key for key, info in ai_models.items() if info["available"]]
    # 添加mrdpm模型（如果有MRDPM权重文件）
    mrdpm_available = check_mrdpm_models_available()
    for model_key in mrdpm_available:
        if model_key not in available:
            available.append(model_key)
    return available


def check_mrdpm_models_available():
    """检查MRDPM模型是否可用"""
    available = []
    current_dir = os.path.dirname(os.path.abspath(__file__))
    mrdpm_weights_dir = os.path.join(current_dir, "mrdpm", "weights")

    if not os.path.exists(mrdpm_weights_dir):
        return available

    # 检查mrdpm主目录是否存在（使用mrdpm作为特殊model_key）
    bran_path = os.path.join(mrdpm_weights_dir, "bran_pretrained_3channel.pth")
    residual_path = os.path.join(mrdpm_weights_dir, "200_Network_ema.pth")

    # mrdpm作为特殊标识，只要有一个子模型可用，mrdpm就可用
    subdirs = [
        d
        for d in os.listdir(mrdpm_weights_dir)
        if os.path.isdir(os.path.join(mrdpm_weights_dir, d))
    ]
    for subdir in subdirs:
        sub_bran = os.path.join(
            mrdpm_weights_dir, subdir, "bran_pretrained_3channel.pth"
        )
        sub_residual = os.path.join(mrdpm_weights_dir, subdir, "200_Network_ema.pth")
        if os.path.exists(sub_bran) and os.path.exists(sub_residual):
            available.append("mrdpm")
            break

    return available


# ==================== 改进的伪彩图生成函数 ====================


def create_medical_pseudocolor(grayscale_data, mask_data):
    """
    Build medical pseudocolor image and return LUT statistics for viewer colorbar.
    Returns: (pseudocolor_rgb, lut_stats)
    lut_stats keys:
      - min_value/max_value: mapped LUT range for this slice
      - raw_min/raw_max: raw normalized range inside mask
      - valid_pixels: number of valid mask pixels
    """
    try:
        print("Start generating medical pseudocolor...")
        print(f"Input range: [{grayscale_data.min():.3f}, {grayscale_data.max():.3f}]")
        print(f"Mask range: [{mask_data.min():.3f}, {mask_data.max():.3f}]")

        grayscale_data = np.clip(grayscale_data, 0, 1)
        mask_binary = mask_data > 0.5
        valid_pixels = int(np.sum(mask_binary))

        lut_stats = {
            "min_value": None,
            "max_value": None,
            "raw_min": None,
            "raw_max": None,
            "valid_pixels": valid_pixels,
        }

        if not np.any(mask_binary):
            print("Warning: empty mask region")
            empty = np.zeros((*grayscale_data.shape, 3), dtype=np.uint8)
            return empty, lut_stats

        masked_values = grayscale_data[mask_binary]
        raw_min = float(masked_values.min())
        raw_max = float(masked_values.max())
        lut_stats["raw_min"] = raw_min
        lut_stats["raw_max"] = raw_max

        print(f"Masked range: [{raw_min:.3f}, {raw_max:.3f}]")
        print(f"Masked pixels: {valid_pixels}")

        colormap = plt.get_cmap("jet")

        if raw_max > raw_min:
            lower_bound = float(np.percentile(masked_values, 2))
            upper_bound = float(np.percentile(masked_values, 98))

            if upper_bound - lower_bound < 1e-6:
                lower_bound = raw_min
                upper_bound = raw_max
                if upper_bound - lower_bound < 1e-6:
                    lower_bound = 0.0
                    upper_bound = 1.0

            enhanced_data = np.clip(
                (grayscale_data - lower_bound) / (upper_bound - lower_bound), 0, 1
            )
            print(f"Contrast enhance: [{lower_bound:.3f}, {upper_bound:.3f}] -> [0, 1]")
        else:
            lower_bound = raw_min
            upper_bound = raw_max
            enhanced_data = grayscale_data
            print("No dynamic range in mask, use normalized source values")

        lut_stats["min_value"] = float(lower_bound)
        lut_stats["max_value"] = float(upper_bound)

        colored_data = colormap(enhanced_data)
        rgb_data = (colored_data[:, :, :3] * 255).astype(np.uint8)

        grayscale_8bit = (grayscale_data * 255).astype(np.uint8)
        result = np.zeros_like(rgb_data)
        for i in range(3):
            result[:, :, i] = np.where(mask_binary, rgb_data[:, :, i], grayscale_8bit)

        print(f"Pseudocolor generated, output range: [{result.min()}, {result.max()}]")
        return result, lut_stats

    except Exception as e:
        print(f"Create pseudocolor failed: {e}")
        traceback.print_exc()
        grayscale_8bit = (grayscale_data * 255).astype(np.uint8)
        result = np.zeros((*grayscale_data.shape, 3), dtype=np.uint8)
        for i in range(3):
            result[:, :, i] = np.where(mask_data > 0.5, grayscale_8bit, grayscale_8bit)
        return result, {
            "min_value": None,
            "max_value": None,
            "raw_min": None,
            "raw_max": None,
            "valid_pixels": 0,
        }


def generate_pseudocolor_for_slice(
    grayscale_path, mask_path, output_dir, slice_idx, model_key
):
    """
    为单个切片的灰度图生成伪彩图 - 改进版本
    """
    try:
        print(f"为切片 {slice_idx} 的 {model_key.upper()} 生成医学标准伪彩图...")

        # 检查文件是否存在
        if not os.path.exists(grayscale_path):
            return {"success": False, "error": "灰度图不存在"}

        # 加载图像数据
        grayscale_img = Image.open(grayscale_path).convert("L")
        grayscale_data = np.array(grayscale_img) / 255.0

        # 尝试加载掩码文件，如果不存在则创建默认掩码
        # 首先尝试标准掩码文件格式（slice_000_mask.png）
        standard_mask_path = os.path.join(output_dir, f"slice_{slice_idx:03d}_mask.png")
        if os.path.exists(standard_mask_path):
            mask_img = Image.open(standard_mask_path).convert("L")
            mask_data = np.array(mask_img) / 255.0
            print(f"使用标准掩码文件: {standard_mask_path}")
        elif os.path.exists(mask_path):
            # 然后尝试传入的mask_path
            mask_img = Image.open(mask_path).convert("L")
            mask_data = np.array(mask_img) / 255.0
            print(f"使用掩码文件: {mask_path}")
        else:
            # 创建默认掩码（使用更合理的阈值，而不是全白）
            print(f"掩码文件不存在，创建默认掩码: {standard_mask_path}")
            # 使用Otsu阈值创建掩码，而不是全白
            from skimage import filters

            try:
                otsu_threshold = filters.threshold_otsu(grayscale_data)
                mask_data = grayscale_data > otsu_threshold
            except:
                # 如果Otsu失败，使用基于百分比的阈值
                low_thresh = np.percentile(grayscale_data, 10)
                high_thresh = np.percentile(grayscale_data, 90)
                mask_data = np.logical_and(
                    grayscale_data > low_thresh, grayscale_data < high_thresh
                )
            # 保存默认掩码到文件系统（使用标准命名格式）
            mask_8bit = (mask_data * 255).astype(np.uint8)
            os.makedirs(os.path.dirname(standard_mask_path), exist_ok=True)
            Image.fromarray(mask_8bit).save(standard_mask_path)
            print(f"默认掩码已保存: {standard_mask_path}")

        # 生成医学标准伪彩图
        pseudocolor_data, lut_stats = create_medical_pseudocolor(
            grayscale_data, mask_data
        )

        # 保存伪彩图
        slice_prefix = f"slice_{slice_idx:03d}"
        pseudocolor_path = os.path.join(
            output_dir, f"{slice_prefix}_{model_key}_pseudocolor.png"
        )

        # 确保目录存在
        os.makedirs(os.path.dirname(pseudocolor_path), exist_ok=True)
        Image.fromarray(pseudocolor_data).save(pseudocolor_path)

        # 构建URL
        file_id = os.path.basename(output_dir)
        pseudocolor_url = (
            f"/get_image/{file_id}/{slice_prefix}_{model_key}_pseudocolor.png"
        )

        print(f"✓ {model_key.upper()} 医学标准伪彩图生成成功: {pseudocolor_path}")

        return {
            "success": True,
            "pseudocolor_url": pseudocolor_url,
            "colormap": "jet",  # 统一使用jet颜色映射
            "output_path": pseudocolor_path,
            "lut_stats": lut_stats,
        }

    except Exception as e:
        print(f"✗ 生成伪彩图失败: {e}")
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def generate_all_pseudocolors(output_dir, file_id, slice_idx):
    """
    为单个切片的所有模型生成伪彩图 - 改进版本
    """
    try:
        pseudocolor_results = {}
        success_count = 0

        for model_key in MODEL_CONFIGS.keys():
            # 构建文件路径
            slice_prefix = f"slice_{slice_idx:03d}"
            # 首先尝试查找AI生成的输出文件
            grayscale_path = os.path.join(
                output_dir, f"{slice_prefix}_{model_key}_output.png"
            )
            # 如果AI输出文件不存在，尝试查找原始CTP图像文件
            if not os.path.exists(grayscale_path):
                grayscale_path = os.path.join(
                    output_dir, f"{slice_prefix}_{model_key}.png"
                )
            mask_path = os.path.join(output_dir, f"{slice_prefix}_mask.png")
            # 如果标准掩码文件不存在，尝试查找其他可能的掩码文件
            if not os.path.exists(mask_path):
                mask_path = os.path.join(output_dir, f"{slice_prefix}_ncct_mask.png")

            # 检查灰度图文件是否存在
            if os.path.exists(grayscale_path):
                print(f"\n--- 为 {model_key.upper()} 生成医学标准伪彩图 ---")
                result = generate_pseudocolor_for_slice(
                    grayscale_path, mask_path, output_dir, slice_idx, model_key
                )
                pseudocolor_results[model_key] = result
                if result["success"]:
                    success_count += 1
            else:
                error_msg = f"文件不存在: {grayscale_path}"
                print(f"✗ {error_msg}")
                pseudocolor_results[model_key] = {"success": False, "error": error_msg}

        print(f"\n伪彩图生成统计: {success_count}/{len(MODEL_CONFIGS)} 个模型成功")
        return pseudocolor_results

    except Exception as e:
        print(f"生成所有伪彩图失败: {e}")
        traceback.print_exc()
        return {}


# ==================== 路由函数 ====================


@app.route("/generate_pseudocolor/<file_id>/<int:slice_index>")
def generate_pseudocolor(file_id, slice_index):
    """生成指定切片的伪彩图 - 医学标准版本"""
    try:
        output_dir = os.path.join(app.config["PROCESSED_FOLDER"], file_id)

        if not os.path.exists(output_dir):
            return jsonify({"success": False, "error": "文件目录不存在"})

        print(f"开始为切片 {slice_index} 生成医学标准伪彩图...")

        # 生成所有模型的伪彩图
        pseudocolor_results = generate_all_pseudocolors(
            output_dir, file_id, slice_index
        )

        # 统计成功数量
        success_count = sum(
            1 for result in pseudocolor_results.values() if result["success"]
        )

        return jsonify(
            {
                "success": True,
                "slice_index": slice_index,
                "pseudocolor_results": pseudocolor_results,
                "success_count": success_count,
                "total_models": len(MODEL_CONFIGS),
                "message": f"成功生成 {success_count}/{len(MODEL_CONFIGS)} 个模型的医学标准伪彩图",
            }
        )

    except Exception as e:
        print(f"生成伪彩图路由错误: {e}")
        return jsonify({"success": False, "error": str(e)})


@app.route("/generate_all_pseudocolors/<file_id>")
def generate_all_pseudocolors_route(file_id):
    """为所有切片生成伪彩图 - 医学标准版本"""
    try:
        output_dir = os.path.join(app.config["PROCESSED_FOLDER"], file_id)

        if not os.path.exists(output_dir):
            return jsonify({"success": False, "error": "文件目录不存在"})

        # 查找所有切片
        # 同时查找AI生成的文件和原始CTP文件
        slice_files = []
        for f in os.listdir(output_dir):
            if f.startswith("slice_") and any(
                f.endswith(f"_{model_key}_output.png")
                or f.endswith(f"_{model_key}.png")
                for model_key in MODEL_CONFIGS.keys()
            ):
                slice_files.append(f)
        slice_indices = []

        for file in slice_files:
            try:
                # 提取切片索引：slice_001_cbf_output.png 或 slice_001_cbf.png -> 1
                index_str = file.split("_")[1]
                slice_index = int(index_str)
                slice_indices.append(slice_index)
            except:
                continue

        slice_indices.sort()

        if not slice_indices:
            return jsonify({"success": False, "error": "未找到切片文件"})

        print(f"开始为 {len(slice_indices)} 个切片生成医学标准伪彩图...")

        all_results = {}
        total_success = 0

        for slice_idx in slice_indices:
            print(f"\n=== 处理切片 {slice_idx} ===")
            results = generate_all_pseudocolors(output_dir, file_id, slice_idx)
            all_results[slice_idx] = results

            # 统计该切片的成功数量
            slice_success = sum(1 for result in results.values() if result["success"])
            total_success += slice_success
            print(f"切片 {slice_idx} 完成: {slice_success}/{len(MODEL_CONFIGS)}")

        total_attempts = len(slice_indices) * len(MODEL_CONFIGS)

        return jsonify(
            {
                "success": True,
                "total_slices": len(slice_indices),
                "total_models": len(MODEL_CONFIGS),
                "total_success": total_success,
                "total_attempts": total_attempts,
                "success_rate": f"{(total_success / total_attempts * 100):.1f}%",
                "results": all_results,
                "message": f"成功为 {total_success}/{total_attempts} 个组合生成医学标准伪彩图",
            }
        )

    except Exception as e:
        print(f"生成所有伪彩图路由错误: {e}")
        return jsonify({"success": False, "error": str(e)})


@app.route("/analyze_stroke/<file_id>")
def analyze_stroke(file_id):
    """执行脑卒中病灶分析"""
    try:
        # 获取偏侧参数（默认为双侧）
        hemisphere = request.args.get("hemisphere", "both")

        print(f"开始脑卒中分析 - 病例: {file_id}, 偏侧: {hemisphere}")

        # 调用分析函数
        analysis_results = analyze_stroke_case(file_id, hemisphere)

        # 将numpy类型转换为Python原生类型以确保JSON序列化
        def convert_numpy_types(obj):
            if isinstance(obj, dict):
                return {k: convert_numpy_types(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy_types(v) for v in obj]
            elif isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.bool_):
                return bool(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            else:
                return obj

        # 转换分析结果中的numpy类型
        analysis_results = convert_numpy_types(analysis_results)

        if analysis_results["success"]:
            return jsonify(
                {
                    "success": True,
                    "file_id": file_id,
                    "hemisphere": hemisphere,
                    "analysis_results": analysis_results,
                }
            )
        else:
            return jsonify(
                {"success": False, "error": analysis_results.get("error", "分析失败")}
            )

    except Exception as e:
        print(f"脑卒中分析路由错误: {e}")
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)})


@app.route("/get_stroke_analysis_image/<file_id>/<filename>")
def get_stroke_analysis_image(file_id, filename):
    """获取脑卒中分析生成的图像"""
    try:
        image_path = os.path.join(
            app.config["PROCESSED_FOLDER"], file_id, "stroke_analysis", filename
        )
        print(f"获取脑卒中分析图像: {image_path}")  # 调试信息
        if os.path.exists(image_path):
            return send_file(image_path, mimetype="image/png")
        else:
            print(f"分析图像不存在: {image_path}")  # 调试信息
            return jsonify({"error": "分析图像不存在"}), 404
    except Exception as e:
        print(f"获取脑卒中分析图像错误: {e}")  # 调试信息
        return jsonify({"error": str(e)}), 404


@app.route("/api/insert_patient", methods=["POST"])
def api_insert_patient():
    # 1. 接收前端传过来的JSON数据
    data = request.get_json()
    print("收到数据:", data)

    # 2. 核心补全：调用你core目录里的入库函数，执行Supabase写入操作
    success, result = insert_patient_info(data)

    # 3. 根据入库结果，返回真实的响应给前端
    if success:
        # 写入成功：返回真实的入库数据（含Supabase自动生成的ID）
        return jsonify({"status": "success", "message": "数据写入成功", "data": result})
    else:
        # 写入失败：返回错误信息，前端会弹出红色错误提示
        return jsonify({"status": "error", "message": result}), 200


@app.route("/api/update_analysis", methods=["POST"])
def api_update_analysis():
    """更新患者的分析结果到 patient_info 表"""
    data = request.get_json()
    patient_id = data.get("patient_id")

    if not patient_id:
        return jsonify({"status": "error", "message": "缺少 patient_id"}), 400

    # 调用封装好的函数
    success, result = update_analysis_result(patient_id, data)

    if success:
        return jsonify(
            {"status": "success", "message": "分析结果已更新", "data": result}
        )
    else:
        return jsonify({"status": "error", "message": result}), 500


# ==================== MedGemma AI Report API ====================


@app.route("/api/generate_report/<int:patient_id>", methods=["GET", "POST"])
def api_generate_report(patient_id):
    """
    Generate imaging report via MedGemma using structured data.
    """
    request_start = time.time()
    try:
        # Format + file_id
        if request.method == "POST":
            data = request.get_json() or {}
            output_format = data.get("format", "markdown")
            file_id = data.get("file_id") or request.args.get("file_id")
            source = data.get("source") or request.args.get("source", "manual")
        else:
            data = {}
            output_format = request.args.get("format", "markdown")
            file_id = request.args.get("file_id")
            source = request.args.get("source", "manual")

        if output_format not in ["markdown", "json"]:
            return jsonify(
                {
                    "status": "error",
                    "message": "Invalid format; use 'markdown' or 'json'",
                }
            ), 400

        if not file_id:
            return jsonify({"status": "error", "message": "Missing file_id"}), 400

        print(
            f"[MedGemma] /api/generate_report patient_id={patient_id} file_id={file_id} format={output_format} source={source}"
        )

        patient_data = get_patient_by_id(patient_id)
        if not patient_data:
            return jsonify(
                {"status": "error", "message": f"Patient {patient_id} not found"}
            ), 404

        imaging_data = get_imaging_by_case(patient_id, file_id)
        if not imaging_data:
            return jsonify(
                {"status": "error", "message": f"Imaging case {file_id} not found"}
            ), 404

        # Compute onset-to-admission hours
        onset_time = patient_data.get("onset_exact_time")
        admission_time = patient_data.get("admission_time")
        onset_to_admission_hours = None
        if onset_time and admission_time:
            try:
                from datetime import datetime

                onset_dt = datetime.fromisoformat(
                    str(onset_time).replace("Z", "+00:00")
                )
                admission_dt = datetime.fromisoformat(
                    str(admission_time).replace("Z", "+00:00")
                )
                onset_to_admission_hours = round(
                    (admission_dt - onset_dt).total_seconds() / 3600, 1
                )
            except Exception as e:
                print(f"Onset-to-admission calc failed: {e}")

        hemisphere_value = (
            (imaging_data or {}).get("hemisphere")
            or patient_data.get("hemisphere")
            or "both"
        )
        structured_data = {
            "id": patient_data.get("id"),
            "ID": patient_data.get("id"),
            "patient_name": patient_data.get("patient_name", ""),
            "patient_age": patient_data.get("patient_age", ""),
            "patient_sex": patient_data.get("patient_sex", ""),
            "admission_nihss": patient_data.get("admission_nihss", None),
            "onset_to_admission_hours": onset_to_admission_hours,
            "core_infarct_volume": patient_data.get("core_infarct_volume"),
            "penumbra_volume": patient_data.get("penumbra_volume"),
            "mismatch_ratio": patient_data.get("mismatch_ratio"),
            "hemisphere": hemisphere_value,
            "analysis_status": patient_data.get("analysis_status", "pending"),
        }

        # Debug summary
        print("=" * 60)
        print("[AI Report] structured_data:")
        print(json.dumps(structured_data, ensure_ascii=False, indent=2, default=str))
        print("=" * 60)
        print("[AI Report] key fields:")
        print(f"  - NIHSS: {structured_data.get('admission_nihss')}")
        print(f"  - Age: {structured_data.get('patient_age')}")
        print(f"  - Onset->Admission (h): {onset_to_admission_hours}")
        print("=" * 60)

        if structured_data.get("admission_nihss") is None:
            print("WARN: admission_nihss is empty")
        if structured_data.get("patient_age") in ["", None]:
            print("WARN: patient_age is empty")
        if onset_to_admission_hours is None:
            print("WARN: onset_to_admission_hours is empty")

        result = generate_report_with_medgemma(
            structured_data, imaging_data, file_id, output_format
        )

        if result["success"]:
            elapsed = round(time.time() - request_start, 2)
            if result.get("json_path"):
                print(f"[MedGemma] report json saved: {result.get('json_path')}")
            print(
                f"[MedGemma] /api/generate_report success patient_id={patient_id} file_id={file_id} elapsed={elapsed}s"
            )
            return jsonify(
                {
                    "status": "success",
                    "message": "Report generated",
                    "patient_id": patient_id,
                    "format": output_format,
                    "report": result["report"],
                    "report_payload": result.get("report_payload"),
                    "json_path": result.get("json_path"),
                    "is_mock": result.get("is_mock", False),
                    "warning": result.get("warning"),
                    "source": source,
                }
            )
        else:
            elapsed = round(time.time() - request_start, 2)
            print(
                f"[MedGemma] /api/generate_report failed patient_id={patient_id} file_id={file_id} elapsed={elapsed}s error={result.get('error')}"
            )
            return jsonify(
                {
                    "status": "error",
                    "message": result.get("error", "Report generation failed"),
                    "format": output_format,
                }
            ), 500

    except Exception as e:
        elapsed = round(time.time() - request_start, 2)
        print(
            f"[MedGemma] /api/generate_report exception patient_id={patient_id} elapsed={elapsed}s error={e}"
        )
        import traceback

        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/auto_analyze_stroke", methods=["POST"])
def api_auto_analyze_stroke():
    """
    自动触发脑卒中分析的API端点
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"status": "error", "message": "请求数据为空"}), 400

        # 获取必要参数
        case_id = data.get("case_id")
        patient_id = data.get("patient_id")

        if not case_id:
            return jsonify({"status": "error", "message": "缺少必要参数: case_id"}), 400

        print(f"收到自动脑卒中分析请求 - case_id: {case_id}, patient_id: {patient_id}")

        # 导入auto_analyze_stroke函数
        from stroke_analysis import auto_analyze_stroke

        # 执行自动分析
        analysis_result = auto_analyze_stroke(case_id, patient_id)

        if analysis_result.get("success"):
            return jsonify(
                {
                    "status": "success",
                    "message": "自动脑卒中分析成功",
                    "case_id": case_id,
                    "analysis_result": analysis_result,
                }
            )
        else:
            return jsonify(
                {
                    "status": "error",
                    "message": analysis_result.get("error", "分析失败"),
                    "case_id": case_id,
                }
            ), 500

    except Exception as e:
        print(f"自动脑卒中分析API错误: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/generate_report_from_data", methods=["POST"])
def api_generate_report_from_data():
    """
    Generate report from provided structured data (file_id still required).
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"status": "error", "message": "Empty request payload"}), 400

        output_format = data.get("format", "markdown")
        if output_format not in ["markdown", "json"]:
            return jsonify(
                {
                    "status": "error",
                    "message": "Invalid format; use 'markdown' or 'json'",
                }
            ), 400

        file_id = data.get("file_id")
        if not file_id:
            return jsonify({"status": "error", "message": "Missing file_id"}), 400

        patient_id = data.get("patient_id")
        if patient_id:
            patient_data = get_patient_by_id(patient_id)
            if patient_data:
                if (
                    data.get("admission_nihss") is None
                    and patient_data.get("admission_nihss") is not None
                ):
                    data["admission_nihss"] = patient_data.get("admission_nihss")
                if (
                    data.get("patient_age") in ["", None]
                    and patient_data.get("patient_age") is not None
                ):
                    data["patient_age"] = patient_data.get("patient_age")
                if (
                    data.get("patient_sex") in ["", None]
                    and patient_data.get("patient_sex") is not None
                ):
                    data["patient_sex"] = patient_data.get("patient_sex")
                if (
                    data.get("onset_to_admission_hours") is None
                    and patient_data.get("onset_exact_time")
                    and patient_data.get("admission_time")
                ):
                    try:
                        from datetime import datetime

                        onset_dt = datetime.fromisoformat(
                            str(patient_data.get("onset_exact_time")).replace(
                                "Z", "+00:00"
                            )
                        )
                        admission_dt = datetime.fromisoformat(
                            str(patient_data.get("admission_time")).replace(
                                "Z", "+00:00"
                            )
                        )
                        data["onset_to_admission_hours"] = round(
                            (admission_dt - onset_dt).total_seconds() / 3600, 1
                        )
                    except Exception as e:
                        print(f"Onset-to-admission calc failed: {e}")

        imaging_data = get_imaging_by_case(patient_id, file_id)
        if not imaging_data:
            return jsonify(
                {"status": "error", "message": f"Imaging case {file_id} not found"}
            ), 404

        result = generate_report_with_medgemma(
            data, imaging_data, file_id, output_format
        )

        if result["success"]:
            return jsonify(
                {
                    "status": "success",
                    "message": "Report generated",
                    "format": output_format,
                    "report": result["report"],
                    "report_payload": result.get("report_payload"),
                    "is_mock": result.get("is_mock", False),
                    "warning": result.get("warning"),
                }
            )
        else:
            return jsonify(
                {
                    "status": "error",
                    "message": result.get("error", "Report generation failed"),
                    "format": output_format,
                }
            ), 500

    except Exception as e:
        print(f"Report generation error: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/get_patient/<int:patient_id>")
def api_get_patient(patient_id):
    """获取患者信息"""
    try:
        response = (
            supabase.table("patient_info").select("*").eq("id", patient_id).execute()
        )

        if response.data and len(response.data) > 0:
            return jsonify({"status": "success", "data": response.data[0]})
        else:
            return jsonify(
                {"status": "error", "message": f"未找到ID为 {patient_id} 的患者信息"}
            ), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/get_imaging/<case_id>")
def api_get_imaging(case_id):
    """返回 patient_imaging 中与 case_id 关联的记录，主要用于获取 hemisphere 等字段"""
    try:
        if SUPABASE_AVAILABLE:
            resp = (
                supabase.table("patient_imaging")
                .select("*")
                .eq("case_id", case_id)
                .execute()
            )
            if resp.data and len(resp.data) > 0:
                return jsonify({"success": True, "data": resp.data[0]})
            else:
                return jsonify({"success": False, "error": "not found"}), 404
        else:
            return jsonify({"success": False, "error": "supabase not available"}), 500
    except Exception as e:
        print(f"api_get_imaging error: {e}")
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/save_report", methods=["POST"])
def api_save_report():
    """保存结构化临床报告"""
    data = request.get_json() or {}
    patient_id = data.get("patient_id")
    file_id = data.get("file_id")

    if not patient_id or not file_id:
        return jsonify({"status": "error", "message": "缺少患者ID或文件ID"}), 400

    try:
        save_result = save_report_notes(patient_id, file_id, data)
        if not save_result.get("success"):
            return jsonify(
                {
                    "status": "error",
                    "message": save_result.get("error", "报告保存失败"),
                    "warnings": save_result.get("warnings", []),
                    "saved_targets": save_result.get("saved_targets", {}),
                }
            ), 500

        return jsonify(
            {
                "status": "success",
                "message": "报告保存成功",
                "data": save_result.get("data"),
                "warnings": save_result.get("warnings", []),
                "saved_targets": save_result.get("saved_targets", {}),
                "json_sync": save_result.get("json_sync", {}),
            }
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# 简单的测试路由
@app.route("/test")
def test_page():
    """测试路由"""
    return "Test page works!"


@app.route("/chat")
def chat_page():
    """渲染AI问诊页面"""
    return render_template("patient/upload/viewer/chat.html")


def _sse_format(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _truncate_text(text: str, max_chars: int = 6000) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[内容过长，已截断]"


_CHAT_CONTEXT_LOCK = threading.Lock()
_CHAT_CONTEXT_CACHE = {}
_CHAT_CONTEXT_TTL_SECONDS = int(os.environ.get("CHAT_CONTEXT_TTL_SECONDS", "3600"))


def _cleanup_chat_context_cache(now_ts=None):
    now_ts = now_ts or time.time()
    expired = []
    for key, value in _CHAT_CONTEXT_CACHE.items():
        loaded_at = float(value.get("loaded_at", 0))
        if now_ts - loaded_at > _CHAT_CONTEXT_TTL_SECONDS:
            expired.append(key)
    for key in expired:
        _CHAT_CONTEXT_CACHE.pop(key, None)


def _set_chat_context(session_id: str, context_payload: dict):
    if not session_id:
        return
    with _CHAT_CONTEXT_LOCK:
        _cleanup_chat_context_cache()
        payload = dict(context_payload or {})
        payload["loaded_at"] = time.time()
        _CHAT_CONTEXT_CACHE[session_id] = payload


def _get_chat_context(session_id: str):
    if not session_id:
        return None
    with _CHAT_CONTEXT_LOCK:
        _cleanup_chat_context_cache()
        return _CHAT_CONTEXT_CACHE.get(session_id)


def _clear_chat_context(session_id: str):
    if not session_id:
        return
    with _CHAT_CONTEXT_LOCK:
        _CHAT_CONTEXT_CACHE.pop(session_id, None)


def _extract_patient_id_command(text: str):
    if not text:
        return None
    content = str(text).strip()
    if re.fullmatch(r"\d{1,10}", content):
        try:
            return int(content)
        except Exception:
            return None

    patterns = [
        r"^(?:请)?(?:加载|读取|查询|查看|切换到)?\s*(?:患者|病人|patient)\s*(?:id)?\s*[:：#]?\s*(\d{1,10})\s*$",
        r"^(?:患者|病人|patient)\s*(?:id)?\s*[:：#]?\s*(\d{1,10})\s*$",
    ]
    for pattern in patterns:
        match = re.match(pattern, content, flags=re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except Exception:
                return None
    return None


def _safe_float(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            return float(value)
        except Exception:
            return None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return float(stripped)
        except Exception:
            return None
    return None


def _pick_first_numeric(source: dict, keys):
    if not isinstance(source, dict):
        return None
    for key in keys:
        value = _safe_float(source.get(key))
        if value is not None:
            return value
    return None


def _normalize_modalities_for_chat(modalities):
    alias = {
        "mcat": "mcta",
        "vcat": "vcta",
        "dcat": "dcta",
    }
    normalized = []
    if isinstance(modalities, list):
        for item in modalities:
            m = str(item).strip().lower()
            if not m:
                continue
            normalized.append(alias.get(m, m))
    return sorted(set(normalized))


def _compute_onset_to_admission_hours(patient_data: dict):
    if not isinstance(patient_data, dict):
        return None
    onset_time = patient_data.get("onset_exact_time")
    admission_time = patient_data.get("admission_time")
    if not onset_time or not admission_time:
        return None
    try:
        onset_dt = datetime.fromisoformat(str(onset_time).replace("Z", "+00:00"))
        admission_dt = datetime.fromisoformat(
            str(admission_time).replace("Z", "+00:00")
        )
        return round((admission_dt - onset_dt).total_seconds() / 3600, 1)
    except Exception:
        return None


def _get_latest_imaging_by_patient(patient_id: int):
    if not SUPABASE_AVAILABLE:
        return None
    try:
        response = (
            supabase.table("patient_imaging")
            .select("*")
            .eq("patient_id", patient_id)
            .order("updated_at", desc=True)
            .limit(1)
            .execute()
        )
        if response.data and len(response.data) > 0:
            return response.data[0]
    except Exception as e:
        print(f"[Baichuan Chat] latest imaging query failed (updated_at): {e}")
    try:
        response = (
            supabase.table("patient_imaging")
            .select("*")
            .eq("patient_id", patient_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if response.data and len(response.data) > 0:
            return response.data[0]
    except Exception as e:
        print(f"[Baichuan Chat] latest imaging query failed (created_at): {e}")
    return None


def _latest_result_json_for_file(file_id: str):
    if not file_id:
        return None
    results_dir = _medgemma_results_dir()
    if not os.path.isdir(results_dir):
        return None
    pattern = os.path.join(results_dir, f"medgemma_report_{file_id}_*.json")
    candidates = glob.glob(pattern)
    if not candidates:
        return None
    candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return candidates[0]


def _load_result_json_for_file(file_id: str):
    json_path = _latest_result_json_for_file(file_id)
    if not json_path:
        return None, None
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            return json_path, json.load(f)
    except Exception as e:
        print(f"[Baichuan Chat] failed to read result json {json_path}: {e}")
        return json_path, None


def mask_patient_context(raw: dict):
    patient = raw.get("patient", {}) if isinstance(raw, dict) else {}
    imaging = raw.get("imaging", {}) if isinstance(raw, dict) else {}
    ctp = raw.get("ctp", {}) if isinstance(raw, dict) else {}
    notes = raw.get("doctor_notes", {}) if isinstance(raw, dict) else {}

    age = patient.get("patient_age")
    age_value = None
    if isinstance(age, (int, float)):
        age_value = int(age)
    elif isinstance(age, str) and age.strip().isdigit():
        age_value = int(age.strip())

    masked = {
        "patient_id": patient.get("id"),
        "patient_basic": {
            "sex": patient.get("patient_sex") or "未提供",
            "age": age_value if age_value is not None else "未提供",
            "admission_nihss": patient.get("admission_nihss")
            if patient.get("admission_nihss") is not None
            else "未提供",
            "onset_to_admission_hours": _compute_onset_to_admission_hours(patient),
        },
        "imaging": {
            "file_id": imaging.get("file_id"),
            "modalities": _normalize_modalities_for_chat(
                imaging.get("available_modalities") or []
            ),
            "hemisphere": imaging.get("hemisphere") or "未提供",
        },
        "ctp_quantification": {
            "core_infarct_volume": ctp.get("core_infarct_volume"),
            "penumbra_volume": ctp.get("penumbra_volume"),
            "mismatch_ratio": ctp.get("mismatch_ratio"),
        },
        "doctor_notes": {
            "text": notes.get("text") or "",
            "source": notes.get("source") or "unknown",
        },
    }
    return masked


def _build_context_summary(masked_context: dict, missing_flags):
    patient_id = masked_context.get("patient_id")
    basic = masked_context.get("patient_basic", {})
    imaging = masked_context.get("imaging", {})
    ctp = masked_context.get("ctp_quantification", {})
    notes = masked_context.get("doctor_notes", {})

    lines = [f"已加载患者ID {patient_id} 的脱敏病例上下文。", ""]
    lines.append("【患者基本信息（脱敏）】")
    lines.append(f"- 性别：{basic.get('sex', '未提供')}")
    lines.append(f"- 年龄：{basic.get('age', '未提供')}")
    lines.append(f"- 入院NIHSS：{basic.get('admission_nihss', '未提供')}")
    onset_hours = basic.get("onset_to_admission_hours")
    lines.append(
        f"- 发病至入院时长：{onset_hours if onset_hours is not None else '未提供'}"
    )
    lines.append("")

    lines.append("【结构化关键字段】")
    lines.append(f"- 病例 file_id：{imaging.get('file_id') or '未提供'}")
    modalities = imaging.get("modalities") or []
    lines.append(f"- 影像模态：{', '.join(modalities) if modalities else '未提供'}")
    lines.append(f"- 病灶偏侧：{imaging.get('hemisphere') or '未提供'}")
    lines.append("")

    lines.append("【CTP灌注量化信息】")
    core = ctp.get("core_infarct_volume")
    penumbra = ctp.get("penumbra_volume")
    mismatch = ctp.get("mismatch_ratio")
    if core is None and penumbra is None and mismatch is None:
        lines.append("- 暂未找到CTP量化结果。")
    else:
        lines.append(f"- 核心梗死体积：{core if core is not None else '未提供'}")
        lines.append(
            f"- 缺血半暗带体积：{penumbra if penumbra is not None else '未提供'}"
        )
        lines.append(
            f"- mismatch比值：{mismatch if mismatch is not None else '未提供'}"
        )
    lines.append("")

    lines.append("【医生备注】")
    note_text = (notes.get("text") or "").strip()
    lines.append(f"- {note_text if note_text else '暂未找到医生备注。'}")

    if missing_flags:
        lines.append("")
        lines.append("【缺失提示】")
        for item in missing_flags:
            lines.append(f"- {item}")

    lines.append("")
    lines.append("你可以继续提问，例如：该患者是否存在灌注不匹配？")
    return "\n".join(lines)


def load_patient_context_by_id(patient_id: int):
    result = {
        "found": False,
        "patient_id": patient_id,
        "file_id": None,
        "context_struct": None,
        "context_summary": "",
        "missing_flags": [],
    }

    patient_data = get_patient_by_id(patient_id)
    if not patient_data:
        result["context_summary"] = (
            f"暂未找到患者ID {patient_id} 对应的患者信息。请确认ID后重试。"
        )
        return result

    result["found"] = True
    imaging = _get_latest_imaging_by_patient(patient_id)
    raw_context = {
        "patient": patient_data,
        "imaging": {
            "file_id": None,
            "available_modalities": [],
            "hemisphere": patient_data.get("hemisphere"),
        },
        "ctp": {},
        "doctor_notes": {},
    }

    if imaging:
        file_id = imaging.get("case_id")
        result["file_id"] = file_id
        raw_context["imaging"] = {
            "file_id": file_id,
            "available_modalities": imaging.get("available_modalities") or [],
            "hemisphere": imaging.get("hemisphere") or patient_data.get("hemisphere"),
        }

        analysis_result = imaging.get("analysis_result") or {}
        if not isinstance(analysis_result, dict):
            analysis_result = {}

        core = patient_data.get("core_infarct_volume")
        if core is None:
            core = _pick_first_numeric(
                analysis_result,
                ["core_infarct_volume", "core_volume_ml", "core_volume", "core"],
            )
        penumbra = patient_data.get("penumbra_volume")
        if penumbra is None:
            penumbra = _pick_first_numeric(
                analysis_result,
                ["penumbra_volume", "penumbra_volume_ml", "penumbra", "penumbra_ml"],
            )
        mismatch = patient_data.get("mismatch_ratio")
        if mismatch is None:
            mismatch = _pick_first_numeric(
                analysis_result, ["mismatch_ratio", "mismatch"]
            )

        raw_context["ctp"] = {
            "core_infarct_volume": core,
            "penumbra_volume": penumbra,
            "mismatch_ratio": mismatch,
        }

        note_text = str(imaging.get("notes") or "").strip()
        note_source = "patient_imaging.notes"
        if not note_text and file_id:
            _, report_json = _load_result_json_for_file(file_id)
            if isinstance(report_json, dict):
                doctor_notes = report_json.get("doctor_notes") or {}
                if isinstance(doctor_notes, dict):
                    note_text = str(
                        doctor_notes.get("text") or doctor_notes.get("html") or ""
                    ).strip()
                    if note_text:
                        note_source = "result_json.doctor_notes"
        raw_context["doctor_notes"] = {
            "text": note_text,
            "source": note_source,
        }
    else:
        result["missing_flags"].append("未找到影像记录（patient_imaging）。")
        raw_context["ctp"] = {
            "core_infarct_volume": patient_data.get("core_infarct_volume"),
            "penumbra_volume": patient_data.get("penumbra_volume"),
            "mismatch_ratio": patient_data.get("mismatch_ratio"),
        }

    masked = mask_patient_context(raw_context)
    if not masked.get("imaging", {}).get("file_id"):
        result["missing_flags"].append("未找到对应报告JSON。")
    ctp_masked = masked.get("ctp_quantification", {})
    if (
        ctp_masked.get("core_infarct_volume") is None
        and ctp_masked.get("penumbra_volume") is None
        and ctp_masked.get("mismatch_ratio") is None
    ):
        result["missing_flags"].append("未找到CTP量化字段。")
    if not (masked.get("doctor_notes", {}).get("text") or "").strip():
        result["missing_flags"].append("未找到医生备注。")

    result["context_struct"] = masked
    result["context_summary"] = _build_context_summary(masked, result["missing_flags"])
    return result


def _build_chat_system_prompt(parsed_text: str, session_context: dict):
    system_content = "你是一位专业的神经放射科医生，擅长脑卒中影像诊断和分析。"

    if session_context and isinstance(session_context.get("context_struct"), dict):
        context_struct = session_context.get("context_struct")
        context_json = json.dumps(context_struct, ensure_ascii=False)
        system_content += (
            "\n\n当前会话已加载脱敏病例上下文，请优先基于该上下文与医生备注回答。"
            "\n要求：不得编造缺失字段；缺失时必须明确写“未提供/需补充”。"
            f"\n\n[脱敏病例上下文]\n{context_json}"
        )
    else:
        system_content += (
            "\n\n若需要结合具体病例，请先让医生输入患者ID（如500）加载脱敏上下文。"
        )

    if parsed_text:
        system_content += (
            f"\n\n以下是用户上传PDF的解析内容，请结合回答：\n\n{parsed_text}"
        )
    return system_content


def _decode_data_uri(data_uri: str):
    if not data_uri or not isinstance(data_uri, str):
        return None, None
    if not data_uri.startswith("data:"):
        return None, None
    try:
        header, b64_data = data_uri.split(",", 1)
    except ValueError:
        return None, None
    mime = header.split(";")[0].replace("data:", "").strip()
    try:
        file_bytes = base64.b64decode(b64_data)
    except Exception:
        return None, None
    return file_bytes, mime


def _upload_baichuan_file(
    file_bytes: bytes, filename: str, purpose: str = "medical"
) -> str:
    if not BAICHUAN_API_KEY:
        return ""
    api_base = _get_baichuan_api_base()
    url = f"{api_base}/files"
    headers = {"Authorization": f"Bearer {BAICHUAN_API_KEY}"}
    files = {"file": (filename, file_bytes)}
    data = {"purpose": purpose}
    response = requests.post(url, headers=headers, files=files, data=data, timeout=60)
    if response.status_code != 200:
        return ""
    result = response.json() or {}
    return result.get("id", "")


def _fetch_baichuan_parsed_content(
    file_id: str, timeout_seconds: int = 30, interval_seconds: int = 2
) -> str:
    if not file_id or not BAICHUAN_API_KEY:
        return ""
    api_base = _get_baichuan_api_base()
    url = f"{api_base}/files/{file_id}/parsed-content"
    headers = {"Authorization": f"Bearer {BAICHUAN_API_KEY}"}
    start_time = time.time()
    while True:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code != 200:
            return ""
        result = response.json() or {}
        status = result.get("status")
        if status == "online":
            return result.get("content", "")
        if status in ("fail", "unsafe"):
            return ""
        if time.time() - start_time > timeout_seconds:
            return ""
        time.sleep(interval_seconds)


def _collect_pdf_parsed_text(images) -> str:
    if not images:
        return ""
    parsed_blocks = []
    for idx, item in enumerate(images, start=1):
        data_uri = None
        filename = f"upload_{idx}.pdf"
        mime = ""

        if isinstance(item, dict):
            data_uri = item.get("data")
            filename = item.get("name") or filename
            mime = item.get("type") or ""
        elif isinstance(item, str):
            data_uri = item

        if not data_uri:
            continue

        file_bytes, detected_mime = _decode_data_uri(data_uri)
        if not file_bytes:
            continue

        mime = mime or detected_mime
        if mime != "application/pdf":
            continue

        file_id = _upload_baichuan_file(file_bytes, filename, purpose="medical")
        if not file_id:
            continue

        parsed_content = _fetch_baichuan_parsed_content(file_id)
        if not parsed_content:
            continue

        parsed_blocks.append(f"[PDF文件: {filename}]\n{_truncate_text(parsed_content)}")

    if not parsed_blocks:
        return ""
    return "\n\n".join(parsed_blocks)


def _append_kb_to_chat_payload(payload: dict) -> None:
    """Attach Baichuan knowledge-base options when IDs are configured."""
    if BAICHUAN_KB_IDS:
        payload["with_search_enhance"] = True
        payload["knowledge_base"] = {"ids": BAICHUAN_KB_IDS}


def _is_kb_model_unsupported_error(resp_text: str) -> bool:
    text = (resp_text or "").lower()
    return "knowledge base does not support model" in text


def _post_baichuan_chat_with_kb_fallback(headers, payload, timeout=60, stream=False):
    """
    Send chat request and retry once without KB if the model is unsupported by KB.
    Returns: (response, kb_fallback_used: bool)
    """
    response = requests.post(
        BAICHUAN_API_URL, headers=headers, json=payload, timeout=timeout, stream=stream
    )

    kb_fallback_used = False
    if (
        response.status_code == 400
        and payload.get("knowledge_base")
        and _is_kb_model_unsupported_error(response.text)
    ):
        retry_payload = dict(payload)
        retry_payload.pop("knowledge_base", None)
        retry_payload.pop("with_search_enhance", None)
        kb_fallback_used = True
        print(
            f"[Baichuan Chat] KB unsupported for model={payload.get('model')}, retrying without KB"
        )
        response = requests.post(
            BAICHUAN_API_URL,
            headers=headers,
            json=retry_payload,
            timeout=timeout,
            stream=stream,
        )

    return response, kb_fallback_used


@app.route("/api/chat/clinical/stream", methods=["POST"])
def api_chat_clinical_stream():
    """医疗AI临床聊天接口 - 流式响应 (SSE)"""
    data = request.get_json() or {}
    session_id = data.get("sessionId")
    question = data.get("question")
    images = data.get("images", [])
    patient_context = data.get("patientContext", {})

    if not session_id or not question:
        return jsonify({"success": False, "error": "缺少会话ID或问题"}), 400

    def generate_stream():
        command_patient_id = _extract_patient_id_command(question)
        if command_patient_id is not None:
            context_result = load_patient_context_by_id(command_patient_id)
            if context_result.get("found"):
                _set_chat_context(session_id, context_result)
            else:
                _clear_chat_context(session_id)
            yield _sse_format(
                {
                    "type": "delta",
                    "content": context_result.get(
                        "context_summary",
                        f"暂未找到患者ID {command_patient_id} 的相关内容。",
                    ),
                }
            )
            yield _sse_format({"type": "done"})
            return

        if not BAICHUAN_API_KEY:
            mock_text = "当前未配置 BAICHUAN_API_KEY，无法进行实时问答。"
            yield _sse_format({"type": "delta", "content": mock_text})
            yield _sse_format({"type": "done"})
            return

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {BAICHUAN_API_KEY}",
        }

        parsed_text = _collect_pdf_parsed_text(images)
        session_context = _get_chat_context(session_id)
        system_content = _build_chat_system_prompt(parsed_text, session_context)

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": question},
        ]

        print(
            f"[Baichuan Chat] stream model={BAICHUAN_CHAT_MODEL} session_id={session_id}"
        )
        payload = {
            "model": BAICHUAN_CHAT_MODEL,
            "messages": messages,
            "max_tokens": 8192,
            "temperature": 0.4,
            "top_p": 0.5,
            "top_k": 10,
            "stream": True,
        }
        _append_kb_to_chat_payload(payload)

        try:
            response, kb_fallback_used = _post_baichuan_chat_with_kb_fallback(
                headers=headers, payload=payload, timeout=60, stream=True
            )
        except Exception as e:
            yield _sse_format({"type": "error", "error": f"API请求失败: {e}"})
            yield _sse_format({"type": "done"})
            return

        if kb_fallback_used:
            yield _sse_format(
                {
                    "type": "delta",
                    "content": "提示：当前问诊模型不支持知识库增强，本次已自动切换为不带知识库的回答模式。\n\n",
                }
            )

        if response.status_code != 200:
            error_text = response.text[:2000]
            yield _sse_format(
                {"type": "error", "error": f"API调用失败: {response.status_code}"}
            )
            if error_text:
                yield _sse_format({"type": "delta", "content": error_text})
            yield _sse_format({"type": "done"})
            return

        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
            if not line.startswith("data:"):
                continue

            data_str = line[len("data:") :].strip()
            if data_str == "[DONE]":
                yield _sse_format({"type": "done"})
                break

            try:
                chunk = json.loads(data_str)
            except json.JSONDecodeError:
                continue

            delta = ""
            if isinstance(chunk, dict):
                if "choices" in chunk and chunk["choices"]:
                    choice = chunk["choices"][0]
                    if isinstance(choice, dict):
                        if "delta" in choice and isinstance(choice["delta"], dict):
                            delta = choice["delta"].get("content", "")
                        elif "message" in choice and isinstance(
                            choice["message"], dict
                        ):
                            delta = choice["message"].get("content", "")
                        elif "text" in choice:
                            delta = choice.get("text", "")
                elif "content" in chunk:
                    delta = chunk.get("content", "")

            if delta:
                yield _sse_format({"type": "delta", "content": delta})

    return Response(
        stream_with_context(generate_stream()),
        content_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.route("/api/chat/clinical/", methods=["POST"])
def api_chat_clinical():
    """医疗AI临床聊天接口"""
    try:
        data = request.get_json() or {}
        session_id = data.get("sessionId")
        question = data.get("question")
        images = data.get("images", [])
        patient_context = data.get("patientContext", {})

        if not session_id or not question:
            return jsonify({"success": False, "error": "缺少会话ID或问题"}), 400

        command_patient_id = _extract_patient_id_command(question)
        if command_patient_id is not None:
            context_result = load_patient_context_by_id(command_patient_id)
            if context_result.get("found"):
                _set_chat_context(session_id, context_result)
            else:
                _clear_chat_context(session_id)
            return jsonify(
                {
                    "success": True,
                    "message": {
                        "role": "assistant",
                        "content": context_result.get(
                            "context_summary",
                            f"暂未找到患者ID {command_patient_id} 的相关内容。",
                        ),
                    },
                    "context_loaded": bool(context_result.get("found")),
                    "context_patient_id": command_patient_id,
                    "context_file_id": context_result.get("file_id"),
                }
            )

        # 调用百川API进行临床问答
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {BAICHUAN_API_KEY}",
        }

        parsed_text = _collect_pdf_parsed_text(images)
        session_context = _get_chat_context(session_id)
        system_content = _build_chat_system_prompt(parsed_text, session_context)

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": question},
        ]

        print(
            f"[Baichuan Chat] sync model={BAICHUAN_CHAT_MODEL} session_id={session_id}"
        )
        payload = {
            "model": BAICHUAN_CHAT_MODEL,
            "messages": messages,
            "max_tokens": 8192,
            "temperature": 0.4,
            "top_p": 0.5,
            "top_k": 10,
        }
        _append_kb_to_chat_payload(payload)

        response, kb_fallback_used = _post_baichuan_chat_with_kb_fallback(
            headers=headers, payload=payload, timeout=60, stream=False
        )

        if response.status_code == 200:
            result = response.json()
            ai_response = (
                result.get("choices", [{}])[0].get("message", {}).get("content", "")
            )

            return jsonify(
                {
                    "success": True,
                    "message": {"role": "assistant", "content": ai_response},
                    "kb_fallback_used": kb_fallback_used,
                    "context_loaded": bool(session_context),
                    "context_patient_id": session_context.get("patient_id")
                    if session_context
                    else None,
                    "context_file_id": session_context.get("file_id")
                    if session_context
                    else None,
                }
            )
        else:
            return jsonify(
                {"success": False, "error": f"API调用失败: {response.status_code}"}
            ), 500

    except Exception as e:
        print(f"聊天错误: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/kb/docs", methods=["GET"])
def api_kb_docs():
    """返回知识库PDF列表"""
    docs = []
    if os.path.isdir(KB_PDF_DIR):
        for filename in sorted(os.listdir(KB_PDF_DIR)):
            if not filename.lower().endswith(".pdf"):
                continue
            title = os.path.splitext(filename)[0]
            docs.append(
                {
                    "title": title,
                    "fileName": filename,
                    "url": f"{KB_PDF_URL_PREFIX}/{filename}",
                }
            )
    return jsonify({"success": True, "docs": docs})


@app.route("/kb-pdfs/<path:filename>")
def serve_kb_pdf(filename):
    """提供知识库PDF文件"""
    if not filename.lower().endswith(".pdf"):
        return jsonify({"error": "只允许PDF文件"}), 400
    if not os.path.isdir(KB_PDF_DIR):
        return jsonify({"error": "PDF目录不存在"}), 404
    return send_from_directory(KB_PDF_DIR, filename, mimetype="application/pdf")


@app.route("/report/<int:patient_id>")
def report_page(patient_id):
    """渲染报告页面
    
    生产环境：直接返回 Vite 构建的 index.html（已包含正确的 /static/dist/ 前缀）
    开发环境：提示开启 Vite 开发服务器或先构建前端
    """
    dist_index = os.path.join(app.static_folder, "dist", "index.html")
    
    if os.path.exists(dist_index):
        # ✅ 直接返回构建好的文件，无需正则替换（Vite 已配置 base 路径）
        return send_from_directory(os.path.join(app.static_folder, "dist"), "index.html")
    else:
        # ⚠️ 开发环境提示
        return jsonify({
            "error": "前端应用未构建",
            "solution": [
                "方案1（推荐）：cd frontend && npm run build",
                "方案2（开发）：cd frontend && npm run dev，然后访问 http://localhost:5173"
            ]
        }), 404


@app.route("/assets/<path:filename>")
def serve_vite_assets(filename):
    """为 Vite 构建的前端应用提供静态资源（JS/CSS 等）"""
    dist_assets = os.path.join(app.static_folder, "dist", "assets")
    return send_from_directory(dist_assets, filename)


# ==================== 图像对比度调节API ====================


@app.route("/adjust_contrast/<file_id>/<int:slice_index>/<image_type>")
def adjust_contrast(file_id, slice_index, image_type):
    """
    调节图像对比度（窗宽窗位）

    参数:
    - file_id: 文件ID
    - slice_index: 切片索引
    - image_type: 图像类型 (mcta, ncct)
    - window_width: 窗宽 (查询参数)
    - window_level: 窗位 (查询参数)
    """
    try:
        # 获取窗宽窗位参数
        window_width = float(request.args.get("ww", 80))
        window_level = float(request.args.get("wl", 40))

        # 验证图像类型
        if image_type not in ["mcta", "ncct"]:
            return jsonify({"error": "无效的图像类型"}), 400

        # 构建原始图像路径
        slice_prefix = f"slice_{slice_index:03d}"
        original_path = os.path.join(
            app.config["PROCESSED_FOLDER"], file_id, f"{slice_prefix}_{image_type}.png"
        )

        if not os.path.exists(original_path):
            return jsonify({"error": "原始图像不存在"}), 404

        # 加载原始图像
        original_img = Image.open(original_path).convert("L")
        img_array = np.array(original_img, dtype=np.float32)

        # 应用窗宽窗位调节
        adjusted_array = apply_window_level(img_array, window_width, window_level)

        # 转换为PIL图像
        adjusted_img = Image.fromarray(adjusted_array.astype(np.uint8))

        # 返回调节后的图像
        from io import BytesIO

        img_buffer = BytesIO()
        adjusted_img.save(img_buffer, format="PNG")
        img_buffer.seek(0)

        return send_file(img_buffer, mimetype="image/png")

    except Exception as e:
        print(f"对比度调节错误: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


def apply_window_level(img_array, window_width, window_level):
    """
    应用窗宽窗位调节

    参数:
    - img_array: 输入图像数组 (0-255)
    - window_width: 窗宽
    - window_level: 窗位（窗中心）

    返回:
    - 调节后的图像数组 (0-255)
    """
    # 计算窗口范围
    window_min = window_level - window_width / 2
    window_max = window_level + window_width / 2

    # 应用窗宽窗位变换
    # 将图像值映射到窗口范围内
    adjusted = np.clip(img_array, window_min, window_max)

    # 归一化到0-255
    if window_max > window_min:
        adjusted = ((adjusted - window_min) / (window_max - window_min)) * 255
    else:
        adjusted = np.zeros_like(img_array)

    return adjusted


@app.route("/get_image_histogram/<file_id>/<int:slice_index>/<image_type>")
def get_image_histogram(file_id, slice_index, image_type):
    """
    获取图像直方图数据

    参数:
    - file_id: 文件ID
    - slice_index: 切片索引
    - image_type: 图像类型 (mcta, ncct)
    """
    try:
        # 验证图像类型
        if image_type not in ["mcta", "ncct"]:
            return jsonify({"error": "无效的图像类型"}), 400

        # 构建图像路径
        slice_prefix = f"slice_{slice_index:03d}"
        image_path = os.path.join(
            app.config["PROCESSED_FOLDER"], file_id, f"{slice_prefix}_{image_type}.png"
        )

        if not os.path.exists(image_path):
            return jsonify({"error": "图像不存在"}), 404

        # 加载图像
        img = Image.open(image_path).convert("L")
        img_array = np.array(img)

        # 计算直方图
        histogram, bin_edges = np.histogram(
            img_array.flatten(), bins=256, range=(0, 256)
        )

        # 计算统计信息
        non_zero_mask = img_array > 5  # 忽略背景
        if np.any(non_zero_mask):
            min_val = float(img_array[non_zero_mask].min())
            max_val = float(img_array[non_zero_mask].max())
            mean_val = float(img_array[non_zero_mask].mean())
            std_val = float(img_array[non_zero_mask].std())
        else:
            min_val = 0
            max_val = 255
            mean_val = 128
            std_val = 0

        return jsonify(
            {
                "success": True,
                "histogram": histogram.tolist(),
                "statistics": {
                    "min": min_val,
                    "max": max_val,
                    "mean": mean_val,
                    "std": std_val,
                },
                "suggested_window": {
                    "width": max_val - min_val,
                    "level": (max_val + min_val) / 2,
                },
            }
        )

    except Exception as e:
        print(f"获取直方图错误: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/save_contrast_settings/<file_id>", methods=["POST"])
def save_contrast_settings(file_id):
    """
    保存对比度设置

    请求体:
    {
        "cta": {"windowWidth": 80, "windowLevel": 40},
        "ncct": {"windowWidth": 80, "windowLevel": 40}
    }
    """
    try:
        settings = request.get_json()

        if not settings:
            return jsonify({"error": "无效的设置数据"}), 400

        # 保存设置到文件
        settings_path = os.path.join(
            app.config["PROCESSED_FOLDER"], file_id, "contrast_settings.json"
        )

        import json

        with open(settings_path, "w") as f:
            json.dump(settings, f, indent=2, cls=NumpyJSONEncoder)

        return jsonify({"success": True, "message": "对比度设置已保存"})

    except Exception as e:
        print(f"保存对比度设置错误: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/load_contrast_settings/<file_id>")
def load_contrast_settings(file_id):
    """
    加载对比度设置
    """
    try:
        settings_path = os.path.join(
            app.config["PROCESSED_FOLDER"], file_id, "contrast_settings.json"
        )

        if not os.path.exists(settings_path):
            # 返回默认设置
            return jsonify(
                {
                    "success": True,
                    "settings": {
                        "cta": {"windowWidth": 80, "windowLevel": 40},
                        "ncct": {"windowWidth": 80, "windowLevel": 40},
                    },
                    "is_default": True,
                }
            )

        import json

        with open(settings_path, "r") as f:
            settings = json.load(f)

        return jsonify({"success": True, "settings": settings, "is_default": False})

    except Exception as e:
        print(f"加载对比度设置错误: {e}")
        return jsonify({"error": str(e)}), 500


# ==================== 其余函数保持不变 ====================


def create_brain_mask(image, low_thresh=0.05, high_thresh=0.95):
    """
    改进的脑部掩码生成算法，提高识别完整性
    """
    try:
        from skimage import morphology, measure, filters

        # 提取所有通道中强度最高的通道
        max_channel = np.argmax(np.max(image, axis=(0, 1)))
        channel_img = image[:, :, max_channel]

        print(
            f"通道 {max_channel} 数据范围: [{channel_img.min():.3f}, {channel_img.max():.3f}]"
        )

        # 1. 使用更宽松的阈值范围
        # 先进行高斯滤波减少噪声，但保留更多细节
        smoothed = filters.gaussian(channel_img, sigma=0.5)

        # 计算自适应阈值
        data_min = smoothed.min()
        data_max = smoothed.max()
        data_range = data_max - data_min

        # 自适应阈值计算
        adaptive_low = data_min + data_range * low_thresh
        adaptive_high = data_min + data_range * high_thresh

        print(f"自适应阈值: [{adaptive_low:.3f}, {adaptive_high:.3f}]")

        # 初始阈值分割 - 使用更宽松的范围
        initial_mask = np.logical_and(
            smoothed > adaptive_low, smoothed < adaptive_high
        ).astype(np.uint8)

        print(f"初始掩码中值为1的像素数量: {np.sum(initial_mask)}")

        # 2. 改进的连通区域分析
        labeled_mask = measure.label(initial_mask)
        regions = measure.regionprops(labeled_mask)

        if not regions:
            print("未找到任何区域")
            return np.zeros_like(channel_img)

        # 按面积排序，保留更多区域
        regions_sorted = sorted(regions, key=lambda r: r.area, reverse=True)

        print(f"找到 {len(regions_sorted)} 个连通区域")
        print("前5个区域面积:", [r.area for r in regions_sorted[:5]])

        # 创建包含多个大区域的掩码
        brain_mask = np.zeros_like(channel_img, dtype=np.uint8)
        total_area = 0
        area_threshold = max(50, channel_img.shape[0] * channel_img.shape[1] * 0.001)

        for i, region in enumerate(regions_sorted):
            if (
                region.area > area_threshold
                and total_area < channel_img.shape[0] * channel_img.shape[1] * 0.8
            ):
                brain_mask[labeled_mask == region.label] = 1
                total_area += region.area
                if i >= 5:
                    break

        print(f"最终掩码中值为1的像素数量: {np.sum(brain_mask)}")

        # 3. 更温和的形态学操作
        small_disk = morphology.disk(1)

        # 先闭运算填充小孔洞
        closed_mask = morphology.binary_closing(brain_mask, small_disk)

        # 然后开运算去除小噪点
        opened_mask = morphology.binary_opening(closed_mask, small_disk)

        # 填充剩余孔洞
        filled_mask = morphology.remove_small_holes(opened_mask, area_threshold=100)

        # 去除太小的孤立区域
        final_mask = morphology.remove_small_objects(filled_mask, min_size=50)

        # 轻微膨胀以连接邻近区域
        dilated_mask = morphology.binary_dilation(final_mask, small_disk)

        # 最终平滑
        smoothed_mask = morphology.binary_closing(dilated_mask, small_disk)

        final_pixel_count = np.sum(smoothed_mask)
        print(f"处理后掩码像素数量: {final_pixel_count}")
        print(
            f"掩码覆盖率: {final_pixel_count / (channel_img.shape[0] * channel_img.shape[1]) * 100:.1f}%"
        )

        return smoothed_mask.astype(np.float32)

    except ImportError:
        print("skimage不可用，使用简化版本")
        return create_brain_mask_numpy(image, low_thresh, high_thresh)


def create_brain_mask_numpy(image, low_thresh=0.05, high_thresh=0.95):
    """
    使用纯 NumPy 实现的改进脑部掩码生成
    """
    try:
        from scipy import ndimage

        # 提取所有通道中强度最高的通道
        max_channel = np.argmax(np.max(image, axis=(0, 1)))
        channel_img = image[:, :, max_channel]

        # 高斯滤波
        smoothed = ndimage.gaussian_filter(channel_img, sigma=0.5)

        # 自适应阈值
        data_min = smoothed.min()
        data_max = smoothed.max()
        data_range = data_max - data_min

        adaptive_low = data_min + data_range * low_thresh
        adaptive_high = data_min + data_range * high_thresh

        # 阈值分割
        initial_mask = np.logical_and(
            smoothed > adaptive_low, smoothed < adaptive_high
        ).astype(np.uint8)

        # 连通组件分析
        labeled_mask, num_features = ndimage.label(initial_mask)

        if num_features == 0:
            return np.zeros_like(channel_img)

        # 计算每个组件的面积
        sizes = ndimage.sum(initial_mask, labeled_mask, range(1, num_features + 1))

        # 创建掩码，保留面积足够大的组件
        brain_mask = np.zeros_like(channel_img)
        min_size = max(50, channel_img.shape[0] * channel_img.shape[1] * 0.001)

        for i in range(num_features):
            if sizes[i] >= min_size:
                brain_mask[labeled_mask == i + 1] = 1

        # 形态学操作
        structure = np.ones((2, 2))

        # 闭运算填充孔洞
        closed_mask = ndimage.binary_closing(brain_mask, structure=structure)

        # 开运算去除噪声
        opened_mask = ndimage.binary_opening(closed_mask, structure=structure)

        # 填充剩余孔洞
        filled_mask = ndimage.binary_fill_holes(opened_mask)

        # 最终闭运算平滑边界
        final_mask = ndimage.binary_closing(filled_mask, structure=structure)

        return final_mask.astype(np.float32)

    except ImportError:
        # 最简版本 - 直接阈值
        max_channel = np.argmax(np.max(image, axis=(0, 1)))
        channel_img = image[:, :, max_channel]

        data_min = channel_img.min()
        data_max = channel_img.max()
        data_range = data_max - data_min

        adaptive_low = data_min + data_range * low_thresh
        adaptive_high = data_min + data_range * high_thresh

        mask = np.logical_and(
            channel_img > adaptive_low, channel_img < adaptive_high
        ).astype(np.float32)
        return mask


def create_adaptive_brain_mask(image):
    """
    使用自适应阈值方法的脑部掩码生成
    """
    try:
        from skimage import filters, morphology, measure

        max_channel = np.argmax(np.max(image, axis=(0, 1)))
        channel_img = image[:, :, max_channel]

        # 使用Otsu方法自动计算阈值
        try:
            otsu_threshold = filters.threshold_otsu(channel_img)
            # 基于Otsu阈值设置范围
            low_thresh = otsu_threshold * 0.3
            high_thresh = otsu_threshold * 2.0
        except:
            # 如果Otsu失败，使用百分比
            low_thresh = np.percentile(channel_img, 10)
            high_thresh = np.percentile(channel_img, 90)

        print(f"自适应阈值: [{low_thresh:.3f}, {high_thresh:.3f}]")

        initial_mask = np.logical_and(
            channel_img > low_thresh, channel_img < high_thresh
        ).astype(np.uint8)

        # 后续处理
        labeled_mask = measure.label(initial_mask)
        regions = measure.regionprops(labeled_mask)

        if not regions:
            return np.zeros_like(channel_img)

        regions_sorted = sorted(regions, key=lambda r: r.area, reverse=True)
        brain_mask = np.zeros_like(channel_img, dtype=np.uint8)

        for i, region in enumerate(regions_sorted[:3]):
            if region.area > 100:
                brain_mask[labeled_mask == region.label] = 1

        # 温和的形态学操作
        small_disk = morphology.disk(1)
        cleaned_mask = morphology.binary_opening(brain_mask, small_disk)
        filled_mask = morphology.remove_small_holes(cleaned_mask, area_threshold=50)
        final_mask = morphology.binary_closing(filled_mask, small_disk)

        return final_mask.astype(np.float32)

    except Exception as e:
        print(f"自适应方法失败: {e}")
        return create_brain_mask(image)


def create_otsu_brain_mask(image):
    """
    使用Otsu阈值方法的脑部掩码生成
    """
    try:
        from skimage import filters, morphology, measure

        max_channel = np.argmax(np.max(image, axis=(0, 1)))
        channel_img = image[:, :, max_channel]

        # Otsu自动阈值
        otsu_threshold = filters.threshold_otsu(channel_img)
        initial_mask = channel_img > otsu_threshold

        # 形态学操作
        small_disk = morphology.disk(1)
        cleaned_mask = morphology.binary_opening(initial_mask, small_disk)
        filled_mask = morphology.remove_small_holes(cleaned_mask, area_threshold=100)
        final_mask = morphology.binary_closing(filled_mask, small_disk)

        return final_mask.astype(np.float32)

    except Exception as e:
        print(f"Otsu方法失败: {e}")
        return create_brain_mask(image)


def create_overlay_image(rgb_data, mask, output_dir, slice_idx):
    """
    创建原始图像与掩码的叠加图像
    """
    try:
        # 提取强度最高的通道作为灰度背景
        max_channel = np.argmax(np.max(rgb_data, axis=(0, 1)))
        background = rgb_data[:, :, max_channel]

        # 归一化背景
        background_normalized = (background - background.min()) / (
            background.max() - background.min()
        )
        background_8bit = (background_normalized * 255).astype(np.uint8)

        # 创建RGB叠加图像
        overlay = np.stack([background_8bit] * 3, axis=2)

        # 在掩码区域添加红色叠加
        mask_indices = mask > 0.5
        overlay[mask_indices, 0] = 255
        overlay[mask_indices, 1] = np.minimum(overlay[mask_indices, 1], 150)
        overlay[mask_indices, 2] = np.minimum(overlay[mask_indices, 2], 150)

        # 保存叠加图像
        overlay_path = os.path.join(output_dir, f"slice_{slice_idx:03d}_overlay.png")
        Image.fromarray(overlay).save(overlay_path)

        return f"/get_image/{os.path.basename(output_dir)}/slice_{slice_idx:03d}_overlay.png"

    except Exception as e:
        print(f"创建叠加图像失败: {e}")
        return ""


def generate_mask_for_slice(rgb_data, output_dir, slice_idx):
    """
    为单个切片生成掩码，尝试多种方法 - 修正版本
    """
    try:
        print(f"为切片 {slice_idx} 生成掩码...")

        # 尝试多种方法，选择最好的一个
        methods = ["adaptive", "standard", "otsu"]
        best_mask = None
        best_coverage = 0
        best_method = "unknown"

        for method in methods:
            try:
                if method == "adaptive":
                    mask = create_adaptive_brain_mask(rgb_data)
                elif method == "otsu":
                    mask = create_otsu_brain_mask(rgb_data)
                else:
                    mask = create_brain_mask(
                        rgb_data, low_thresh=0.01, high_thresh=0.99
                    )

                coverage = np.sum(mask) / (mask.shape[0] * mask.shape[1])
                print(f"方法 {method} 覆盖率: {coverage:.3f}")

                if coverage > best_coverage and coverage > 0.02 and coverage < 0.98:
                    best_mask = mask
                    best_coverage = coverage
                    best_method = method

            except Exception as e:
                print(f"方法 {method} 失败: {e}")
                continue

        if best_mask is None:
            print("所有方法都失败，使用默认方法")
            best_mask = create_brain_mask(rgb_data, low_thresh=0.00, high_thresh=0.99)
            best_method = "default"
            best_coverage = np.sum(best_mask) / (
                best_mask.shape[0] * best_mask.shape[1]
            )

        print(f"选择方法: {best_method}, 最终覆盖率: {best_coverage:.3f}")

        # 保存掩码为PNG图像
        mask_8bit = (best_mask * 255).astype(np.uint8)
        mask_path = os.path.join(output_dir, f"slice_{slice_idx:03d}_mask.png")
        Image.fromarray(mask_8bit).save(mask_path)

        # 保存掩码为NPY文件
        mask_npy_path = os.path.join(output_dir, f"slice_{slice_idx:03d}_mask.npy")
        np.save(mask_npy_path, best_mask)

        # 生成叠加图像
        overlay_url = create_overlay_image(rgb_data, best_mask, output_dir, slice_idx)

        return {
            "success": True,
            "mask_url": f"/get_image/{os.path.basename(output_dir)}/slice_{slice_idx:03d}_mask.png",
            "mask_npy_url": f"/get_file/{os.path.basename(output_dir)}/slice_{slice_idx:03d}_mask.npy",
            "overlay_url": overlay_url,
            "coverage": float(best_coverage),
            "method": best_method,
            "mask_data": best_mask,  # 关键：确保返回掩码数据
        }

    except Exception as e:
        print(f"生成掩码失败: {e}")
        # 返回一个空的掩码，但确保包含mask_data
        empty_mask = np.zeros((rgb_data.shape[0], rgb_data.shape[1]))
        mask_path = os.path.join(output_dir, f"slice_{slice_idx:03d}_mask.png")
        Image.fromarray(empty_mask.astype(np.uint8)).save(mask_path)

        mask_npy_path = os.path.join(output_dir, f"slice_{slice_idx:03d}_mask.npy")
        np.save(mask_npy_path, empty_mask)

        overlay_url = create_overlay_image(rgb_data, empty_mask, output_dir, slice_idx)

        return {
            "success": True,
            "mask_url": f"/get_image/{os.path.basename(output_dir)}/slice_{slice_idx:03d}_mask.png",
            "mask_npy_url": f"/get_file/{os.path.basename(output_dir)}/slice_{slice_idx:03d}_mask.npy",
            "overlay_url": overlay_url,
            "coverage": 0.0,
            "method": "error",
            "mask_data": empty_mask,  # 关键：即使失败也返回掩码数据
        }


def process_ai_inference(
    rgb_result,
    mask_result,
    output_dir,
    slice_idx,
    model_key="mrdpm",
    model_type="mrdpm",
):
    """处理单个切片的AI推理 - 支持多模型版本"""
    try:
        # 获取RGB数据
        rgb_data = rgb_result.get("rgb_data")
        if rgb_data is None:
            print(f"⚠ RGB数据不可用")
            return {
                "success": False,
                "error": "RGB数据不可用",
                "ai_url": "",
                "ai_npy_url": "",
            }

        # 获取掩码数据
        mask_data = mask_result.get("mask_data")
        if mask_data is None:
            # 尝试从文件加载掩码
            mask_npy_path = os.path.join(output_dir, f"slice_{slice_idx:03d}_mask.npy")
            if os.path.exists(mask_npy_path):
                try:
                    mask_data = np.load(mask_npy_path)
                    print(f"✓ 从文件加载掩码数据: {mask_npy_path}")
                except Exception as e:
                    print(f"⚠ 加载掩码文件失败: {e}")
                    mask_data = None

        if mask_data is None:
            print(f"⚠ 掩码数据不可用，创建空掩码")
            mask_data = np.zeros_like(rgb_data[:, :, 0])

        # 验证掩码数据
        print(f"{model_key.upper()}模型掩码数据统计:")
        print(f"  - 形状: {mask_data.shape}")
        print(f"  - 值范围: [{mask_data.min():.3f}, {mask_data.max():.3f}]")
        print(f"  - 非零像素: {np.sum(mask_data > 0.5)}")

        # 根据model_type选择不同的模型推理逻辑
        if model_type == "mrdpm":
            print(f"开始{model_key.upper()}模型推理 (使用MRDPM模型)...")
            # MRDPM模型推理逻辑
            # 1. 获取mrdpm模型权重路径
            from ai_inference import MRDPMModel
            import torch

            # 确定mrdpm子模型（当model_key为'mrdpm'时，默认使用'cbf'）
            mrdpm_submodel = model_key if model_key != "mrdpm" else "cbf"

            # 构建mrdpm模型权重路径
            current_dir = os.path.dirname(os.path.abspath(__file__))
            bran_pretrained_path = os.path.join(
                current_dir,
                "mrdpm",
                "weights",
                mrdpm_submodel,
                "bran_pretrained_3channel.pth",
            )
            residual_weight_path = os.path.join(
                current_dir, "mrdpm", "weights", mrdpm_submodel, "200_Network_ema.pth"
            )

            # 验证权重文件是否存在
            print(f"📁 检查BRAN权重文件: {bran_pretrained_path}")
            print(f"📁 检查残差权重文件: {residual_weight_path}")

            if not os.path.exists(bran_pretrained_path):
                print(f"❌ BRAN权重文件不存在: {bran_pretrained_path}")
                return {
                    "success": False,
                    "error": f"BRAN权重文件不存在: {bran_pretrained_path}",
                    "ai_url": "",
                    "ai_npy_url": "",
                }

            if not os.path.exists(residual_weight_path):
                print(f"❌ 残差权重文件不存在: {residual_weight_path}")
                return {
                    "success": False,
                    "error": f"残差权重文件不存在: {residual_weight_path}",
                    "ai_url": "",
                    "ai_npy_url": "",
                }

            print(f"✅ 所有权重文件存在")

            # 2. 初始化MRDPMModel
            mrdpm_model = MRDPMModel(
                bran_pretrained_path,
                residual_weight_path,
                device="cuda" if torch.cuda.is_available() else "cpu",
            )

            # 3. 执行AI推理，传递save_path保存初始预测图
            save_path = os.path.join(
                output_dir, f"slice_{slice_idx:03d}_{model_key}_initial.png"
            )
            ai_output = mrdpm_model.inference(rgb_data, mask_data, save_path)
        else:
            # 默认使用palette模型
            print(f"开始{model_key.upper()}模型推理 (使用palette模型)...")
            ai_model = get_ai_model(model_key)
            if ai_model is None:
                print(f"⚠ {model_key.upper()} 模型未初始化")
                return {
                    "success": False,
                    "error": f"{model_key.upper()}模型未初始化",
                    "ai_url": "",
                    "ai_npy_url": "",
                }

            # 执行AI推理
            ai_output = ai_model.inference(rgb_data, mask_data)

        # 确保输出有效
        if ai_output is None or ai_output.size == 0:
            print(f"✗ {model_key.upper()}模型推理返回空结果")
            return {
                "success": False,
                "error": f"{model_key.upper()}模型推理返回空结果",
                "ai_url": "",
                "ai_npy_url": "",
            }

        # 保存AI结果
        slice_prefix = f"slice_{slice_idx:03d}"
        ai_npy_path = os.path.join(output_dir, f"{slice_prefix}_{model_key}_output.npy")

        # 保存NPY文件
        # 使用合适的方法保存结果
        try:
            # 保存NPY
            np.save(ai_npy_path, ai_output)

            # 保存PNG预览
            from PIL import Image

            png_path = ai_npy_path.replace(".npy", ".png")
            result_8bit = (ai_output * 255).astype(np.uint8)
            Image.fromarray(result_8bit).save(png_path)
            success = True
        except Exception as e:
            print(f"保存结果失败: {e}")
            success = False

        if not success:
            print(f"✗ 保存{model_key.upper()}结果失败")
            return {
                "success": False,
                "error": f"保存{model_key.upper()}结果失败",
                "ai_url": "",
                "ai_npy_url": "",
            }

        # 构建正确的URL路径
        file_id = os.path.basename(output_dir)
        ai_image_url = f"/get_image/{file_id}/{slice_prefix}_{model_key}_output.png"
        ai_npy_url = f"/get_file/{file_id}/{slice_prefix}_{model_key}_output.npy"

        print(f"✓ {model_key.upper()}模型推理成功")
        print(f"AI图像URL: {ai_image_url}")
        print(f"AI数据URL: {ai_npy_url}")

        return {"success": True, "ai_url": ai_image_url, "ai_npy_url": ai_npy_url}

    except Exception as e:
        print(f"✗ {model_key.upper()}模型推理处理失败: {e}")
        traceback.print_exc()
        return {"success": False, "error": str(e), "ai_url": "", "ai_npy_url": ""}


def process_rgb_synthesis(
    mcta_path, vcta_path, dcta_path, ncct_path, output_dir, model_type="mrdpm"
):
    """处理RGB合成，现在支持多模型AI推理"""
    try:
        if not NIBABEL_AVAILABLE:
            return {
                "success": False,
                "error": 'nibabel 库不可用，请安装: pip install "numpy<2.0" nibabel',
            }

        # NCCT 必选
        ncct_img = nib.load(ncct_path)
        ncct_data = ncct_img.get_fdata()
        print(f"NCCT 维度: {ncct_data.shape}")

        def load_optional_nifti(file_path, label):
            if not file_path:
                print(f"{label} 未提供，使用空数据")
                return None, None
            img = nib.load(file_path)
            data = img.get_fdata()
            print(f"{label} 维度: {data.shape}")
            return img, data

        mcta_img, mcta_data = load_optional_nifti(mcta_path, "动脉期CTA")
        vcta_img, vcta_data = load_optional_nifti(vcta_path, "静脉期CTA")
        dcta_img, dcta_data = load_optional_nifti(dcta_path, "延迟期CTA")

        # 检查已提供文件维度是否一致（以 NCCT 为基准）
        for label, data in [
            ("动脉期CTA", mcta_data),
            ("静脉期CTA", vcta_data),
            ("延迟期CTA", dcta_data),
        ]:
            if data is not None and data.shape != ncct_data.shape:
                return {
                    "success": False,
                    "error": f"{label}维度{data.shape}与NCCT维度{ncct_data.shape}不匹配",
                }

        # 对缺失的期相使用零矩阵占位，确保流程一致
        mcta_data = mcta_data if mcta_data is not None else np.zeros_like(ncct_data)
        vcta_data = vcta_data if vcta_data is not None else np.zeros_like(ncct_data)
        dcta_data = dcta_data if dcta_data is not None else np.zeros_like(ncct_data)

        # 获取基本信息
        metadata = {
            "mcta_present": mcta_img is not None,
            "vcta_present": vcta_img is not None,
            "dcta_present": dcta_img is not None,
            "mcta_shape": [int(dim) for dim in mcta_data.shape]
            if mcta_img is not None
            else None,
            "vcta_shape": [int(dim) for dim in vcta_data.shape]
            if vcta_img is not None
            else None,
            "dcta_shape": [int(dim) for dim in dcta_data.shape]
            if dcta_img is not None
            else None,
            "ncct_shape": [int(dim) for dim in ncct_data.shape],
            "mcta_range": [float(mcta_data.min()), float(mcta_data.max())]
            if mcta_img is not None
            else None,
            "vcta_range": [float(vcta_data.min()), float(vcta_data.max())]
            if vcta_img is not None
            else None,
            "dcta_range": [float(dcta_data.min()), float(dcta_data.max())]
            if dcta_img is not None
            else None,
            "ncct_range": [float(ncct_data.min()), float(ncct_data.max())],
            "voxel_dims": [float(dim) for dim in ncct_img.header.get_zooms()[:3]],
        }

        # 处理每个切片
        rgb_files = []
        num_slices = mcta_data.shape[2] if len(mcta_data.shape) >= 3 else 1

        # 检查AI模型可用性
        available_models = get_available_models()
        # MRDPM 推理只需要 CBF/CBV/TMAX 三类子模型，过滤掉占位的 mrdpm 标识
        if model_type == "mrdpm":
            available_models = [key for key in available_models if key in MODEL_CONFIGS]
        models_available = len(available_models) > 0

        print(f"AI模型可用性: {models_available}")
        print(f"可用模型: {available_models}")

        # 记录每个模型的成功推理数量
        model_success_counts = {model_key: 0 for model_key in MODEL_CONFIGS.keys()}
        has_any_model_success = False

        for slice_idx in range(num_slices):
            print(f"\n=== 处理切片 {slice_idx + 1}/{num_slices} ===")

            if len(mcta_data.shape) == 3:
                mcta_slice = mcta_data[:, :, slice_idx]
                vcta_slice = vcta_data[:, :, slice_idx]
                dcta_slice = dcta_data[:, :, slice_idx]
                ncct_slice = ncct_data[:, :, slice_idx]
            elif len(mcta_data.shape) == 4:
                mcta_slice = mcta_data[:, :, slice_idx, 0]
                vcta_slice = vcta_data[:, :, slice_idx, 0]
                dcta_slice = dcta_data[:, :, slice_idx, 0]
                ncct_slice = ncct_data[:, :, slice_idx, 0]
            else:
                mcta_slice = mcta_data
                vcta_slice = vcta_data
                dcta_slice = dcta_data
                ncct_slice = ncct_data

            # 生成RGB合成图像和NPY数据
            rgb_result = generate_rgb_slices(
                mcta_slice,
                vcta_slice,
                dcta_slice,
                ncct_slice,
                output_dir,
                slice_idx,
                mcta_present=(mcta_img is not None),
                vcta_present=(vcta_img is not None),
                dcta_present=(dcta_img is not None),
            )
            if not rgb_result["success"]:
                print(f"⚠ 切片 {slice_idx} RGB合成失败，跳过")
                continue

            # 生成掩码
            mask_result = generate_mask_for_slice(
                rgb_result["rgb_data"], output_dir, slice_idx
            )

            # 确保mask_result包含mask_data
            if "mask_data" not in mask_result:
                print(f"⚠ 切片 {slice_idx} 的掩码生成失败，使用空掩码")
                mask_result["mask_data"] = np.zeros_like(
                    rgb_result["rgb_data"][:, :, 0]
                )

            # 初始化切片结果
            slice_result = {
                "slice_index": slice_idx,
                "rgb_image": rgb_result.get("rgb_url", ""),
                "mcta_image": rgb_result.get("mcta_url", ""),
                "vcta_url": rgb_result.get("vcta_url", ""),
                "dcta_url": rgb_result.get("dcta_url", ""),
                "ncct_image": rgb_result.get("ncct_url", ""),
                "npy_url": rgb_result.get("npy_url", ""),
                "mask_image": mask_result.get("mask_url", ""),
                "mask_npy_url": mask_result.get("mask_npy_url", ""),
                "overlay_url": mask_result.get("overlay_url", ""),
                "coverage": mask_result.get("coverage", 0),
                "method": mask_result.get("method", "unknown"),
            }

            # 为每个模型初始化AI结果
            for model_key in MODEL_CONFIGS.keys():
                slice_result.update(
                    {
                        f"has_{model_key}": False,
                        f"{model_key}_image": "",
                        f"{model_key}_npy_url": "",
                    }
                )

            # 对每个可用模型进行推理
            slice_has_any_ai = False

            for model_key in available_models:
                try:
                    # 根据参数类型选择合适的模型类型
                    # CBF和CBV参数始终使用palette模型
                    # TMAX参数使用用户选择的模型
                    if model_key in ["cbf", "cbv"]:
                        current_model_type = "palette"
                    elif model_key == "tmax":
                        current_model_type = model_type
                    else:
                        current_model_type = model_type

                    print(
                        f"开始{model_key.upper()}模型推理切片 {slice_idx} (使用{current_model_type}模型)..."
                    )
                    ai_result = process_ai_inference(
                        rgb_result,
                        mask_result,
                        output_dir,
                        slice_idx,
                        model_key,
                        current_model_type,
                    )

                    if ai_result and ai_result["success"]:
                        print(f"✓ {model_key.upper()}模型推理完成切片 {slice_idx}")
                        slice_result.update(
                            {
                                f"has_{model_key}": True,
                                f"{model_key}_image": ai_result.get("ai_url", ""),
                                f"{model_key}_npy_url": ai_result.get("ai_npy_url", ""),
                            }
                        )
                        model_success_counts[model_key] += 1
                        slice_has_any_ai = True
                        has_any_model_success = True
                    else:
                        error_msg = (
                            ai_result.get("error", "未知错误")
                            if ai_result
                            else "无结果"
                        )
                        print(
                            f"⚠ {model_key.upper()}模型推理失败切片 {slice_idx}: {error_msg}"
                        )
                except Exception as e:
                    print(f"✗ {model_key.upper()}模型推理异常切片 {slice_idx}: {e}")

            # 添加总体AI状态
            slice_result["has_ai"] = slice_has_any_ai
            rgb_files.append(slice_result)

        # 统计信息
        print(f"\n=== AI模型处理统计 ===")
        print(f"总切片数: {len(rgb_files)}")
        for model_key, count in model_success_counts.items():
            status = "可用" if model_key in available_models else "不可用"
            print(f"{model_key.upper()}模型: {count}个切片成功 ({status})")

        # 在元数据中添加模型状态信息
        metadata.update(
            {
                "models_available": available_models,
                "models_status": {
                    key: key in available_models for key in MODEL_CONFIGS.keys()
                },
                "models_success_counts": model_success_counts,
                "has_any_ai": has_any_model_success,
            }
        )

        # 添加每个模型的详细信息
        for model_key, config in MODEL_CONFIGS.items():
            metadata.update(
                {
                    f"{model_key}_name": config["name"],
                    f"{model_key}_color": config["color"],
                    f"{model_key}_description": config["description"],
                    f"{model_key}_available": model_key in available_models,
                    f"{model_key}_success_count": model_success_counts[model_key],
                }
            )

        # 构建最终返回结果
        result = {
            "success": True,
            "file_id": os.path.basename(output_dir),
            "metadata": metadata,
            "rgb_files": rgb_files,
            "total_slices": int(num_slices),
            "has_ai": has_any_model_success,
            "available_models": available_models,
            "model_configs": MODEL_CONFIGS,
        }

        print(f"\n=== 返回给前端的数据结构 ===")
        print(f"顶层has_ai: {result['has_ai']}")
        print(f"可用模型: {result['available_models']}")
        print(f"模型配置: {list(result['model_configs'].keys())}")
        print("============================\n")

        return result

    except Exception as e:
        print(f"处理RGB合成失败: {e}")
        traceback.print_exc()
        return {"success": False, "error": str(e)}


# 在应用启动时初始化
def initialize_app():
    """应用初始化函数 - 多模型版本"""
    print("=" * 50)
    print("医学图像处理Web系统初始化 - 医学标准伪彩图版本")
    print("=" * 50)

    # 创建必要的目录
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["PROCESSED_FOLDER"], exist_ok=True)

    print(f"上传目录: {app.config['UPLOAD_FOLDER']}")
    print(f"处理目录: {app.config['PROCESSED_FOLDER']}")

    # 初始化AI模型
    ai_initialized = init_ai_models()

    # 设置全局标志
    app.config["AI_AVAILABLE"] = ai_initialized
    app.config["AI_MODELS"] = ai_models
    app.config["MODEL_CONFIGS"] = MODEL_CONFIGS

    print(f"AI功能可用: {ai_initialized}")
    print("✓ 应用初始化完成")
    print("=" * 50)


def ensure_app_initialized():
    """Ensure heavy startup initialization runs only once per process."""
    if getattr(app, "has_initialized", False):
        return
    initialize_app()
    app.has_initialized = True


# 使用应用上下文进行初始化
with app.app_context():
    ensure_app_initialized()


# 添加启动时初始化
@app.before_request
def before_first_request():
    """替代before_first_request的解决方案"""
    ensure_app_initialized()


# 修改下载路由以支持多模型
@app.route("/download_ai/<model_key>/<file_id>/<int:slice_index>")
def download_ai(model_key, file_id, slice_index):
    """下载特定模型的AI推理结果NPY文件"""
    try:
        if model_key not in MODEL_CONFIGS:
            return jsonify({"error": f"无效的模型类型: {model_key}"}), 400

        filename = f"slice_{slice_index:03d}_{model_key}_output.npy"
        file_path = os.path.join(app.config["PROCESSED_FOLDER"], file_id, filename)

        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({"error": "文件不存在"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 404


# 其余函数保持不变...
def generate_rgb_slices(
    mcta_slice,
    vcta_slice,
    dcta_slice,
    ncct_slice,
    output_dir,
    slice_idx,
    mcta_present=True,
    vcta_present=True,
    dcta_present=True,
):
    """
    生成RGB合成图像和单独通道图像
    """
    try:
        # 1. 归一化处理
        mcta_normalized = normalize_slice(mcta_slice)
        vcta_normalized = normalize_slice(vcta_slice)
        dcta_normalized = normalize_slice(dcta_slice)
        ncct_normalized = normalize_slice(ncct_slice)

        # 2. 创建RGB图像 [R, G, B] = [mCTA1, NCCT, 空]
        rgb_data = np.stack(
            [mcta_normalized, ncct_normalized, np.zeros_like(mcta_normalized)], axis=2
        )
        rgb_8bit = (rgb_data * 255).astype(np.uint8)

        # 3. 创建单独通道的图像（用于显示）
        mcta_8bit = (mcta_normalized * 255).astype(np.uint8)
        vcta_8bit = (vcta_normalized * 255).astype(np.uint8)
        dcta_8bit = (dcta_normalized * 255).astype(np.uint8)
        ncct_8bit = (ncct_normalized * 255).astype(np.uint8)

        # 创建输出路径
        slice_prefix = f"slice_{slice_idx:03d}"

        # 保存RGB合成图像
        rgb_path = os.path.join(output_dir, f"{slice_prefix}_rgb.png")
        Image.fromarray(rgb_8bit).save(rgb_path)

        # 保存单独通道图像，仅当对应模态为真实上传（非零矩阵占位）时才保存该通道文件
        mcta_path = os.path.join(output_dir, f"{slice_prefix}_mcta.png")
        vcta_path = os.path.join(output_dir, f"{slice_prefix}_vcta.png")
        dcta_path = os.path.join(output_dir, f"{slice_prefix}_dcta.png")
        ncct_path = os.path.join(output_dir, f"{slice_prefix}_ncct.png")

        if mcta_present:
            Image.fromarray(mcta_8bit).save(mcta_path)
        else:
            mcta_path = ""

        if vcta_present:
            Image.fromarray(vcta_8bit).save(vcta_path)
        else:
            vcta_path = ""

        if dcta_present:
            Image.fromarray(dcta_8bit).save(dcta_path)
        else:
            dcta_path = ""

        # NCCT 总是保存
        Image.fromarray(ncct_8bit).save(ncct_path)

        # 保存NPY数据 - 直接保存RGB数组，而不是字典
        npy_path = os.path.join(output_dir, f"{slice_prefix}_data.npy")
        np.save(npy_path, rgb_data.astype(np.float32))  # 直接保存数组

        # 获取输出目录的basename作为file_id
        file_id = os.path.basename(output_dir)

        return {
            "success": True,
            "rgb_url": f"/get_image/{file_id}/{slice_prefix}_rgb.png",
            "mcta_url": f"/get_image/{file_id}/{slice_prefix}_mcta.png"
            if mcta_present
            else "",
            "vcta_url": f"/get_image/{file_id}/{slice_prefix}_vcta.png"
            if vcta_present
            else "",
            "dcta_url": f"/get_image/{file_id}/{slice_prefix}_dcta.png"
            if dcta_present
            else "",
            "ncct_url": f"/get_image/{file_id}/{slice_prefix}_ncct.png",
            "npy_url": f"/get_file/{file_id}/{slice_prefix}_data.npy",
            "rgb_data": rgb_data,
        }

    except Exception as e:
        print(f"生成RGB切片失败: {e}")
        traceback.print_exc()
        return {"success": False}


def normalize_slice(slice_data):
    """
    归一化切片数据到 [0, 1] 范围
    """
    slice_data = np.nan_to_num(slice_data)

    # 使用2%和98%百分位进行稳健归一化
    lower_bound = np.percentile(slice_data, 2)
    upper_bound = np.percentile(slice_data, 98)

    if upper_bound - lower_bound < 1e-6:
        lower_bound = slice_data.min()
        upper_bound = slice_data.max()
        if upper_bound - lower_bound < 1e-6:
            return np.zeros_like(slice_data)

    # 裁剪异常值并缩放到 0-1
    data_clipped = np.clip(slice_data, lower_bound, upper_bound)
    data_normalized = (data_clipped - lower_bound) / (upper_bound - lower_bound)

    return np.clip(data_normalized, 0, 1)


def generate_modality_slices(nifti_path, output_dir, suffix):
    """
    将单一模态NIfTI生成PNG切片并返回URL列表
    """
    if not nifti_path:
        return [], [], 0
    try:
        # 读取 NIfTI 并统一到 3D 体数据
        img = nib.load(nifti_path)
        data = img.get_fdata()
        if data.ndim == 4:
            data = data[:, :, :, 0]
        elif data.ndim == 2:
            data = data[:, :, np.newaxis]

        # 计算切片数量与文件ID
        num_slices = data.shape[2] if data.ndim == 3 else 1
        file_id = os.path.basename(output_dir)
        urls = []
        npy_urls = []
        for slice_idx in range(num_slices):
            # 提取单张切片并进行归一化
            slice_data = data[:, :, slice_idx] if data.ndim == 3 else data
            normalized = normalize_slice(slice_data)
            # 生成 PNG 预览图
            img_8bit = (normalized * 255).astype(np.uint8)
            slice_prefix = f"slice_{slice_idx:03d}"
            filename = f"{slice_prefix}_{suffix}.png"
            save_path = os.path.join(output_dir, filename)
            Image.fromarray(img_8bit).save(save_path)
            urls.append(f"/get_image/{file_id}/{filename}")
            # 保存归一化后的 NPY 文件（带 _output 后缀）
            npy_filename = f"{slice_prefix}_{suffix}_output.npy"
            npy_path = os.path.join(output_dir, npy_filename)
            np.save(npy_path, normalized.astype(np.float32))
            npy_urls.append(f"/get_file/{file_id}/{npy_filename}")
        return urls, npy_urls, num_slices
    except Exception as e:
        print(f"生成{suffix}切片失败: {e}")
        traceback.print_exc()
        return [], [], 0


@app.route("/")
def index():
    return render_template("patient/index.html")


@app.route("/upload")
def upload_page():
    return render_template("patient/upload/index.html")


@app.route("/viewer")
def viewer_page():
    return render_template("patient/upload/viewer/index.html")


@app.route("/processing")
def processing_page():
    return render_template("patient/upload/processing/index.html")


@app.route("/api/upload/start", methods=["POST"])
def api_upload_start():
    """Start an async upload-processing job and return job_id for polling."""
    try:
        if not NIBABEL_AVAILABLE:
            return jsonify(
                {"success": False, "error": "nibabel 库不可用，请先安装依赖"}
            ), 400

        if "ncct_file" not in request.files:
            return jsonify({"success": False, "error": "请至少上传 NCCT 文件"}), 400

        patient_id_str = request.form.get("patient_id")
        if not patient_id_str:
            return jsonify({"success": False, "error": "缺少 patient_id"}), 400
        try:
            patient_id = int(patient_id_str)
        except ValueError:
            return jsonify({"success": False, "error": "patient_id 非法"}), 400

        valid_extensions = [".nii", ".nii.gz"]

        def get_optional_file(key):
            f = request.files.get(key)
            if not f or f.filename == "":
                return None
            return f

        def is_valid_nifti(file_obj):
            return any(
                file_obj.filename.lower().endswith(ext) for ext in valid_extensions
            )

        files = {
            "ncct_file": request.files["ncct_file"],
            "mcta_file": get_optional_file("mcta_file"),
            "vcta_file": get_optional_file("vcta_file"),
            "dcta_file": get_optional_file("dcta_file"),
            "cbf_file": get_optional_file("cbf_file"),
            "cbv_file": get_optional_file("cbv_file"),
            "tmax_file": get_optional_file("tmax_file"),
        }

        if files["ncct_file"].filename == "" or not is_valid_nifti(files["ncct_file"]):
            return jsonify(
                {
                    "success": False,
                    "error": "NCCT 文件格式不正确（仅支持 .nii/.nii.gz）",
                }
            ), 400

        for key, f in files.items():
            if key == "ncct_file":
                continue
            if f and not is_valid_nifti(f):
                return jsonify(
                    {
                        "success": False,
                        "error": f"{key} 文件格式不正确（仅支持 .nii/.nii.gz）",
                    }
                ), 400

        requested_file_id = (request.form.get("file_id") or "").strip()
        if requested_file_id:
            safe_file_id = re.sub(r"[^a-zA-Z0-9_-]", "", requested_file_id)[:32]
            file_id = safe_file_id or str(uuid.uuid4())[:8]
        else:
            file_id = str(uuid.uuid4())[:8]

        job_id = str(uuid.uuid4())
        temp_dir = os.path.join(app.config["UPLOAD_FOLDER"], "_jobs", job_id)
        os.makedirs(temp_dir, exist_ok=True)

        saved_files = {}
        detected_modalities = []
        modality_map = {
            "ncct_file": "ncct",
            "mcta_file": "mcta",
            "vcta_file": "vcta",
            "dcta_file": "dcta",
            "cbf_file": "cbf",
            "cbv_file": "cbv",
            "tmax_file": "tmax",
        }

        for field_name, f in files.items():
            if not f:
                continue
            safe_name = os.path.basename(f.filename)
            temp_path = os.path.join(temp_dir, f"{field_name}_{safe_name}")
            f.save(temp_path)
            saved_files[field_name] = {
                "path": temp_path,
                "filename": safe_name,
            }
            detected_modalities.append(modality_map[field_name])

        normalized_modalities = _normalize_uploaded_modalities(detected_modalities)

        _create_upload_job(job_id, patient_id, file_id, normalized_modalities)
        _update_step(
            job_id, "archive_ready", "completed", f"患者档案已建立（ID={patient_id}）"
        )
        _update_step(
            job_id, "modality_detect", "completed", f"识别模态: {normalized_modalities}"
        )

        payload = {
            "job_id": job_id,
            "patient_id": patient_id,
            "file_id": file_id,
            "files": saved_files,
            "temp_dir": temp_dir,
            "modalities": normalized_modalities,
            "hemisphere": request.form.get("hemisphere", "both"),
            "model_type": request.form.get("model_type", "mrdpm"),
            "upload_mode": request.form.get("upload_mode", "ncct"),
            "cta_phase": request.form.get("cta_phase", ""),
            "skip_ai": (request.form.get("skip_ai") == "true"),
        }

        worker = threading.Thread(
            target=_run_upload_processing_job, args=(job_id, payload), daemon=True
        )
        worker.start()

        return jsonify(
            {
                "success": True,
                "job_id": job_id,
                "file_id": file_id,
                "status": "queued",
                "progress_url": f"/api/upload/progress/{job_id}",
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": f"启动处理任务失败: {str(e)}"}), 500


@app.route("/api/upload/progress/<job_id>", methods=["GET"])
def api_upload_progress(job_id):
    job = _get_upload_job(job_id)
    if not job:
        return jsonify({"success": False, "error": "任务不存在或已过期"}), 404
    return jsonify({"success": True, "job": job})


@app.route("/upload", methods=["POST"])
def upload_files():
    """处理四文件上传 - 多模型版本"""
    try:
        print("收到上传请求...")

        if not NIBABEL_AVAILABLE:
            return jsonify(
                {
                    "success": False,
                    "error": 'nibabel 库不可用。请运行: pip install "numpy<2.0" nibabel',
                }
            )

        # NCCT 必选，其余期相可选
        if "ncct_file" not in request.files:
            return jsonify({"success": False, "error": "请至少选择NCCT文件"})

        def get_optional_file(key):
            file_obj = request.files.get(key)
            if not file_obj or file_obj.filename == "":
                return None
            return file_obj

        mcta_file = get_optional_file("mcta_file")
        vcta_file = get_optional_file("vcta_file")
        dcta_file = get_optional_file("dcta_file")
        ncct_file = request.files["ncct_file"]
        cbf_file = get_optional_file("cbf_file")
        cbv_file = get_optional_file("cbv_file")
        tmax_file = get_optional_file("tmax_file")

        if ncct_file.filename == "":
            return jsonify({"success": False, "error": "请至少选择NCCT文件"})

        # 检查文件格式
        valid_extensions = [".nii", ".nii.gz"]

        def is_valid_nifti(file_obj):
            return any(
                file_obj.filename.lower().endswith(ext) for ext in valid_extensions
            )

        if not is_valid_nifti(ncct_file):
            return jsonify(
                {"success": False, "error": "请上传NIfTI文件 (.nii 或 .nii.gz)"}
            )
        for optional_file in [
            mcta_file,
            vcta_file,
            dcta_file,
            cbf_file,
            cbv_file,
            tmax_file,
        ]:
            if optional_file and not is_valid_nifti(optional_file):
                return jsonify(
                    {"success": False, "error": "请上传NIfTI文件 (.nii 或 .nii.gz)"}
                )

        print("文件验证通过:")
        print(f"NCCT: {ncct_file.filename}")
        if mcta_file:
            print(f"动脉期CTA: {mcta_file.filename}")
        if vcta_file:
            print(f"静脉期CTA: {vcta_file.filename}")
        if dcta_file:
            print(f"延迟期CTA: {dcta_file.filename}")

        # 生成（或复用）唯一ID
        requested_file_id = (request.form.get("file_id") or "").strip()
        if requested_file_id:
            safe_file_id = re.sub(r"[^a-zA-Z0-9_-]", "", requested_file_id)[:32]
            file_id = safe_file_id or str(uuid.uuid4())[:8]
        else:
            file_id = str(uuid.uuid4())[:8]

        # 保存上传的文件
        ncct_extension = (
            ".nii.gz" if ncct_file.filename.lower().endswith(".nii.gz") else ".nii"
        )

        def save_optional_file(file_obj, suffix):
            if not file_obj:
                return None
            extension = (
                ".nii.gz" if file_obj.filename.lower().endswith(".nii.gz") else ".nii"
            )
            file_path = os.path.join(
                app.config["UPLOAD_FOLDER"], f"{file_id}_{suffix}{extension}"
            )
            file_obj.save(file_path)
            return file_path

        mcta_path = save_optional_file(mcta_file, "mcta")
        vcta_path = save_optional_file(vcta_file, "vcta")
        dcta_path = save_optional_file(dcta_file, "dcta")
        cbf_path = save_optional_file(cbf_file, "cbf")
        cbv_path = save_optional_file(cbv_file, "cbv")
        tmax_path = save_optional_file(tmax_file, "tmax")
        ncct_path = os.path.join(
            app.config["UPLOAD_FOLDER"], f"{file_id}_ncct{ncct_extension}"
        )
        ncct_file.save(ncct_path)

        print(f"文件保存成功: NCCT={ncct_path}")
        if mcta_path:
            print(f"动脉期CTA: {mcta_path}")
        if vcta_path:
            print(f"静脉期CTA: {vcta_path}")
        if dcta_path:
            print(f"延迟期CTA: {dcta_path}")
        if cbf_path:
            print(f"CBF功能图: {cbf_path}")
        if cbv_path:
            print(f"CBV功能图: {cbv_path}")
        if tmax_path:
            print(f"TMAX功能图: {tmax_path}")

        # 根据前端上传的切片更新 available_modalities（仅原始上传，不含AI生成）
        patient_id_str = request.form.get("patient_id")
        patient_id = None
        if patient_id_str:
            try:
                patient_id = int(patient_id_str)
            except ValueError:
                patient_id = None

        # 将偏侧信息写入 patient_imaging 表（根据 patient_id + case_id）
        hemisphere = request.form.get("hemisphere", "both")
        try:
            if SUPABASE_AVAILABLE and patient_id:
                try:
                    # 先尝试更新已存在记录
                    update_resp = (
                        supabase.table("patient_imaging")
                        .update({"hemisphere": hemisphere})
                        .eq("patient_id", patient_id)
                        .eq("case_id", file_id)
                        .execute()
                    )
                    if update_resp.data and len(update_resp.data) > 0:
                        print(
                            f"patient_imaging 已更新偏侧: patient_id={patient_id}, case_id={file_id}, hemisphere={hemisphere}"
                        )
                    else:
                        # 若未更新到任何行，则插入新记录
                        insert_payload = {
                            "patient_id": patient_id,
                            "case_id": file_id,
                            "hemisphere": hemisphere,
                        }
                        insert_resp = (
                            supabase.table("patient_imaging")
                            .insert([insert_payload])
                            .execute()
                        )
                        if insert_resp.data and len(insert_resp.data) > 0:
                            print(
                                f"patient_imaging 已插入新记录: {insert_resp.data[0]}"
                            )
                        else:
                            print(
                                f"警告: 向 patient_imaging 插入记录未返回数据: {getattr(insert_resp, 'error', None)}"
                            )
                except Exception as e:
                    print(f"写入 patient_imaging 失败: {e}")
        except Exception as e:
            print(f"处理 hemisphere 时出错: {e}")

        if patient_id:
            # Batch-write uploaded modalities in one DB update to avoid occasional missing items.
            uploaded_modalities = []
            if ncct_path and os.path.exists(ncct_path):
                uploaded_modalities.append("ncct")
            if mcta_path and os.path.exists(mcta_path):
                uploaded_modalities.append("mcta")
            if vcta_path and os.path.exists(vcta_path):
                uploaded_modalities.append("vcta")
            if dcta_path and os.path.exists(dcta_path):
                uploaded_modalities.append("dcta")
            if cbf_path and os.path.exists(cbf_path):
                uploaded_modalities.append("cbf")
            if cbv_path and os.path.exists(cbv_path):
                uploaded_modalities.append("cbv")
            if tmax_path and os.path.exists(tmax_path):
                uploaded_modalities.append("tmax")

            success, result = append_modalities_to_imaging(
                patient_id, file_id, uploaded_modalities, hemisphere
            )
            if not success:
                print(
                    f"patient_imaging available_modalities batch update failed: {result}"
                )
            else:
                if isinstance(result, dict):
                    print(
                        f"patient_imaging available_modalities batch updated: {result.get('available_modalities')}"
                    )
                else:
                    print(
                        f"patient_imaging available_modalities batch updated: {result}"
                    )

        # ??????
        output_dir = os.path.join(app.config["PROCESSED_FOLDER"], file_id)
        os.makedirs(output_dir, exist_ok=True)

        # 异步工作流可要求延迟执行脑卒中自动分析
        defer_stroke_analysis = (
            request.form.get("defer_stroke_analysis", "false") == "true"
        )

        # 检查是否上传了全部CTA功能图像
        skip_ai = True
        if request.form.get("skip_ai") == "false" or (
            (mcta_path and vcta_path and dcta_path)
            and not (cbf_path or cbv_path or tmax_path)
        ):
            skip_ai = False
        print(f"skip_ai: {skip_ai}")

        # 获取模型类型参数，默认使用mrdpm
        selected_model = request.form.get("model_type", "mrdpm")
        model_type = selected_model
        print(f"用户选择的模型: {selected_model}, 实际使用的模型: {model_type}")

        # 如果skip_ai为True，则直接生成上传图像的PNG切片，不做AI推理
        if skip_ai:
            print("跳过AI分析，生成上传图像切片PNG")

            modality_paths = {
                "ncct": ncct_path,
                "mcta": mcta_path,
                "vcta": vcta_path,
                "dcta": dcta_path,
                "cbf": cbf_path,
                "cbv": cbv_path,
                "tmax": tmax_path,
            }

            modality_urls = {}
            modality_npy_urls = {}
            modality_counts = {}
            for key, path in modality_paths.items():
                urls, npy_urls, count = generate_modality_slices(path, output_dir, key)
                modality_urls[key] = urls
                modality_npy_urls[key] = npy_urls
                modality_counts[key] = count

            total_slices = max([c for c in modality_counts.values() if c], default=0)

            rgb_files = []
            for slice_idx in range(total_slices):
                # 为当前切片生成掩码
                # 尝试加载NCCT图像数据用于掩码生成
                ncct_slice_path = os.path.join(
                    output_dir, f"slice_{slice_idx:03d}_ncct.png"
                )
                if os.path.exists(ncct_slice_path):
                    from PIL import Image

                    ncct_img = Image.open(ncct_slice_path).convert("RGB")
                    rgb_data = np.array(ncct_img) / 255.0
                    # 生成掩码
                    mask_result = generate_mask_for_slice(
                        rgb_data, output_dir, slice_idx
                    )
                    mask_image = mask_result.get("mask_url", "")
                    mask_npy_url = mask_result.get("mask_npy_url", "")
                    overlay_url = mask_result.get("overlay_url", "")
                    coverage = float(mask_result.get("coverage", 0.0))
                    method = mask_result.get("method", "skip_ai")
                else:
                    mask_image = ""
                    mask_npy_url = ""
                    overlay_url = ""
                    coverage = 0.0
                    method = "skip_ai"

                slice_result = {
                    "slice_index": slice_idx,
                    "rgb_image": "",
                    "mcta_image": modality_urls["mcta"][slice_idx]
                    if slice_idx < len(modality_urls["mcta"])
                    else "",
                    "vcta_url": modality_urls["vcta"][slice_idx]
                    if slice_idx < len(modality_urls["vcta"])
                    else "",
                    "dcta_url": modality_urls["dcta"][slice_idx]
                    if slice_idx < len(modality_urls["dcta"])
                    else "",
                    "ncct_image": modality_urls["ncct"][slice_idx]
                    if slice_idx < len(modality_urls["ncct"])
                    else "",
                    "npy_url": modality_npy_urls["ncct"][slice_idx]
                    if slice_idx < len(modality_npy_urls["ncct"])
                    else "",
                    "mask_image": mask_image,
                    "mask_npy_url": mask_npy_url,
                    "overlay_url": overlay_url,
                    "coverage": float(coverage),
                    "method": method,
                }

                for model_key in MODEL_CONFIGS.keys():
                    slice_result.update(
                        {
                            f"has_{model_key}": False,
                            f"{model_key}_image": "",
                            f"{model_key}_npy_url": "",
                        }
                    )

                if slice_idx < len(modality_urls["cbf"]):
                    slice_result["has_cbf"] = True
                    slice_result["cbf_image"] = modality_urls["cbf"][slice_idx]
                    slice_result["cbf_npy_url"] = (
                        modality_npy_urls["cbf"][slice_idx]
                        if slice_idx < len(modality_npy_urls["cbf"])
                        else ""
                    )
                if slice_idx < len(modality_urls["cbv"]):
                    slice_result["has_cbv"] = True
                    slice_result["cbv_image"] = modality_urls["cbv"][slice_idx]
                    slice_result["cbv_npy_url"] = (
                        modality_npy_urls["cbv"][slice_idx]
                        if slice_idx < len(modality_npy_urls["cbv"])
                        else ""
                    )
                if slice_idx < len(modality_urls["tmax"]):
                    slice_result["has_tmax"] = True
                    slice_result["tmax_image"] = modality_urls["tmax"][slice_idx]
                    slice_result["tmax_npy_url"] = (
                        modality_npy_urls["tmax"][slice_idx]
                        if slice_idx < len(modality_npy_urls["tmax"])
                        else ""
                    )

                slice_result["has_ai"] = False
                rgb_files.append(slice_result)

            # 自动触发脑卒中分析（如果满足条件）
            if patient_id and not defer_stroke_analysis:
                print("尝试自动触发脑卒中分析...")
                try:
                    from stroke_analysis import auto_analyze_stroke

                    analysis_result = auto_analyze_stroke(file_id, patient_id)
                    print(
                        f"自动脑卒中分析结果: {'成功' if analysis_result.get('success') else '失败'}"
                    )
                    if not analysis_result.get("success"):
                        print(f"自动分析失败原因: {analysis_result.get('error')}")
                except Exception as e:
                    print(f"自动触发脑卒中分析失败: {e}")
            elif patient_id and defer_stroke_analysis:
                print("已启用 defer_stroke_analysis，上传接口跳过自动脑卒中分析。")

            return jsonify(
                {
                    "success": True,
                    "file_id": file_id,
                    "cbf_filename": cbf_file.filename if cbf_file else "",
                    "cbv_filename": cbv_file.filename if cbv_file else "",
                    "tmax_filename": tmax_file.filename if tmax_file else "",
                    "ncct_filename": ncct_file.filename,
                    "metadata": {},
                    "rgb_files": rgb_files,
                    "total_slices": int(total_slices),
                    "has_ai": False,
                    "available_models": [],
                    "model_configs": MODEL_CONFIGS,
                    "skip_ai": skip_ai,
                }
            )
        else:
            # 处理RGB合成（现在包含多模型AI推理）
            print("开始处理RGB合成和多模型AI推理...")
            result = process_rgb_synthesis(
                mcta_path, vcta_path, dcta_path, ncct_path, output_dir, model_type
            )

            if result["success"]:
                print("RGB合成和多模型AI推理处理成功")

                # 自动触发脑卒中分析（如果满足条件）
                if patient_id and not defer_stroke_analysis:
                    print("尝试自动触发脑卒中分析...")
                    try:
                        from stroke_analysis import auto_analyze_stroke

                        analysis_result = auto_analyze_stroke(file_id, patient_id)
                        print(
                            f"自动脑卒中分析结果: {'成功' if analysis_result.get('success') else '失败'}"
                        )
                        if not analysis_result.get("success"):
                            print(f"自动分析失败原因: {analysis_result.get('error')}")
                    except Exception as e:
                        print(f"自动触发脑卒中分析失败: {e}")
                elif patient_id and defer_stroke_analysis:
                    print("已启用 defer_stroke_analysis，上传接口跳过自动脑卒中分析。")

                def ensure_json_serializable(obj):
                    if isinstance(obj, dict):
                        return {k: ensure_json_serializable(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [ensure_json_serializable(v) for v in obj]
                    elif isinstance(obj, np.integer):
                        return int(obj)
                    elif isinstance(obj, np.floating):
                        return float(obj)
                    elif isinstance(obj, np.bool_):
                        return bool(obj)
                    elif isinstance(obj, np.ndarray):
                        return obj.tolist()
                    else:
                        return obj

                return jsonify(
                    {
                        "success": True,
                        "file_id": file_id,
                        "mcta_filename": mcta_file.filename if mcta_file else "",
                        "vcta_filename": vcta_file.filename if vcta_file else "",
                        "dcta_filename": dcta_file.filename if dcta_file else "",
                        "ncct_filename": ncct_file.filename,
                        "metadata": ensure_json_serializable(result["metadata"]),
                        "rgb_files": ensure_json_serializable(result["rgb_files"]),
                        "total_slices": result["total_slices"],
                        "has_ai": result["has_ai"],
                        "available_models": result["available_models"],
                        "model_configs": result["model_configs"],
                        "skip_ai": skip_ai,
                    }
                )
            else:
                print(f"RGB合成处理失败: {result['error']}")
                return jsonify({"success": False, "error": result["error"]})

    except Exception as e:
        print(f"上传处理异常: {e}")
        traceback.print_exc()
        return jsonify({"success": False, "error": f"处理失败: {str(e)}"})


# 其余路由保持不变...
@app.route("/download_mask/<file_id>/<int:slice_index>")
def download_mask(file_id, slice_index):
    """下载特定切片的掩码NPY文件"""
    try:
        filename = f"slice_{slice_index:03d}_mask.npy"
        file_path = os.path.join(app.config["PROCESSED_FOLDER"], file_id, filename)
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 404


@app.route("/get_image/<file_id>/<filename>")
def get_image(file_id, filename):
    """获取生成的PNG图像"""
    try:
        image_path = os.path.join(app.config["PROCESSED_FOLDER"], file_id, filename)
        if os.path.exists(image_path):
            return send_file(image_path, mimetype="image/png")
        else:
            return jsonify({"error": "图像不存在"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 404


@app.route("/get_file/<file_id>/<filename>")
def get_file(file_id, filename):
    """获取NPY等文件"""
    try:
        file_path = os.path.join(app.config["PROCESSED_FOLDER"], file_id, filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({"error": "文件不存在"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 404


@app.route("/get_slice/<file_id>/<int:slice_index>/<image_type>")
def get_slice(file_id, slice_index, image_type):
    """获取特定切片和类型"""
    try:
        filename = f"slice_{slice_index:03d}_{image_type}.png"
        image_path = os.path.join(app.config["PROCESSED_FOLDER"], file_id, filename)
        if os.path.exists(image_path):
            return send_file(image_path, mimetype="image/png")
        else:
            return jsonify({"error": "切片不存在"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("🚀 启动Flask开发服务器...")

    # 获取本机IP地址
    import socket

    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        print(f"🌐 本机IP地址: {local_ip}")
        print(f"🔗 局域网访问地址: http://{local_ip}:8765")
    except:
        local_ip = "0.0.0.0"
        print("⚠ 无法获取本机IP，使用默认配置")

    print("📱 本地访问地址: http://127.0.0.1:8765")
    print("🌍 服务器监听: 所有网络接口 (0.0.0.0:8765)")
    print("⏹️ 按 Ctrl+C 停止服务器")
    print("=" * 60)

    try:
        # 关键修改：使用明确的参数启动
        app.run(
            host="0.0.0.0",  # 监听所有网络接口
            port=8765,  # 明确指定端口
            debug=True,  # 调试模式
            threaded=True,  # 多线程
            use_reloader=False,  # 关闭自动重载，避免重复初始化
        )
    except Exception as e:
        print(f"❌ 服务器启动失败: {e}")
        import traceback

        traceback.print_exc()


# ==================== 保存报告并生成 AI 诊断报告 ====================


@app.route("/api/save_and_generate_report", methods=["POST"])
def api_save_and_generate_report():
    """Save structured report and generate AI report."""
    data = request.get_json() or {}
    patient_id = data.get("patient_id")
    file_id = data.get("file_id")

    if not patient_id or not file_id:
        return jsonify(
            {"status": "error", "message": "Missing patient_id or file_id"}
        ), 400

    try:
        # 1. Save report notes (primary target: patient_imaging.notes)
        save_result = save_report_notes(patient_id, file_id, data)
        if not save_result.get("success"):
            return jsonify(
                {
                    "status": "error",
                    "message": save_result.get("error", "Save report failed"),
                    "warnings": save_result.get("warnings", []),
                    "saved_targets": save_result.get("saved_targets", {}),
                }
            ), 500

        # 2. Load structured data
        structured_data = get_patient_by_id(patient_id) or {}
        imaging_data = get_imaging_by_case(patient_id, file_id)
        if not imaging_data:
            return jsonify(
                {"status": "error", "message": f"Imaging case {file_id} not found"}
            ), 404

        # 3. Generate MedGemma report
        print(f"Auto-generate AI report after save, patient_id: {patient_id}")
        ai_result = generate_report_with_medgemma(
            structured_data, imaging_data, file_id, output_format="markdown"
        )
        if not ai_result.get("success"):
            return jsonify(
                {
                    "status": "error",
                    "message": ai_result.get("error", "Report generation failed"),
                }
            ), 500

        # Ensure the newly generated report json also carries latest doctor notes.
        try:
            post_sync = _sync_notes_to_result_json(
                file_id=file_id,
                patient_id=patient_id,
                notes_html=str(data.get("notes", "") or ""),
                saved_at=str(
                    data.get("saved_at") or (datetime.utcnow().isoformat() + "Z")
                ),
            )
            if post_sync.get("failed_files"):
                save_result.setdefault("warnings", []).append(
                    f"post-generate json sync partially failed ({len(post_sync['failed_files'])}/{len(post_sync['matched_files'])})"
                )
            save_result["json_sync"] = post_sync
        except Exception as e:
            save_result.setdefault("warnings", []).append(
                f"post-generate json sync failed: {e}"
            )

        return jsonify(
            {
                "status": "success",
                "message": "Report saved and AI report generated",
                "data": save_result.get("data"),
                "ai_report": ai_result.get("report", ""),
                "report_payload": ai_result.get("report_payload"),
                "ai_generated": True,
                "warnings": save_result.get("warnings", []),
                "saved_targets": save_result.get("saved_targets", {}),
                "json_sync": save_result.get("json_sync", {}),
            }
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
