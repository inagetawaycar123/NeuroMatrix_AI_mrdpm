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
import os
import requests  # 娣诲姞 requests 瀵煎叆锛岀敤浜庤皟鐢ㄧ櫨宸?M3 API
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
try:
    from .ai_inference import get_ai_model
    from .extensions import NumpyJSONEncoder
except ImportError:
    # 鍏煎鐩存帴杩愯 backend/app.py 鐨勫満鏅?
    from ai_inference import get_ai_model
    from extensions import NumpyJSONEncoder
from datetime import datetime
from dotenv import load_dotenv

# ==================== Supabase 瀹㈡埛绔唴鑱斿垵濮嬪寲 ====================
try:
    from supabase import create_client, Client

    SUPABASE_URL = "https://ppyexzqdbsnwqfyugfvc.supabase.co"
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBweWV4enFkYnNud3FmeXVnZnZjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njc1Nzc3ODAsImV4cCI6MjA4MzE1Mzc4MH0.EjDH3eufPKBF8MJiHM6SVzPQlsWvGqhLQPKKhVG5Ffo"
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    SUPABASE_AVAILABLE = True
    print("鉁?Supabase 瀹㈡埛绔垵濮嬪寲鎴愬姛")
except ImportError as e:
    print(f"鉁?Supabase 瀵煎叆澶辫触: {e}")
    supabase = None
    SUPABASE_AVAILABLE = False
except Exception as e:
    print(f"鉁?Supabase 鍒濆鍖栧け璐? {e}")
    supabase = None
    SUPABASE_AVAILABLE = False


# ==================== Supabase database helpers ====================
def insert_patient_info(patient_data: dict):
    """
    Insert patient info into Supabase patient_info table.
    """
    if not SUPABASE_AVAILABLE:
        return (False, "Supabase unavailable")
    try:
        if "create_time" in patient_data:
            del patient_data["create_time"]
        response = supabase.table("patient_info").insert([patient_data]).execute()
        if response.data and len(response.data) > 0:
            return (True, response.data[0])
        else:
            return (False, "Insert failed: empty response from Supabase")
    except Exception as e:
        return (False, f"Insert failed: {str(e)}")


def update_analysis_result(patient_id: int, analysis_data: dict):
    """
    Update patient analysis result in patient_info table.
    """
    if not SUPABASE_AVAILABLE:
        return (False, "Supabase unavailable")
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
            return (False, "Update failed: empty response from Supabase")
    except Exception as e:
        return (False, f"Update failed: {str(e)}")


def get_patient_by_id(patient_id: int):
    """
    鏍规嵁 ID 鑾峰彇鎮ｈ€呬俊鎭?
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
        print(f"鑾峰彇鎮ｈ€呬俊鎭け璐? {e}")
        return None


def get_imaging_by_case(patient_id: int, case_id: str):
    """
    忙聽鹿忙聧庐 case_id 氓鈥櫯?patient_id 忙鸥楼猫炉垄 patient_imaging 猫庐掳氓陆鈥?
    """
    if not SUPABASE_AVAILABLE:
        return None
    try:
        query = supabase.table("patient_imaging").select("*").eq("case_id", case_id)
        if patient_id:
            query = query.eq("patient_id", patient_id)
        try:
            response = query.order("updated_at", desc=True).limit(1).execute()
        except Exception:
            response = query.limit(1).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        print(f"patient_imaging 忙鸥楼猫炉垄氓陇卤猫麓楼: {e}")
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


# ==================== 鐧惧窛 M3 API 閰嶇疆 ====================


# ==================== 鐧惧窛 M3 API 閰嶇疆 ====================
# 棣栧厛灏濊瘯浠?.env 鏂囦欢鍔犺浇鐜鍙橀噺
        
load_dotenv()

# 鐒跺悗璇诲彇鐜鍙橀噺锛堝凡浠?env鍔犺浇鎴栫郴缁熺幆澧冨彉閲忥級
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
# 淇璺緞锛歘_file__ 鍦?backend/ 涓嬶紝闇€瑕佸悜涓婁竴绾у埌椤圭洰鏍圭洰褰?
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


print(f"鐧惧窛 API URL: {BAICHUAN_API_URL}")
print(
    f"百川 API Key: {'***' + BAICHUAN_API_KEY[-4:] if BAICHUAN_API_KEY else '未配置'}"
)
print(f"鐧惧窛妯″瀷: {BAICHUAN_MODEL}")
print(f"鐧惧窛闂瘖妯″瀷: {BAICHUAN_CHAT_MODEL}")
print(f"鐭ヨ瘑搴揑D鏁伴噺: {len(BAICHUAN_KB_IDS)}")
print(f"鐭ヨ瘑搴揚DF鐩綍: {KB_PDF_DIR}")

# 鍗掍腑褰卞儚鎶ュ憡 Prompt 妯℃澘 (Markdown 鏍煎紡)
REPORT_PROMPT_TEMPLATE = """
浣犳槸涓€浣嶄笓涓氱殑绁炵粡鏀惧皠绉戝尰鐢熴€侫I 绯荤粺鍩轰簬鎮ｈ€?NCCT + 鍔ㄨ剦鏈?CTA + 闈欒剦鏈?CTA + 寤惰繜鏈?CTA锛? 閫氶亾 mCTA锛夊奖鍍忥紝閫氳繃 MRDPM 鎵╂暎妯″瀷鐢熸垚 CBF/CBV/Tmax 鐏屾敞鍙傛暟鍥撅紝璇风患鍚堝垎鏋愯繖 4 绫诲奖鍍忕殑鐏屾敞鐗瑰緛锛岀敓鎴愮鍚堝崚涓瘖鐤楄鑼冪殑褰卞儚璇婃柇鎶ュ憡銆?

銆愭偅鑰呬复搴婁笌褰卞儚鏁版嵁銆?
- 鎮ｈ€匢D: {patient_id}
- 濮撳悕: {patient_name}
- 骞撮緞: {patient_age}
- 鎬у埆: {patient_sex}
- 鍏ラ櫌 NIHSS 璇勫垎: {nihss_score}
- 鍙戠梾鑷冲叆闄㈡椂闂? {onset_to_admission}
- 鍩轰簬 NCCT + 鍔ㄨ剦鏈?闈欒剦鏈?寤惰繜鏈?mCTA 鐢熸垚鐨勭亴娉ㄥ弬鏁帮細
  鈥?鏍稿績姊楁浣撶Н (Core): {core_volume} ml
  鈥?鍗婃殫甯︿綋绉?(Penumbra): {penumbra_volume} ml
  鈥?涓嶅尮閰嶆瘮鍊?(Mismatch Ratio): {mismatch_ratio}
  鈥?鍙戠梾渚? {hemisphere}

銆愰噸瑕佹彁绀?- 蹇呴』涓ユ牸閬靛畧銆?
鍦ㄨ瘖鏂剰瑙佷腑锛屼綘蹇呴』閫愪竴鍒嗘瀽浠ヤ笅涓変釜涓村簥鏁版嵁锛?
1. NIHSS璇勫垎鍒嗘瀽锛氬叆闄?NIHSS 璇勫垎涓?{nihss_score}锛岃璇︾粏鍒嗘瀽璇ヨ瘎鍒嗗搴旂殑绁炵粡鍔熻兘缂烘崯涓ラ噸绋嬪害锛堝杞诲害銆佷腑搴︺€侀噸搴︼級
2. 骞撮緞鍒嗘瀽锛氭偅鑰呭勾榫?{patient_age} 宀侊紝璇峰垎鏋愬勾榫勫娌荤枟鍐崇瓥鐨勫奖鍝?
3. 鍙戠梾鏃堕棿鍒嗘瀽锛氬彂鐥呰嚦鍏ラ櫌鏃堕棿涓?{onset_to_admission}锛岃璇勪及鏄惁鍦ㄦ不鐤楁椂闂寸獥鍐?

銆愭姤鍛婅姹傘€?
1. 绗﹀悎銆婁腑鍥芥€ユ€х己琛€鎬ц剳鍗掍腑璇婃不鎸囧崡銆嬭鑼?
2. 鍚勭珷鑺傞渶璇﹀敖鎻忚堪
3. 浣跨敤鍖诲涓撲笟鏈
4. 杈撳嚭鏍煎紡涓?Markdown
5. 灏忔爣棰樹娇鐢?"##" 鍓嶇紑鏍囪锛屽 "## 妫€鏌ユ柟娉?
6. 涓嶈浣跨敤绮椾綋鏍囪锛?*鏂囧瓧**锛夛紝鐩存帴浣跨敤鏅€氭枃瀛楁弿杩?

銆愯緭鍑烘牸寮忋€?

路 妫€鏌ユ柟娉?
澶撮 CT 骞虫壂 (NCCT) + 涓夋湡 CT 琛€绠℃垚鍍?(mCTA锛氬姩鑴夋湡銆侀潤鑴夋湡銆佸欢杩熸湡)

路 褰卞儚瀛﹁〃鐜?
鍩轰簬 NCCT + 鍔ㄨ剦鏈?闈欒剦鏈?寤惰繜鏈?mCTA 缁煎悎鍒嗘瀽锛?
1. 鏍稿績姊楁鍖猴細[缁撳悎 CBF/CBV/Tmax 鍙傛暟锛屾牴鎹?DEFUSE 3 鏍囧噯锛坮CBF<30%銆乀max>6s锛夎缁嗘弿杩颁綅缃€佷綋绉€佺亴娉ㄥ紓甯告儏鍐礭
2. 鍗婃殫甯﹀尯锛歔璇︾粏鎻忚堪鑼冨洿銆佷笌鏍稿績姊楁鍖虹殑绌洪棿鍏崇郴銆乀max 寤惰繜绋嬪害]
3. 宸﹀彸鑴戜笉瀵圭О鍒嗘瀽锛歔姣旇緝鎮ｄ晶涓庡仴渚х殑 CBF/CBV 宸紓锛岄噺鍖栦笉瀵圭О鎸囨暟]
4. 涓嶅尮閰嶈瘎浼帮細[涓嶅尮閰嶆瘮鍊煎強涓村簥鎰忎箟]

路 琛€绠¤瘎浼?
[鏍规嵁涓夋湡 CTA 鐨勫姩鑴?闈欒剦鏄惧奖宸紓锛屾帹鏂矗浠昏绠″強渚ф敮寰幆鎯呭喌]

路 璇婃柇鎰忚
[蹇呴』鍖呭惈浠ヤ笅鍐呭锛岄€愭潯鍒嗘瀽锛?
1. NIHSS璇勫垎鍒嗘瀽锛氬叆闄?NIHSS 璇勫垎涓?{nihss_score}锛岃璇︾粏鍒嗘瀽璇ヨ瘎鍒嗗搴旂殑绁炵粡鍔熻兘缂烘崯涓ラ噸绋嬪害
2. 骞撮緞鍒嗘瀽锛氭偅鑰呭勾榫?{patient_age} 宀侊紝璇峰垎鏋愬勾榫勫娌荤枟鍐崇瓥鐨勫奖鍝?
3. 鍙戠梾鏃堕棿鍒嗘瀽锛氬彂鐥呰嚦鍏ラ櫌鏃堕棿涓?{onset_to_admission}锛岃璇勪及鏄惁鍦ㄦ不鐤楁椂闂寸獥鍐?
4. 鎬ユ€х己琛€鎬у崚涓瘖鏂?
5. 鏍稿績姊楁浣撶Н鍙婁綅缃紙鍩轰簬 rCBF<30% 闃堝€硷級
6. 鍗婃殫甯︿綋绉強鍙尳鏁戣剳缁勭粐璇勪及锛堝熀浜?Tmax>6s 闃堝€硷級
7. 涓嶅尮閰嶆瘮鍊煎強 DEFUSE 3 鍏ラ€夋爣鍑嗗垽鏂?
8. 寤鸿杩涗竴姝ヨ琛€绠″唴娌荤枟璇勪及]

路 娌荤枟寤鸿
鎺ㄨ崘瀹屽杽鏁板瓧鍑忓奖琛€绠￠€犲奖 (DSA) 浠ユ槑纭绠￠棴濉為儴浣嶅強渚ф敮寰幆鎯呭喌銆傜患鍚?NIHSS 璇勫垎銆佹偅鑰呭勾榫勫強鍙戠梾鑷冲叆闄㈡椂闂翠互鍙婃牳蹇冩姝?鍗婃殫甯︿綋绉瘮鍊硷紝鍒ゆ柇琛€绠″唴娌荤枟鎸囧緛銆傝嫢绗﹀悎 DEFUSE 3 鏍囧噯锛屽缓璁Н鏋佽琛€绠″唴娌荤枟銆?

璇锋牴鎹互涓婃偅鑰呮暟鎹敓鎴愭姤鍛婏細
"""

# JSON 缁撴瀯鍖栬緭鍑?Prompt
REPORT_JSON_PROMPT = """
浣犳槸涓€浣嶄笓涓氱殑绁炵粡鏀惧皠绉戝尰鐢熴€侫I 绯荤粺鍩轰簬鎮ｈ€?NCCT + 鍔ㄨ剦鏈?CTA + 闈欒剦鏈?CTA + 寤惰繜鏈?CTA锛? 閫氶亾 mCTA锛夊奖鍍忥紝閫氳繃 MRDPM 鎵╂暎妯″瀷鐢熸垚 CBF/CBV/Tmax 鐏屾敞鍙傛暟鍥撅紝璇风患鍚堝垎鏋愮敓鎴愯鑼冪殑鍗掍腑褰卞儚璇婃柇鎶ュ憡 JSON銆?

銆愭偅鑰呭奖鍍忔暟鎹€?
- 鎮ｈ€匢D: {patient_id}
- 鍩轰簬 NCCT + 鍔ㄨ剦鏈?闈欒剦鏈?寤惰繜鏈?mCTA 鐢熸垚鐨勭亴娉ㄥ弬鏁帮細
  鈥?鏍稿績姊楁浣撶Н (Core): {core_volume} ml
  鈥?鍗婃殫甯︿綋绉?(Penumbra): {penumbra_volume} ml
  鈥?涓嶅尮閰嶆瘮鍊?(Mismatch Ratio): {mismatch_ratio}
  鈥?鍙戠梾渚? {hemisphere}

銆愪复搴婅瘖鏂爣鍑嗐€?
- 鏍稿績姊楁锛歳CBF < 30%锛堢浉瀵硅剳琛€娴侀噺锛?
- 鍗婃殫甯︼細Tmax > 6 绉?
- DEFUSE 3 鏍囧噯锛氫笉鍖归厤浣撶Н 鈮?15ml 涓斾笉鍖归厤姣斿€?鈮?1.8

銆愯緭鍑鸿姹傘€?
璇蜂弗鏍兼寜鐓т互涓?JSON 鏍煎紡杈撳嚭锛?*涓嶈鍖呭惈浠讳綍鍏朵粬鏂囧瓧鎴栦唬鐮佸潡鏍囪**锛?

{{"妫€鏌ユ柟娉?: "澶撮CT骞虫壂(NCCT)+涓夋湡CTA(mCTA:鍔ㄨ剦鏈熴€侀潤鑴夋湡銆佸欢杩熸湡)", "鏍稿績姊楁": {{"浣撶Н": "鏍稿績姊楁浣撶Нml", "浣嶇疆": "鍏蜂綋鑴戝彾鍜岃绠′緵琛€鍖?, "CT琛ㄧ幇": "NCCT浣庡瘑搴︽敼鍙樻儏鍐?, "鐏屾敞鏍囧噯": "rCBF<30%"}}, "鍗婃殫甯?: {{"浣撶Н": "鍗婃殫甯︿綋绉痬l", "浣嶇疆": "缂鸿鍗婃殫甯﹀垎甯冨尯鍩?, "鐏屾敞鐗瑰緛": "Tmax>6s, CBF闄嶄綆浣咰BV鐩稿淇濈暀", "涓庢牳蹇冨叧绯?: "绌洪棿鍏崇郴鎻忚堪"}}, "宸﹀彸鑴戜笉瀵圭О鍒嗘瀽": {{"鎮ｄ晶": "鎮ｄ晶鐏屾敞鍙傛暟", "鍋ヤ晶": "鍋ヤ晶鐏屾敞鍙傛暟", "涓嶅绉版寚鏁?: "閲忓寲鍊?}}, "琛€绠¤瘎浼?: "鏍规嵁涓夋湡CTA鎺ㄦ柇璐ｄ换琛€绠″拰渚ф敮寰幆鎯呭喌", "DEFUSE3璇勪及": {{"涓嶅尮閰嶄綋绉?: "浣撶Нml", "涓嶅尮閰嶆瘮鍊?: "姣斿€?, "鏄惁鍏ラ€?: "鏄?鍚?}}, "璇婃柇鎰忚": "缁煎悎璇婃柇鎰忚", "娌荤枟寤鸿": ["寤鸿1", "寤鸿2", "寤鸿3"]}}

