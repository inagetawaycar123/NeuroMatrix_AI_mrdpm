# app.py - 改进的伪彩图生成版本
import torch
from ai_inference import init_ai_model, get_ai_model
import os
from flask import Flask, render_template, request, jsonify, send_file

from core.supabase_client import insert_patient_info, update_analysis_result
from extensions import NumpyJSONEncoder
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
        'weight_base': os.path.join(AI_WEIGHTS_BASE, 'cbf', '150'),
        'use_ema': True,
        'color': '#e74c3c',  # 红色
        'description': '脑血流量 (Cerebral Blood Flow)'
    },
    'cbv': {
        'name': 'CBV灌注图',
        'config_path': os.path.join(AI_CONFIG_BASE, 'cbv.json'),
        'weight_base': os.path.join(AI_WEIGHTS_BASE, 'cbv', '140'),
        'use_ema': True,
        'color': '#3498db',  # 蓝色
        'description': '脑血容量 (Cerebral Blood Volume)'
    },
    'tmax': {
        'name': 'Tmax灌注图',
        'config_path': os.path.join(AI_CONFIG_BASE, 'tmax.json'),
        'weight_base': os.path.join(AI_WEIGHTS_BASE, 'tmax', '160'),
        'use_ema': True,
        'color': '#27ae60',  # 绿色
        'description': '达峰时间 (Time to Maximum)'
    }
}

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
        print(f"  权重基础: {config['weight_base']}")

        # 检查文件是否存在
        config_exists = os.path.exists(config['config_path'])
        ema_exists = os.path.exists(f"{config['weight_base']}_Network_ema.pth")
        normal_exists = os.path.exists(f"{config['weight_base']}_Network.pth")

        print(f"  配置文件: {'✓' if config_exists else '✗'}")
        print(f"  EMA权重: {'✓' if ema_exists else '✗'}")
        print(f"  普通权重: {'✓' if normal_exists else '✗'}")

        if config_exists and (ema_exists or normal_exists):
            try:
                # 这里需要根据您的ai_inference模块调整初始化方式
                model = init_single_ai_model(config['config_path'], config['weight_base'], config['use_ema'], device=device)
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
        return jsonify({
            "status": "error",
            "message": result
        }), 500

@app.route('/api/get_patient/<int:patient_id>')
def api_get_patient(patient_id):
    """获取患者信息"""
    try:
        from core.supabase_client import supabase
        
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
        # 这里简化为更新患者记录，实际项目建议新建独立的 reports 表
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
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/report/<int:patient_id>')
def report_page(patient_id):
    """渲染报告页面"""
    return render_template('patient/upload/viewer/report/index.html')

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


