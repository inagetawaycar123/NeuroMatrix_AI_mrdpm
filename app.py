import torch
import json
import base64
import time
from ai_inference import init_ai_model, get_ai_model
import os
import requests  # 添加 requests 导入，用于调用百川 M3 API
from flask import Flask, render_template, request, jsonify, send_file, Response, stream_with_context
from extensions import NumpyJSONEncoder

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
        if 'create_time' in patient_data:
            del patient_data['create_time']
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
            'core_infarct_volume': analysis_data.get('core_infarct_volume'),
            'penumbra_volume': analysis_data.get('penumbra_volume'),
            'mismatch_ratio': analysis_data.get('mismatch_ratio'),
            'hemisphere': analysis_data.get('hemisphere'),
            'analysis_status': analysis_data.get('analysis_status', 'completed')
        }
        response = supabase.table('patient_info') \
            .update(update_data) \
            .eq('id', patient_id) \
            .execute()
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
        response = supabase.table('patient_info') \
            .select('*') \
            .eq('id', patient_id) \
            .execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        print(f"获取患者信息失败: {e}")
        return None


# ==================== 百川 M3 API 配置 ====================


# ==================== 百川 M3 API 配置 ====================
# 首先尝试从 .env 文件加载环境变量
try:
    from dotenv import load_dotenv
    dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)
        print(f"✓ 已从 .env 文件加载环境变量")
    else:
        print(f"⚠ .env 文件不存在: {dotenv_path}")
except ImportError:
    print("⚠ python-dotenv 未安装，无法从 .env 文件加载")
except Exception as e:
    print(f"✗ 加载 .env 文件失败: {e}")

# 然后读取环境变量（已从.env加载或系统环境变量）
BAICHUAN_API_URL = os.environ.get('BAICHUAN_API_URL', 'https://api.baichuan-ai.com/v1/chat/completions')
BAICHUAN_API_KEY = os.environ.get('BAICHUAN_API_KEY', '') or os.environ.get('BAICHUAN_AK', '')
BAICHUAN_MODEL = os.environ.get('BAICHUAN_MODEL', 'Baichuan-M3')

def _get_baichuan_api_base() -> str:
    env_base = os.environ.get('BAICHUAN_API_BASE')
    if env_base:
        return env_base.rstrip('/')
    if '/v1/' in BAICHUAN_API_URL:
        return BAICHUAN_API_URL.split('/v1/')[0] + '/v1'
    return 'https://api.baichuan-ai.com/v1'

print(f"百川 API URL: {BAICHUAN_API_URL}")
print(f"百川 API Key: {'***' + BAICHUAN_API_KEY[-4:] if BAICHUAN_API_KEY else '未配置'}")
print(f"百川模型: {BAICHUAN_MODEL}")

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