璇峰彧杈撳嚭 JSON 瀵硅薄锛岀‘淇濇墍鏈夊瓧绗︿覆浣跨敤鍙屽紩鍙峰寘瑁广€?
"""


def generate_report_with_baichuan(
    structured_data: dict, output_format: str = "markdown"
) -> dict:
    """
    璋冪敤鐧惧窛 M3 API 鐢熸垚鍗掍腑褰卞儚鎶ュ憡
    """
    try:
        # 鍑嗗 NIHSS 璇勫垎鏄剧ず
        nihss_score = structured_data.get("admission_nihss", None)
        nihss_display = (
            f"{nihss_score} 分" if nihss_score is not None else "未记录"
        )

        # 鍑嗗鎮ｈ€呬俊鎭樉绀?
        patient_id = structured_data.get("id", structured_data.get("ID", "鏈煡"))
        patient_name = structured_data.get("patient_name", "鏈煡")
        patient_age = structured_data.get("patient_age", "鏈煡")
        patient_sex = structured_data.get("patient_sex", "鏈煡")
        onset_to_admission = structured_data.get("onset_to_admission_hours", None)
        onset_display = (
            f"{onset_to_admission} 小时"
            if onset_to_admission is not None
            else "未记录"
        )

        # 鍑嗗 Prompt
        if output_format == "json":
            prompt = REPORT_JSON_PROMPT.format(
                patient_id=patient_id,
                core_volume=structured_data.get("core_infarct_volume", "N/A"),
                penumbra_volume=structured_data.get("penumbra_volume", "N/A"),
                mismatch_ratio=structured_data.get("mismatch_ratio", "N/A"),
                hemisphere=structured_data.get("hemisphere", "鍙屼晶"),
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
                hemisphere=structured_data.get("hemisphere", "鍙屼晶"),
            )

        # 妫€鏌?API Key
        if not BAICHUAN_API_KEY:
            print("鈿?鐧惧窛 API Key 鏈厤缃紝杩斿洖妯℃嫙鎶ュ憡")
            mock_report = generate_mock_report(structured_data, output_format)
            return {
                "success": True,
                "report": mock_report,
                "format": output_format,
                "is_mock": True,
                "warning": "浣跨敤妯℃嫙鎶ュ憡锛岃閰嶇疆 BAICHUAN_API_KEY 鐜鍙橀噺",
            }

        # 璋冪敤鐧惧窛 M3 API
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

        print(f"璋冪敤鐧惧窛 M3 API... format={output_format}")
        print(f"Payload: {json.dumps(payload, ensure_ascii=False)[:500]}...")
        response = requests.post(
            BAICHUAN_API_URL, headers=headers, json=payload, timeout=60
        )

        print(f"鍝嶅簲鐘舵€佺爜: {response.status_code}")
        print(f"鍝嶅簲鍐呭: {response.text[:1000]}...")

        if response.status_code == 200:
            result = response.json()

            # 鐧惧窛 M3 API 鍙兘鏈夊绉嶅搷搴旀牸寮忥紝灏濊瘯澶氱瑙ｆ瀽鏂瑰紡
            report_content = ""

            # 鏂瑰紡1: OpenAI 鏍煎紡 (choices[0].message.content)
            if "choices" in result and len(result["choices"]) > 0:
                choice = result["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    report_content = choice["message"]["content"]
                elif "text" in choice:
                    report_content = choice["text"]

            # 鏂瑰紡2: 鐩存帴 content 瀛楁
            if not report_content and "content" in result:
                report_content = result["content"]

            # 鏂瑰紡3: data 瀛楁
            if not report_content and "data" in result:
                data = result["data"]
                if "content" in data:
                    report_content = data["content"]

            print(f"鉁?鐧惧窛 M3 API 璋冪敤鎴愬姛锛屾姤鍛婇暱搴? {len(report_content)}")
            return {
                "success": True,
                "report": report_content,
                "format": output_format,
                "is_mock": False,
            }
        else:
            error_msg = f"API 璋冪敤澶辫触: {response.status_code} - {response.text}"
            print(f"鉁?{error_msg}")
            return {"success": False, "error": error_msg, "format": output_format}

    except requests.exceptions.Timeout:
        error_msg = "鐧惧窛 M3 API 璋冪敤瓒呮椂"
        print(f"鉁?{error_msg}")
        return {"success": False, "error": error_msg, "format": output_format}
    except Exception as e:
        error_msg = f"鐢熸垚鎶ュ憡澶辫触: {str(e)}"
        print(f"鉁?{error_msg}")
        import traceback

        traceback.print_exc()
        return {"success": False, "error": error_msg, "format": output_format}


def generate_mock_report(structured_data: dict, output_format: str = "markdown") -> str:
    """Generate a fallback report when BAICHUAN_API_KEY is not configured."""
    patient_id = structured_data.get("id", structured_data.get("ID", "未知"))
    core_volume = structured_data.get("core_infarct_volume", 0)
    penumbra_volume = structured_data.get("penumbra_volume", 0)
    mismatch_ratio = structured_data.get("mismatch_ratio", 0)
    hemisphere = structured_data.get("hemisphere", "both")

    mock_report = f"""影像诊断报告

患者ID: {patient_id}

检查方法:
头颅 CT 平扫 (NCCT) + 三期 CTA (mCTA: 动脉期/静脉期/延迟期)

影像学表现:
1. 核心梗死体积约 {core_volume} ml
2. 半暗带体积约 {penumbra_volume} ml
3. 不匹配比值约 {mismatch_ratio}
4. 偏侧: {hemisphere}

诊断意见:
提示急性缺血性卒中影像改变，建议结合临床与后续检查综合判断。