def process_rgb_synthesis(mcta_path, ncct_path, output_dir, model_type='mrdpm'):
    """处理RGB合成，现在支持多模型AI推理"""
    try:
        if not NIBABEL_AVAILABLE:
            return {
                'success': False,
                'error': 'nibabel 库不可用，请安装: pip install "numpy<2.0" nibabel'
            }

        # 加载两个NIfTI文件
        mcta_img = nib.load(mcta_path)
        ncct_img = nib.load(ncct_path)

        mcta_data = mcta_img.get_fdata()
        ncct_data = ncct_img.get_fdata()

        print(f"mCTA1 维度: {mcta_data.shape}")
        print(f"NCCT 维度: {ncct_data.shape}")

        # 检查两个文件维度是否一致
        if mcta_data.shape != ncct_data.shape:
            return {
                'success': False,
                'error': f'文件维度不匹配: mCTA1{mcta_data.shape} vs NCCT{ncct_data.shape}'
            }

        # 获取基本信息
        metadata = {
            'mcta_shape': [int(dim) for dim in mcta_data.shape],
            'ncct_shape': [int(dim) for dim in ncct_data.shape],
            'mcta_range': [float(mcta_data.min()), float(mcta_data.max())],
            'ncct_range': [float(ncct_data.min()), float(ncct_data.max())],
            'voxel_dims': [float(dim) for dim in mcta_img.header.get_zooms()[:3]]
        }

        # 处理每个切片
        rgb_files = []
        num_slices = mcta_data.shape[2] if len(mcta_data.shape) >= 3 else 1

        # 检查AI模型可用性
        available_models = get_available_models()
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
                ncct_slice = ncct_data[:, :, slice_idx]
            elif len(mcta_data.shape) == 4:
                mcta_slice = mcta_data[:, :, slice_idx, 0]
                ncct_slice = ncct_data[:, :, slice_idx, 0]
            else:
                mcta_slice = mcta_data
                ncct_slice = ncct_data

            # 生成RGB合成图像和NPY数据
            rgb_result = generate_rgb_slices(mcta_slice, ncct_slice, output_dir, slice_idx)
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
def generate_rgb_slices(mcta_slice, ncct_slice, output_dir, slice_idx):
    """
    生成RGB合成图像和单独通道图像
    """
    try:
        # 1. 归一化处理
        mcta_normalized = normalize_slice(mcta_slice)
        ncct_normalized = normalize_slice(ncct_slice)

        # 2. 创建空通道 (B通道)
        empty_channel = np.zeros_like(mcta_normalized)

        # 3. 创建RGB图像 [R, G, B] = [mCTA1, NCCT, 空]
        rgb_data = np.stack([mcta_normalized, ncct_normalized, empty_channel], axis=2)
        rgb_8bit = (rgb_data * 255).astype(np.uint8)

        # 4. 创建单独通道的图像（用于显示）
        mcta_8bit = (mcta_normalized * 255).astype(np.uint8)
        ncct_8bit = (ncct_normalized * 255).astype(np.uint8)

        # 创建输出路径
        slice_prefix = f'slice_{slice_idx:03d}'

        # 保存RGB合成图像
        rgb_path = os.path.join(output_dir, f'{slice_prefix}_rgb.png')
        Image.fromarray(rgb_8bit).save(rgb_path)

        # 保存单独通道图像
        mcta_path = os.path.join(output_dir, f'{slice_prefix}_mcta.png')
        ncct_path = os.path.join(output_dir, f'{slice_prefix}_ncct.png')
        Image.fromarray(mcta_8bit).save(mcta_path)
        Image.fromarray(ncct_8bit).save(ncct_path)

        # 保存NPY数据 - 直接保存RGB数组，而不是字典
        npy_path = os.path.join(output_dir, f'{slice_prefix}_data.npy')
        np.save(npy_path, rgb_data.astype(np.float32))  # 直接保存数组

        return {
            'success': True,
            'rgb_url': f'/get_image/{os.path.basename(output_dir)}/{slice_prefix}_rgb.png',
            'mcta_url': f'/get_image/{os.path.basename(output_dir)}/{slice_prefix}_mcta.png',
            'ncct_url': f'/get_image/{os.path.basename(output_dir)}/{slice_prefix}_ncct.png',
            'npy_url': f'/get_file/{os.path.basename(output_dir)}/{slice_prefix}_data.npy',
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
    """处理双文件上传 - 多模型版本"""
    try:
        print("收到上传请求...")

        if not NIBABEL_AVAILABLE:
            return jsonify({
                'success': False,
                'error': 'nibabel 库不可用。请运行: pip install "numpy<2.0" nibabel'
            })

        # 检查文件是否存在
        if 'mcta_file' not in request.files or 'ncct_file' not in request.files:
            return jsonify({'success': False, 'error': '请选择两个文件'})

        mcta_file = request.files['mcta_file']
        ncct_file = request.files['ncct_file']

        if mcta_file.filename == '' or ncct_file.filename == '':
            return jsonify({'success': False, 'error': '请选择两个文件'})

        # 检查文件格式
        valid_extensions = ['.nii', '.nii.gz']
        mcta_valid = any(mcta_file.filename.lower().endswith(ext) for ext in valid_extensions)
        ncct_valid = any(ncct_file.filename.lower().endswith(ext) for ext in valid_extensions)

        if not (mcta_valid and ncct_valid):
            return jsonify({'success': False, 'error': '请上传NIfTI文件 (.nii 或 .nii.gz)'})

        print(f"文件验证通过: {mcta_file.filename}, {ncct_file.filename}")

        # 生成唯一ID
        file_id = str(uuid.uuid4())[:8]

        # 保存上传的文件
        mcta_extension = '.nii.gz' if mcta_file.filename.lower().endswith('.nii.gz') else '.nii'
        ncct_extension = '.nii.gz' if ncct_file.filename.lower().endswith('.nii.gz') else '.nii'

        mcta_path = os.path.join(app.config['UPLOAD_FOLDER'], f'{file_id}_mcta{mcta_extension}')
        ncct_path = os.path.join(app.config['UPLOAD_FOLDER'], f'{file_id}_ncct{ncct_extension}')

        mcta_file.save(mcta_path)
        ncct_file.save(ncct_path)

        print(f"文件保存成功: {mcta_path}, {ncct_path}")

        # 创建输出目录
        output_dir = os.path.join(app.config['PROCESSED_FOLDER'], file_id)
        os.makedirs(output_dir, exist_ok=True)

        # 获取模型类型参数，默认使用mrdpm
        model_type = request.form.get('model_type', 'mrdpm')
        print(f"选择的模型类型: {model_type}")

        # 处理RGB合成（现在包含多模型AI推理）
        print("开始处理RGB合成和多模型AI推理...")
        result = process_rgb_synthesis(mcta_path, ncct_path, output_dir, model_type)

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
        print(f"🔗 局域网访问地址: http://{local_ip}:5000")
    except:
        local_ip = '0.0.0.0'
        print("⚠ 无法获取本机IP，使用默认配置")

    print("📱 本地访问地址: http://127.0.0.1:5000")
    print("🌍 服务器监听: 所有网络接口 (0.0.0.0:5000)")
    print("⏹️ 按 Ctrl+C 停止服务器")
    print("=" * 60)

    try:
        # 关键修改：使用明确的参数启动
        app.run(
            host='0.0.0.0',      # 监听所有网络接口
            port=5000,           # 明确指定端口
            debug=True,          # 调试模式
            threaded=True,       # 多线程
            use_reloader=False   # 关闭自动重载，避免重复初始化
        )
    except Exception as e:
        print(f"❌ 服务器启动失败: {e}")
        import traceback
        traceback.print_exc()