def generate_report_with_baichuan(structured_data: dict, output_format: str = 'markdown') -> dict:
    """
    调用百川 M3 API 生成卒中影像报告
    """
    try:
        # 准备 NIHSS 评分显示
        nihss_score = structured_data.get('admission_nihss', None)
        nihss_display = f"{nihss_score} 分" if nihss_score is not None else "未记录"
        
        # 准备患者信息显示
        patient_id = structured_data.get('id', structured_data.get('ID', '未知'))
        patient_name = structured_data.get('patient_name', '未知')
        patient_age = structured_data.get('patient_age', '未知')
        patient_sex = structured_data.get('patient_sex', '未知')
        onset_to_admission = structured_data.get('onset_to_admission_hours', None)
        onset_display = f"{onset_to_admission} 小时" if onset_to_admission is not None else "未记录"
        
        # 准备 Prompt
        if output_format == 'json':
            prompt = REPORT_JSON_PROMPT.format(
                patient_id=patient_id,
                core_volume=structured_data.get('core_infarct_volume', 'N/A'),
                penumbra_volume=structured_data.get('penumbra_volume', 'N/A'),
                mismatch_ratio=structured_data.get('mismatch_ratio', 'N/A'),
                hemisphere=structured_data.get('hemisphere', '双侧')
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
                core_volume=structured_data.get('core_infarct_volume', 'N/A'),
                penumbra_volume=structured_data.get('penumbra_volume', 'N/A'),
                mismatch_ratio=structured_data.get('mismatch_ratio', 'N/A'),
                hemisphere=structured_data.get('hemisphere', '双侧')
            )
        
        # 检查 API Key
        if not BAICHUAN_API_KEY:
            print("⚠ 百川 API Key 未配置，返回模拟报告")
            mock_report = generate_mock_report(structured_data, output_format)
            return {
                'success': True,
                'report': mock_report,
                'format': output_format,
                'is_mock': True,
                'warning': '使用模拟报告，请配置 BAICHUAN_API_KEY 环境变量'
            }
            
        # 调用百川 M3 API
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {BAICHUAN_API_KEY}'
        }
        
        payload = {
            'model': BAICHUAN_MODEL,
            'messages': [
                {
                    'role': 'system',
                    'content': '你是一位专业的神经放射科医生，擅长撰写规范的卒中影像诊断报告。'
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'max_tokens': 4096,
            'temperature': 0.3,
            'top_p': 0.9
        }
        
        print(f"调用百川 M3 API... format={output_format}")
        print(f"Payload: {json.dumps(payload, ensure_ascii=False)[:500]}...")
        response = requests.post(BAICHUAN_API_URL, headers=headers, json=payload, timeout=60)
        
        print(f"响应状态码: {response.status_code}")
        print(f"响应内容: {response.text[:1000]}...")
        
        if response.status_code == 200:
            result = response.json()
            
            # 百川 M3 API 可能有多种响应格式，尝试多种解析方式
            report_content = ''
            
            # 方式1: OpenAI 格式 (choices[0].message.content)
            if 'choices' in result and len(result['choices']) > 0:
                choice = result['choices'][0]
                if 'message' in choice and 'content' in choice['message']:
                    report_content = choice['message']['content']
                elif 'text' in choice:
                    report_content = choice['text']
            
            # 方式2: 直接 content 字段
            if not report_content and 'content' in result:
                report_content = result['content']
            
            # 方式3: data 字段
            if not report_content and 'data' in result:
                data = result['data']
                if 'content' in data:
                    report_content = data['content']
            
            print(f"✓ 百川 M3 API 调用成功，报告长度: {len(report_content)}")
            return {
                'success': True,
                'report': report_content,
                'format': output_format,
                'is_mock': False
            }
        else:
            error_msg = f"API 调用失败: {response.status_code} - {response.text}"
            print(f"✗ {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'format': output_format
            }
            
    except requests.exceptions.Timeout:
        error_msg = "百川 M3 API 调用超时"
        print(f"✗ {error_msg}")
        return {'success': False, 'error': error_msg, 'format': output_format}
    except Exception as e:
        error_msg = f"生成报告失败: {str(e)}"
        print(f"✗ {error_msg}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': error_msg, 'format': output_format}


def generate_mock_report(structured_data: dict, output_format: str = 'markdown') -> str:
    """生成模拟报告（当 API Key 未配置时使用）"""
    patient_id = structured_data.get('id', structured_data.get('ID', '未知'))
    core_volume = structured_data.get('core_infarct_volume', 0)
    penumbra_volume = structured_data.get('penumbra_volume', 0)
    mismatch_ratio = structured_data.get('mismatch_ratio', 0)
    hemisphere = structured_data.get('hemisphere', '双侧')
    
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

    if output_format == 'json':
        import json
        return json.dumps(
            {
                "ID": patient_id,
                "检查方法": "头颅CT平扫(NCCT)+三期CTA(mCTA:动脉期、静脉期、延迟期)",
                "核心梗死": {
                    "体积": f"{core_volume} ml",
                    "位置": f"{hemisphere}大脑半球",
                    "CT表现": "NCCT未见明显低密度灶",
                    "灌注标准": "rCBF<30%"
                },
                "半暗带": {
                    "体积": f"{penumbra_volume} ml",
                    "位置": f"{hemisphere}大脑半球",
                    "灌注特征": "Tmax>6s, CBF降低但CBV相对保留",
                    "与核心关系": "相邻区域"
                },
                "左右脑不对称分析": {
                    "患侧": "CBF/CBV降低",
                    "健侧": "正常范围",
                    "不对称指数": "显著"
                },
                "血管评估": "根据三期CTA推断责任血管",
                "DEFUSE3评估": {
                    "不匹配体积": f"{penumbra_volume} ml",
                    "不匹配比值": f"{mismatch_ratio}",
                    "是否入选": "是" if penumbra_volume >= 15 and mismatch_ratio >= 1.8 else "否"
                },
                "诊断意见": f"{hemisphere}大脑半球急性缺血性改变，核心梗死体积约 {core_volume} ml，半暗带体积约 {penumbra_volume} ml",
                "治疗建议": "建议行血管内介入治疗评估"
            },
            ensure_ascii=False,
            indent=2
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

# 尝试导入 nibabel
try:
    import nibabel as nib

    NIBABEL_AVAILABLE = True
    print("✓ nibabel 导入成功")
except ImportError as e:
    print(f"✗ nibabel 导入失败: {e}")
    NIBABEL_AVAILABLE = False

app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['PROCESSED_FOLDER'] = 'static/processed'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024
app.config['TEMPLATES_AUTO_RELOAD'] = True  # 禁用HTML缓存，修改立即生效
app.jinja_env.auto_reload = True

# 核心：配置NumpyJSONEncoder用于JSON序列化
app.json_encoder = NumpyJSONEncoder


# 创建必要的目录
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['PROCESSED_FOLDER'], exist_ok=True)

print(f"上传目录: {app.config['UPLOAD_FOLDER']}")
print(f"处理目录: {app.config['PROCESSED_FOLDER']}")

# 获取项目根目录
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# AI模型配置 - 扩展为三个模型
AI_CONFIG_BASE = os.path.join(PROJECT_ROOT, 'palette', 'config')
AI_WEIGHTS_BASE = os.path.join(PROJECT_ROOT, 'palette', 'weights')  

# 三个模型的配置
MODEL_CONFIGS = {
    'cbf': {
        'name': 'CBF灌注图',
        'config_path': os.path.join(AI_CONFIG_BASE, 'cbf.json'),
        'weight_dir': os.path.join(AI_WEIGHTS_BASE, 'cbf'),
        'use_ema': True,
        'color': '#e74c3c',  # 红色
        'description': '脑血流量 (Cerebral Blood Flow)'
    },
    'cbv': {
        'name': 'CBV灌注图',
        'config_path': os.path.join(AI_CONFIG_BASE, 'cbv.json'),
        'weight_dir': os.path.join(AI_WEIGHTS_BASE, 'cbv'),
        'use_ema': True,
        'color': '#3498db',  # 蓝色
        'description': '脑血容量 (Cerebral Blood Volume)'
    },
    'tmax': {
        'name': 'Tmax灌注图',
        'config_path': os.path.join(AI_CONFIG_BASE, 'tmax.json'),
        'weight_dir': os.path.join(AI_WEIGHTS_BASE, 'tmax'),
        'use_ema': True,
        'color': '#27ae60',  # 绿色
        'description': '达峰时间 (Time to Maximum)'
    }
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
        if filename.endswith('.pth') and filename.startswith(pattern.split('_')[0]):
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
        if filename.endswith('_Network.pth') or filename.endswith('_Network_ema.pth'):
            # 提取数字部分（如 200）
            prefix = filename.split('_')[0]
            return os.path.join(weight_dir, prefix)
    
    return None

# 全局模型字典
ai_models = {}

# 统一的伪彩图配置 - 使用医学标准颜色映射
PSEUDOCOLOR_CONFIG = {
    'colormap': 'jet',  # 医学图像标准颜色映射
    'vmin': 0.1,  # 忽略过低的值
    'vmax': 0.9  # 避免过饱和
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
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"使用设备: {device}")

    for model_key, config in MODEL_CONFIGS.items():
        print(f"\n初始化 {config['name']} 模型:")
        print(f"  配置路径: {config['config_path']}")
        print(f"  权重目录: {config['weight_dir']}")

        # 使用新的权重检测逻辑
        weight_base = get_weight_base_path(config['weight_dir'])
        
        # 检查文件是否存在
        config_exists = os.path.exists(config['config_path'])
        ema_exists = find_weight_file(config['weight_dir'], '_Network_ema.pth') is not None
        normal_exists = find_weight_file(config['weight_dir'], '_Network.pth') is not None

        print(f"  配置文件: {'✓' if config_exists else '✗'}")
        print(f"  权重基础路径: {weight_base}")
        print(f"  EMA权重: {'✓' if ema_exists else '✗'}")
        print(f"  普通权重: {'✓' if normal_exists else '✗'}")

        if config_exists and weight_base:
            try:
                # 这里需要根据您的ai_inference模块调整初始化方式
                model = init_single_ai_model(config['config_path'], weight_base, config['use_ema'], device=device)
                if model:
                    ai_models[model_key] = {
                        'model': model,
                        'config': config,
                        'available': True
                    }
                    models_initialized += 1
                    print(f"  ✓ {config['name']} 模型初始化成功")
                else:
                    ai_models[model_key] = {
                        'model': None,
                        'config': config,
                        'available': False
                    }
                    print(f"  ✗ {config['name']} 模型初始化失败")
            except Exception as e:
                ai_models[model_key] = {
                    'model': None,
                    'config': config,
                    'available': False
                }
                print(f"  ✗ {config['name']} 模型初始化异常: {e}")
        else:
            ai_models[model_key] = {
                'model': None,
                'config': config,
                'available': False
            }
            print(f"  ✗ {config['name']} 模型文件不完整")

    print(f"\n模型初始化统计: {models_initialized}/{len(MODEL_CONFIGS)} 个模型成功初始化")
    print("=" * 50)

    return models_initialized > 0


def init_single_ai_model(config_path, weight_base, use_ema=True, device='cpu'):
    """初始化单个AI模型"""
    try:
        # 这里需要根据您的ai_inference模块调整初始化方式
        from ai_inference import MedicalAIModel
        model = MedicalAIModel(config_path, weight_base, use_ema=use_ema, device=device)
        return model
    except Exception as e:
        print(f"初始化单个模型失败: {e}")
        return None


def get_ai_model(model_key='cbf'):
    """获取指定的AI模型"""
    global ai_models
    if model_key in ai_models and ai_models[model_key]['available']:
        return ai_models[model_key]['model']
    return None


def are_any_models_available():
    """检查是否有任何模型可用"""
    global ai_models
    return any(model_info['available'] for model_info in ai_models.values())


def get_available_models():
    """获取可用的模型列表"""
    global ai_models
    # 从palette模型配置中获取可用模型
    available = [key for key, info in ai_models.items() if info['available']]
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
    mrdpm_weights_dir = os.path.join(current_dir, 'mrdpm', 'weights')
    
    if not os.path.exists(mrdpm_weights_dir):
        return available
    
    # 检查mrdpm主目录是否存在（使用mrdpm作为特殊model_key）
    bran_path = os.path.join(mrdpm_weights_dir, 'bran_pretrained_3channel.pth')
    residual_path = os.path.join(mrdpm_weights_dir, '200_Network_ema.pth')
    
    # mrdpm作为特殊标识，只要有一个子模型可用，mrdpm就可用
    subdirs = [d for d in os.listdir(mrdpm_weights_dir) if os.path.isdir(os.path.join(mrdpm_weights_dir, d))]
    for subdir in subdirs:
        sub_bran = os.path.join(mrdpm_weights_dir, subdir, 'bran_pretrained_3channel.pth')
        sub_residual = os.path.join(mrdpm_weights_dir, subdir, '200_Network_ema.pth')
        if os.path.exists(sub_bran) and os.path.exists(sub_residual):
            available.append('mrdpm')
            break
    
    return available


# ==================== 改进的伪彩图生成函数 ====================

def create_medical_pseudocolor(grayscale_data, mask_data):
    """
    医学标准伪彩图生成 - 只在掩码区域内应用伪彩色
    基于参考代码改进，符合临床规范
    """
    try:
        print("开始生成医学标准伪彩图...")
        print(f"输入数据范围: [{grayscale_data.min():.3f}, {grayscale_data.max():.3f}]")
        print(f"掩码数据范围: [{mask_data.min():.3f}, {mask_data.max():.3f}]")

        # 确保数据在有效范围内
        grayscale_data = np.clip(grayscale_data, 0, 1)

        # 获取掩码区域内的数据
        mask_binary = mask_data > 0.5
        masked_data = grayscale_data * mask_binary

        # 统计掩码区域内的数据
        if np.any(mask_binary):
            masked_values = grayscale_data[mask_binary]
            print(f"掩码区域内数据范围: [{masked_values.min():.3f}, {masked_values.max():.3f}]")
            print(f"掩码区域像素数量: {np.sum(mask_binary)}")
        else:
            print("⚠ 警告: 掩码区域为空")
            # 返回全黑图像
            return np.zeros((*grayscale_data.shape, 3), dtype=np.uint8)

        # 使用医学标准的jet颜色映射
        colormap = plt.get_cmap('jet')

        # 对掩码区域内的数据进行对比度增强
        if np.any(mask_binary) and masked_values.max() > masked_values.min():
            # 使用2%和98%百分位进行稳健归一化（参考代码方法）
            lower_bound = np.percentile(masked_values, 2)
            upper_bound = np.percentile(masked_values, 98)

            # 避免除零
            if upper_bound - lower_bound < 1e-6:
                lower_bound = masked_values.min()
                upper_bound = masked_values.max()
                if upper_bound - lower_bound < 1e-6:
                    # 如果数据范围仍然很小，使用默认范围
                    lower_bound = 0
                    upper_bound = 1

            # 应用对比度拉伸
            enhanced_data = np.clip((grayscale_data - lower_bound) / (upper_bound - lower_bound), 0, 1)
            print(f"对比度增强: [{lower_bound:.3f}, {upper_bound:.3f}] -> [0, 1]")
        else:
            enhanced_data = grayscale_data
            print("使用原始数据（对比度增强不可用）")

        # 应用颜色映射
        colored_data = colormap(enhanced_data)

        # 转换为RGB (去掉alpha通道)
        rgb_data = (colored_data[:, :, :3] * 255).astype(np.uint8)

        # 关键步骤：只在掩码区域内显示伪彩色，背景设为纯黑色
        result = np.zeros_like(rgb_data)
        for i in range(3):
            result[:, :, i] = np.where(mask_binary, rgb_data[:, :, i], 0)

        print(f"伪彩图生成完成，输出范围: [{result.min()}, {result.max()}]")
        return result

    except Exception as e:
        print(f"创建伪彩图失败: {e}")
        traceback.print_exc()
        # 返回默认的灰度图作为后备，但确保背景为黑色
        grayscale_8bit = (grayscale_data * 255).astype(np.uint8)
        result = np.zeros((*grayscale_data.shape, 3), dtype=np.uint8)
        for i in range(3):
            result[:, :, i] = np.where(mask_data > 0.5, grayscale_8bit, 0)
        return result


def generate_pseudocolor_for_slice(grayscale_path, mask_path, output_dir, slice_idx, model_key):
    """
    为单个切片的灰度图生成伪彩图 - 改进版本
    """
    try:
        print(f"为切片 {slice_idx} 的 {model_key.upper()} 生成医学标准伪彩图...")

        # 检查文件是否存在
        if not os.path.exists(grayscale_path):
            return {'success': False, 'error': '灰度图不存在'}
        if not os.path.exists(mask_path):
            return {'success': False, 'error': '掩码文件不存在'}

        # 加载图像数据
        grayscale_img = Image.open(grayscale_path).convert('L')
        grayscale_data = np.array(grayscale_img) / 255.0

        mask_img = Image.open(mask_path).convert('L')
        mask_data = np.array(mask_img) / 255.0

        # 生成医学标准伪彩图
        pseudocolor_data = create_medical_pseudocolor(grayscale_data, mask_data)

        # 保存伪彩图
        slice_prefix = f'slice_{slice_idx:03d}'
        pseudocolor_path = os.path.join(output_dir, f'{slice_prefix}_{model_key}_pseudocolor.png')

        # 确保目录存在
        os.makedirs(os.path.dirname(pseudocolor_path), exist_ok=True)
        Image.fromarray(pseudocolor_data).save(pseudocolor_path)

        # 构建URL
        file_id = os.path.basename(output_dir)
        pseudocolor_url = f'/get_image/{file_id}/{slice_prefix}_{model_key}_pseudocolor.png'

        print(f"✓ {model_key.upper()} 医学标准伪彩图生成成功: {pseudocolor_path}")

        return {
            'success': True,
            'pseudocolor_url': pseudocolor_url,
            'colormap': 'jet',  # 统一使用jet颜色映射
            'output_path': pseudocolor_path
        }

    except Exception as e:
        print(f"✗ 生成伪彩图失败: {e}")
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }


def generate_all_pseudocolors(output_dir, file_id, slice_idx):
    """
    为单个切片的所有模型生成伪彩图 - 改进版本
    """
    try:
        pseudocolor_results = {}
        success_count = 0

        for model_key in MODEL_CONFIGS.keys():
            # 构建文件路径
            slice_prefix = f'slice_{slice_idx:03d}'
            grayscale_path = os.path.join(output_dir, f'{slice_prefix}_{model_key}_output.png')
            mask_path = os.path.join(output_dir, f'{slice_prefix}_mask.png')

            # 检查文件是否存在
            if os.path.exists(grayscale_path) and os.path.exists(mask_path):
                print(f"\n--- 为 {model_key.upper()} 生成医学标准伪彩图 ---")
                result = generate_pseudocolor_for_slice(
                    grayscale_path, mask_path, output_dir, slice_idx, model_key
                )
                pseudocolor_results[model_key] = result
                if result['success']:
                    success_count += 1
            else:
                error_msg = f"文件不存在: {grayscale_path if not os.path.exists(grayscale_path) else mask_path}"
                print(f"✗ {error_msg}")
                pseudocolor_results[model_key] = {
                    'success': False,
                    'error': error_msg
                }

        print(f"\n伪彩图生成统计: {success_count}/{len(MODEL_CONFIGS)} 个模型成功")
        return pseudocolor_results

    except Exception as e:
        print(f"生成所有伪彩图失败: {e}")
        traceback.print_exc()
        return {}


# ==================== 路由函数 ====================

@app.route('/generate_pseudocolor/<file_id>/<int:slice_index>')
def generate_pseudocolor(file_id, slice_index):
    """生成指定切片的伪彩图 - 医学标准版本"""
    try:
        output_dir = os.path.join(app.config['PROCESSED_FOLDER'], file_id)

        if not os.path.exists(output_dir):
            return jsonify({'success': False, 'error': '文件目录不存在'})

        print(f"开始为切片 {slice_index} 生成医学标准伪彩图...")

        # 生成所有模型的伪彩图
        pseudocolor_results = generate_all_pseudocolors(output_dir, file_id, slice_index)

        # 统计成功数量
        success_count = sum(1 for result in pseudocolor_results.values() if result['success'])

        return jsonify({
            'success': True,
            'slice_index': slice_index,
            'pseudocolor_results': pseudocolor_results,
            'success_count': success_count,
            'total_models': len(MODEL_CONFIGS),
            'message': f'成功生成 {success_count}/{len(MODEL_CONFIGS)} 个模型的医学标准伪彩图'
        })

    except Exception as e:
        print(f"生成伪彩图路由错误: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/generate_all_pseudocolors/<file_id>')
def generate_all_pseudocolors_route(file_id):
    """为所有切片生成伪彩图 - 医学标准版本"""
    try:
        output_dir = os.path.join(app.config['PROCESSED_FOLDER'], file_id)

        if not os.path.exists(output_dir):
            return jsonify({'success': False, 'error': '文件目录不存在'})

        # 查找所有切片
        slice_files = [f for f in os.listdir(output_dir) if f.startswith('slice_') and f.endswith('_cbf_output.png')]
        slice_indices = []

        for file in slice_files:
            try:
                # 提取切片索引：slice_001_cbf_output.png -> 1
                index_str = file.split('_')[1]
                slice_index = int(index_str)
                slice_indices.append(slice_index)
            except:
                continue

        slice_indices.sort()

        if not slice_indices:
            return jsonify({'success': False, 'error': '未找到切片文件'})

        print(f"开始为 {len(slice_indices)} 个切片生成医学标准伪彩图...")

        all_results = {}
        total_success = 0

        for slice_idx in slice_indices:
            print(f"\n=== 处理切片 {slice_idx} ===")
            results = generate_all_pseudocolors(output_dir, file_id, slice_idx)
            all_results[slice_idx] = results

            # 统计该切片的成功数量
            slice_success = sum(1 for result in results.values() if result['success'])
            total_success += slice_success
            print(f"切片 {slice_idx} 完成: {slice_success}/{len(MODEL_CONFIGS)}")

        total_attempts = len(slice_indices) * len(MODEL_CONFIGS)

        return jsonify({
            'success': True,
            'total_slices': len(slice_indices),
            'total_models': len(MODEL_CONFIGS),
            'total_success': total_success,
            'total_attempts': total_attempts,
            'success_rate': f'{(total_success / total_attempts * 100):.1f}%',
            'results': all_results,
            'message': f'成功为 {total_success}/{total_attempts} 个组合生成医学标准伪彩图'
        })

    except Exception as e:
        print(f"生成所有伪彩图路由错误: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/analyze_stroke/<file_id>')
def analyze_stroke(file_id):
    """执行脑卒中病灶分析"""
    try:
        # 获取偏侧参数（默认为双侧）
        hemisphere = request.args.get('hemisphere', 'both')

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

        if analysis_results['success']:
            return jsonify({
                'success': True,
                'file_id': file_id,
                'hemisphere': hemisphere,
                'analysis_results': analysis_results
            })
        else:
            return jsonify({
                'success': False,
                'error': analysis_results.get('error', '分析失败')
            })

    except Exception as e:
        print(f"脑卒中分析路由错误: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})


@app.route('/get_stroke_analysis_image/<file_id>/<filename>')
def get_stroke_analysis_image(file_id, filename):
    """获取脑卒中分析生成的图像"""
    try:
        image_path = os.path.join(app.config['PROCESSED_FOLDER'], file_id, 'stroke_analysis', filename)
        print(f"获取脑卒中分析图像: {image_path}")  # 调试信息
        if os.path.exists(image_path):
            return send_file(image_path, mimetype='image/png')
        else:
            print(f"分析图像不存在: {image_path}")  # 调试信息
            return jsonify({'error': '分析图像不存在'}), 404
    except Exception as e:
        print(f"获取脑卒中分析图像错误: {e}")  # 调试信息
        return jsonify({'error': str(e)}), 404


@app.route('/api/insert_patient', methods=['POST'])
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

@app.route('/api/update_analysis', methods=['POST'])
def api_update_analysis():
    """更新患者的分析结果到 patient_info 表"""
    data = request.get_json()
    patient_id = data.get('patient_id')
    
    if not patient_id:
        return jsonify({"status": "error", "message": "缺少 patient_id"}), 400
    
    # 调用封装好的函数
    success, result = update_analysis_result(patient_id, data)
    
    if success:
        return jsonify({
            "status": "success",
            "message": "分析结果已更新",
            "data": result
        })
    else:
        return jsonify({{
            "status": "error",
            "message": result
        }}), 500


# ==================== 百川 M3 AI 报告生成 API ====================

@app.route('/api/generate_report/<int:patient_id>', methods=['GET', 'POST'])
def api_generate_report(patient_id):
    """
    基于患者结构化数据调用百川 M3 生成影像报告
    """
    try:
        # 获取输出格式参数
        if request.method == 'POST':
            data = request.get_json() or {{}}
            output_format = data.get('format', 'markdown')
        else:
            output_format = request.args.get('format', 'markdown')
        
        # 验证格式参数
        if output_format not in ['markdown', 'json']:
            return jsonify({{
                "status": "error",
                "message": "无效的输出格式，支持 'markdown' 或 'json'"
            }}), 400
        
        # 从数据库获取患者结构化数据
        patient_data = get_patient_by_id(patient_id)
        
        if not patient_data:
            return jsonify({
                "status": "error",
                "message": f"未找到 ID 为 {patient_id} 的患者信息"
            }), 404
        
        # 提取结构化数据
        # 获取发病时间和入院时间用于计算发病至入院时长
        onset_time = patient_data.get('onset_exact_time')
        admission_time = patient_data.get('admission_time')
        onset_to_admission_hours = None
        if onset_time and admission_time:
            try:
                from datetime import datetime
                onset_dt = datetime.fromisoformat(str(onset_time).replace('Z', '+00:00'))
                admission_dt = datetime.fromisoformat(str(admission_time).replace('Z', '+00:00'))
                onset_to_admission_hours = round((admission_dt - onset_dt).total_seconds() / 3600, 1)
            except Exception as e:
                print(f"计算发病至入院时间失败: {e}")
        
        structured_data = {
            'id': patient_data.get('id'),
            'ID': patient_data.get('id'),
            'patient_name': patient_data.get('patient_name', ''),
            'patient_age': patient_data.get('patient_age', ''),
            'patient_sex': patient_data.get('patient_sex', ''),
            'admission_nihss': patient_data.get('admission_nihss', None),
            'onset_to_admission_hours': onset_to_admission_hours,
            'core_infarct_volume': patient_data.get('core_infarct_volume'),
            'penumbra_volume': patient_data.get('penumbra_volume'),
            'mismatch_ratio': patient_data.get('mismatch_ratio'),
            'hemisphere': patient_data.get('hemisphere', '左侧'),
            'analysis_status': patient_data.get('analysis_status', 'pending')
        }
        
        # 打印完整的 structured_data 用于调试
        print("=" * 60)
        print("【AI 报告生成】完整的 structured_data：")
        print(json.dumps(structured_data, ensure_ascii=False, indent=2, default=str))
        print("=" * 60)
        
        # 打印日志，证明已成功读取这三个关键数据
        print("=" * 60)
        print("【AI 报告生成】已读取的关键临床数据：")
        print(f"  - 入院 NIHSS 评分: {structured_data.get('admission_nihss')} 分")
        print(f"  - 患者年龄: {structured_data.get('patient_age')} 岁")
        print(f"  - 发病至入院时间: {onset_to_admission_hours} 小时")
        print("=" * 60)
        
        # 如果某个关键数据缺失，打印警告
        if structured_data.get('admission_nihss') is None:
            print("⚠️ 警告: admission_nihss 字段为空！")
        if structured_data.get('patient_age') in ['', None]:
            print("⚠️ 警告: patient_age 字段为空！")
        if onset_to_admission_hours is None:
            print("⚠️ 警告: onset_to_admission_hours 字段为空！")
        
        # 调用百川 M3 生成报告
        result = generate_report_with_baichuan(structured_data, output_format)
        
        if result['success']:
            return jsonify({
                "status": "success",
                "message": "报告生成成功",
                "patient_id": patient_id,
                "format": output_format,
                "report": result['report'],
                "is_mock": result.get('is_mock', False),
                "warning": result.get('warning')
            })
        else:
            return jsonify({
                "status": "error",
                "message": result.get('error', '生成报告失败'),
                "format": output_format
            }), 500
            
    except Exception as e:
        print(f"生成报告异常: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/api/generate_report_from_data', methods=['POST'])
def api_generate_report_from_data():
    """
    直接从传入的结构化数据生成报告（不查询数据库）
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "status": "error",
                "message": "请求数据为空"
            }), 400
        
        # 验证必要参数
        required_fields = ['core_infarct_volume', 'penumbra_volume', 'mismatch_ratio']
        missing_fields = [f for f in required_fields if f not in data]
        
        if missing_fields:
            return jsonify({
                "status": "error",
                "message": f"缺少必要参数: {', '.join(missing_fields)}"
            }), 400
        
        output_format = data.get('format', 'markdown')
        
        # 如果前端没有提供 patient_id，尝试从数据库补充 NIHSS、年龄、发病时间
        patient_id = data.get('patient_id')
        if patient_id:
            patient_data = get_patient_by_id(patient_id)
            if patient_data:
                # 从数据库补充缺失的字段
                if data.get('admission_nihss') is None and patient_data.get('admission_nihss') is not None:
                    data['admission_nihss'] = patient_data.get('admission_nihss')
                if data.get('patient_age') in ['', None] and patient_data.get('patient_age') is not None:
                    data['patient_age'] = patient_data.get('patient_age')
                if data.get('onset_to_admission_hours') is None and patient_data.get('onset_exact_time') and patient_data.get('admission_time'):
                    try:
                        from datetime import datetime
                        onset_dt = datetime.fromisoformat(str(patient_data.get('onset_exact_time')).replace('Z', '+00:00'))
                        admission_dt = datetime.fromisoformat(str(patient_data.get('admission_time')).replace('Z', '+00:00'))
                        data['onset_to_admission_hours'] = round((admission_dt - onset_dt).total_seconds() / 3600, 1)
                    except Exception as e:
                        print(f"计算发病至入院时间失败: {e}")
        
        # 调用百川 M3 生成报告
        result = generate_report_with_baichuan(data, output_format)
        
        if result['success']:
            return jsonify({
                "status": "success",
                "message": "报告生成成功",
                "format": output_format,
                "report": result['report'],
                "is_mock": result.get('is_mock', False),
                "warning": result.get('warning')
            })
        else:
            return jsonify({
                "status": "error",
                "message": result.get('error', '生成报告失败'),
                "format": output_format
            }), 500
            
    except Exception as e:
        print(f"生成报告异常: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500



@app.route('/api/get_patient/<int:patient_id>')
def api_get_patient(patient_id):
    """获取患者信息"""
    try:
        response = supabase.table('patient_info') \
            .select('*') \
            .eq('id', patient_id) \
            .execute()
        
        if response.data and len(response.data) > 0:
            return jsonify({
                "status": "success",
                "data": response.data[0]
            })
        else:
            return jsonify({
                "status": "error",
                "message": f"未找到ID为 {patient_id} 的患者信息"
            }), 404
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/save_report', methods=['POST'])
def api_save_report():
    """保存结构化临床报告"""
    data = request.get_json()
    patient_id = data.get('patient_id')
    file_id = data.get('file_id')
    
    if not patient_id or not file_id:
        return jsonify({"status": "error", "message": "缺少患者ID或文件ID"}), 400
    
    try:
        # 将报告保存到数据库
        report_notes = f"""
患者信息：{data.get('patient', {}).get('patient_name', '')}
核心梗死：{data.get('findings', {}).get('core', '')}
半暗带：{data.get('findings', {}).get('penumbra', '')}
血管评估：{data.get('findings', {}).get('vessel', '')}
灌注分析：{data.get('findings', {}).get('perfusion', '')}
医生备注：{data.get('notes', '')}
"""
        
        update_data = {
            'uncertainty_remark': report_notes
        }
        
        response = supabase.table('patient_info') \
            .update(update_data) \
            .eq('id', patient_id) \
            .execute()
        
        return jsonify({
            "status": "success",
            "message": "报告保存成功",
            "data": response.data
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# 简单的测试路由
@app.route('/test')
def test_page():
    """测试路由"""
    return "Test page works!"

@app.route('/chat')
def chat_page():
    """渲染AI问诊页面"""
    return render_template('patient/upload/viewer/chat.html')


def _sse_format(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _truncate_text(text: str, max_chars: int = 6000) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[内容过长，已截断]"


def _decode_data_uri(data_uri: str):
    if not data_uri or not isinstance(data_uri, str):
        return None, None
    if not data_uri.startswith('data:'):
        return None, None
    try:
        header, b64_data = data_uri.split(',', 1)
    except ValueError:
        return None, None
    mime = header.split(';')[0].replace('data:', '').strip()
    try:
        file_bytes = base64.b64decode(b64_data)
    except Exception:
        return None, None
    return file_bytes, mime


def _upload_baichuan_file(file_bytes: bytes, filename: str, purpose: str = 'medical') -> str:
    if not BAICHUAN_API_KEY:
        return ''
    api_base = _get_baichuan_api_base()
    url = f"{api_base}/files"
    headers = {
        'Authorization': f'Bearer {BAICHUAN_API_KEY}'
    }
    files = {
        'file': (filename, file_bytes)
    }
    data = {
        'purpose': purpose
    }
    response = requests.post(url, headers=headers, files=files, data=data, timeout=60)
    if response.status_code != 200:
        return ''
    result = response.json() or {}
    return result.get('id', '')


def _fetch_baichuan_parsed_content(file_id: str, timeout_seconds: int = 30, interval_seconds: int = 2) -> str:
    if not file_id or not BAICHUAN_API_KEY:
        return ''
    api_base = _get_baichuan_api_base()
    url = f"{api_base}/files/{file_id}/parsed-content"
    headers = {
        'Authorization': f'Bearer {BAICHUAN_API_KEY}'
    }
    start_time = time.time()
    while True:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code != 200:
            return ''
        result = response.json() or {}
        status = result.get('status')
        if status == 'online':
            return result.get('content', '')
        if status in ('fail', 'unsafe'):
            return ''
        if time.time() - start_time > timeout_seconds:
            return ''
        time.sleep(interval_seconds)


def _collect_pdf_parsed_text(images) -> str:
    if not images:
        return ''
    parsed_blocks = []
    for idx, item in enumerate(images, start=1):
        data_uri = None
        filename = f"upload_{idx}.pdf"
        mime = ''

        if isinstance(item, dict):
            data_uri = item.get('data')
            filename = item.get('name') or filename
            mime = item.get('type') or ''
        elif isinstance(item, str):
            data_uri = item

        if not data_uri:
            continue

        file_bytes, detected_mime = _decode_data_uri(data_uri)
        if not file_bytes:
            continue

        mime = mime or detected_mime
        if mime != 'application/pdf':
            continue

        file_id = _upload_baichuan_file(file_bytes, filename, purpose='medical')
        if not file_id:
            continue

        parsed_content = _fetch_baichuan_parsed_content(file_id)
        if not parsed_content:
            continue

        parsed_blocks.append(
            f"[PDF文件: {filename}]\n{_truncate_text(parsed_content)}"
        )

    if not parsed_blocks:
        return ''
    return "\n\n".join(parsed_blocks)


@app.route('/api/chat/clinical/stream', methods=['POST'])
def api_chat_clinical_stream():
    """医疗AI临床聊天接口 - 流式响应 (SSE)"""
    data = request.get_json() or {}
    session_id = data.get('sessionId')
    question = data.get('question')
    images = data.get('images', [])
    patient_context = data.get('patientContext', {})

    if not session_id or not question:
        return jsonify({
            "success": False,
            "error": "缺少会话ID或问题"
        }), 400

    def generate_stream():
        if not BAICHUAN_API_KEY:
            mock_text = "当前未配置 BAICHUAN_API_KEY，无法进行实时问答。"
            yield _sse_format({"type": "delta", "content": mock_text})
            yield _sse_format({"type": "done"})
            return

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {BAICHUAN_API_KEY}'
        }

        parsed_text = _collect_pdf_parsed_text(images)
        system_content = '你是一位专业的神经放射科医生，擅长脑卒中影像诊断和分析。'
        if parsed_text:
            system_content += f"\n\n以下是用户上传PDF的解析内容，请结合回答：\n\n{parsed_text}"

        messages = [
            {
                'role': 'system',
                'content': system_content
            },
            {
                'role': 'user',
                'content': question
            }
        ]

        payload = {
            'model': BAICHUAN_MODEL,
            'messages': messages,
            'max_tokens': 8192,
            'temperature': 0.3,
            'stream': True
        }

        try:
            response = requests.post(
                BAICHUAN_API_URL,
                headers=headers,
                json=payload,
                timeout=60,
                stream=True
            )
        except Exception as e:
            yield _sse_format({"type": "error", "error": f"API请求失败: {e}"})
            yield _sse_format({"type": "done"})
            return

        if response.status_code != 200:
            error_text = response.text[:2000]
            yield _sse_format({
                "type": "error",
                "error": f"API调用失败: {response.status_code}"
            })
            if error_text:
                yield _sse_format({"type": "delta", "content": error_text})
            yield _sse_format({"type": "done"})
            return

        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
            if not line.startswith('data:'):
                continue

            data_str = line[len('data:'):].strip()
            if data_str == '[DONE]':
                yield _sse_format({"type": "done"})
                break

            try:
                chunk = json.loads(data_str)
            except json.JSONDecodeError:
                continue

            delta = ''
            if isinstance(chunk, dict):
                if 'choices' in chunk and chunk['choices']:
                    choice = chunk['choices'][0]
                    if isinstance(choice, dict):
                        if 'delta' in choice and isinstance(choice['delta'], dict):
                            delta = choice['delta'].get('content', '')
                        elif 'message' in choice and isinstance(choice['message'], dict):
                            delta = choice['message'].get('content', '')
                        elif 'text' in choice:
                            delta = choice.get('text', '')
                elif 'content' in chunk:
                    delta = chunk.get('content', '')

            if delta:
                yield _sse_format({"type": "delta", "content": delta})

    return Response(
        stream_with_context(generate_stream()),
        content_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )


@app.route('/api/chat/clinical/', methods=['POST'])
def api_chat_clinical():
    """医疗AI临床聊天接口"""
    try:
        data = request.get_json()
        session_id = data.get('sessionId')
        question = data.get('question')
        images = data.get('images', [])
        patient_context = data.get('patientContext', {})
        
        if not session_id or not question:
            return jsonify({
                "success": False,
                "error": "缺少会话ID或问题"
            }), 400
        
        # 调用百川API进行临床问答
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {BAICHUAN_API_KEY}'
        }
        
        parsed_text = _collect_pdf_parsed_text(images)
        system_content = '你是一位专业的神经放射科医生，擅长脑卒中影像诊断和分析。'
        if parsed_text:
            system_content += f"\n\n以下是用户上传PDF的解析内容，请结合回答：\n\n{parsed_text}"

        messages = [
            {
                'role': 'system',
                'content': system_content
            },
            {
                'role': 'user',
                'content': question
            }
        ]

        payload = {
            'model': BAICHUAN_MODEL,
            'messages': messages,
            'max_tokens': 8192,
            'temperature': 0.3
        }
        
        response = requests.post(BAICHUAN_API_URL, headers=headers, json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            ai_response = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            
            return jsonify({
                "success": True,
                "message": {
                    "role": "assistant",
                    "content": ai_response
                }
            })
        else:
            return jsonify({
                "success": False,
                "error": f"API调用失败: {response.status_code}"
            }), 500
            
    except Exception as e:
        print(f"聊天错误: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/report/<int:patient_id>')
def report_page(patient_id):
    """渲染报告页面"""
    import os
    import re
    # 检查是否有编译后的生产文件
    dist_file = os.path.join(app.static_folder, 'dist', 'index.html')
    if os.path.exists(dist_file):
        # 生产环境：使用编译后的文件，并修改资源路径
        with open(dist_file, 'r', encoding='utf-8') as f:
            html = f.read()
        
        # 修改 <link> 标签中的 href 路径：from /assets/ to /static/dist/assets/
        html = re.sub(r'href="\/assets\/', 'href="/static/dist/assets/', html)
        
        # 修改 <script> 标签中的 src 路径：from /assets/ to /static/dist/assets/
        html = re.sub(r'src="\/assets\/', 'src="/static/dist/assets/', html)
        
        return html
    else:
        # 开发环境：返回 Vite 开发服务器入口
        return render_template('patient/upload/viewer/report/vite.html')

# ==================== 图像对比度调节API ====================

@app.route('/adjust_contrast/<file_id>/<int:slice_index>/<image_type>')
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
        window_width = float(request.args.get('ww', 80))
        window_level = float(request.args.get('wl', 40))
        
        # 验证图像类型
        if image_type not in ['mcta', 'ncct']:
            return jsonify({'error': '无效的图像类型'}), 400
        
        # 构建原始图像路径
        slice_prefix = f'slice_{slice_index:03d}'
        original_path = os.path.join(
            app.config['PROCESSED_FOLDER'],
            file_id,
            f'{slice_prefix}_{image_type}.png'
        )
        
        if not os.path.exists(original_path):
            return jsonify({'error': '原始图像不存在'}), 404
        
        # 加载原始图像
        original_img = Image.open(original_path).convert('L')
        img_array = np.array(original_img, dtype=np.float32)
        
        # 应用窗宽窗位调节
        adjusted_array = apply_window_level(img_array, window_width, window_level)
        
        # 转换为PIL图像
        adjusted_img = Image.fromarray(adjusted_array.astype(np.uint8))
        
        # 返回调节后的图像
        from io import BytesIO
        img_buffer = BytesIO()
        adjusted_img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        return send_file(img_buffer, mimetype='image/png')
        
    except Exception as e:
        print(f"对比度调节错误: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


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


@app.route('/get_image_histogram/<file_id>/<int:slice_index>/<image_type>')
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
        if image_type not in ['mcta', 'ncct']:
            return jsonify({'error': '无效的图像类型'}), 400
        
        # 构建图像路径
        slice_prefix = f'slice_{slice_index:03d}'
        image_path = os.path.join(
            app.config['PROCESSED_FOLDER'],
            file_id,
            f'{slice_prefix}_{image_type}.png'
        )
        
        if not os.path.exists(image_path):
            return jsonify({'error': '图像不存在'}), 404
        
        # 加载图像
        img = Image.open(image_path).convert('L')
        img_array = np.array(img)
        
        # 计算直方图
        histogram, bin_edges = np.histogram(img_array.flatten(), bins=256, range=(0, 256))
        
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
        
        return jsonify({
            'success': True,
            'histogram': histogram.tolist(),
            'statistics': {
                'min': min_val,
                'max': max_val,
                'mean': mean_val,
                'std': std_val
            },
            'suggested_window': {
                'width': max_val - min_val,
                'level': (max_val + min_val) / 2
            }
        })
        
    except Exception as e:
        print(f"获取直方图错误: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/save_contrast_settings/<file_id>', methods=['POST'])
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
            return jsonify({'error': '无效的设置数据'}), 400

        # 保存设置到文件
        settings_path = os.path.join(
            app.config['PROCESSED_FOLDER'],
            file_id,
            'contrast_settings.json'
        )

        import json
        with open(settings_path, 'w') as f:
            json.dump(settings, f, indent=2, cls=NumpyJSONEncoder)

        return jsonify({
            'success': True,
            'message': '对比度设置已保存'
        })

    except Exception as e:
        print(f"保存对比度设置错误: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/load_contrast_settings/<file_id>')
def load_contrast_settings(file_id):
    """
    加载对比度设置
    """
    try:
        settings_path = os.path.join(
            app.config['PROCESSED_FOLDER'],
            file_id,
            'contrast_settings.json'
        )
        
        if not os.path.exists(settings_path):
            # 返回默认设置
            return jsonify({
                'success': True,
                'settings': {
                    'cta': {'windowWidth': 80, 'windowLevel': 40},
                    'ncct': {'windowWidth': 80, 'windowLevel': 40}
                },
                'is_default': True
            })
        
        import json
        with open(settings_path, 'r') as f:
            settings = json.load(f)
        
        return jsonify({
            'success': True,
            'settings': settings,
            'is_default': False
        })
        
    except Exception as e:
        print(f"加载对比度设置错误: {e}")
        return jsonify({'error': str(e)}), 500


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

        print(f"通道 {max_channel} 数据范围: [{channel_img.min():.3f}, {channel_img.max():.3f}]")

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
            smoothed > adaptive_low,
            smoothed < adaptive_high
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
            if region.area > area_threshold and total_area < channel_img.shape[0] * channel_img.shape[1] * 0.8:
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
        print(f"掩码覆盖率: {final_pixel_count / (channel_img.shape[0] * channel_img.shape[1]) * 100:.1f}%")

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
            smoothed > adaptive_low,
            smoothed < adaptive_high
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
            channel_img > adaptive_low,
            channel_img < adaptive_high
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
            channel_img > low_thresh,
            channel_img < high_thresh
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
        background_normalized = (background - background.min()) / (background.max() - background.min())
        background_8bit = (background_normalized * 255).astype(np.uint8)

        # 创建RGB叠加图像
        overlay = np.stack([background_8bit] * 3, axis=2)

        # 在掩码区域添加红色叠加
        mask_indices = mask > 0.5
        overlay[mask_indices, 0] = 255
        overlay[mask_indices, 1] = np.minimum(overlay[mask_indices, 1], 150)
        overlay[mask_indices, 2] = np.minimum(overlay[mask_indices, 2], 150)

        # 保存叠加图像
        overlay_path = os.path.join(output_dir, f'slice_{slice_idx:03d}_overlay.png')
        Image.fromarray(overlay).save(overlay_path)

        return f'/get_image/{os.path.basename(output_dir)}/slice_{slice_idx:03d}_overlay.png'

    except Exception as e:
        print(f"创建叠加图像失败: {e}")
        return ''


def generate_mask_for_slice(rgb_data, output_dir, slice_idx):
    """
    为单个切片生成掩码，尝试多种方法 - 修正版本
    """
    try:
        print(f"为切片 {slice_idx} 生成掩码...")

        # 尝试多种方法，选择最好的一个
        methods = ['adaptive', 'standard', 'otsu']
        best_mask = None
        best_coverage = 0
        best_method = 'unknown'

        for method in methods:
            try:
                if method == 'adaptive':
                    mask = create_adaptive_brain_mask(rgb_data)
                elif method == 'otsu':
                    mask = create_otsu_brain_mask(rgb_data)
                else:
                    mask = create_brain_mask(rgb_data, low_thresh=0.01, high_thresh=0.99)

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
            best_method = 'default'
            best_coverage = np.sum(best_mask) / (best_mask.shape[0] * best_mask.shape[1])

        print(f"选择方法: {best_method}, 最终覆盖率: {best_coverage:.3f}")

        # 保存掩码为PNG图像
        mask_8bit = (best_mask * 255).astype(np.uint8)
        mask_path = os.path.join(output_dir, f'slice_{slice_idx:03d}_mask.png')
        Image.fromarray(mask_8bit).save(mask_path)

        # 保存掩码为NPY文件
        mask_npy_path = os.path.join(output_dir, f'slice_{slice_idx:03d}_mask.npy')
        np.save(mask_npy_path, best_mask)

        # 生成叠加图像
        overlay_url = create_overlay_image(rgb_data, best_mask, output_dir, slice_idx)

        return {
            'success': True,
            'mask_url': f'/get_image/{os.path.basename(output_dir)}/slice_{slice_idx:03d}_mask.png',
            'mask_npy_url': f'/get_file/{os.path.basename(output_dir)}/slice_{slice_idx:03d}_mask.npy',
            'overlay_url': overlay_url,
            'coverage': best_coverage,
            'method': best_method,
            'mask_data': best_mask  # 关键：确保返回掩码数据
        }

    except Exception as e:
        print(f"生成掩码失败: {e}")
        # 返回一个空的掩码，但确保包含mask_data
        empty_mask = np.zeros((rgb_data.shape[0], rgb_data.shape[1]))
        mask_path = os.path.join(output_dir, f'slice_{slice_idx:03d}_mask.png')
        Image.fromarray(empty_mask.astype(np.uint8)).save(mask_path)

        mask_npy_path = os.path.join(output_dir, f'slice_{slice_idx:03d}_mask.npy')
        np.save(mask_npy_path, empty_mask)

        overlay_url = create_overlay_image(rgb_data, empty_mask, output_dir, slice_idx)

        return {
            'success': True,
            'mask_url': f'/get_image/{os.path.basename(output_dir)}/slice_{slice_idx:03d}_mask.png',
            'mask_npy_url': f'/get_file/{os.path.basename(output_dir)}/slice_{slice_idx:03d}_mask.npy',
            'overlay_url': overlay_url,
            'coverage': 0,
            'method': 'error',
            'mask_data': empty_mask  # 关键：即使失败也返回掩码数据
        }


def process_ai_inference(rgb_result, mask_result, output_dir, slice_idx, model_key='mrdpm', model_type='mrdpm'):
    """处理单个切片的AI推理 - 支持多模型版本"""
    try:
        # 获取RGB数据
        rgb_data = rgb_result.get('rgb_data')
        if rgb_data is None:
            print(f"⚠ RGB数据不可用")
            return {
                'success': False,
                'error': 'RGB数据不可用',
                'ai_url': '',
                'ai_npy_url': ''
            }

        # 获取掩码数据
        mask_data = mask_result.get('mask_data')
        if mask_data is None:
            # 尝试从文件加载掩码
            mask_npy_path = os.path.join(output_dir, f'slice_{slice_idx:03d}_mask.npy')
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
        if model_type == 'mrdpm':
            print(f"开始{model_key.upper()}模型推理 (使用MRDPM模型)...")
            # MRDPM模型推理逻辑
            # 1. 获取mrdpm模型权重路径
            from ai_inference import MRDPMModel
            import torch
            
            # 确定mrdpm子模型（当model_key为'mrdpm'时，默认使用'cbf'）
            mrdpm_submodel = model_key if model_key != 'mrdpm' else 'cbf'
            
            # 构建mrdpm模型权重路径
            current_dir = os.path.dirname(os.path.abspath(__file__))
            bran_pretrained_path = os.path.join(current_dir, 'mrdpm', 'weights', mrdpm_submodel, 'bran_pretrained_3channel.pth')
            residual_weight_path = os.path.join(current_dir, 'mrdpm', 'weights', mrdpm_submodel, '200_Network_ema.pth')
            
            # 验证权重文件是否存在
            print(f"📁 检查BRAN权重文件: {bran_pretrained_path}")
            print(f"📁 检查残差权重文件: {residual_weight_path}")
            
            if not os.path.exists(bran_pretrained_path):
                print(f"❌ BRAN权重文件不存在: {bran_pretrained_path}")
                return {
                    'success': False,
                    'error': f'BRAN权重文件不存在: {bran_pretrained_path}',
                    'ai_url': '',
                    'ai_npy_url': ''
                }
            
            if not os.path.exists(residual_weight_path):
                print(f"❌ 残差权重文件不存在: {residual_weight_path}")
                return {
                    'success': False,
                    'error': f'残差权重文件不存在: {residual_weight_path}',
                    'ai_url': '',
                    'ai_npy_url': ''
                }
            
            print(f"✅ 所有权重文件存在")
            
            # 2. 初始化MRDPMModel
            mrdpm_model = MRDPMModel(bran_pretrained_path, residual_weight_path, device='cuda' if torch.cuda.is_available() else 'cpu')
            
            # 3. 执行AI推理，传递save_path保存初始预测图
            save_path = os.path.join(output_dir, f'slice_{slice_idx:03d}_{model_key}_initial.png')
            ai_output = mrdpm_model.inference(rgb_data, mask_data, save_path)
        else:
            # 默认使用palette模型
            print(f"开始{model_key.upper()}模型推理 (使用palette模型)...")
            ai_model = get_ai_model(model_key)
            if ai_model is None:
                print(f"⚠ {model_key.upper()} 模型未初始化")
                return {
                    'success': False,
                    'error': f'{model_key.upper()}模型未初始化',
                    'ai_url': '',
                    'ai_npy_url': ''
                }
            
            # 执行AI推理
            ai_output = ai_model.inference(rgb_data, mask_data)

        # 确保输出有效
        if ai_output is None or ai_output.size == 0:
            print(f"✗ {model_key.upper()}模型推理返回空结果")
            return {
                'success': False,
                'error': f'{model_key.upper()}模型推理返回空结果',
                'ai_url': '',
                'ai_npy_url': ''
            }

        # 保存AI结果
        slice_prefix = f'slice_{slice_idx:03d}'
        ai_npy_path = os.path.join(output_dir, f'{slice_prefix}_{model_key}_output.npy')

        # 保存NPY文件
        # 使用合适的方法保存结果
        try:
            # 保存NPY
            np.save(ai_npy_path, ai_output)
            
            # 保存PNG预览
            from PIL import Image
            png_path = ai_npy_path.replace('.npy', '.png')
            result_8bit = (ai_output * 255).astype(np.uint8)
            Image.fromarray(result_8bit).save(png_path)
            success = True
        except Exception as e:
            print(f"保存结果失败: {e}")
            success = False
        
        if not success:
            print(f"✗ 保存{model_key.upper()}结果失败")
            return {
                'success': False,
                'error': f'保存{model_key.upper()}结果失败',
                'ai_url': '',
                'ai_npy_url': ''
            }

        # 构建正确的URL路径
        file_id = os.path.basename(output_dir)
        ai_image_url = f'/get_image/{file_id}/{slice_prefix}_{model_key}_output.png'
        ai_npy_url = f'/get_file/{file_id}/{slice_prefix}_{model_key}_output.npy'

        print(f"✓ {model_key.upper()}模型推理成功")
        print(f"AI图像URL: {ai_image_url}")
        print(f"AI数据URL: {ai_npy_url}")

        return {
            'success': True,
            'ai_url': ai_image_url,
            'ai_npy_url': ai_npy_url
        }

    except Exception as e:
        print(f"✗ {model_key.upper()}模型推理处理失败: {e}")
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e),
            'ai_url': '',
            'ai_npy_url': ''
        }


def process_rgb_synthesis(mcta_path, vcta_path, dcta_path, ncct_path, output_dir, model_type='mrdpm'):
    """处理RGB合成，现在支持多模型AI推理"""
    try:
        if not NIBABEL_AVAILABLE:
            return {
                'success': False,
                'error': 'nibabel 库不可用，请安装: pip install "numpy<2.0" nibabel'
            }

        # 加载四个NIfTI文件
        mcta_img = nib.load(mcta_path)
        vcta_img = nib.load(vcta_path)
        dcta_img = nib.load(dcta_path)
        ncct_img = nib.load(ncct_path)

        mcta_data = mcta_img.get_fdata()
        vcta_data = vcta_img.get_fdata()
        dcta_data = dcta_img.get_fdata()
        ncct_data = ncct_img.get_fdata()

        print(f"动脉期CTA 维度: {mcta_data.shape}")
        print(f"静脉期CTA 维度: {vcta_data.shape}")
        print(f"延迟期CTA 维度: {dcta_data.shape}")
        print(f"NCCT 维度: {ncct_data.shape}")

        # 检查所有文件维度是否一致
        all_shapes = [mcta_data.shape, vcta_data.shape, dcta_data.shape, ncct_data.shape]
        if not all(shape == all_shapes[0] for shape in all_shapes):
            return {
                'success': False,
                'error': f'文件维度不匹配: 动脉期CTA{all_shapes[0]} vs 静脉期CTA{all_shapes[1]} vs 延迟期CTA{all_shapes[2]} vs NCCT{all_shapes[3]}'
            }

        # 获取基本信息
        metadata = {
            'mcta_shape': [int(dim) for dim in mcta_data.shape],
            'vcta_shape': [int(dim) for dim in vcta_data.shape],
            'dcta_shape': [int(dim) for dim in dcta_data.shape],
            'ncct_shape': [int(dim) for dim in ncct_data.shape],
            'mcta_range': [float(mcta_data.min()), float(mcta_data.max())],
            'vcta_range': [float(vcta_data.min()), float(vcta_data.max())],
            'dcta_range': [float(dcta_data.min()), float(dcta_data.max())],
            'ncct_range': [float(ncct_data.min()), float(ncct_data.max())],
            'voxel_dims': [float(dim) for dim in mcta_img.header.get_zooms()[:3]]
        }

        # 处理每个切片
        rgb_files = []
        num_slices = mcta_data.shape[2] if len(mcta_data.shape) >= 3 else 1

        # 检查AI模型可用性
        available_models = get_available_models()
        # MRDPM 推理只需要 CBF/CBV/TMAX 三类子模型，过滤掉占位的 mrdpm 标识
        if model_type == 'mrdpm':
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
            rgb_result = generate_rgb_slices(mcta_slice, vcta_slice, dcta_slice, ncct_slice, output_dir, slice_idx)
            if not rgb_result['success']:
                print(f"⚠ 切片 {slice_idx} RGB合成失败，跳过")
                continue

            # 生成掩码
            mask_result = generate_mask_for_slice(rgb_result['rgb_data'], output_dir, slice_idx)

            # 确保mask_result包含mask_data
            if 'mask_data' not in mask_result:
                print(f"⚠ 切片 {slice_idx} 的掩码生成失败，使用空掩码")
                mask_result['mask_data'] = np.zeros_like(rgb_result['rgb_data'][:, :, 0])

            # 初始化切片结果
            slice_result = {
                'slice_index': slice_idx,
                'rgb_image': rgb_result.get('rgb_url', ''),
                'mcta_image': rgb_result.get('mcta_url', ''),
                'vcta_url': rgb_result.get('vcta_url', ''),
                'dcta_url': rgb_result.get('dcta_url', ''),
                'ncct_image': rgb_result.get('ncct_url', ''),
                'npy_url': rgb_result.get('npy_url', ''),
                'mask_image': mask_result.get('mask_url', ''),
                'mask_npy_url': mask_result.get('mask_npy_url', ''),
                'overlay_url': mask_result.get('overlay_url', ''),
                'coverage': mask_result.get('coverage', 0),
                'method': mask_result.get('method', 'unknown'),
            }

            # 为每个模型初始化AI结果
            for model_key in MODEL_CONFIGS.keys():
                slice_result.update({
                    f'has_{model_key}': False,
                    f'{model_key}_image': '',
                    f'{model_key}_npy_url': ''
                })

            # 对每个可用模型进行推理
            slice_has_any_ai = False

            for model_key in available_models:
                try:
                    print(f"开始{model_key.upper()}模型推理切片 {slice_idx}...")
                    ai_result = process_ai_inference(
                        rgb_result,
                        mask_result,
                        output_dir,
                        slice_idx,
                        model_key,
                        model_type
                    )

                    if ai_result and ai_result['success']:
                        print(f"✓ {model_key.upper()}模型推理完成切片 {slice_idx}")
                        slice_result.update({
                            f'has_{model_key}': True,
                            f'{model_key}_image': ai_result.get('ai_url', ''),
                            f'{model_key}_npy_url': ai_result.get('ai_npy_url', '')
                        })
                        model_success_counts[model_key] += 1
                        slice_has_any_ai = True
                        has_any_model_success = True
                    else:
                        error_msg = ai_result.get('error', '未知错误') if ai_result else '无结果'
                        print(f"⚠ {model_key.upper()}模型推理失败切片 {slice_idx}: {error_msg}")
                except Exception as e:
                    print(f"✗ {model_key.upper()}模型推理异常切片 {slice_idx}: {e}")

            # 添加总体AI状态
            slice_result['has_ai'] = slice_has_any_ai
            rgb_files.append(slice_result)

        # 统计信息
        print(f"\n=== AI模型处理统计 ===")
        print(f"总切片数: {len(rgb_files)}")
        for model_key, count in model_success_counts.items():
            status = "可用" if model_key in available_models else "不可用"
            print(f"{model_key.upper()}模型: {count}个切片成功 ({status})")

        # 在元数据中添加模型状态信息
        metadata.update({
            'models_available': available_models,
            'models_status': {key: key in available_models for key in MODEL_CONFIGS.keys()},
            'models_success_counts': model_success_counts,
            'has_any_ai': has_any_model_success
        })

        # 添加每个模型的详细信息
        for model_key, config in MODEL_CONFIGS.items():
            metadata.update({
                f'{model_key}_name': config['name'],
                f'{model_key}_color': config['color'],
                f'{model_key}_description': config['description'],
                f'{model_key}_available': model_key in available_models,
                f'{model_key}_success_count': model_success_counts[model_key]
            })

        # 构建最终返回结果
        result = {
            'success': True,
            'file_id': os.path.basename(output_dir),
            'metadata': metadata,
            'rgb_files': rgb_files,
            'total_slices': int(num_slices),
            'has_ai': has_any_model_success,
            'available_models': available_models,
            'model_configs': MODEL_CONFIGS
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
        return {
            'success': False,
            'error': str(e)
        }


# 在应用启动时初始化
def initialize_app():
    """应用初始化函数 - 多模型版本"""
    print("=" * 50)
    print("医学图像处理Web系统初始化 - 医学标准伪彩图版本")
    print("=" * 50)

    # 创建必要的目录
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['PROCESSED_FOLDER'], exist_ok=True)

    print(f"上传目录: {app.config['UPLOAD_FOLDER']}")
    print(f"处理目录: {app.config['PROCESSED_FOLDER']}")

    # 初始化AI模型
    ai_initialized = init_ai_models()

    # 设置全局标志
    app.config['AI_AVAILABLE'] = ai_initialized
    app.config['AI_MODELS'] = ai_models
    app.config['MODEL_CONFIGS'] = MODEL_CONFIGS

    print(f"AI功能可用: {ai_initialized}")
    print("✓ 应用初始化完成")
    print("=" * 50)


# 使用应用上下文进行初始化
with app.app_context():
    initialize_app()


# 添加启动时初始化
@app.before_request
def before_first_request():
    """替代before_first_request的解决方案"""
    if not hasattr(app, 'has_initialized'):
        initialize_app()
        app.has_initialized = True


# 修改下载路由以支持多模型
@app.route('/download_ai/<model_key>/<file_id>/<int:slice_index>')
def download_ai(model_key, file_id, slice_index):
    """下载特定模型的AI推理结果NPY文件"""
    try:
        if model_key not in MODEL_CONFIGS:
            return jsonify({'error': f'无效的模型类型: {model_key}'}), 400

        filename = f'slice_{slice_index:03d}_{model_key}_output.npy'
        file_path = os.path.join(app.config['PROCESSED_FOLDER'], file_id, filename)

        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({'error': '文件不存在'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 404


# 其余函数保持不变...
def generate_rgb_slices(mcta_slice, vcta_slice, dcta_slice, ncct_slice, output_dir, slice_idx):
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
        rgb_data = np.stack([mcta_normalized, ncct_normalized, np.zeros_like(mcta_normalized)], axis=2)
        rgb_8bit = (rgb_data * 255).astype(np.uint8)

        # 3. 创建单独通道的图像（用于显示）
        mcta_8bit = (mcta_normalized * 255).astype(np.uint8)
        vcta_8bit = (vcta_normalized * 255).astype(np.uint8)
        dcta_8bit = (dcta_normalized * 255).astype(np.uint8)
        ncct_8bit = (ncct_normalized * 255).astype(np.uint8)

        # 创建输出路径
        slice_prefix = f'slice_{slice_idx:03d}'

        # 保存RGB合成图像
        rgb_path = os.path.join(output_dir, f'{slice_prefix}_rgb.png')
        Image.fromarray(rgb_8bit).save(rgb_path)

        # 保存单独通道图像
        mcta_path = os.path.join(output_dir, f'{slice_prefix}_mcta.png')
        vcta_path = os.path.join(output_dir, f'{slice_prefix}_vcta.png')
        dcta_path = os.path.join(output_dir, f'{slice_prefix}_dcta.png')
        ncct_path = os.path.join(output_dir, f'{slice_prefix}_ncct.png')
        
        Image.fromarray(mcta_8bit).save(mcta_path)
        Image.fromarray(vcta_8bit).save(vcta_path)
        Image.fromarray(dcta_8bit).save(dcta_path)
        Image.fromarray(ncct_8bit).save(ncct_path)

        # 保存NPY数据 - 直接保存RGB数组，而不是字典
        npy_path = os.path.join(output_dir, f'{slice_prefix}_data.npy')
        np.save(npy_path, rgb_data.astype(np.float32))  # 直接保存数组

        # 获取输出目录的basename作为file_id
        file_id = os.path.basename(output_dir)

        return {
            'success': True,
            'rgb_url': f'/get_image/{file_id}/{slice_prefix}_rgb.png',
            'mcta_url': f'/get_image/{file_id}/{slice_prefix}_mcta.png',
            'vcta_url': f'/get_image/{file_id}/{slice_prefix}_vcta.png',
            'dcta_url': f'/get_image/{file_id}/{slice_prefix}_dcta.png',
            'ncct_url': f'/get_image/{file_id}/{slice_prefix}_ncct.png',
            'npy_url': f'/get_file/{file_id}/{slice_prefix}_data.npy',
            'rgb_data': rgb_data
        }

    except Exception as e:
        print(f"生成RGB切片失败: {e}")
        traceback.print_exc()
        return {'success': False}


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

    data_clipped = np.clip(slice_data, lower_bound, upper_bound)
    data_normalized = (data_clipped - lower_bound) / (upper_bound - lower_bound)

    return np.clip(data_normalized, 0, 1)



@app.route('/')
def index():
    return render_template('patient/index.html')


@app.route('/upload')
def upload_page():
    return render_template('patient/upload/index.html')


@app.route('/viewer')
def viewer_page():
    return render_template('patient/upload/viewer/index.html')


@app.route('/upload', methods=['POST'])
def upload_files():
    """处理四文件上传 - 多模型版本"""
    try:
        print("收到上传请求...")

        if not NIBABEL_AVAILABLE:
            return jsonify({
                'success': False,
                'error': 'nibabel 库不可用。请运行: pip install "numpy<2.0" nibabel'
            })

        # 检查文件是否存在（动脉期CTA、静脉期CTA、延迟期CTA、NCCT）
        required_keys = ['mcta_file', 'vcta_file', 'dcta_file', 'ncct_file']
        if not all(key in request.files for key in required_keys):
            return jsonify({'success': False, 'error': '请选择四个文件：动脉期CTA、静脉期CTA、延迟期CTA、NCCT'})

        mcta_file = request.files['mcta_file']
        vcta_file = request.files['vcta_file']
        dcta_file = request.files['dcta_file']
        ncct_file = request.files['ncct_file']

        if any(f.filename == '' for f in [mcta_file, vcta_file, dcta_file, ncct_file]):
            return jsonify({'success': False, 'error': '请选择四个文件：动脉期CTA、静脉期CTA、延迟期CTA、NCCT'})

        # 检查文件格式
        valid_extensions = ['.nii', '.nii.gz']
        mcta_valid = any(mcta_file.filename.lower().endswith(ext) for ext in valid_extensions)
        vcta_valid = any(vcta_file.filename.lower().endswith(ext) for ext in valid_extensions)
        dcta_valid = any(dcta_file.filename.lower().endswith(ext) for ext in valid_extensions)
        ncct_valid = any(ncct_file.filename.lower().endswith(ext) for ext in valid_extensions)

        if not (mcta_valid and vcta_valid and dcta_valid and ncct_valid):
            return jsonify({'success': False, 'error': '请上传NIfTI文件 (.nii 或 .nii.gz)'})

        print(
            f"文件验证通过: {mcta_file.filename}, {vcta_file.filename}, {dcta_file.filename}, {ncct_file.filename}"
        )

        # 生成唯一ID
        file_id = str(uuid.uuid4())[:8]

        # 保存上传的文件
        mcta_extension = '.nii.gz' if mcta_file.filename.lower().endswith('.nii.gz') else '.nii'
        vcta_extension = '.nii.gz' if vcta_file.filename.lower().endswith('.nii.gz') else '.nii'
        dcta_extension = '.nii.gz' if dcta_file.filename.lower().endswith('.nii.gz') else '.nii'
        ncct_extension = '.nii.gz' if ncct_file.filename.lower().endswith('.nii.gz') else '.nii'

        mcta_path = os.path.join(app.config['UPLOAD_FOLDER'], f'{file_id}_mcta{mcta_extension}')
        vcta_path = os.path.join(app.config['UPLOAD_FOLDER'], f'{file_id}_vcta{vcta_extension}')
        dcta_path = os.path.join(app.config['UPLOAD_FOLDER'], f'{file_id}_dcta{dcta_extension}')
        ncct_path = os.path.join(app.config['UPLOAD_FOLDER'], f'{file_id}_ncct{ncct_extension}')

        mcta_file.save(mcta_path)
        vcta_file.save(vcta_path)
        dcta_file.save(dcta_path)
        ncct_file.save(ncct_path)

        print(f"文件保存成功: {mcta_path}, {vcta_path}, {dcta_path}, {ncct_path}")

        # 创建输出目录
        output_dir = os.path.join(app.config['PROCESSED_FOLDER'], file_id)
        os.makedirs(output_dir, exist_ok=True)

        # 获取模型类型参数，默认使用mrdpm
        selected_model = request.form.get('model_type', 'mrdpm')
        # 实现模型选择的映射转换
        model_mapping = {'mrdpm': 'palette', 'palette': 'mrdpm'}
        model_type = model_mapping.get(selected_model, 'palette')
        print(f"用户选择的模型: {selected_model}, 实际使用的模型: {model_type}")

        # 处理RGB合成（现在包含多模型AI推理）
        # 使用所有四个期相CTA文件进行处理
        print("开始处理RGB合成和多模型AI推理...")
        result = process_rgb_synthesis(mcta_path, vcta_path, dcta_path, ncct_path, output_dir, model_type)

        if result['success']:
            print("RGB合成和多模型AI推理处理成功")

            # 确保所有数据都是JSON可序列化的
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

            return jsonify({
                'success': True,
                'file_id': file_id,
                'mcta_filename': mcta_file.filename,
                'vcta_filename': vcta_file.filename,
                'dcta_filename': dcta_file.filename,
                'ncct_filename': ncct_file.filename,
                'metadata': ensure_json_serializable(result['metadata']),
                'rgb_files': ensure_json_serializable(result['rgb_files']),
                'total_slices': result['total_slices'],
                'has_ai': result['has_ai'],
                'available_models': result['available_models'],
                'model_configs': result['model_configs']
            })
        else:
            print(f"RGB合成处理失败: {result['error']}")
            return jsonify({'success': False, 'error': result['error']})

    except Exception as e:
        print(f"上传处理异常: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'处理失败: {str(e)}'})


# 其余路由保持不变...
@app.route('/download_mask/<file_id>/<int:slice_index>')
def download_mask(file_id, slice_index):
    """下载特定切片的掩码NPY文件"""
    try:
        filename = f'slice_{slice_index:03d}_mask.npy'
        file_path = os.path.join(app.config['PROCESSED_FOLDER'], file_id, filename)
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        return jsonify({'error': str(e)}), 404


@app.route('/get_image/<file_id>/<filename>')
def get_image(file_id, filename):
    """获取生成的PNG图像"""
    try:
        image_path = os.path.join(app.config['PROCESSED_FOLDER'], file_id, filename)
        if os.path.exists(image_path):
            return send_file(image_path, mimetype='image/png')
        else:
            return jsonify({'error': '图像不存在'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 404


@app.route('/get_file/<file_id>/<filename>')
def get_file(file_id, filename):
    """获取NPY等文件"""
    try:
        file_path = os.path.join(app.config['PROCESSED_FOLDER'], file_id, filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({'error': '文件不存在'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 404


@app.route('/get_slice/<file_id>/<int:slice_index>/<image_type>')
def get_slice(file_id, slice_index, image_type):
    """获取特定切片和类型"""
    try:
        filename = f'slice_{slice_index:03d}_{image_type}.png'
        image_path = os.path.join(app.config['PROCESSED_FOLDER'], file_id, filename)
        if os.path.exists(image_path):
            return send_file(image_path, mimetype='image/png')
        else:
            return jsonify({'error': '切片不存在'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("🚀 启动Flask开发服务器...")

    # 获取本机IP地址
    import socket
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        print(f"🌐 本机IP地址: {local_ip}")
        print(f"🔗 局域网访问地址: http://{local_ip}:8765")
    except:
        local_ip = '0.0.0.0'
        print("⚠ 无法获取本机IP，使用默认配置")

    print("📱 本地访问地址: http://127.0.0.1:8765")
    print("🌍 服务器监听: 所有网络接口 (0.0.0.0:8765)")
    print("⏹️ 按 Ctrl+C 停止服务器")
    print("=" * 60)

    try:
        # 关键修改：使用明确的参数启动
        app.run(
            host='0.0.0.0',      # 监听所有网络接口
            port=8765,           # 明确指定端口
            debug=True,          # 调试模式
            threaded=True,       # 多线程
            use_reloader=False   # 关闭自动重载，避免重复初始化
        )
    except Exception as e:
        print(f"❌ 服务器启动失败: {e}")
        import traceback
        traceback.print_exc()


# ==================== 保存报告并生成 AI 诊断报告 ====================

@app.route('/api/save_and_generate_report', methods=['POST'])
def api_save_and_generate_report():
    """保存结构化临床报告，同时生成 AI 诊断报告"""
    data = request.get_json()
    patient_id = data.get('patient_id')
    file_id = data.get('file_id')
    
    if not patient_id or not file_id:
        return jsonify({"status": "error", "message": "缺少患者ID或文件ID"}), 400
    
    try:
        # 1. 先保存报告到数据库
        report_notes = f"""
        患者信息：{data.get('patient', {}).get('patient_name', '')}
        核心梗死：{data.get('findings', {}).get('core', '')}
        半暗带：{data.get('findings', {}).get('penumbra', '')}
        血管评估：{data.get('findings', {}).get('vessel', '')}
        灌注分析：{data.get('findings', {}).get('perfusion', '')}
        医生备注：{data.get('notes', '')}
        """
        
        update_data = {
            'uncertainty_remark': report_notes
        }
        
        response = supabase.table('patient_info') \
            .update(update_data) \
            .eq('id', patient_id) \
            .execute()
        
        # 2. 获取患者结构化数据
        structured_data = get_patient_by_id(patient_id) or {}
        
        # 3. 调用百川 M3 生成 AI 报告
        print(f"保存报告时自动生成 AI 报告，患者ID: {patient_id}")
        ai_result = generate_report_with_baichuan(structured_data, output_format='markdown')
        
        return jsonify({
            "status": "success",
            "message": "报告保存并生成 AI 诊断报告成功",
            "data": response.data,
            "ai_report": ai_result.get('report', ''),
            "ai_generated": True
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