治疗建议:
1. 结合时间窗评估再灌注治疗机会
2. 完善血管与灌注信息
3. 动态监测神经功能评分
"""

    if output_format == "json":
        return json.dumps(
            {
                "ID": patient_id,
                "检查方法": "NCCT + mCTA",
                "核心梗死": {
                    "体积": f"{core_volume} ml",
                    "灌注标准": "rCBF<30%",
                },
                "半暗带": {
                    "体积": f"{penumbra_volume} ml",
                    "灌注特征": "Tmax>6s",
                },
                "左右脑不对称分析": {
                    "患侧": hemisphere,
                    "不对称指数": "示例值",
                },
                "DEFUSE3评估": {
                    "不匹配体积": f"{penumbra_volume} ml",
                    "不匹配比值": f"{mismatch_ratio}",
                    "是否入组": "是"
                    if penumbra_volume >= 15 and mismatch_ratio >= 1.8
                    else "否",
                },
                "诊断意见": "示例报告（未调用外部模型）",
                "治疗建议": "请结合临床决策",
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

# 鍦╝pp.py鐨勫鍏ラ儴鍒嗘坊鍔?
try:
    from .stroke_analysis import analyze_stroke_case
    from .medgemma_report import generate_report_with_medgemma
except ImportError:
    from stroke_analysis import analyze_stroke_case
    from medgemma_report import generate_report_with_medgemma

# 灏濊瘯瀵煎叆 nibabel
try:
    import nibabel as nib

    NIBABEL_AVAILABLE = True
    print("鉁?nibabel 瀵煎叆鎴愬姛")
except ImportError as e:
    print(f"鉁?nibabel 瀵煎叆澶辫触: {e}")
    NIBABEL_AVAILABLE = False

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__, static_folder=os.path.join(PROJECT_ROOT, "static"))
app.config["SECRET_KEY"] = "your-secret-key-here"
app.config["UPLOAD_FOLDER"] = os.path.join(PROJECT_ROOT, "static", "uploads")
app.config["PROCESSED_FOLDER"] = os.path.join(
    PROJECT_ROOT, "static", "processed"
)
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024
app.config["TEMPLATES_AUTO_RELOAD"] = True  # 绂佺敤HTML缂撳瓨锛屼慨鏀圭珛鍗崇敓鏁?
app.jinja_env.auto_reload = True

# 鏍稿績锛氶厤缃甆umpyJSONEncoder鐢ㄤ簬JSON搴忓垪鍖?
app.json_encoder = NumpyJSONEncoder


# 鍒涘缓蹇呰鐨勭洰褰?
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["PROCESSED_FOLDER"], exist_ok=True)

print(f"涓婁紶鐩綍: {app.config['UPLOAD_FOLDER']}")
print(f"澶勭悊鐩綍: {app.config['PROCESSED_FOLDER']}")

# ==================== Upload Job Center (for /processing) ====================
UPLOAD_JOB_STEP_DEFS = [
    {"key": "archive_ready", "title": "建立患者档案"},
    {"key": "modality_detect", "title": "识别上传模态"},
    {"key": "ctp_generate", "title": "生成CTP灌注图"},
    {"key": "stroke_analysis", "title": "脑卒中自动分析"},
    {"key": "pseudocolor", "title": "生成伪彩图"},
    {"key": "ai_report", "title": "自动生成结构化报告"},
]

UPLOAD_JOBS = {}
UPLOAD_JOBS_LOCK = threading.Lock()


def _job_now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _upload_log(
    job_id,
    file_id,
    patient_id,
    step,
    status,
    message=None,
    linked_run_id=None,
):
    suffix = f" message={message}" if message else ""
    run_part = f" run_id={linked_run_id}" if linked_run_id else ""
    print(
        "[UPLOAD] "
        f"job_id={job_id or '-'} "
        f"file_id={file_id or '-'} "
        f"patient_id={patient_id or '-'} "
        f"step={step or '-'} "
        f"status={status or '-'}"
        f"{run_part}"
        f"{suffix}"
    )


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
        _upload_log(
            job_id=job.get("job_id"),
            file_id=job.get("file_id"),
            patient_id=job.get("patient_id"),
            step="job",
            status=status,
            message=error or "",
            linked_run_id=job.get("agent_run_id"),
        )

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
            _upload_log(
                job_id=job.get("job_id"),
                file_id=job.get("file_id"),
                patient_id=job.get("patient_id"),
                step=step_key,
                status=status,
                message=message or "",
                linked_run_id=job.get("agent_run_id"),
            )
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
    alias = {
        "mcat": "mcta",
        "vcat": "vcta",
        "dcat": "dcta",
    }
    normalized = []
    for item in modalities or []:
        key = alias.get(str(item).strip().lower(), str(item).strip().lower())
        if key and key not in normalized:
            normalized.append(key)
    return normalized


def _build_path_decision(modalities):
    raw_modalities = []
    for item in modalities or []:
        value = str(item).strip().lower()
        if value:
            raw_modalities.append(value)

    canonical_modalities = _normalize_uploaded_modalities(raw_modalities)
    modality_set = set(canonical_modalities)
    valid_keys = {"ncct", "mcta", "vcta", "dcta", "cbf", "cbv", "tmax"}
    unknown_modalities = sorted([m for m in modality_set if m not in valid_keys])

    decision = {
        "raw_modalities": raw_modalities,
        "canonical_modalities": canonical_modalities,
        "imaging_path": None,
        "should_generate_ctp": False,
        "should_run_stroke_analysis": False,
        "unknown_modalities": unknown_modalities,
        "valid": False,
        "error": None,
    }

    # Fixed priority: ncct_mcta_ctp -> ncct_mcta -> ncct_single_phase_cta -> ncct_only
    if {"ncct", "mcta", "vcta", "dcta", "cbf", "cbv", "tmax"}.issubset(modality_set):
        decision["imaging_path"] = "ncct_mcta_ctp"
        decision["should_run_stroke_analysis"] = True
        decision["valid"] = True
        return decision

    if {"ncct", "mcta", "vcta", "dcta"}.issubset(modality_set):
        decision["imaging_path"] = "ncct_mcta"
        decision["should_generate_ctp"] = True
        decision["should_run_stroke_analysis"] = True
        decision["valid"] = True
        return decision

    single_phase_hits = modality_set.intersection({"mcta", "vcta", "dcta"})
    if "ncct" in modality_set and len(single_phase_hits) == 1 and len(modality_set) == 2:
        decision["imaging_path"] = "ncct_single_phase_cta"
        decision["valid"] = True
        return decision

    if modality_set == {"ncct"}:
        decision["imaging_path"] = "ncct_only"
        decision["valid"] = True
        return decision

    decision["error"] = "Invalid or unsupported modality combination"
    return decision


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
                return False, f"鍐呴儴涓婁紶鎺ュ彛杩斿洖 {resp.status_code}", result
            if not result.get("success"):
                return False, result.get("error", "涓婁紶澶勭悊澶辫触"), result
            return True, "ok", result


def _invoke_internal_generate_report(patient_id, file_id):
    with app.test_client() as client:
        url = f"/api/generate_report/{patient_id}?format=markdown&file_id={file_id}&source=processing_page"
        resp = client.get(url)
        data = resp.get_json(silent=True) or {}
        if resp.status_code != 200:
            return False, f"鎶ュ憡鎺ュ彛杩斿洖 {resp.status_code}", data
        if data.get("status") != "success":
            return False, data.get("message", "鎶ュ憡鐢熸垚澶辫触"), data
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
    msg = f"伪彩图生成成功: {total_success}/{total_attempts}"
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
                "已上传真实 CTP 数据，无需生成"
                if has_real_ctp
                else "当前模态不支持 CTP 生成"
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
                try:
                    from .stroke_analysis import auto_analyze_stroke
                except ImportError:
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
                job_id, "pseudocolor", "skipped", "无可用 CTP 图像，跳过伪彩图生成"
            )

        if payload.get("agent_run_id"):
            _update_step(
                job_id,
                "ai_report",
                "skipped",
                "已启用 Agent 主链，上传链跳过 AI 报告生成。",
            )
        else:
            _update_step(job_id, "ai_report", "running", "正在生成 AI 影像报告")
            ok, report_msg, report_result = _invoke_internal_generate_report(
                payload["patient_id"], payload["file_id"]
            )
            if ok:
                upload_result["report"] = report_result.get("report")
                upload_result["report_payload"] = report_result.get("report_payload")
                upload_result["json_path"] = report_result.get("json_path")
                _update_step(job_id, "ai_report", "completed", "AI 影像报告生成完成")
            else:
                warn = f"AI 影像报告生成失败: {report_msg}"
                warnings.append(warn)
                _add_job_warning(job_id, warn)
                _update_step(job_id, "ai_report", "failed", report_msg)

        def _mut(job):
            job["status"] = "completed"
            job["result"] = upload_result
            job["error"] = None
            job["current_step"] = None
            job["agent_run_id"] = payload.get("agent_run_id")
            if warnings:
                job["warnings"] = list({*job.get("warnings", []), *warnings})
            job["progress"] = 100

        _update_upload_job(job_id, _mut)
        _upload_log(
            job_id=job_id,
            file_id=payload.get("file_id"),
            patient_id=payload.get("patient_id"),
            step="job",
            status="completed",
            message="upload_pipeline_completed",
            linked_run_id=payload.get("agent_run_id"),
        )

        if payload.get("agent_run_id"):
            _start_deferred_upload_agent_run(
                run_id=payload.get("agent_run_id"),
                job_id=job_id,
                file_id=payload.get("file_id"),
                patient_id=payload.get("patient_id"),
            )
    except Exception as e:
        _set_job_status(job_id, "failed", f"浠诲姟寮傚父: {e}")
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


# AI妯″瀷閰嶇疆 - 鎵╁睍涓轰笁涓ā鍨?
# ==================== Agent Runtime (Week3 Phase 1) ====================
CANONICAL_RUN_STATUSES = {"queued", "running", "succeeded", "failed", "cancelled"}
CANONICAL_STEP_STATUSES = {"pending", "running", "completed", "failed", "skipped"}
CANONICAL_STAGES = {"triage", "tooling", "icv", "ekv", "consensus", "summary", "done"}

AGENT_TOOL_SEQUENCE_MAP = {
    "ncct_only": [
        "detect_modalities",
        "load_patient_context",
        "generate_medgemma_report",
    ],
    "ncct_single_phase_cta": [
        "detect_modalities",
        "load_patient_context",
        "generate_medgemma_report",
    ],
    "ncct_mcta": [
        "detect_modalities",
        "load_patient_context",
        "generate_ctp_maps",
        "run_stroke_analysis",
        "generate_medgemma_report",
    ],
    "ncct_mcta_ctp": [
        "detect_modalities",
        "load_patient_context",
        "run_stroke_analysis",
        "generate_medgemma_report",
    ],
}

POST_UPLOAD_SUMMARY_TOOL_SEQUENCE = [
    "detect_modalities",
    "load_patient_context",
    "generate_medgemma_report",
]

AGENT_TOOL_RETRY_LIMITS = {
    "generate_ctp_maps": 1,
    "run_stroke_analysis": 1,
    "generate_medgemma_report": 1,
}

TOOL_ERROR_SUGGESTIONS = {
    "TOOL_INPUT_INVALID": "Fix request fields and retry",
    "TOOL_NOT_APPLICABLE": "Check modality path and tool sequence",
    "TOOL_DEPENDENCY_MISSING": "Restore missing files/dependencies and retry",
    "TOOL_TIMEOUT": "Retry this step or fallback",
    "TOOL_EXECUTION_FAILED": "Inspect logs and retry this step",
    "TOOL_EXTERNAL_API_FAILED": "Retry after backoff or fallback",
}

TOOL_RETRYABLE = {
    "TOOL_INPUT_INVALID": False,
    "TOOL_NOT_APPLICABLE": False,
    "TOOL_DEPENDENCY_MISSING": False,
    "TOOL_TIMEOUT": True,
    "TOOL_EXECUTION_FAILED": True,
    "TOOL_EXTERNAL_API_FAILED": True,
}

AGENT_RUNS = {}
AGENT_EVENTS = {}
AGENT_RUNTIME_LOCK = threading.Lock()


def _agent_now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _safe_agent_copy(obj):
    return copy.deepcopy(obj) if obj is not None else None


def _agent_log(
    run_id,
    stage,
    tool,
    attempt,
    status,
    error_code=None,
    latency_ms=None,
    message=None,
):
    suffix = f" message={message}" if message else ""
    print(
        "[AGENT] "
        f"run_id={run_id} "
        f"stage={stage or '-'} "
        f"tool={tool or '-'} "
        f"attempt={attempt if attempt is not None else '-'} "
        f"status={status or '-'} "
        f"error_code={error_code or '-'} "
        f"latency_ms={latency_ms if latency_ms is not None else '-'}"
        f"{suffix}"
    )


def _canonicalize_hemisphere(value):
    raw = str(value or "").strip().lower()
    if not raw:
        return "both", None
    if raw in {"left", "right", "both"}:
        return raw, None
    return "both", f"Invalid hemisphere '{value}', normalized to 'both'"


def _tool_error_contract(error_code, error_message):
    code = str(error_code or "TOOL_EXECUTION_FAILED")
    return {
        "error_code": code,
        "error_message": str(error_message or code),
        "retryable": bool(TOOL_RETRYABLE.get(code, False)),
        "suggested_action": TOOL_ERROR_SUGGESTIONS.get(
            code, "Inspect logs and retry when safe"
        ),
    }


def _create_agent_run(
    run_id,
    patient_id,
    file_id,
    available_modalities,
    hemisphere="both",
    source="api",
    linked_upload_job_id=None,
    execution_mode="default",
    trigger_source="api",
):
    normalized_hemisphere, warning = _canonicalize_hemisphere(hemisphere)
    run = {
        "run_id": run_id,
        "patient_id": patient_id,
        "file_id": file_id,
        "status": "queued",
        "stage": "triage",
        "created_at": _agent_now(),
        "updated_at": _agent_now(),
        "source": source,
        "linked_upload_job_id": linked_upload_job_id,
        "execution_mode": execution_mode,
        "trigger_source": trigger_source,
        "planner_input": {
            "run_id": run_id,
            "patient_id": patient_id,
            "file_id": file_id,
            "available_modalities": _normalize_uploaded_modalities(
                available_modalities or []
            ),
            "hemisphere": normalized_hemisphere,
        },
        "planner_output": None,
        "current_tool": None,
        "steps": [],
        "tool_results": [],
        "error": None,
        "warnings": [warning] if warning else [],
        "result": None,
    }
    with AGENT_RUNTIME_LOCK:
        AGENT_RUNS[run_id] = run
        AGENT_EVENTS[run_id] = []
    _agent_log(
        run_id=run_id,
        stage="triage",
        tool="run",
        attempt=0,
        status="queued",
        error_code=None,
        latency_ms=0,
        message=f"source={source}",
    )
    return _safe_agent_copy(run)


def _start_deferred_upload_agent_run(run_id, job_id, file_id, patient_id):
    run = _get_agent_run(run_id)
    if not run:
        _upload_log(
            job_id=job_id,
            file_id=file_id,
            patient_id=patient_id,
            step="agent_trigger",
            status="failed",
            message="run_not_found",
            linked_run_id=run_id,
        )
        return False

    if run.get("status") != "queued":
        _upload_log(
            job_id=job_id,
            file_id=file_id,
            patient_id=patient_id,
            step="agent_trigger",
            status="skipped",
            message=f"run_status={run.get('status')}",
            linked_run_id=run_id,
        )
        return False

    _upload_log(
        job_id=job_id,
        file_id=file_id,
        patient_id=patient_id,
        step="agent_trigger",
        status="running",
        message="post_upload_summary",
        linked_run_id=run_id,
    )
    worker = threading.Thread(target=_run_agent_pipeline, args=(run_id,), daemon=True)
    worker.start()
    return True


def _update_agent_run(run_id, updater):
    with AGENT_RUNTIME_LOCK:
        run = AGENT_RUNS.get(run_id)
        if not run:
            return None
        updater(run)
        run["updated_at"] = _agent_now()
        return _safe_agent_copy(run)


def _get_agent_run(run_id):
    with AGENT_RUNTIME_LOCK:
        return _safe_agent_copy(AGENT_RUNS.get(run_id))


def _get_agent_events(run_id):
    with AGENT_RUNTIME_LOCK:
        return _safe_agent_copy(AGENT_EVENTS.get(run_id, []))


def _append_agent_event(
    run_id,
    agent_name,
    tool_name,
    status,
    input_ref=None,
    output_ref=None,
    latency_ms=None,
    error_code=None,
    retryable=False,
    attempt=1,
):
    event = {
        "event_id": str(uuid.uuid4()),
        "run_id": run_id,
        "timestamp": _agent_now(),
        "agent_name": agent_name,
        "tool_name": tool_name,
        "input_ref": input_ref,
        "output_ref": output_ref,
        "latency_ms": int(latency_ms or 0),
        "status": status,
        "error_code": error_code,
        "retryable": bool(retryable),
        "attempt": int(attempt),
    }
    with AGENT_RUNTIME_LOCK:
        AGENT_EVENTS.setdefault(run_id, []).append(event)
    run_state = _get_agent_run(run_id) or {}
    _agent_log(
        run_id=run_id,
        stage=run_state.get("stage"),
        tool=tool_name,
        attempt=event.get("attempt"),
        status=status,
        error_code=error_code,
        latency_ms=event.get("latency_ms"),
        message=f"agent={agent_name}",
    )
    return event


def _upsert_agent_step(run_id, tool_name, status, message="", retryable=False, attempt=1):
    def _mut(run):
        step = None
        for item in run.get("steps", []):
            if item.get("key") == tool_name:
                step = item
                break
        if not step:
            step = {
                "key": tool_name,
                "title": tool_name,
                "status": "pending",
                "message": "",
                "retryable": False,
                "attempts": 0,
                "started_at": None,
                "ended_at": None,
            }
            run["steps"].append(step)
        now = _agent_now()
        step["status"] = status
        step["message"] = str(message or "")
        step["retryable"] = bool(retryable)
        step["attempts"] = max(int(step.get("attempts", 0)), int(attempt))
        if status == "running":
            step["started_at"] = step["started_at"] or now
            step["ended_at"] = None
            run["current_tool"] = tool_name
        elif status in {"completed", "failed", "skipped"}:
            step["started_at"] = step["started_at"] or now
            step["ended_at"] = now
            if run.get("current_tool") == tool_name:
                run["current_tool"] = None

    _update_agent_run(run_id, _mut)


def _append_agent_tool_result(run_id, tool_result):
    def _mut(run):
        run.setdefault("tool_results", []).append(tool_result)

    _update_agent_run(run_id, _mut)


def _agent_tool_sequence(imaging_path):
    return AGENT_TOOL_SEQUENCE_MAP.get(str(imaging_path or "").strip(), [])


def _collect_case_upload_files(file_id):
    suffix_to_field = {
        "ncct": "ncct_file",
        "mcta": "mcta_file",
        "vcta": "vcta_file",
        "dcta": "dcta_file",
        "cbf": "cbf_file",
        "cbv": "cbv_file",
        "tmax": "tmax_file",
    }
    files = {}
    for suffix, field_name in suffix_to_field.items():
        pattern = os.path.join(app.config["UPLOAD_FOLDER"], f"{file_id}_{suffix}.nii*")
        matches = sorted(glob.glob(pattern))
        if not matches:
            continue
        path = matches[-1]
        files[field_name] = {
            "path": path,
            "filename": os.path.basename(path),
        }
    return files


def _latest_tool_result_by_name(run, tool_name):
    for item in reversed(run.get("tool_results", [])):
        if item.get("tool_name") == tool_name:
            return item
    return None


def _tool_attempts(run, tool_name):
    return sum(1 for x in run.get("tool_results", []) if x.get("tool_name") == tool_name)


def _run_triage_planner(run_id):
    run = _get_agent_run(run_id)
    if not run:
        return False, _tool_error_contract("TOOL_INPUT_INVALID", "run_id not found")

    started = time.time()
    planner_input = run.get("planner_input") or {}
    decision = _build_path_decision(planner_input.get("available_modalities") or [])
    if not decision.get("valid"):
        err = _tool_error_contract(
            "TOOL_INPUT_INVALID", decision.get("error") or "invalid modality path"
        )
        _append_agent_event(
            run_id=run_id,
            agent_name="Triage Planner Agent",
            tool_name="triage_planner",
            status="failed",
            input_ref=planner_input,
            output_ref=err,
            latency_ms=int((time.time() - started) * 1000),
            error_code=err["error_code"],
            retryable=err["retryable"],
            attempt=1,
        )
        return False, err

    execution_mode = str(run.get("execution_mode") or "default").strip().lower()
    if execution_mode == "post_upload_summary":
        tool_sequence = list(POST_UPLOAD_SUMMARY_TOOL_SEQUENCE)
    else:
        tool_sequence = _agent_tool_sequence(decision.get("imaging_path"))
    if not tool_sequence:
        err = _tool_error_contract(
            "TOOL_NOT_APPLICABLE", "No tool sequence for current imaging path"
        )
        _append_agent_event(
            run_id=run_id,
            agent_name="Triage Planner Agent",
            tool_name="triage_planner",
            status="failed",
            input_ref=planner_input,
            output_ref=err,
            latency_ms=int((time.time() - started) * 1000),
            error_code=err["error_code"],
            retryable=err["retryable"],
            attempt=1,
        )
        return False, err

    planner_output = {
        "imaging_path": decision["imaging_path"],
        "tool_sequence": tool_sequence,
        "should_generate_ctp": bool(decision.get("should_generate_ctp")),
        "should_run_stroke_analysis": bool(decision.get("should_run_stroke_analysis")),
        "path_decision": decision,
    }

    def _mut_state(state):
        state["stage"] = "tooling"
        state["planner_output"] = planner_output
        state["steps"] = [
            {
                "key": tool_name,
                "title": tool_name,
                "status": "pending",
                "message": "",
                "retryable": False,
                "attempts": 0,
                "started_at": None,
                "ended_at": None,
            }
            for tool_name in tool_sequence
        ]

    _update_agent_run(run_id, _mut_state)
    _append_agent_event(
        run_id=run_id,
        agent_name="Triage Planner Agent",
        tool_name="triage_planner",
        status="completed",
        input_ref=planner_input,
        output_ref=planner_output,
        latency_ms=int((time.time() - started) * 1000),
        error_code=None,
        retryable=False,
        attempt=1,
    )
    return True, planner_output


def _tool_detect_modalities(run):
    planner_output = run.get("planner_output") or {}
    decision = (planner_output.get("path_decision") or {}).copy()
    if not decision.get("valid"):
        return (
            False,
            None,
            _tool_error_contract("TOOL_INPUT_INVALID", "Path decision is invalid"),
        )
    return (
        True,
        {
            "raw_modalities": decision.get("raw_modalities") or [],
            "canonical_modalities": decision.get("canonical_modalities") or [],
            "imaging_path": decision.get("imaging_path"),
            "should_generate_ctp": bool(decision.get("should_generate_ctp")),
            "should_run_stroke_analysis": bool(decision.get("should_run_stroke_analysis")),
        },
        None,
    )


def _tool_load_patient_context(run):
    planner_input = run.get("planner_input") or {}
    patient_id = planner_input.get("patient_id")
    file_id = planner_input.get("file_id")
    if not patient_id or not file_id:
        return (
            False,
            None,
            _tool_error_contract("TOOL_INPUT_INVALID", "Missing patient_id or file_id"),
        )

    patient_data = get_patient_by_id(patient_id)
    if not patient_data:
        return (
            False,
            None,
            _tool_error_contract("TOOL_INPUT_INVALID", f"Patient {patient_id} not found"),
        )

    imaging_data = get_imaging_by_case(patient_id, file_id)
    wait_start = time.time()
    wait_timeout_s = 10.0
    wait_interval_s = 0.5
    while not imaging_data and (time.time() - wait_start) < wait_timeout_s:
        time.sleep(wait_interval_s)
        imaging_data = get_imaging_by_case(patient_id, file_id)

    if not imaging_data:
        return (
            False,
            None,
            _tool_error_contract(
                "TOOL_DEPENDENCY_MISSING",
                f"Imaging case {file_id} not found for patient {patient_id} "
                f"after waiting {int(time.time() - wait_start)}s",
            ),
        )

    hemisphere, warning = _canonicalize_hemisphere(
        planner_input.get("hemisphere")
        or imaging_data.get("hemisphere")
        or patient_data.get("hemisphere")
    )
    output = {
        "context_struct": {
            "patient_id": patient_id,
            "file_id": file_id,
            "patient": {
                "patient_age": patient_data.get("patient_age"),
                "patient_sex": patient_data.get("patient_sex"),
                "admission_nihss": patient_data.get("admission_nihss"),
            },
            "imaging": {
                "available_modalities": _normalize_uploaded_modalities(
                    imaging_data.get("available_modalities") or []
                ),
                "hemisphere": hemisphere,
            },
        },
        "hemisphere": hemisphere,
        "missing_flags": [],
    }
    if warning:
        output["missing_flags"].append(warning)
    return True, output, None


def _tool_generate_ctp_maps(run):
    planner_input = run.get("planner_input") or {}
    file_id = planner_input.get("file_id")
    patient_id = planner_input.get("patient_id")
    hemisphere = planner_input.get("hemisphere", "both")
    if not file_id or not patient_id:
        return (
            False,
            None,
            _tool_error_contract("TOOL_INPUT_INVALID", "Missing patient_id or file_id"),
        )

    files = _collect_case_upload_files(file_id)
    required = ["ncct_file", "mcta_file", "vcta_file", "dcta_file"]
    missing = [key for key in required if key not in files]
    if missing:
        return (
            False,
            None,
            _tool_error_contract(
                "TOOL_DEPENDENCY_MISSING",
                f"Missing required uploaded files: {', '.join(missing)}",
            ),
        )

    payload = {
        "patient_id": patient_id,
        "file_id": file_id,
        "files": {key: files[key] for key in required},
        "hemisphere": hemisphere,
        "model_type": "mrdpm",
        "upload_mode": "ncct_3phase_cta",
        "skip_ai": True,
    }
    ok, msg, upload_result = _invoke_internal_upload(payload)
    if not ok:
        return (
            False,
            None,
            _tool_error_contract("TOOL_EXECUTION_FAILED", f"CTP generation failed: {msg}"),
        )

    has_ctp = _result_has_ctp_images(upload_result)
    if not has_ctp:
        return (
            False,
            None,
            _tool_error_contract("TOOL_EXECUTION_FAILED", "CTP images were not generated"),
        )

    return (
        True,
        {
            "ctp_generated": True,
            "generated_modalities": ["cbf", "cbv", "tmax"],
            "artifacts_ref": [
                upload_result.get("file_id") or file_id,
                upload_result.get("json_path"),
            ],
            "total_slices": upload_result.get("total_slices"),
        },
        None,
    )


def _tool_run_stroke_analysis(run):
    planner_input = run.get("planner_input") or {}
    file_id = planner_input.get("file_id")
    patient_id = planner_input.get("patient_id")
    hemisphere = planner_input.get("hemisphere", "both")
    if not file_id:
        return (
            False,
            None,
            _tool_error_contract("TOOL_INPUT_INVALID", "Missing file_id"),
        )

    analysis = analyze_stroke_case(file_id, hemisphere)
    if not analysis or not analysis.get("success"):
        return (
            False,
            None,
            _tool_error_contract(
                "TOOL_EXECUTION_FAILED",
                (analysis or {}).get("error", "Stroke analysis failed"),
            ),
        )

    report_summary = ((analysis.get("report") or {}).get("summary") or {}) if isinstance(analysis, dict) else {}
    core_volume = report_summary.get("core_volume_ml")
    penumbra_volume = report_summary.get("penumbra_volume_ml")
    mismatch_ratio = report_summary.get("mismatch_ratio")

    def _to_float(value):
        try:
            return float(value)
        except Exception:
            return None

    if patient_id:
        update_analysis_result(
            patient_id,
            {
                "core_infarct_volume": _to_float(core_volume),
                "penumbra_volume": _to_float(penumbra_volume),
                "mismatch_ratio": _to_float(mismatch_ratio),
                "hemisphere": hemisphere,
                "analysis_status": "completed",
            },
        )

    return (
        True,
        {
            "core_infarct_volume": _to_float(core_volume),
            "penumbra_volume": _to_float(penumbra_volume),
            "mismatch_ratio": _to_float(mismatch_ratio),
            "analysis_status": "completed",
            "hemisphere": hemisphere,
        },
        None,
    )


def _tool_generate_medgemma_report(run):
    planner_input = run.get("planner_input") or {}
    patient_id = planner_input.get("patient_id")
    file_id = planner_input.get("file_id")
    if not patient_id or not file_id:
        return (
            False,
            None,
            _tool_error_contract("TOOL_INPUT_INVALID", "Missing patient_id or file_id"),
        )

    ok, msg, data = _invoke_internal_generate_report(patient_id, file_id)
    if not ok:
        return (
            False,
            None,
            _tool_error_contract("TOOL_EXTERNAL_API_FAILED", msg),
        )
    return (
        True,
        {
            "report": data.get("report"),
            "report_payload": data.get("report_payload"),
            "json_path": data.get("json_path"),
        },
        None,
    )


def _execute_agent_tool(run_id, tool_name):
    run = _get_agent_run(run_id)
    if not run:
        return False, _tool_error_contract("TOOL_INPUT_INVALID", "run_id not found")

    attempt = _tool_attempts(run, tool_name) + 1
    _upsert_agent_step(run_id, tool_name, "running", "Tool is running", attempt=attempt)

    started = time.time()
    input_ref = {"run_id": run_id, "tool_name": tool_name}

    try:
        if tool_name == "detect_modalities":
            ok, output, err = _tool_detect_modalities(run)
            agent_name = "Triage Planner Agent"
        elif tool_name == "load_patient_context":
            ok, output, err = _tool_load_patient_context(run)
            agent_name = "Triage Planner Agent"
        elif tool_name == "generate_ctp_maps":
            ok, output, err = _tool_generate_ctp_maps(run)
            agent_name = "Clinical Tool Agent"
        elif tool_name == "run_stroke_analysis":
            ok, output, err = _tool_run_stroke_analysis(run)
            agent_name = "Clinical Tool Agent"
        elif tool_name == "generate_medgemma_report":
            ok, output, err = _tool_generate_medgemma_report(run)
            agent_name = "Clinical Summary Agent"
        else:
            ok = False
            output = None
            err = _tool_error_contract(
                "TOOL_NOT_APPLICABLE", f"Unknown tool_name: {tool_name}"
            )
            agent_name = "Clinical Tool Agent"
    except Exception as exc:
        ok = False
        output = None
        err = _tool_error_contract("TOOL_EXECUTION_FAILED", str(exc))
        agent_name = "Clinical Tool Agent"

    latency_ms = int((time.time() - started) * 1000)
    if ok:
        tool_result = {
            "tool_name": tool_name,
            "status": "completed",
            "error_code": None,
            "retryable": False,
            "structured_output": output,
            "raw_ref": {"tool_name": tool_name},
            "latency_ms": latency_ms,
            "attempt": attempt,
        }
        _append_agent_tool_result(run_id, tool_result)
        _upsert_agent_step(
            run_id, tool_name, "completed", "Tool completed", retryable=False, attempt=attempt
        )
        _append_agent_event(
            run_id=run_id,
            agent_name=agent_name,
            tool_name=tool_name,
            status="completed",
            input_ref=input_ref,
            output_ref=output,
            latency_ms=latency_ms,
            error_code=None,
            retryable=False,
            attempt=attempt,
        )
        return True, tool_result

    tool_result = {
        "tool_name": tool_name,
        "status": "failed",
        "error_code": err["error_code"],
        "retryable": bool(err["retryable"]),
        "structured_output": None,
        "raw_ref": {"tool_name": tool_name},
        "latency_ms": latency_ms,
        "attempt": attempt,
        "error_message": err["error_message"],
        "suggested_action": err["suggested_action"],
    }
    _append_agent_tool_result(run_id, tool_result)
    _upsert_agent_step(
        run_id,
        tool_name,
        "failed",
        err["error_message"],
        retryable=err["retryable"],
        attempt=attempt,
    )
    _append_agent_event(
        run_id=run_id,
        agent_name=agent_name,
        tool_name=tool_name,
        status="failed",
        input_ref=input_ref,
        output_ref=err,
        latency_ms=latency_ms,
        error_code=err["error_code"],
        retryable=err["retryable"],
        attempt=attempt,
    )
    return False, tool_result


def _build_context_from_completed_tools(run):
    context = {
        "path_decision": ((run.get("planner_output") or {}).get("path_decision") or {}),
        "patient_context": None,
        "analysis_result": None,
        "report_result": None,
    }
    for result in run.get("tool_results", []):
        if result.get("status") != "completed":
            continue
        tool_name = result.get("tool_name")
        output = result.get("structured_output")
        if tool_name == "load_patient_context":
            context["patient_context"] = output
        elif tool_name == "run_stroke_analysis":
            context["analysis_result"] = output
        elif tool_name == "generate_medgemma_report":
            context["report_result"] = output
    return context


def _run_agent_pipeline(run_id, start_tool=None):
    def _start_mut(run):
        run["status"] = "running"
        if start_tool:
            run["stage"] = "tooling"
        else:
            run["stage"] = "triage"
        run["error"] = None
        run["result"] = None

    run = _update_agent_run(run_id, _start_mut)
    if not run:
        return
    _agent_log(
        run_id=run_id,
        stage=run.get("stage"),
        tool=start_tool or "run",
        attempt=1,
        status="run_start",
        error_code=None,
        latency_ms=0,
        message="pipeline_start",
    )

    if not start_tool:
        ok, planner_out = _run_triage_planner(run_id)
        if not ok:
            def _fail_triage(state):
                state["status"] = "failed"
                state["stage"] = "triage"
                state["error"] = planner_out

            _update_agent_run(run_id, _fail_triage)
            _agent_log(
                run_id=run_id,
                stage="triage",
                tool="triage_planner",
                attempt=1,
                status="run_failed",
                error_code=(planner_out or {}).get("error_code"),
                latency_ms=0,
                message=(planner_out or {}).get("error_message"),
            )
            return

    run = _get_agent_run(run_id)
    planner_output = run.get("planner_output") or {}
    tool_sequence = planner_output.get("tool_sequence") or []
    if not tool_sequence:
        err = _tool_error_contract("TOOL_NOT_APPLICABLE", "Empty tool sequence")

        def _fail_empty(state):
            state["status"] = "failed"
            state["stage"] = "triage"
            state["error"] = err

        _update_agent_run(run_id, _fail_empty)
        _agent_log(
            run_id=run_id,
            stage="triage",
            tool="triage_planner",
            attempt=1,
            status="run_failed",
            error_code=err.get("error_code"),
            latency_ms=0,
            message=err.get("error_message"),
        )
        return

    start_index = 0
    if start_tool:
        if start_tool not in tool_sequence:
            err = _tool_error_contract(
                "TOOL_NOT_APPLICABLE", f"Retry step {start_tool} not in tool sequence"
            )

            def _fail_retry_step(state):
                state["status"] = "failed"
                state["stage"] = "tooling"
                state["error"] = err

            _update_agent_run(run_id, _fail_retry_step)
            _agent_log(
                run_id=run_id,
                stage="tooling",
                tool=start_tool,
                attempt=1,
                status="run_failed",
                error_code=err.get("error_code"),
                latency_ms=0,
                message=err.get("error_message"),
            )
            return
        start_index = tool_sequence.index(start_tool)

    for tool_name in tool_sequence[start_index:]:
        ok, tool_result = _execute_agent_tool(run_id, tool_name)
        if not ok:
            fail_contract = _tool_error_contract(
                tool_result.get("error_code"),
                tool_result.get("error_message") or "Tool execution failed",
            )

            def _fail_tool(state):
                state["status"] = "failed"
                state["stage"] = "tooling"
                state["error"] = fail_contract

            _update_agent_run(run_id, _fail_tool)
            _agent_log(
                run_id=run_id,
                stage="tooling",
                tool=tool_name,
                attempt=tool_result.get("attempt"),
                status="run_failed",
                error_code=fail_contract.get("error_code"),
                latency_ms=tool_result.get("latency_ms"),
                message=fail_contract.get("error_message"),
            )
            return

    run = _get_agent_run(run_id)
    context = _build_context_from_completed_tools(run)
    final_result = {
        "summary": "Week3 main chain completed",
        "path_decision": (planner_output.get("path_decision") or {}),
        "tool_sequence": tool_sequence,
        "tool_results": run.get("tool_results", []),
        "patient_context": context.get("patient_context"),
        "analysis_result": context.get("analysis_result"),
        "report_result": context.get("report_result"),
        "uncertainties": [],
        "next_actions": [],
    }

    def _complete(state):
        state["status"] = "succeeded"
        state["stage"] = "done"
        state["current_tool"] = None
        state["error"] = None
        state["result"] = final_result

    _update_agent_run(run_id, _complete)
    _agent_log(
        run_id=run_id,
        stage="done",
        tool="run",
        attempt=1,
        status="run_done",
        error_code=None,
        latency_ms=0,
        message="pipeline_completed",
    )
    _append_agent_event(
        run_id=run_id,
        agent_name="Clinical Summary Agent",
        tool_name="summary",
        status="completed",
        input_ref={"run_id": run_id},
        output_ref={"status": "succeeded"},
        latency_ms=0,
        error_code=None,
        retryable=False,
        attempt=1,
    )


def _queue_agent_retry(run_id, step_key, reason=""):
    run = _get_agent_run(run_id)
    if not run:
        return False, "Run not found"
    if run.get("status") == "running":
        return False, "Run is currently running"
    if run.get("status") != "failed":
        return False, "Only failed runs can retry"

    step_key = str(step_key or "").strip()
    if not step_key:
        return False, "Missing step_key"

    last_result = _latest_tool_result_by_name(run, step_key)
    if not last_result:
        return False, f"No tool result found for step {step_key}"
    if last_result.get("status") != "failed":
        return False, f"Step {step_key} is not in failed state"
    if not last_result.get("retryable"):
        return False, f"Step {step_key} is not retryable"

    attempts = _tool_attempts(run, step_key)
    retries_done = max(0, attempts - 1)
    retry_limit = int(AGENT_TOOL_RETRY_LIMITS.get(step_key, 0))
    if retries_done >= retry_limit:
        return False, f"Retry limit reached for step {step_key}"

    _append_agent_event(
        run_id=run_id,
        agent_name="System",
        tool_name=step_key,
        status="retry_queued",
        input_ref={"reason": reason or "manual retry"},
        output_ref={"retry_limit": retry_limit, "retries_done": retries_done},
        latency_ms=0,
        error_code=None,
        retryable=True,
        attempt=attempts + 1,
    )

    worker = threading.Thread(
        target=_run_agent_pipeline,
        args=(run_id, step_key),
        daemon=True,
    )
    worker.start()
    return True, "Retry started"


AI_CONFIG_BASE = os.path.join(PROJECT_ROOT, "palette", "config")
AI_WEIGHTS_BASE = os.path.join(PROJECT_ROOT, "palette", "weights")

# 涓変釜妯″瀷鐨勯厤缃?
MODEL_CONFIGS = {
    "cbf": {
        "name": "CBF灌注图",
        "config_path": os.path.join(AI_CONFIG_BASE, "cbf.json"),
        "weight_dir": os.path.join(AI_WEIGHTS_BASE, "cbf"),
        "use_ema": True,
        "color": "#e74c3c",  # 绾㈣壊
        "description": "鑴戣娴侀噺 (Cerebral Blood Flow)",
    },
    "cbv": {
        "name": "CBV灌注图",
        "config_path": os.path.join(AI_CONFIG_BASE, "cbv.json"),
        "weight_dir": os.path.join(AI_WEIGHTS_BASE, "cbv"),
        "use_ema": True,
        "color": "#3498db",  # 钃濊壊
        "description": "鑴戣瀹归噺 (Cerebral Blood Volume)",
    },
    "tmax": {
        "name": "Tmax灌注图",
        "config_path": os.path.join(AI_CONFIG_BASE, "tmax.json"),
        "weight_dir": os.path.join(AI_WEIGHTS_BASE, "tmax"),
        "use_ema": True,
        "color": "#27ae60",  # 缁胯壊
        "description": "杈惧嘲鏃堕棿 (Time to Maximum)",
    },
}


def find_weight_file(weight_dir: str, pattern: str) -> str:
    """
    鍦ㄦ潈閲嶇洰褰曚腑鏌ユ壘鍖归厤鐨勬枃浠?

    Args:
        weight_dir: 鏉冮噸鐩綍璺緞
        pattern: 鏂囦欢鍚嶆ā寮忥紙濡?"200_Network_ema.pth"锛?

    Returns:
        鎵惧埌鐨勬枃浠惰矾寰勶紝鎴?None
    """
    if not os.path.exists(weight_dir):
        return None

    # 鐩存帴鍖归厤
    direct_path = os.path.join(weight_dir, pattern)
    if os.path.exists(direct_path):
        return direct_path

    # 鏌ユ壘鎵€鏈?.pth 鏂囦欢骞跺尮閰嶅墠缂€
    for filename in os.listdir(weight_dir):
        if filename.endswith(".pth") and filename.startswith(pattern.split("_")[0]):
            return os.path.join(weight_dir, filename)

    return None


def get_weight_base_path(weight_dir: str) -> str:
    """
    鑾峰彇鏉冮噸鏂囦欢鐨勫熀纭€璺緞锛堝幓鎺夋枃浠跺悕锛?
    鏉冮噸鏂囦欢鍚嶆牸寮? XXX_Network.pth 鎴?XXX_Network_ema.pth
    """
    if not os.path.exists(weight_dir):
        return None

    # 鏌ユ壘鏉冮噸鏂囦欢
    for filename in os.listdir(weight_dir):
        if filename.endswith("_Network.pth") or filename.endswith("_Network_ema.pth"):
            # 鎻愬彇鏁板瓧閮ㄥ垎锛堝 200锛?
            prefix = filename.split("_")[0]
            return os.path.join(weight_dir, prefix)

    return None


# 鍏ㄥ眬妯″瀷瀛楀吀
ai_models = {}

# 缁熶竴鐨勪吉褰╁浘閰嶇疆 - 浣跨敤鍖诲鏍囧噯棰滆壊鏄犲皠
PSEUDOCOLOR_CONFIG = {
    "colormap": "jet",  # 鍖诲鍥惧儚鏍囧噯棰滆壊鏄犲皠
    "vmin": 0.1,  # 蹇界暐杩囦綆鐨勫€?
    "vmax": 0.9,  # 閬垮厤杩囬ケ鍜?
}


def init_ai_models():
    """鍒濆鍖栨墍鏈堿I妯″瀷"""
    global ai_models
    ai_models = {}

    print("=" * 50)
    print("寮€濮嬪垵濮嬪寲AI妯″瀷...")
    print("=" * 50)

    models_initialized = 0

    # 鑷姩妫€娴嬭澶囷紝浼樺厛浣跨敤CUDA锛屽鏋滀笉鍙敤鍒欎娇鐢–PU
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"浣跨敤璁惧: {device}")

    for model_key, config in MODEL_CONFIGS.items():
        print(f"\n鍒濆鍖?{config['name']} 妯″瀷:")
        print(f"  閰嶇疆璺緞: {config['config_path']}")
        print(f"  鏉冮噸鐩綍: {config['weight_dir']}")

        # 浣跨敤鏂扮殑鏉冮噸妫€娴嬮€昏緫
        weight_base = get_weight_base_path(config["weight_dir"])

        # 妫€鏌ユ枃浠舵槸鍚﹀瓨鍦?
        config_exists = os.path.exists(config["config_path"])
        ema_exists = (
            find_weight_file(config["weight_dir"], "_Network_ema.pth") is not None
        )
        normal_exists = (
            find_weight_file(config["weight_dir"], "_Network.pth") is not None
        )

        print(f"  配置文件: {'✓' if config_exists else '✗'}")
        print(f"  鏉冮噸鍩虹璺緞: {weight_base}")
        print(f"  EMA权重: {'✓' if ema_exists else '✗'}")
        print(f"  普通权重: {'✓' if normal_exists else '✗'}")

        if config_exists and weight_base:
            try:
                # 杩欓噷闇€瑕佹牴鎹偍鐨刟i_inference妯″潡璋冩暣鍒濆鍖栨柟寮?
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

    print(f"\n模型初始化统计: {models_initialized}/{len(MODEL_CONFIGS)} 个模型成功初始化")
    print("=" * 50)

    return models_initialized > 0


def init_single_ai_model(config_path, weight_base, use_ema=True, device="cpu"):
    """鍒濆鍖栧崟涓狝I妯″瀷"""
    try:
        # 杩欓噷闇€瑕佹牴鎹偍鐨刟i_inference妯″潡璋冩暣鍒濆鍖栨柟寮?
        try:
            from .ai_inference import MedicalAIModel
        except ImportError:
            from ai_inference import MedicalAIModel

        model = MedicalAIModel(config_path, weight_base, use_ema=use_ema, device=device)
        return model
    except Exception as e:
        print(f"鍒濆鍖栧崟涓ā鍨嬪け璐? {e}")
        return None


def get_ai_model(model_key="cbf"):
    """鑾峰彇鎸囧畾鐨凙I妯″瀷"""
    global ai_models
    if model_key in ai_models and ai_models[model_key]["available"]:
        return ai_models[model_key]["model"]
    return None


def are_any_models_available():
    """妫€鏌ユ槸鍚︽湁浠讳綍妯″瀷鍙敤"""
    global ai_models
    return any(model_info["available"] for model_info in ai_models.values())


def get_available_models():
    """Return a list of available model keys."""
    global ai_models
    # 浠巔alette妯″瀷閰嶇疆涓幏鍙栧彲鐢ㄦā鍨?
    available = [key for key, info in ai_models.items() if info["available"]]
    # 娣诲姞mrdpm妯″瀷锛堝鏋滄湁MRDPM鏉冮噸鏂囦欢锛?
    mrdpm_available = check_mrdpm_models_available()
    for model_key in mrdpm_available:
        if model_key not in available:
            available.append(model_key)
    return available


def check_mrdpm_models_available():
    """妫€鏌RDPM妯″瀷鏄惁鍙敤"""
    available = []
    mrdpm_weights_dir = os.path.join(PROJECT_ROOT, "mrdpm", "weights")

    if not os.path.exists(mrdpm_weights_dir):
        return available

    # 妫€鏌rdpm涓荤洰褰曟槸鍚﹀瓨鍦紙浣跨敤mrdpm浣滀负鐗规畩model_key锛?
    bran_path = os.path.join(mrdpm_weights_dir, "bran_pretrained_3channel.pth")
    residual_path = os.path.join(mrdpm_weights_dir, "200_Network_ema.pth")

    # mrdpm浣滀负鐗规畩鏍囪瘑锛屽彧瑕佹湁涓€涓瓙妯″瀷鍙敤锛宮rdpm灏卞彲鐢?
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


# ==================== 鏀硅繘鐨勪吉褰╁浘鐢熸垚鍑芥暟 ====================


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
    涓哄崟涓垏鐗囩殑鐏板害鍥剧敓鎴愪吉褰╁浘 - 鏀硅繘鐗堟湰
    """
    try:
        print(f"涓哄垏鐗?{slice_idx} 鐨?{model_key.upper()} 鐢熸垚鍖诲鏍囧噯浼僵鍥?..")

        # 妫€鏌ユ枃浠舵槸鍚﹀瓨鍦?
        if not os.path.exists(grayscale_path):
            return {"success": False, "error": "鐏板害鍥句笉瀛樺湪"}

        # 鍔犺浇鍥惧儚鏁版嵁
        grayscale_img = Image.open(grayscale_path).convert("L")
        grayscale_data = np.array(grayscale_img) / 255.0

        # 灏濊瘯鍔犺浇鎺╃爜鏂囦欢锛屽鏋滀笉瀛樺湪鍒欏垱寤洪粯璁ゆ帺鐮?
        # 棣栧厛灏濊瘯鏍囧噯鎺╃爜鏂囦欢鏍煎紡锛坰lice_000_mask.png锛?
        standard_mask_path = os.path.join(output_dir, f"slice_{slice_idx:03d}_mask.png")
        if os.path.exists(standard_mask_path):
            mask_img = Image.open(standard_mask_path).convert("L")
            mask_data = np.array(mask_img) / 255.0
            print(f"浣跨敤鏍囧噯鎺╃爜鏂囦欢: {standard_mask_path}")
        elif os.path.exists(mask_path):
            # 鐒跺悗灏濊瘯浼犲叆鐨刴ask_path
            mask_img = Image.open(mask_path).convert("L")
            mask_data = np.array(mask_img) / 255.0
            print(f"浣跨敤鎺╃爜鏂囦欢: {mask_path}")
        else:
            # 鍒涘缓榛樿鎺╃爜锛堜娇鐢ㄦ洿鍚堢悊鐨勯槇鍊硷紝鑰屼笉鏄叏鐧斤級
            print(f"鎺╃爜鏂囦欢涓嶅瓨鍦紝鍒涘缓榛樿鎺╃爜: {standard_mask_path}")
            # 浣跨敤Otsu闃堝€煎垱寤烘帺鐮侊紝鑰屼笉鏄叏鐧?
            from skimage import filters

            try:
                otsu_threshold = filters.threshold_otsu(grayscale_data)
                mask_data = grayscale_data > otsu_threshold
            except:
                # 濡傛灉Otsu澶辫触锛屼娇鐢ㄥ熀浜庣櫨鍒嗘瘮鐨勯槇鍊?
                low_thresh = np.percentile(grayscale_data, 10)
                high_thresh = np.percentile(grayscale_data, 90)
                mask_data = np.logical_and(
                    grayscale_data > low_thresh, grayscale_data < high_thresh
                )
            # 淇濆瓨榛樿鎺╃爜鍒版枃浠剁郴缁燂紙浣跨敤鏍囧噯鍛藉悕鏍煎紡锛?
            mask_8bit = (mask_data * 255).astype(np.uint8)
            os.makedirs(os.path.dirname(standard_mask_path), exist_ok=True)
            Image.fromarray(mask_8bit).save(standard_mask_path)
            print(f"榛樿鎺╃爜宸蹭繚瀛? {standard_mask_path}")

        # 鐢熸垚鍖诲鏍囧噯浼僵鍥?
        pseudocolor_data, lut_stats = create_medical_pseudocolor(
            grayscale_data, mask_data
        )

        # 淇濆瓨浼僵鍥?
        slice_prefix = f"slice_{slice_idx:03d}"
        pseudocolor_path = os.path.join(
            output_dir, f"{slice_prefix}_{model_key}_pseudocolor.png"
        )

        # 纭繚鐩綍瀛樺湪
        os.makedirs(os.path.dirname(pseudocolor_path), exist_ok=True)
        Image.fromarray(pseudocolor_data).save(pseudocolor_path)

        # 鏋勫缓URL
        file_id = os.path.basename(output_dir)
        pseudocolor_url = (
            f"/get_image/{file_id}/{slice_prefix}_{model_key}_pseudocolor.png"
        )

        print(f"鉁?{model_key.upper()} 鍖诲鏍囧噯浼僵鍥剧敓鎴愭垚鍔? {pseudocolor_path}")

        return {
            "success": True,
            "pseudocolor_url": pseudocolor_url,
            "colormap": "jet",  # 缁熶竴浣跨敤jet棰滆壊鏄犲皠
            "output_path": pseudocolor_path,
            "lut_stats": lut_stats,
        }

    except Exception as e:
        print(f"鉁?鐢熸垚浼僵鍥惧け璐? {e}")
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def generate_all_pseudocolors(output_dir, file_id, slice_idx):
    """
    涓哄崟涓垏鐗囩殑鎵€鏈夋ā鍨嬬敓鎴愪吉褰╁浘 - 鏀硅繘鐗堟湰
    """
    try:
        pseudocolor_results = {}
        success_count = 0

        for model_key in MODEL_CONFIGS.keys():
            # 鏋勫缓鏂囦欢璺緞
            slice_prefix = f"slice_{slice_idx:03d}"
            # 棣栧厛灏濊瘯鏌ユ壘AI鐢熸垚鐨勮緭鍑烘枃浠?
            grayscale_path = os.path.join(
                output_dir, f"{slice_prefix}_{model_key}_output.png"
            )
            # 濡傛灉AI杈撳嚭鏂囦欢涓嶅瓨鍦紝灏濊瘯鏌ユ壘鍘熷CTP鍥惧儚鏂囦欢
            if not os.path.exists(grayscale_path):
                grayscale_path = os.path.join(
                    output_dir, f"{slice_prefix}_{model_key}.png"
                )
            mask_path = os.path.join(output_dir, f"{slice_prefix}_mask.png")
            # 濡傛灉鏍囧噯鎺╃爜鏂囦欢涓嶅瓨鍦紝灏濊瘯鏌ユ壘鍏朵粬鍙兘鐨勬帺鐮佹枃浠?
            if not os.path.exists(mask_path):
                mask_path = os.path.join(output_dir, f"{slice_prefix}_ncct_mask.png")

            # 妫€鏌ョ伆搴﹀浘鏂囦欢鏄惁瀛樺湪
            if os.path.exists(grayscale_path):
                print(f"\n--- 涓?{model_key.upper()} 鐢熸垚鍖诲鏍囧噯浼僵鍥?---")
                result = generate_pseudocolor_for_slice(
                    grayscale_path, mask_path, output_dir, slice_idx, model_key
                )
                pseudocolor_results[model_key] = result
                if result["success"]:
                    success_count += 1
            else:
                error_msg = f"鏂囦欢涓嶅瓨鍦? {grayscale_path}"
                print(f"鉁?{error_msg}")
                pseudocolor_results[model_key] = {"success": False, "error": error_msg}

        print(f"\n伪彩图生成统计: {success_count}/{len(MODEL_CONFIGS)} 个模型成功")
        return pseudocolor_results

    except Exception as e:
        print(f"鐢熸垚鎵€鏈変吉褰╁浘澶辫触: {e}")
        traceback.print_exc()
        return {}


# ==================== 璺敱鍑芥暟 ====================


@app.route("/generate_pseudocolor/<file_id>/<int:slice_index>")
def generate_pseudocolor(file_id, slice_index):
    """鐢熸垚鎸囧畾鍒囩墖鐨勪吉褰╁浘 - 鍖诲鏍囧噯鐗堟湰"""
    try:
        output_dir = os.path.join(app.config["PROCESSED_FOLDER"], file_id)

        if not os.path.exists(output_dir):
            return jsonify({"success": False, "error": "文件目录不存在"})

        print(f"寮€濮嬩负鍒囩墖 {slice_index} 鐢熸垚鍖诲鏍囧噯浼僵鍥?..")

        # 鐢熸垚鎵€鏈夋ā鍨嬬殑浼僵鍥?
        pseudocolor_results = generate_all_pseudocolors(
            output_dir, file_id, slice_index
        )

        # 缁熻鎴愬姛鏁伴噺
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
        print(f"鐢熸垚浼僵鍥捐矾鐢遍敊璇? {e}")
        return jsonify({"success": False, "error": str(e)})


@app.route("/generate_all_pseudocolors/<file_id>")
def generate_all_pseudocolors_route(file_id):
    """涓烘墍鏈夊垏鐗囩敓鎴愪吉褰╁浘 - 鍖诲鏍囧噯鐗堟湰"""
    try:
        output_dir = os.path.join(app.config["PROCESSED_FOLDER"], file_id)

        if not os.path.exists(output_dir):
            return jsonify({"success": False, "error": "文件目录不存在"})

        # 鏌ユ壘鎵€鏈夊垏鐗?
        # 鍚屾椂鏌ユ壘AI鐢熸垚鐨勬枃浠跺拰鍘熷CTP鏂囦欢
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
                # 鎻愬彇鍒囩墖绱㈠紩锛歴lice_001_cbf_output.png 鎴?slice_001_cbf.png -> 1
                index_str = file.split("_")[1]
                slice_index = int(index_str)
                slice_indices.append(slice_index)
            except:
                continue

        slice_indices.sort()

        if not slice_indices:
            return jsonify({"success": False, "error": "未找到切片文件"})

        print(f"寮€濮嬩负 {len(slice_indices)} 涓垏鐗囩敓鎴愬尰瀛︽爣鍑嗕吉褰╁浘...")

        all_results = {}
        total_success = 0

        for slice_idx in slice_indices:
            print(f"\n=== 澶勭悊鍒囩墖 {slice_idx} ===")
            results = generate_all_pseudocolors(output_dir, file_id, slice_idx)
            all_results[slice_idx] = results

            # 缁熻璇ュ垏鐗囩殑鎴愬姛鏁伴噺
            slice_success = sum(1 for result in results.values() if result["success"])
            total_success += slice_success
            print(f"鍒囩墖 {slice_idx} 瀹屾垚: {slice_success}/{len(MODEL_CONFIGS)}")

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
                "message": f"鎴愬姛涓?{total_success}/{total_attempts} 涓粍鍚堢敓鎴愬尰瀛︽爣鍑嗕吉褰╁浘",
            }
        )

    except Exception as e:
        print(f"鐢熸垚鎵€鏈変吉褰╁浘璺敱閿欒: {e}")
        return jsonify({"success": False, "error": str(e)})


@app.route("/analyze_stroke/<file_id>")
def analyze_stroke(file_id):
    """执行脑卒中病灶分析。"""
    try:
        # 鑾峰彇鍋忎晶鍙傛暟锛堥粯璁や负鍙屼晶锛?
        hemisphere = request.args.get("hemisphere", "both")

        print(f"寮€濮嬭剳鍗掍腑鍒嗘瀽 - 鐥呬緥: {file_id}, 鍋忎晶: {hemisphere}")

        # 璋冪敤鍒嗘瀽鍑芥暟
        analysis_results = analyze_stroke_case(file_id, hemisphere)

        # 灏唍umpy绫诲瀷杞崲涓篜ython鍘熺敓绫诲瀷浠ョ‘淇滼SON搴忓垪鍖?
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

        # 杞崲鍒嗘瀽缁撴灉涓殑numpy绫诲瀷
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
                {"success": False, "error": analysis_results.get("error", "鍒嗘瀽澶辫触")}
            )

    except Exception as e:
        print(f"鑴戝崚涓垎鏋愯矾鐢遍敊璇? {e}")
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)})


@app.route("/get_stroke_analysis_image/<file_id>/<filename>")
def get_stroke_analysis_image(file_id, filename):
    """鑾峰彇鑴戝崚涓垎鏋愮敓鎴愮殑鍥惧儚"""
    try:
        image_path = os.path.join(
            app.config["PROCESSED_FOLDER"], file_id, "stroke_analysis", filename
        )
        print(f"鑾峰彇鑴戝崚涓垎鏋愬浘鍍? {image_path}")  # 璋冭瘯淇℃伅
        if os.path.exists(image_path):
            return send_file(image_path, mimetype="image/png")
        else:
            print(f"鍒嗘瀽鍥惧儚涓嶅瓨鍦? {image_path}")  # 璋冭瘯淇℃伅
            return jsonify({"error": "分析图像不存在"}), 404
    except Exception as e:
        print(f"鑾峰彇鑴戝崚涓垎鏋愬浘鍍忛敊璇? {e}")  # 璋冭瘯淇℃伅
        return jsonify({"error": str(e)}), 404


@app.route("/api/insert_patient", methods=["POST"])
def api_insert_patient():
    # 1. 鎺ユ敹鍓嶇浼犺繃鏉ョ殑JSON鏁版嵁
    data = request.get_json()
    print("鏀跺埌鏁版嵁:", data)

    # 2. 鏍稿績琛ュ叏锛氳皟鐢ㄤ綘core鐩綍閲岀殑鍏ュ簱鍑芥暟锛屾墽琛孲upabase鍐欏叆鎿嶄綔
    success, result = insert_patient_info(data)

    # 3. 鏍规嵁鍏ュ簱缁撴灉锛岃繑鍥炵湡瀹炵殑鍝嶅簲缁欏墠绔?
    if success:
        # 鍐欏叆鎴愬姛锛氳繑鍥炵湡瀹炵殑鍏ュ簱鏁版嵁锛堝惈Supabase鑷姩鐢熸垚鐨処D锛?
        return jsonify({"status": "success", "message": "鏁版嵁鍐欏叆鎴愬姛", "data": result})
    else:
        # 鍐欏叆澶辫触锛氳繑鍥為敊璇俊鎭紝鍓嶇浼氬脊鍑虹孩鑹查敊璇彁绀?
        return jsonify({"status": "error", "message": result}), 200


@app.route("/api/update_analysis", methods=["POST"])
def api_update_analysis():
    """更新患者的分析结果到 patient_info 表。"""
    data = request.get_json()
    patient_id = data.get("patient_id")

    if not patient_id:
        return jsonify({"status": "error", "message": "缂哄皯 patient_id"}), 400

    # 璋冪敤灏佽濂界殑鍑芥暟
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
                                {"status": "error", "message": f"未找到 ID 为 {patient_id} 的患者信息"}
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
    """Auto trigger stroke analysis API."""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"status": "error", "message": "璇锋眰鏁版嵁涓虹┖"}), 400

        # 鑾峰彇蹇呰鍙傛暟
        case_id = data.get("case_id")
        patient_id = data.get("patient_id")

        if not case_id:
            return jsonify({"status": "error", "message": "缂哄皯蹇呰鍙傛暟: case_id"}), 400

        print(f"鏀跺埌鑷姩鑴戝崚涓垎鏋愯姹?- case_id: {case_id}, patient_id: {patient_id}")

        # 瀵煎叆auto_analyze_stroke鍑芥暟
        try:
            from .stroke_analysis import auto_analyze_stroke
        except ImportError:
            from stroke_analysis import auto_analyze_stroke

        # 鎵ц鑷姩鍒嗘瀽
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
                    "message": analysis_result.get("error", "鍒嗘瀽澶辫触"),
                    "case_id": case_id,
                }
            ), 500

    except Exception as e:
        print(f"鑷姩鑴戝崚涓垎鏋怉PI閿欒: {e}")
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
    """Get patient info."""
    try:
        response = (
            supabase.table("patient_info").select("*").eq("id", patient_id).execute()
        )

        if response.data and len(response.data) > 0:
            return jsonify({"status": "success", "data": response.data[0]})
        else:
            return jsonify(
                                {"status": "error", "message": f"未找到 ID 为 {patient_id} 的患者信息"}
            ), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/get_imaging/<case_id>")
def api_get_imaging(case_id):
    """Get imaging record by case_id."""
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
    """保存结构化临床报告。"""
    data = request.get_json() or {}
    patient_id = data.get("patient_id")
    file_id = data.get("file_id")

    if not patient_id or not file_id:
        return jsonify({"status": "error", "message": "缂哄皯鎮ｈ€匢D鎴栨枃浠禝D"}), 400

    try:
        save_result = save_report_notes(patient_id, file_id, data)
        if not save_result.get("success"):
            return jsonify(
                {
                    "status": "error",
                    "message": save_result.get("error", "鎶ュ憡淇濆瓨澶辫触"),
                    "warnings": save_result.get("warnings", []),
                    "saved_targets": save_result.get("saved_targets", {}),
                }
            ), 500

        return jsonify(
            {
                "status": "success",
                "message": "鎶ュ憡淇濆瓨鎴愬姛",
                "data": save_result.get("data"),
                "warnings": save_result.get("warnings", []),
                "saved_targets": save_result.get("saved_targets", {}),
                "json_sync": save_result.get("json_sync", {}),
            }
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# 绠€鍗曠殑娴嬭瘯璺敱
@app.route("/test")
def test_page():
    """娴嬭瘯璺敱"""
    return "Test page works!"


@app.route("/chat")
def chat_page():
    """娓叉煋AI闂瘖椤甸潰"""
    return render_template("patient/upload/viewer/chat.html")


def _sse_format(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _truncate_text(text: str, max_chars: int = 6000) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[鍐呭杩囬暱锛屽凡鎴柇]"


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
        r"^(?:璇??(?:鍔犺浇|璇诲彇|鏌ヨ|鏌ョ湅|鍒囨崲鍒??\s*(?:鎮ｈ€厊鐥呬汉|patient)\s*(?:id)?\s*[:锛?]?\s*(\d{1,10})\s*$",
        r"^(?:鎮ｈ€厊鐥呬汉|patient)\s*(?:id)?\s*[:锛?]?\s*(\d{1,10})\s*$",
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

    lines = [f"已加载患者 ID {patient_id} 的脱敏病例上下文。", ""]
    lines.append("【患者基本信息（脱敏）】")
    lines.append(f"- 性别：{basic.get('sex', '未提供')}")
    lines.append(f"- 年龄：{basic.get('age', '未提供')}")
    lines.append(f"- 入院 NIHSS：{basic.get('admission_nihss', '未提供')}")
    onset_hours = basic.get("onset_to_admission_hours")
    lines.append(f"- 发病至入院时长：{onset_hours if onset_hours is not None else '未提供'}")
    lines.append("")

    lines.append("【结构化关键字段】")
    lines.append(f"- 病例 file_id：{imaging.get('file_id') or '未提供'}")
    modalities = imaging.get("modalities") or []
    lines.append(f"- 影像模态：{', '.join(modalities) if modalities else '未提供'}")
    lines.append(f"- 病灶偏侧：{imaging.get('hemisphere') or '未提供'}")
    lines.append("")

    lines.append("【CTP 灌注量化信息】")
    core = ctp.get("core_infarct_volume")
    penumbra = ctp.get("penumbra_volume")
    mismatch = ctp.get("mismatch_ratio")
    if core is None and penumbra is None and mismatch is None:
        lines.append("- 暂未找到 CTP 量化结果。")
    else:
        lines.append(f"- 核心梗死体积：{core if core is not None else '未提供'}")
        lines.append(f"- 半暗带体积：{penumbra if penumbra is not None else '未提供'}")
        lines.append(f"- Mismatch 比值：{mismatch if mismatch is not None else '未提供'}")
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
        result["context_summary"] = f"暂未找到患者 ID {patient_id} 对应的患者信息，请确认后重试。"
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
            mismatch = _pick_first_numeric(analysis_result, ["mismatch_ratio", "mismatch"])

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
                    note_text = str(doctor_notes.get("text") or doctor_notes.get("html") or "").strip()
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
        result["missing_flags"].append("未找到对应报告 JSON。")

    ctp_masked = masked.get("ctp_quantification", {})
    if (
        ctp_masked.get("core_infarct_volume") is None
        and ctp_masked.get("penumbra_volume") is None
        and ctp_masked.get("mismatch_ratio") is None
    ):
        result["missing_flags"].append("未找到 CTP 量化字段。")

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
            "\n要求：不得编造缺失字段；缺失时请明确写“未提供/需补充”。"
            f"\n\n[脱敏病例上下文]\n{context_json}"
        )
    else:
        system_content += "\n\n若需要结合具体病例，请先输入患者 ID（如 500）加载脱敏上下文。"

    if parsed_text:
        system_content += f"\n\n以下是用户上传 PDF 的解析内容，请结合回答：\n\n{parsed_text}"

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

        parsed_blocks.append(f"[PDF鏂囦欢: {filename}]\n{_truncate_text(parsed_content)}")

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
    """鍖荤枟AI涓村簥鑱婂ぉ鎺ュ彛 - 娴佸紡鍝嶅簲 (SSE)"""
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
                        f"暂未找到患者 ID {command_patient_id} 的相关内容。",
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
            yield _sse_format({"type": "error", "error": f"API璇锋眰澶辫触: {e}"})
            yield _sse_format({"type": "done"})
            return

        if kb_fallback_used:
            yield _sse_format(
                {
                    "type": "delta",
                    "content": "鎻愮ず锛氬綋鍓嶉棶璇婃ā鍨嬩笉鏀寔鐭ヨ瘑搴撳寮猴紝鏈宸茶嚜鍔ㄥ垏鎹负涓嶅甫鐭ヨ瘑搴撶殑鍥炵瓟妯″紡銆俓n\n",
                }
            )

        if response.status_code != 200:
            error_text = response.text[:2000]
            yield _sse_format(
                {"type": "error", "error": f"API璋冪敤澶辫触: {response.status_code}"}
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
    """鍖荤枟AI涓村簥鑱婂ぉ鎺ュ彛"""
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
                            f"暂未找到患者 ID {command_patient_id} 的相关内容。",
                        ),
                    },
                    "context_loaded": bool(context_result.get("found")),
                    "context_patient_id": command_patient_id,
                    "context_file_id": context_result.get("file_id"),
                }
            )

        # 璋冪敤鐧惧窛API杩涜涓村簥闂瓟
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
                {"success": False, "error": f"API璋冪敤澶辫触: {response.status_code}"}
            ), 500

    except Exception as e:
        print(f"鑱婂ぉ閿欒: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/kb/docs", methods=["GET"])
def api_kb_docs():
    """杩斿洖鐭ヨ瘑搴揚DF鍒楄〃"""
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
    """鎻愪緵鐭ヨ瘑搴揚DF鏂囦欢"""
    if not filename.lower().endswith(".pdf"):
        return jsonify({"error": "鍙厑璁窹DF鏂囦欢"}), 400
    if not os.path.isdir(KB_PDF_DIR):
        return jsonify({"error": "PDF目录不存在"}), 404
    return send_from_directory(KB_PDF_DIR, filename, mimetype="application/pdf")


@app.route("/report/<int:patient_id>")
def report_page(patient_id):
    """娓叉煋鎶ュ憡椤甸潰
    
    鐢熶骇鐜锛氱洿鎺ヨ繑鍥?Vite 鏋勫缓鐨?index.html锛堝凡鍖呭惈姝ｇ‘鐨?/static/dist/ 鍓嶇紑锛?
    寮€鍙戠幆澧冿細鎻愮ず寮€鍚?Vite 寮€鍙戞湇鍔″櫒鎴栧厛鏋勫缓鍓嶇
    """
    dist_index = os.path.join(app.static_folder, "dist", "index.html")
    
    if os.path.exists(dist_index):
        # 鉁?鐩存帴杩斿洖鏋勫缓濂界殑鏂囦欢锛屾棤闇€姝ｅ垯鏇挎崲锛圴ite 宸查厤缃?base 璺緞锛?
        return send_from_directory(os.path.join(app.static_folder, "dist"), "index.html")
    else:
        # 鈿狅笍 寮€鍙戠幆澧冩彁绀?
        return jsonify({
            "error": "前端应用未构建",
            "solution": [
                "方案1（推荐）：cd frontend && npm run build",
                "方案2（开发）：cd frontend && npm run dev，然后访问 http://localhost:5173"
            ]
        }), 404


@app.route("/assets/<path:filename>")
def serve_vite_assets(filename):
    """涓?Vite 鏋勫缓鐨勫墠绔簲鐢ㄦ彁渚涢潤鎬佽祫婧愶紙JS/CSS 绛夛級"""
    dist_assets = os.path.join(app.static_folder, "dist", "assets")
    return send_from_directory(dist_assets, filename)


# ==================== 鍥惧儚瀵规瘮搴﹁皟鑺侫PI ====================


@app.route("/adjust_contrast/<file_id>/<int:slice_index>/<image_type>")
def adjust_contrast(file_id, slice_index, image_type):
    """
    璋冭妭鍥惧儚瀵规瘮搴︼紙绐楀绐椾綅锛?

    鍙傛暟:
    - file_id: 鏂囦欢ID
    - slice_index: 鍒囩墖绱㈠紩
    - image_type: 鍥惧儚绫诲瀷 (mcta, ncct)
    - window_width: 绐楀 (鏌ヨ鍙傛暟)
    - window_level: 绐椾綅 (鏌ヨ鍙傛暟)
    """
    try:
        # 鑾峰彇绐楀绐椾綅鍙傛暟
        window_width = float(request.args.get("ww", 80))
        window_level = float(request.args.get("wl", 40))

        # 楠岃瘉鍥惧儚绫诲瀷
        if image_type not in ["mcta", "ncct"]:
            return jsonify({"error": "无效的图像类型"}), 400

        # 鏋勫缓鍘熷鍥惧儚璺緞
        slice_prefix = f"slice_{slice_index:03d}"
        original_path = os.path.join(
            app.config["PROCESSED_FOLDER"], file_id, f"{slice_prefix}_{image_type}.png"
        )

        if not os.path.exists(original_path):
            return jsonify({"error": "原始图像不存在"}), 404

        # 鍔犺浇鍘熷鍥惧儚
        original_img = Image.open(original_path).convert("L")
        img_array = np.array(original_img, dtype=np.float32)

        # 搴旂敤绐楀绐椾綅璋冭妭
        adjusted_array = apply_window_level(img_array, window_width, window_level)

        # 杞崲涓篜IL鍥惧儚
        adjusted_img = Image.fromarray(adjusted_array.astype(np.uint8))

        # 杩斿洖璋冭妭鍚庣殑鍥惧儚
        from io import BytesIO

        img_buffer = BytesIO()
        adjusted_img.save(img_buffer, format="PNG")
        img_buffer.seek(0)

        return send_file(img_buffer, mimetype="image/png")

    except Exception as e:
        print(f"瀵规瘮搴﹁皟鑺傞敊璇? {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


def apply_window_level(img_array, window_width, window_level):
    """
    搴旂敤绐楀绐椾綅璋冭妭

    鍙傛暟:
    - img_array: 杈撳叆鍥惧儚鏁扮粍 (0-255)
    - window_width: 绐楀
    - window_level: 绐椾綅锛堢獥涓績锛?

    杩斿洖:
    - 璋冭妭鍚庣殑鍥惧儚鏁扮粍 (0-255)
    """
    # 璁＄畻绐楀彛鑼冨洿
    window_min = window_level - window_width / 2
    window_max = window_level + window_width / 2

    # 搴旂敤绐楀绐椾綅鍙樻崲
    # 灏嗗浘鍍忓€兼槧灏勫埌绐楀彛鑼冨洿鍐?
    adjusted = np.clip(img_array, window_min, window_max)

    # 褰掍竴鍖栧埌0-255
    if window_max > window_min:
        adjusted = ((adjusted - window_min) / (window_max - window_min)) * 255
    else:
        adjusted = np.zeros_like(img_array)

    return adjusted


@app.route("/get_image_histogram/<file_id>/<int:slice_index>/<image_type>")
def get_image_histogram(file_id, slice_index, image_type):
    """
    鑾峰彇鍥惧儚鐩存柟鍥炬暟鎹?

    鍙傛暟:
    - file_id: 鏂囦欢ID
    - slice_index: 鍒囩墖绱㈠紩
    - image_type: 鍥惧儚绫诲瀷 (mcta, ncct)
    """
    try:
        # 楠岃瘉鍥惧儚绫诲瀷
        if image_type not in ["mcta", "ncct"]:
            return jsonify({"error": "无效的图像类型"}), 400

        # 鏋勫缓鍥惧儚璺緞
        slice_prefix = f"slice_{slice_index:03d}"
        image_path = os.path.join(
            app.config["PROCESSED_FOLDER"], file_id, f"{slice_prefix}_{image_type}.png"
        )

        if not os.path.exists(image_path):
            return jsonify({"error": "图像不存在"}), 404

        # 鍔犺浇鍥惧儚
        img = Image.open(image_path).convert("L")
        img_array = np.array(img)

        # 璁＄畻鐩存柟鍥?
        histogram, bin_edges = np.histogram(
            img_array.flatten(), bins=256, range=(0, 256)
        )

        # 璁＄畻缁熻淇℃伅
        non_zero_mask = img_array > 5  # 蹇界暐鑳屾櫙
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
        print(f"鑾峰彇鐩存柟鍥鹃敊璇? {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/save_contrast_settings/<file_id>", methods=["POST"])
def save_contrast_settings(file_id):
    """
    淇濆瓨瀵规瘮搴﹁缃?

    璇锋眰浣?
    {
        "cta": {"windowWidth": 80, "windowLevel": 40},
        "ncct": {"windowWidth": 80, "windowLevel": 40}
    }
    """
    try:
        settings = request.get_json()

        if not settings:
            return jsonify({"error": "无效的设置数据"}), 400

        # 淇濆瓨璁剧疆鍒版枃浠?
        settings_path = os.path.join(
            app.config["PROCESSED_FOLDER"], file_id, "contrast_settings.json"
        )

        import json

        with open(settings_path, "w") as f:
            json.dump(settings, f, indent=2, cls=NumpyJSONEncoder)

        return jsonify({"success": True, "message": "瀵规瘮搴﹁缃凡淇濆瓨"})

    except Exception as e:
        print(f"淇濆瓨瀵规瘮搴﹁缃敊璇? {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/load_contrast_settings/<file_id>")
def load_contrast_settings(file_id):
    """
    鍔犺浇瀵规瘮搴﹁缃?
    """
    try:
        settings_path = os.path.join(
            app.config["PROCESSED_FOLDER"], file_id, "contrast_settings.json"
        )

        if not os.path.exists(settings_path):
            # 杩斿洖榛樿璁剧疆
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
        print(f"鍔犺浇瀵规瘮搴﹁缃敊璇? {e}")
        return jsonify({"error": str(e)}), 500


# ==================== 鍏朵綑鍑芥暟淇濇寔涓嶅彉 ====================


def create_brain_mask(image, low_thresh=0.05, high_thresh=0.95):
    """
    鏀硅繘鐨勮剳閮ㄦ帺鐮佺敓鎴愮畻娉曪紝鎻愰珮璇嗗埆瀹屾暣鎬?
    """
    try:
        from skimage import morphology, measure, filters

        # 鎻愬彇鎵€鏈夐€氶亾涓己搴︽渶楂樼殑閫氶亾
        max_channel = np.argmax(np.max(image, axis=(0, 1)))
        channel_img = image[:, :, max_channel]

        print(
            f"閫氶亾 {max_channel} 鏁版嵁鑼冨洿: [{channel_img.min():.3f}, {channel_img.max():.3f}]"
        )

        # 1. 浣跨敤鏇村鏉剧殑闃堝€艰寖鍥?
        # 鍏堣繘琛岄珮鏂护娉㈠噺灏戝櫔澹帮紝浣嗕繚鐣欐洿澶氱粏鑺?
        smoothed = filters.gaussian(channel_img, sigma=0.5)

        # 璁＄畻鑷€傚簲闃堝€?
        data_min = smoothed.min()
        data_max = smoothed.max()
        data_range = data_max - data_min

        # 鑷€傚簲闃堝€艰绠?
        adaptive_low = data_min + data_range * low_thresh
        adaptive_high = data_min + data_range * high_thresh

        print(f"鑷€傚簲闃堝€? [{adaptive_low:.3f}, {adaptive_high:.3f}]")

        # 鍒濆闃堝€煎垎鍓?- 浣跨敤鏇村鏉剧殑鑼冨洿
        initial_mask = np.logical_and(
            smoothed > adaptive_low, smoothed < adaptive_high
        ).astype(np.uint8)

        print(f"鍒濆鎺╃爜涓€间负1鐨勫儚绱犳暟閲? {np.sum(initial_mask)}")

        # 2. 鏀硅繘鐨勮繛閫氬尯鍩熷垎鏋?
        labeled_mask = measure.label(initial_mask)
        regions = measure.regionprops(labeled_mask)

        if not regions:
            print("未找到任何区域")
            return np.zeros_like(channel_img)

        # 鎸夐潰绉帓搴忥紝淇濈暀鏇村鍖哄煙
        regions_sorted = sorted(regions, key=lambda r: r.area, reverse=True)

        print(f"找到 {len(regions_sorted)} 个连通区域")
        print("前5个区域面积:", [r.area for r in regions_sorted[:5]])

        # 鍒涘缓鍖呭惈澶氫釜澶у尯鍩熺殑鎺╃爜
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

        print(f"鏈€缁堟帺鐮佷腑鍊间负1鐨勫儚绱犳暟閲? {np.sum(brain_mask)}")

        # 3. 鏇存俯鍜岀殑褰㈡€佸鎿嶄綔
        small_disk = morphology.disk(1)

        # 鍏堥棴杩愮畻濉厖灏忓瓟娲?
        closed_mask = morphology.binary_closing(brain_mask, small_disk)

        # 鐒跺悗寮€杩愮畻鍘婚櫎灏忓櫔鐐?
        opened_mask = morphology.binary_opening(closed_mask, small_disk)

        # 濉厖鍓╀綑瀛旀礊
        filled_mask = morphology.remove_small_holes(opened_mask, area_threshold=100)

        # 鍘婚櫎澶皬鐨勫绔嬪尯鍩?
        final_mask = morphology.remove_small_objects(filled_mask, min_size=50)

        # 杞诲井鑶ㄨ儉浠ヨ繛鎺ラ偦杩戝尯鍩?
        dilated_mask = morphology.binary_dilation(final_mask, small_disk)

        # 鏈€缁堝钩婊?
        smoothed_mask = morphology.binary_closing(dilated_mask, small_disk)

        final_pixel_count = np.sum(smoothed_mask)
        print(f"澶勭悊鍚庢帺鐮佸儚绱犳暟閲? {final_pixel_count}")
        print(
            f"鎺╃爜瑕嗙洊鐜? {final_pixel_count / (channel_img.shape[0] * channel_img.shape[1]) * 100:.1f}%"
        )

        return smoothed_mask.astype(np.float32)

    except ImportError:
        print("skimage 不可用，使用简化版本")
        return create_brain_mask_numpy(image, low_thresh, high_thresh)


def create_brain_mask_numpy(image, low_thresh=0.05, high_thresh=0.95):
    """
    浣跨敤绾?NumPy 瀹炵幇鐨勬敼杩涜剳閮ㄦ帺鐮佺敓鎴?
    """
    try:
        from scipy import ndimage

        # 鎻愬彇鎵€鏈夐€氶亾涓己搴︽渶楂樼殑閫氶亾
        max_channel = np.argmax(np.max(image, axis=(0, 1)))
        channel_img = image[:, :, max_channel]

        # 楂樻柉婊ゆ尝
        smoothed = ndimage.gaussian_filter(channel_img, sigma=0.5)

        # 鑷€傚簲闃堝€?
        data_min = smoothed.min()
        data_max = smoothed.max()
        data_range = data_max - data_min

        adaptive_low = data_min + data_range * low_thresh
        adaptive_high = data_min + data_range * high_thresh

        # 闃堝€煎垎鍓?
        initial_mask = np.logical_and(
            smoothed > adaptive_low, smoothed < adaptive_high
        ).astype(np.uint8)

        # 杩為€氱粍浠跺垎鏋?
        labeled_mask, num_features = ndimage.label(initial_mask)

        if num_features == 0:
            return np.zeros_like(channel_img)

        # 璁＄畻姣忎釜缁勪欢鐨勯潰绉?
        sizes = ndimage.sum(initial_mask, labeled_mask, range(1, num_features + 1))

        # 鍒涘缓鎺╃爜锛屼繚鐣欓潰绉冻澶熷ぇ鐨勭粍浠?
        brain_mask = np.zeros_like(channel_img)
        min_size = max(50, channel_img.shape[0] * channel_img.shape[1] * 0.001)

        for i in range(num_features):
            if sizes[i] >= min_size:
                brain_mask[labeled_mask == i + 1] = 1

        # 褰㈡€佸鎿嶄綔
        structure = np.ones((2, 2))

        # 闂繍绠楀～鍏呭瓟娲?
        closed_mask = ndimage.binary_closing(brain_mask, structure=structure)

        # 寮€杩愮畻鍘婚櫎鍣０
        opened_mask = ndimage.binary_opening(closed_mask, structure=structure)

        # 濉厖鍓╀綑瀛旀礊
        filled_mask = ndimage.binary_fill_holes(opened_mask)

        # 鏈€缁堥棴杩愮畻骞虫粦杈圭晫
        final_mask = ndimage.binary_closing(filled_mask, structure=structure)

        return final_mask.astype(np.float32)

    except ImportError:
        # 鏈€绠€鐗堟湰 - 鐩存帴闃堝€?
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
    浣跨敤鑷€傚簲闃堝€兼柟娉曠殑鑴戦儴鎺╃爜鐢熸垚
    """
    try:
        from skimage import filters, morphology, measure

        max_channel = np.argmax(np.max(image, axis=(0, 1)))
        channel_img = image[:, :, max_channel]

        # 浣跨敤Otsu鏂规硶鑷姩璁＄畻闃堝€?
        try:
            otsu_threshold = filters.threshold_otsu(channel_img)
            # 鍩轰簬Otsu闃堝€艰缃寖鍥?
            low_thresh = otsu_threshold * 0.3
            high_thresh = otsu_threshold * 2.0
        except:
            # 濡傛灉Otsu澶辫触锛屼娇鐢ㄧ櫨鍒嗘瘮
            low_thresh = np.percentile(channel_img, 10)
            high_thresh = np.percentile(channel_img, 90)

        print(f"鑷€傚簲闃堝€? [{low_thresh:.3f}, {high_thresh:.3f}]")

        initial_mask = np.logical_and(
            channel_img > low_thresh, channel_img < high_thresh
        ).astype(np.uint8)

        # 鍚庣画澶勭悊
        labeled_mask = measure.label(initial_mask)
        regions = measure.regionprops(labeled_mask)

        if not regions:
            return np.zeros_like(channel_img)

        regions_sorted = sorted(regions, key=lambda r: r.area, reverse=True)
        brain_mask = np.zeros_like(channel_img, dtype=np.uint8)

        for i, region in enumerate(regions_sorted[:3]):
            if region.area > 100:
                brain_mask[labeled_mask == region.label] = 1

        # 娓╁拰鐨勫舰鎬佸鎿嶄綔
        small_disk = morphology.disk(1)
        cleaned_mask = morphology.binary_opening(brain_mask, small_disk)
        filled_mask = morphology.remove_small_holes(cleaned_mask, area_threshold=50)
        final_mask = morphology.binary_closing(filled_mask, small_disk)

        return final_mask.astype(np.float32)

    except Exception as e:
        print(f"鑷€傚簲鏂规硶澶辫触: {e}")
        return create_brain_mask(image)


def create_otsu_brain_mask(image):
    """
    浣跨敤Otsu闃堝€兼柟娉曠殑鑴戦儴鎺╃爜鐢熸垚
    """
    try:
        from skimage import filters, morphology, measure

        max_channel = np.argmax(np.max(image, axis=(0, 1)))
        channel_img = image[:, :, max_channel]

        # Otsu鑷姩闃堝€?
        otsu_threshold = filters.threshold_otsu(channel_img)
        initial_mask = channel_img > otsu_threshold

        # 褰㈡€佸鎿嶄綔
        small_disk = morphology.disk(1)
        cleaned_mask = morphology.binary_opening(initial_mask, small_disk)
        filled_mask = morphology.remove_small_holes(cleaned_mask, area_threshold=100)
        final_mask = morphology.binary_closing(filled_mask, small_disk)

        return final_mask.astype(np.float32)

    except Exception as e:
        print(f"Otsu鏂规硶澶辫触: {e}")
        return create_brain_mask(image)


def create_overlay_image(rgb_data, mask, output_dir, slice_idx):
    """
    鍒涘缓鍘熷鍥惧儚涓庢帺鐮佺殑鍙犲姞鍥惧儚
    """
    try:
        # 鎻愬彇寮哄害鏈€楂樼殑閫氶亾浣滀负鐏板害鑳屾櫙
        max_channel = np.argmax(np.max(rgb_data, axis=(0, 1)))
        background = rgb_data[:, :, max_channel]

        # 褰掍竴鍖栬儗鏅?
        background_normalized = (background - background.min()) / (
            background.max() - background.min()
        )
        background_8bit = (background_normalized * 255).astype(np.uint8)

        # 鍒涘缓RGB鍙犲姞鍥惧儚
        overlay = np.stack([background_8bit] * 3, axis=2)

        # 鍦ㄦ帺鐮佸尯鍩熸坊鍔犵孩鑹插彔鍔?
        mask_indices = mask > 0.5
        overlay[mask_indices, 0] = 255
        overlay[mask_indices, 1] = np.minimum(overlay[mask_indices, 1], 150)
        overlay[mask_indices, 2] = np.minimum(overlay[mask_indices, 2], 150)

        # 淇濆瓨鍙犲姞鍥惧儚
        overlay_path = os.path.join(output_dir, f"slice_{slice_idx:03d}_overlay.png")
        Image.fromarray(overlay).save(overlay_path)

        return f"/get_image/{os.path.basename(output_dir)}/slice_{slice_idx:03d}_overlay.png"

    except Exception as e:
        print(f"鍒涘缓鍙犲姞鍥惧儚澶辫触: {e}")
        return ""


def generate_mask_for_slice(rgb_data, output_dir, slice_idx):
    """
    涓哄崟涓垏鐗囩敓鎴愭帺鐮侊紝灏濊瘯澶氱鏂规硶 - 淇鐗堟湰
    """
    try:
        print(f"涓哄垏鐗?{slice_idx} 鐢熸垚鎺╃爜...")

        # 灏濊瘯澶氱鏂规硶锛岄€夋嫨鏈€濂界殑涓€涓?
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
                print(f"鏂规硶 {method} 瑕嗙洊鐜? {coverage:.3f}")

                if coverage > best_coverage and coverage > 0.02 and coverage < 0.98:
                    best_mask = mask
                    best_coverage = coverage
                    best_method = method

            except Exception as e:
                print(f"鏂规硶 {method} 澶辫触: {e}")
                continue

        if best_mask is None:
            print("所有方法都失败，使用默认方法")
            best_mask = create_brain_mask(rgb_data, low_thresh=0.00, high_thresh=0.99)
            best_method = "default"
            best_coverage = np.sum(best_mask) / (
                best_mask.shape[0] * best_mask.shape[1]
            )

        print(f"閫夋嫨鏂规硶: {best_method}, 鏈€缁堣鐩栫巼: {best_coverage:.3f}")

        # 淇濆瓨鎺╃爜涓篜NG鍥惧儚
        mask_8bit = (best_mask * 255).astype(np.uint8)
        mask_path = os.path.join(output_dir, f"slice_{slice_idx:03d}_mask.png")
        Image.fromarray(mask_8bit).save(mask_path)

        # 淇濆瓨鎺╃爜涓篘PY鏂囦欢
        mask_npy_path = os.path.join(output_dir, f"slice_{slice_idx:03d}_mask.npy")
        np.save(mask_npy_path, best_mask)

        # 鐢熸垚鍙犲姞鍥惧儚
        overlay_url = create_overlay_image(rgb_data, best_mask, output_dir, slice_idx)

        return {
            "success": True,
            "mask_url": f"/get_image/{os.path.basename(output_dir)}/slice_{slice_idx:03d}_mask.png",
            "mask_npy_url": f"/get_file/{os.path.basename(output_dir)}/slice_{slice_idx:03d}_mask.npy",
            "overlay_url": overlay_url,
            "coverage": float(best_coverage),
            "method": best_method,
            "mask_data": best_mask,  # 鍏抽敭锛氱‘淇濊繑鍥炴帺鐮佹暟鎹?
        }

    except Exception as e:
        print(f"鐢熸垚鎺╃爜澶辫触: {e}")
        # 杩斿洖涓€涓┖鐨勬帺鐮侊紝浣嗙‘淇濆寘鍚玬ask_data
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
            "mask_data": empty_mask,  # 鍏抽敭锛氬嵆浣垮け璐ヤ篃杩斿洖鎺╃爜鏁版嵁
        }


def process_ai_inference(
    rgb_result,
    mask_result,
    output_dir,
    slice_idx,
    model_key="mrdpm",
    model_type="mrdpm",
):
    """Run AI inference for one slice and save outputs."""
    try:
        rgb_data = rgb_result.get("rgb_data")
        if rgb_data is None:
            print("RGB 数据不可用")
            return {"success": False, "error": "RGB数据不可用", "ai_url": "", "ai_npy_url": ""}

        mask_data = mask_result.get("mask_data")
        if mask_data is None:
            mask_npy_path = os.path.join(output_dir, f"slice_{slice_idx:03d}_mask.npy")
            if os.path.exists(mask_npy_path):
                try:
                    mask_data = np.load(mask_npy_path)
                except Exception:
                    mask_data = None
        if mask_data is None:
            mask_data = np.zeros_like(rgb_data[:, :, 0])

        if model_type == "mrdpm":
            try:
                from .ai_inference import MRDPMModel
            except ImportError:
                from ai_inference import MRDPMModel
            import torch

            submodel = model_key if model_key in MODEL_CONFIGS else "cbf"
            bran_pretrained_path = os.path.join(
                PROJECT_ROOT,
                "mrdpm",
                "weights",
                submodel,
                "bran_pretrained_3channel.pth",
            )
            residual_weight_path = os.path.join(
                PROJECT_ROOT,
                "mrdpm",
                "weights",
                submodel,
                "200_Network_ema.pth",
            )

            if not os.path.exists(bran_pretrained_path) or not os.path.exists(residual_weight_path):
                return {
                    "success": False,
                    "error": f"MRDPM 权重文件缺失: {submodel}",
                    "ai_url": "",
                    "ai_npy_url": "",
                }

            mrdpm_model = MRDPMModel(
                bran_pretrained_path,
                residual_weight_path,
                device="cuda" if torch.cuda.is_available() else "cpu",
            )
            save_path = os.path.join(output_dir, f"slice_{slice_idx:03d}_{model_key}_initial.png")
            ai_output = mrdpm_model.inference(rgb_data, mask_data, save_path)
        else:
            ai_model = get_ai_model(model_key)
            if ai_model is None:
                return {
                    "success": False,
                    "error": f"{model_key} 模型未初始化",
                    "ai_url": "",
                    "ai_npy_url": "",
                }
            ai_output = ai_model.inference(rgb_data, mask_data)

        if ai_output is None or np.size(ai_output) == 0:
            return {
                "success": False,
                "error": f"{model_key} 推理结果为空",
                "ai_url": "",
                "ai_npy_url": "",
            }

        slice_prefix = f"slice_{slice_idx:03d}"
        ai_npy_path = os.path.join(output_dir, f"{slice_prefix}_{model_key}_output.npy")
        np.save(ai_npy_path, ai_output)

        png_path = ai_npy_path.replace(".npy", ".png")
        result_8bit = (np.clip(ai_output, 0, 1) * 255).astype(np.uint8)
        Image.fromarray(result_8bit).save(png_path)

        file_id = os.path.basename(output_dir)
        ai_image_url = f"/get_image/{file_id}/{slice_prefix}_{model_key}_output.png"
        ai_npy_url = f"/get_file/{file_id}/{slice_prefix}_{model_key}_output.npy"
        return {"success": True, "ai_url": ai_image_url, "ai_npy_url": ai_npy_url}
    except Exception as e:
        print(f"{model_key} 推理处理失败: {e}")
        traceback.print_exc()
        return {"success": False, "error": str(e), "ai_url": "", "ai_npy_url": ""}
def process_rgb_synthesis(
    mcta_path, vcta_path, dcta_path, ncct_path, output_dir, model_type="mrdpm"
):
    """处理 RGB 合成，支持多模型 AI 推理。"""
    try:
        if not NIBABEL_AVAILABLE:
            return {
                "success": False,
                "error": 'nibabel 搴撲笉鍙敤锛岃瀹夎: pip install "numpy<2.0" nibabel',
            }

        # NCCT 蹇呴€?
        ncct_img = nib.load(ncct_path)
        ncct_data = ncct_img.get_fdata()
        print(f"NCCT 缁村害: {ncct_data.shape}")

        def load_optional_nifti(file_path, label):
            if not file_path:
                print(f"{label} 未提供，使用空数据")
                return None, None
            img = nib.load(file_path)
            data = img.get_fdata()
            print(f"{label} 缁村害: {data.shape}")
            return img, data

        mcta_img, mcta_data = load_optional_nifti(mcta_path, "鍔ㄨ剦鏈烠TA")
        vcta_img, vcta_data = load_optional_nifti(vcta_path, "闈欒剦鏈烠TA")
        dcta_img, dcta_data = load_optional_nifti(dcta_path, "寤惰繜鏈烠TA")

        # 妫€鏌ュ凡鎻愪緵鏂囦欢缁村害鏄惁涓€鑷达紙浠?NCCT 涓哄熀鍑嗭級
        for label, data in [
            ("鍔ㄨ剦鏈烠TA", mcta_data),
            ("闈欒剦鏈烠TA", vcta_data),
            ("寤惰繜鏈烠TA", dcta_data),
        ]:
            if data is not None and data.shape != ncct_data.shape:
                return {
                    "success": False,
                    "error": f"{label} 维度 {data.shape} 与 NCCT 维度 {ncct_data.shape} 不匹配",
                }

        # 瀵圭己澶辩殑鏈熺浉浣跨敤闆剁煩闃靛崰浣嶏紝纭繚娴佺▼涓€鑷?
        mcta_data = mcta_data if mcta_data is not None else np.zeros_like(ncct_data)
        vcta_data = vcta_data if vcta_data is not None else np.zeros_like(ncct_data)
        dcta_data = dcta_data if dcta_data is not None else np.zeros_like(ncct_data)

        # 鑾峰彇鍩烘湰淇℃伅
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

        # 澶勭悊姣忎釜鍒囩墖
        rgb_files = []
        num_slices = mcta_data.shape[2] if len(mcta_data.shape) >= 3 else 1

        # 妫€鏌I妯″瀷鍙敤鎬?
        available_models = get_available_models()
        # MRDPM 鎺ㄧ悊鍙渶瑕?CBF/CBV/TMAX 涓夌被瀛愭ā鍨嬶紝杩囨护鎺夊崰浣嶇殑 mrdpm 鏍囪瘑
        if model_type == "mrdpm":
            available_models = [key for key in available_models if key in MODEL_CONFIGS]
        models_available = len(available_models) > 0

        print(f"AI妯″瀷鍙敤鎬? {models_available}")
        print(f"鍙敤妯″瀷: {available_models}")

        # 璁板綍姣忎釜妯″瀷鐨勬垚鍔熸帹鐞嗘暟閲?
        model_success_counts = {model_key: 0 for model_key in MODEL_CONFIGS.keys()}
        has_any_model_success = False

        for slice_idx in range(num_slices):
            print(f"\n=== 澶勭悊鍒囩墖 {slice_idx + 1}/{num_slices} ===")

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

            # 鐢熸垚RGB鍚堟垚鍥惧儚鍜孨PY鏁版嵁
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
                print(f"切片 {slice_idx} RGB 合成失败，跳过")
                continue

            # 鐢熸垚鎺╃爜
            mask_result = generate_mask_for_slice(
                rgb_result["rgb_data"], output_dir, slice_idx
            )

            # 纭繚mask_result鍖呭惈mask_data
            if "mask_data" not in mask_result:
                print(f"切片 {slice_idx} 掩码生成失败，使用空掩码")
                mask_result["mask_data"] = np.zeros_like(
                    rgb_result["rgb_data"][:, :, 0]
                )

            # 鍒濆鍖栧垏鐗囩粨鏋?
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

            # 涓烘瘡涓ā鍨嬪垵濮嬪寲AI缁撴灉
            for model_key in MODEL_CONFIGS.keys():
                slice_result.update(
                    {
                        f"has_{model_key}": False,
                        f"{model_key}_image": "",
                        f"{model_key}_npy_url": "",
                    }
                )

            # 瀵规瘡涓彲鐢ㄦā鍨嬭繘琛屾帹鐞?
            slice_has_any_ai = False

            for model_key in available_models:
                try:
                    # 鏍规嵁鍙傛暟绫诲瀷閫夋嫨鍚堥€傜殑妯″瀷绫诲瀷
                    # CBF鍜孋BV鍙傛暟濮嬬粓浣跨敤palette妯″瀷
                    # TMAX鍙傛暟浣跨敤鐢ㄦ埛閫夋嫨鐨勬ā鍨?
                    if model_key in ["cbf", "cbv"]:
                        current_model_type = "palette"
                    elif model_key == "tmax":
                        current_model_type = model_type
                    else:
                        current_model_type = model_type

                    print(
                        f"开始 {model_key.upper()} 模型推理切片 {slice_idx}（使用 {current_model_type}）"
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
                        print(f"鉁?{model_key.upper()}妯″瀷鎺ㄧ悊瀹屾垚鍒囩墖 {slice_idx}")
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
                            ai_result.get("error", "鏈煡閿欒")
                            if ai_result
                            else "无结果"
                        )
                        print(
                            f"鈿?{model_key.upper()}妯″瀷鎺ㄧ悊澶辫触鍒囩墖 {slice_idx}: {error_msg}"
                        )
                except Exception as e:
                    print(f"鉁?{model_key.upper()}妯″瀷鎺ㄧ悊寮傚父鍒囩墖 {slice_idx}: {e}")

            # 娣诲姞鎬讳綋AI鐘舵€?
            slice_result["has_ai"] = slice_has_any_ai
            rgb_files.append(slice_result)

        # 缁熻淇℃伅
        print(f"\n=== AI妯″瀷澶勭悊缁熻 ===")
        print(f"鎬诲垏鐗囨暟: {len(rgb_files)}")
        for model_key, count in model_success_counts.items():
            status = "可用" if model_key in available_models else "不可用"
            print(f"{model_key.upper()} 模型: {count} 个切片成功 ({status})")

        # 鍦ㄥ厓鏁版嵁涓坊鍔犳ā鍨嬬姸鎬佷俊鎭?
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

        # 娣诲姞姣忎釜妯″瀷鐨勮缁嗕俊鎭?
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

        # 鏋勫缓鏈€缁堣繑鍥炵粨鏋?
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

        print(f"\n=== 杩斿洖缁欏墠绔殑鏁版嵁缁撴瀯 ===")
        print(f"椤跺眰has_ai: {result['has_ai']}")
        print(f"鍙敤妯″瀷: {result['available_models']}")
        print(f"妯″瀷閰嶇疆: {list(result['model_configs'].keys())}")
        print("============================\n")

        return result

    except Exception as e:
        print(f"澶勭悊RGB鍚堟垚澶辫触: {e}")
        traceback.print_exc()
        return {"success": False, "error": str(e)}


# 鍦ㄥ簲鐢ㄥ惎鍔ㄦ椂鍒濆鍖?
def initialize_app():
    """应用初始化函数 - 多模型版本。"""
    print("=" * 50)
    print("医学图像处理Web系统初始化 - 医学标准伪彩图版本")
    print("=" * 50)

    # 鍒涘缓蹇呰鐨勭洰褰?
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["PROCESSED_FOLDER"], exist_ok=True)

    print(f"涓婁紶鐩綍: {app.config['UPLOAD_FOLDER']}")
    print(f"澶勭悊鐩綍: {app.config['PROCESSED_FOLDER']}")

    # 鍒濆鍖朅I妯″瀷
    ai_initialized = init_ai_models()

    # 璁剧疆鍏ㄥ眬鏍囧織
    app.config["AI_AVAILABLE"] = ai_initialized
    app.config["AI_MODELS"] = ai_models
    app.config["MODEL_CONFIGS"] = MODEL_CONFIGS

    print(f"AI鍔熻兘鍙敤: {ai_initialized}")
    print("✓ 应用初始化完成")
    print("=" * 50)


def ensure_app_initialized():
    """Ensure heavy startup initialization runs only once per process."""
    if getattr(app, "has_initialized", False):
        return
    initialize_app()
    app.has_initialized = True


# 浣跨敤搴旂敤涓婁笅鏂囪繘琛屽垵濮嬪寲
with app.app_context():
    ensure_app_initialized()


# 娣诲姞鍚姩鏃跺垵濮嬪寲
@app.before_request
def before_first_request():
    """替代 before_first_request 的初始化方案。"""
    ensure_app_initialized()


# 淇敼涓嬭浇璺敱浠ユ敮鎸佸妯″瀷
@app.route("/download_ai/<model_key>/<file_id>/<int:slice_index>")
def download_ai(model_key, file_id, slice_index):
    """涓嬭浇鐗瑰畾妯″瀷鐨凙I鎺ㄧ悊缁撴灉NPY鏂囦欢"""
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


# 鍏朵綑鍑芥暟淇濇寔涓嶅彉...
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
    鐢熸垚RGB鍚堟垚鍥惧儚鍜屽崟鐙€氶亾鍥惧儚
    """
    try:
        # 1. 褰掍竴鍖栧鐞?
        mcta_normalized = normalize_slice(mcta_slice)
        vcta_normalized = normalize_slice(vcta_slice)
        dcta_normalized = normalize_slice(dcta_slice)
        ncct_normalized = normalize_slice(ncct_slice)

        # 2. 鍒涘缓RGB鍥惧儚 [R, G, B] = [mCTA1, NCCT, 绌篯
        rgb_data = np.stack(
            [mcta_normalized, ncct_normalized, np.zeros_like(mcta_normalized)], axis=2
        )
        rgb_8bit = (rgb_data * 255).astype(np.uint8)

        # 3. 鍒涘缓鍗曠嫭閫氶亾鐨勫浘鍍忥紙鐢ㄤ簬鏄剧ず锛?
        mcta_8bit = (mcta_normalized * 255).astype(np.uint8)
        vcta_8bit = (vcta_normalized * 255).astype(np.uint8)
        dcta_8bit = (dcta_normalized * 255).astype(np.uint8)
        ncct_8bit = (ncct_normalized * 255).astype(np.uint8)

        # 鍒涘缓杈撳嚭璺緞
        slice_prefix = f"slice_{slice_idx:03d}"

        # 淇濆瓨RGB鍚堟垚鍥惧儚
        rgb_path = os.path.join(output_dir, f"{slice_prefix}_rgb.png")
        Image.fromarray(rgb_8bit).save(rgb_path)

        # 淇濆瓨鍗曠嫭閫氶亾鍥惧儚锛屼粎褰撳搴旀ā鎬佷负鐪熷疄涓婁紶锛堥潪闆剁煩闃靛崰浣嶏級鏃舵墠淇濆瓨璇ラ€氶亾鏂囦欢
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

        # NCCT 鎬绘槸淇濆瓨
        Image.fromarray(ncct_8bit).save(ncct_path)

        # 淇濆瓨NPY鏁版嵁 - 鐩存帴淇濆瓨RGB鏁扮粍锛岃€屼笉鏄瓧鍏?
        npy_path = os.path.join(output_dir, f"{slice_prefix}_data.npy")
        np.save(npy_path, rgb_data.astype(np.float32))  # 鐩存帴淇濆瓨鏁扮粍

        # 鑾峰彇杈撳嚭鐩綍鐨刡asename浣滀负file_id
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
        print(f"鐢熸垚RGB鍒囩墖澶辫触: {e}")
        traceback.print_exc()
        return {"success": False}


def normalize_slice(slice_data):
    """
    褰掍竴鍖栧垏鐗囨暟鎹埌 [0, 1] 鑼冨洿
    """
    slice_data = np.nan_to_num(slice_data)

    # 浣跨敤2%鍜?8%鐧惧垎浣嶈繘琛岀ǔ鍋ュ綊涓€鍖?
    lower_bound = np.percentile(slice_data, 2)
    upper_bound = np.percentile(slice_data, 98)

    if upper_bound - lower_bound < 1e-6:
        lower_bound = slice_data.min()
        upper_bound = slice_data.max()
        if upper_bound - lower_bound < 1e-6:
            return np.zeros_like(slice_data)

    # 瑁佸壀寮傚父鍊煎苟缂╂斁鍒?0-1
    data_clipped = np.clip(slice_data, lower_bound, upper_bound)
    data_normalized = (data_clipped - lower_bound) / (upper_bound - lower_bound)

    return np.clip(data_normalized, 0, 1)


def generate_modality_slices(nifti_path, output_dir, suffix):
    """
    灏嗗崟涓€妯℃€丯IfTI鐢熸垚PNG鍒囩墖骞惰繑鍥濽RL鍒楄〃
    """
    if not nifti_path:
        return [], [], 0
    try:
        # 璇诲彇 NIfTI 骞剁粺涓€鍒?3D 浣撴暟鎹?
        img = nib.load(nifti_path)
        data = img.get_fdata()
        if data.ndim == 4:
            data = data[:, :, :, 0]
        elif data.ndim == 2:
            data = data[:, :, np.newaxis]

        # 璁＄畻鍒囩墖鏁伴噺涓庢枃浠禝D
        num_slices = data.shape[2] if data.ndim == 3 else 1
        file_id = os.path.basename(output_dir)
        urls = []
        npy_urls = []
        for slice_idx in range(num_slices):
            # 鎻愬彇鍗曞紶鍒囩墖骞惰繘琛屽綊涓€鍖?
            slice_data = data[:, :, slice_idx] if data.ndim == 3 else data
            normalized = normalize_slice(slice_data)
            # 鐢熸垚 PNG 棰勮鍥?
            img_8bit = (normalized * 255).astype(np.uint8)
            slice_prefix = f"slice_{slice_idx:03d}"
            filename = f"{slice_prefix}_{suffix}.png"
            save_path = os.path.join(output_dir, filename)
            Image.fromarray(img_8bit).save(save_path)
            urls.append(f"/get_image/{file_id}/{filename}")
            # 淇濆瓨褰掍竴鍖栧悗鐨?NPY 鏂囦欢锛堝甫 _output 鍚庣紑锛?
            npy_filename = f"{slice_prefix}_{suffix}_output.npy"
            npy_path = os.path.join(output_dir, npy_filename)
            np.save(npy_path, normalized.astype(np.float32))
            npy_urls.append(f"/get_file/{file_id}/{npy_filename}")
        return urls, npy_urls, num_slices
    except Exception as e:
        print(f"鐢熸垚{suffix}鍒囩墖澶辫触: {e}")
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
            return jsonify({"success": False, "error": "璇疯嚦灏戜笂浼?NCCT 鏂囦欢"}), 400

        patient_id_str = request.form.get("patient_id")
        if not patient_id_str:
            return jsonify({"success": False, "error": "缂哄皯 patient_id"}), 400
        try:
            patient_id = int(patient_id_str)
        except ValueError:
            return jsonify({"success": False, "error": "patient_id 闈炴硶"}), 400

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

        agent_run_id = None
        if str(request.form.get("start_agent_run", "false")).lower() == "true":
            agent_run_id = str(uuid.uuid4())
            _create_agent_run(
                run_id=agent_run_id,
                patient_id=patient_id,
                file_id=file_id,
                available_modalities=normalized_modalities,
                hemisphere=request.form.get("hemisphere", "both"),
                source="upload_start",
                linked_upload_job_id=job_id,
                execution_mode="post_upload_summary",
                trigger_source="upload_start",
            )

        payload["agent_run_id"] = agent_run_id

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
                "agent_run_id": agent_run_id,
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": f"鍚姩澶勭悊浠诲姟澶辫触: {str(e)}"}), 500


@app.route("/api/upload/progress/<job_id>", methods=["GET"])
def api_upload_progress(job_id):
    job = _get_upload_job(job_id)
    if not job:
        return jsonify({"success": False, "error": "任务不存在或已过期"}), 404
    return jsonify({"success": True, "job": job})


@app.route("/api/agent/runs", methods=["POST"])
def api_create_agent_run():
    data = request.get_json(silent=True) or {}

    patient_id_raw = data.get("patient_id")
    try:
        patient_id = int(patient_id_raw)
    except Exception:
        return jsonify({"success": False, "error": "Invalid patient_id"}), 400

    file_id = str(data.get("file_id") or "").strip()
    hemisphere = data.get("hemisphere", "both")
    available_modalities = data.get("available_modalities")

    if not file_id:
        latest_imaging = _get_latest_imaging_by_patient(patient_id)
        if latest_imaging:
            file_id = str(latest_imaging.get("case_id") or "").strip()
            if not isinstance(available_modalities, list):
                available_modalities = latest_imaging.get("available_modalities") or []

    if not file_id:
        return jsonify({"success": False, "error": "Missing file_id"}), 400

    if not isinstance(available_modalities, list):
        imaging = get_imaging_by_case(patient_id, file_id)
        available_modalities = (imaging or {}).get("available_modalities") or []

    if not available_modalities:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "available_modalities is required when imaging is missing",
                }
            ),
            400,
        )

    run_id = str(uuid.uuid4())
    run = _create_agent_run(
        run_id=run_id,
        patient_id=patient_id,
        file_id=file_id,
        available_modalities=available_modalities,
        hemisphere=hemisphere,
        source="api",
    )

    worker = threading.Thread(target=_run_agent_pipeline, args=(run_id,), daemon=True)
    worker.start()

    return jsonify(
        {
            "success": True,
            "run_id": run_id,
            "run_state": run,
            "status_url": f"/api/agent/runs/{run_id}",
            "events_url": f"/api/agent/runs/{run_id}/events",
            "result_url": f"/api/agent/runs/{run_id}/result",
        }
    )


@app.route("/api/agent/runs/<run_id>", methods=["GET"])
def api_get_agent_run(run_id):
    run = _get_agent_run(run_id)
    if not run:
        return jsonify({"success": False, "error": "Run not found"}), 404
    return jsonify({"success": True, "run": run})


@app.route("/api/agent/runs/<run_id>/events", methods=["GET"])
def api_get_agent_events(run_id):
    run = _get_agent_run(run_id)
    if not run:
        return jsonify({"success": False, "error": "Run not found"}), 404
    events = _get_agent_events(run_id)
    return jsonify({"success": True, "run_id": run_id, "events": events})


@app.route("/api/agent/runs/<run_id>/result", methods=["GET"])
def api_get_agent_result(run_id):
    run = _get_agent_run(run_id)
    if not run:
        return jsonify({"success": False, "error": "Run not found"}), 404

    if run.get("status") != "succeeded":
        return (
            jsonify(
                {
                    "success": False,
                    "run_id": run_id,
                    "status": run.get("status"),
                    "stage": run.get("stage"),
                    "error": run.get("error"),
                    "result": run.get("result"),
                }
            ),
            409,
        )

    return jsonify(
        {
            "success": True,
            "run_id": run_id,
            "status": run.get("status"),
            "stage": run.get("stage"),
            "result": run.get("result"),
        }
    )


@app.route("/api/agent/runs/<run_id>/retry", methods=["POST"])
def api_retry_agent_run(run_id):
    run = _get_agent_run(run_id)
    if not run:
        return jsonify({"success": False, "error": "Run not found"}), 404

    data = request.get_json(silent=True) or {}
    step_key = data.get("step_key")
    reason = data.get("reason", "")
    if not step_key:
        return jsonify({"success": False, "error": "Missing step_key"}), 400

    ok, message = _queue_agent_retry(run_id, step_key, reason)
    if not ok:
        return jsonify({"success": False, "error": message}), 400
    return jsonify({"success": True, "run_id": run_id, "message": message})


@app.route("/upload", methods=["POST"])
def upload_files():
    """处理上传文件请求。"""
    try:
        print("鏀跺埌涓婁紶璇锋眰...")

        if not NIBABEL_AVAILABLE:
            return jsonify(
                {
                    "success": False,
                    "error": 'nibabel 搴撲笉鍙敤銆傝杩愯: pip install "numpy<2.0" nibabel',
                }
            )

        # NCCT 蹇呴€夛紝鍏朵綑鏈熺浉鍙€?
        if "ncct_file" not in request.files:
            return jsonify({"success": False, "error": "璇疯嚦灏戦€夋嫨NCCT鏂囦欢"})

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
            return jsonify({"success": False, "error": "璇疯嚦灏戦€夋嫨NCCT鏂囦欢"})

        # 妫€鏌ユ枃浠舵牸寮?
        valid_extensions = [".nii", ".nii.gz"]

        def is_valid_nifti(file_obj):
            return any(
                file_obj.filename.lower().endswith(ext) for ext in valid_extensions
            )

        if not is_valid_nifti(ncct_file):
            return jsonify(
                {"success": False, "error": "璇蜂笂浼燦IfTI鏂囦欢 (.nii 鎴?.nii.gz)"}
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
                    {"success": False, "error": "璇蜂笂浼燦IfTI鏂囦欢 (.nii 鎴?.nii.gz)"}
                )

        print("鏂囦欢楠岃瘉閫氳繃:")
        print(f"NCCT: {ncct_file.filename}")
        if mcta_file:
            print(f"鍔ㄨ剦鏈烠TA: {mcta_file.filename}")
        if vcta_file:
            print(f"闈欒剦鏈烠TA: {vcta_file.filename}")
        if dcta_file:
            print(f"寤惰繜鏈烠TA: {dcta_file.filename}")

        # 鐢熸垚锛堟垨澶嶇敤锛夊敮涓€ID
        requested_file_id = (request.form.get("file_id") or "").strip()
        if requested_file_id:
            safe_file_id = re.sub(r"[^a-zA-Z0-9_-]", "", requested_file_id)[:32]
            file_id = safe_file_id or str(uuid.uuid4())[:8]
        else:
            file_id = str(uuid.uuid4())[:8]

        # 淇濆瓨涓婁紶鐨勬枃浠?
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

        print(f"鏂囦欢淇濆瓨鎴愬姛: NCCT={ncct_path}")
        if mcta_path:
            print(f"鍔ㄨ剦鏈烠TA: {mcta_path}")
        if vcta_path:
            print(f"闈欒剦鏈烠TA: {vcta_path}")
        if dcta_path:
            print(f"寤惰繜鏈烠TA: {dcta_path}")
        if cbf_path:
            print(f"CBF鍔熻兘鍥? {cbf_path}")
        if cbv_path:
            print(f"CBV鍔熻兘鍥? {cbv_path}")
        if tmax_path:
            print(f"TMAX鍔熻兘鍥? {tmax_path}")

        # 鏍规嵁鍓嶇涓婁紶鐨勫垏鐗囨洿鏂?available_modalities锛堜粎鍘熷涓婁紶锛屼笉鍚獳I鐢熸垚锛?
        patient_id_str = request.form.get("patient_id")
        patient_id = None
        if patient_id_str:
            try:
                patient_id = int(patient_id_str)
            except ValueError:
                patient_id = None

        # 灏嗗亸渚т俊鎭啓鍏?patient_imaging 琛紙鏍规嵁 patient_id + case_id锛?
        hemisphere = request.form.get("hemisphere", "both")
        try:
            if SUPABASE_AVAILABLE and patient_id:
                try:
                    # 鍏堝皾璇曟洿鏂板凡瀛樺湪璁板綍
                    update_resp = (
                        supabase.table("patient_imaging")
                        .update({"hemisphere": hemisphere})
                        .eq("patient_id", patient_id)
                        .eq("case_id", file_id)
                        .execute()
                    )
                    if update_resp.data and len(update_resp.data) > 0:
                        print(
                            f"patient_imaging 宸叉洿鏂板亸渚? patient_id={patient_id}, case_id={file_id}, hemisphere={hemisphere}"
                        )
                    else:
                        # 鑻ユ湭鏇存柊鍒颁换浣曡锛屽垯鎻掑叆鏂拌褰?
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
                                f"patient_imaging 宸叉彃鍏ユ柊璁板綍: {insert_resp.data[0]}"
                            )
                        else:
                            print(
                                f"璀﹀憡: 鍚?patient_imaging 鎻掑叆璁板綍鏈繑鍥炴暟鎹? {getattr(insert_resp, 'error', None)}"
                            )
                except Exception as e:
                    print(f"鍐欏叆 patient_imaging 澶辫触: {e}")
        except Exception as e:
            print(f"澶勭悊 hemisphere 鏃跺嚭閿? {e}")

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

        # 寮傛宸ヤ綔娴佸彲瑕佹眰寤惰繜鎵ц鑴戝崚涓嚜鍔ㄥ垎鏋?
        defer_stroke_analysis = (
            request.form.get("defer_stroke_analysis", "false") == "true"
        )

        # 妫€鏌ユ槸鍚︿笂浼犱簡鍏ㄩ儴CTA鍔熻兘鍥惧儚
        skip_ai = True
        if request.form.get("skip_ai") == "false" or (
            (mcta_path and vcta_path and dcta_path)
            and not (cbf_path or cbv_path or tmax_path)
        ):
            skip_ai = False
        print(f"skip_ai: {skip_ai}")

        # 鑾峰彇妯″瀷绫诲瀷鍙傛暟锛岄粯璁や娇鐢╩rdpm
        selected_model = request.form.get("model_type", "mrdpm")
        model_type = selected_model
        print(f"鐢ㄦ埛閫夋嫨鐨勬ā鍨? {selected_model}, 瀹為檯浣跨敤鐨勬ā鍨? {model_type}")

        # 濡傛灉skip_ai涓篢rue锛屽垯鐩存帴鐢熸垚涓婁紶鍥惧儚鐨凱NG鍒囩墖锛屼笉鍋欰I鎺ㄧ悊
        if skip_ai:
            print("璺宠繃AI鍒嗘瀽锛岀敓鎴愪笂浼犲浘鍍忓垏鐗嘝NG")

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
                # 涓哄綋鍓嶅垏鐗囩敓鎴愭帺鐮?
                # 灏濊瘯鍔犺浇NCCT鍥惧儚鏁版嵁鐢ㄤ簬鎺╃爜鐢熸垚
                ncct_slice_path = os.path.join(
                    output_dir, f"slice_{slice_idx:03d}_ncct.png"
                )
                if os.path.exists(ncct_slice_path):
                    from PIL import Image

                    ncct_img = Image.open(ncct_slice_path).convert("RGB")
                    rgb_data = np.array(ncct_img) / 255.0
                    # 鐢熸垚鎺╃爜
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

            # 鑷姩瑙﹀彂鑴戝崚涓垎鏋愶紙濡傛灉婊¤冻鏉′欢锛?
            if patient_id and not defer_stroke_analysis:
                print("灏濊瘯鑷姩瑙﹀彂鑴戝崚涓垎鏋?..")
                try:
                    try:
                        from .stroke_analysis import auto_analyze_stroke
                    except ImportError:
                        from stroke_analysis import auto_analyze_stroke

                    analysis_result = auto_analyze_stroke(file_id, patient_id)
                    print(
                        f"鑷姩鑴戝崚涓垎鏋愮粨鏋? {'鎴愬姛' if analysis_result.get('success') else '澶辫触'}"
                    )
                    if not analysis_result.get("success"):
                        print(f"鑷姩鍒嗘瀽澶辫触鍘熷洜: {analysis_result.get('error')}")
                except Exception as e:
                    print(f"鑷姩瑙﹀彂鑴戝崚涓垎鏋愬け璐? {e}")
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
            # 澶勭悊RGB鍚堟垚锛堢幇鍦ㄥ寘鍚妯″瀷AI鎺ㄧ悊锛?
            print("寮€濮嬪鐞哛GB鍚堟垚鍜屽妯″瀷AI鎺ㄧ悊...")
            result = process_rgb_synthesis(
                mcta_path, vcta_path, dcta_path, ncct_path, output_dir, model_type
            )

            if result["success"]:
                print("RGB鍚堟垚鍜屽妯″瀷AI鎺ㄧ悊澶勭悊鎴愬姛")

                # 鑷姩瑙﹀彂鑴戝崚涓垎鏋愶紙濡傛灉婊¤冻鏉′欢锛?
                if patient_id and not defer_stroke_analysis:
                    print("灏濊瘯鑷姩瑙﹀彂鑴戝崚涓垎鏋?..")
                    try:
                        try:
                            from .stroke_analysis import auto_analyze_stroke
                        except ImportError:
                            from stroke_analysis import auto_analyze_stroke

                        analysis_result = auto_analyze_stroke(file_id, patient_id)
                        print(
                            f"鑷姩鑴戝崚涓垎鏋愮粨鏋? {'鎴愬姛' if analysis_result.get('success') else '澶辫触'}"
                        )
                        if not analysis_result.get("success"):
                            print(f"鑷姩鍒嗘瀽澶辫触鍘熷洜: {analysis_result.get('error')}")
                    except Exception as e:
                        print(f"鑷姩瑙﹀彂鑴戝崚涓垎鏋愬け璐? {e}")
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
                print(f"RGB鍚堟垚澶勭悊澶辫触: {result['error']}")
                return jsonify({"success": False, "error": result["error"]})

    except Exception as e:
        print(f"涓婁紶澶勭悊寮傚父: {e}")
        traceback.print_exc()
        return jsonify({"success": False, "error": f"澶勭悊澶辫触: {str(e)}"})


# 鍏朵綑璺敱淇濇寔涓嶅彉...
@app.route("/download_mask/<file_id>/<int:slice_index>")
def download_mask(file_id, slice_index):
    """涓嬭浇鐗瑰畾鍒囩墖鐨勬帺鐮丯PY鏂囦欢"""
    try:
        filename = f"slice_{slice_index:03d}_mask.npy"
        file_path = os.path.join(app.config["PROCESSED_FOLDER"], file_id, filename)
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 404


@app.route("/get_image/<file_id>/<filename>")
def get_image(file_id, filename):
    """鑾峰彇鐢熸垚鐨凱NG鍥惧儚"""
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
    """获取 NPY 等文件。"""
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
    """获取特定切片和类型。"""
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
    print("馃殌 鍚姩Flask寮€鍙戞湇鍔″櫒...")

    # 鑾峰彇鏈満IP鍦板潃
    import socket

    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        print(f"馃寪 鏈満IP鍦板潃: {local_ip}")
        print(f"馃敆 灞€鍩熺綉璁块棶鍦板潃: http://{local_ip}:8765")
    except:
        local_ip = "0.0.0.0"
        print("无法获取本机 IP，使用默认配置")

    print("馃摫 鏈湴璁块棶鍦板潃: http://127.0.0.1:8765")
    print("馃實 鏈嶅姟鍣ㄧ洃鍚? 鎵€鏈夌綉缁滄帴鍙?(0.0.0.0:8765)")
    print("按 Ctrl+C 停止服务器")
    print("=" * 60)

    try:
        # 鍏抽敭淇敼锛氫娇鐢ㄦ槑纭殑鍙傛暟鍚姩
        app.run(
            host="0.0.0.0",  # 鐩戝惉鎵€鏈夌綉缁滄帴鍙?
            port=8765,  # 鏄庣‘鎸囧畾绔彛
            debug=True,  # 璋冭瘯妯″紡
            threaded=True,  # 澶氱嚎绋?
            use_reloader=False,  # 鍏抽棴鑷姩閲嶈浇锛岄伩鍏嶉噸澶嶅垵濮嬪寲
        )
    except Exception as e:
        print(f"鉂?鏈嶅姟鍣ㄥ惎鍔ㄥけ璐? {e}")
        import traceback

        traceback.print_exc()


# ==================== 淇濆瓨鎶ュ憡骞剁敓鎴?AI 璇婃柇鎶ュ憡 ====================


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








