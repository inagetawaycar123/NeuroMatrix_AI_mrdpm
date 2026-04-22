import os
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from torchvision import transforms
from PIL import Image
import cv2
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# ============================================================
# 基础路径
# ============================================================

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ============================================================
# 类别定义
# ============================================================

CLASS_NAMES = [
    "无阻塞",
    "LVO",
    "MEVO"
]

# ============================================================
# 模型结构（与你训练一致）
# ============================================================

def load_backbone(weights, model_name, repo_dir):
    """加载DINOv3 backbone，避免termcolor依赖问题"""
    import sys
    
    # Mock termcolor to avoid import issues
    if 'termcolor' not in sys.modules:
        sys.modules['termcolor'] = type(sys)('mock_termcolor')
        sys.modules['termcolor'].colored = lambda text, color=None, on_color=None, attrs=None: str(text)
    
    try:
        model = torch.hub.load(
            repo_dir, 
            model_name, 
            source='local', 
            pretrained=False  # 不自动加载预训练权重
        )
        
        # 如果提供了权重文件，手动加载
        if weights and os.path.exists(weights):
            print(f"[DINOv3] Loading pretrained weights from: {weights}")
            state_dict = torch.load(weights, map_location='cpu')
            model.load_state_dict(state_dict, strict=False)
            print(f"[DINOv3] Pretrained weights loaded successfully")
        
        return model
    except Exception as e:
        print(f"[DINOv3] Loading failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


class CAMClassifier(nn.Module):
    def __init__(
        self,
        num_classes=3,
        freeze_ratio=0.35,
        weights_path=None,
        repo_dir=None,
        dropout_rate=0.35,
        head_type='mlp'
    ):
        super().__init__()

        self.model_name = 'dinov3_vitb16'
        self.backbone = load_backbone(weights_path, self.model_name, repo_dir)

        for p in self.backbone.parameters():
            p.requires_grad = False

        self.embed_dim = self.backbone.norm.normalized_shape[0]
        self.pool = nn.AdaptiveMaxPool2d((1, 1))

        self.head = nn.Sequential(
            nn.Dropout(dropout_rate),
            nn.Linear(self.embed_dim, 256),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout_rate * 0.5),
            nn.Linear(256, num_classes)
        )

    def forward(self, x, return_features=False):
        features = self.backbone.get_intermediate_layers(
            x, n=1, reshape=True,
            return_class_token=False, norm=True
        )
        features = torch.cat(features, dim=1)
        pooled = self.pool(features)[:, :, 0, 0]
        logits = self.head(pooled)
        
        if return_features:
            return logits, features
        return logits


# ============================================================
# 单例模型管理
# ============================================================

class OcclusionModelManager:

    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load(self):

        if self._model is not None:
            return self._model

        model_path = os.path.join(
            PROJECT_ROOT,
            "exp_dinov3",
            "src",
            "dinov3权重.pth"
        )

        dinov3_weights = os.path.join(
            PROJECT_ROOT,
            "exp_dinov3",
            "src",
            "ckpt",
            "dinov3_vitb16_pretrain_lvd1689m-73cec8be.pth"
        )

        repo_dir = os.path.join(PROJECT_ROOT, "exp_dinov3", "src", "dinov3")

        print("加载血管堵塞分类模型...")

        model = CAMClassifier(
            num_classes=3,
            freeze_ratio=0.35,
            weights_path=dinov3_weights,
            repo_dir=repo_dir,
            dropout_rate=0.35,
            head_type='mlp'
        ).to(DEVICE)

        checkpoint = torch.load(model_path, map_location=DEVICE)
        model.load_state_dict(checkpoint)
        model.eval()

        self._model = model

        print("[OK] Model loaded successfully")
        return model


# ============================================================
# 预处理（与训练保持一致）
# ============================================================

def build_transform():
    return transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(
            [0.485, 0.456, 0.406],
            [0.229, 0.224, 0.225]
        )
    ])


# ============================================================
# Case级 Top‑K 预测
# ============================================================

def analyze_occlusion(case_id, top_k_ratio=0.3):

    case_dir = os.path.join(
        PROJECT_ROOT,
        "static",
        "processed",
        case_id
    )

    if not os.path.exists(case_dir):
        return {"success": False, "error": "病例目录不存在"}

    # ✅ 找到所有 CTP PNG
    png_files = sorted([
        f for f in os.listdir(case_dir)
        if f.lower().endswith(".png")
    ])

    if not png_files:
        return {"success": False, "error": "未找到CTP PNG图像"}

    manager = OcclusionModelManager()
    model = manager.load()

    transform = build_transform()

    slice_results = []

    # ✅ 逐 slice 预测
    for file in png_files:

        img_path = os.path.join(case_dir, file)
        image = Image.open(img_path).convert("RGB")

        tensor = transform(image).unsqueeze(0).to(DEVICE)

        with torch.no_grad():
            output = model(tensor)
            probs = torch.softmax(output, dim=1)[0].cpu().numpy()

        max_conf = float(np.max(probs))

        slice_results.append({
            "file": file,
            "probs": probs,
            "max_conf": max_conf
        })

    # ✅ 按置信度排序
    slice_results.sort(key=lambda x: x["max_conf"], reverse=True)

    total_slices = len(slice_results)
    k = max(1, int(total_slices * top_k_ratio))

    top_slices = slice_results[:k]

    top_probs = np.array([s["probs"] for s in top_slices])

    # ✅ 加权平均（更稳）
    weights = np.array([s["max_conf"] for s in top_slices])
    weights = weights / weights.sum()

    weighted_probs = np.sum(top_probs * weights[:, None], axis=0)

    final_class = int(np.argmax(weighted_probs))

    return {
        "success": True,
        "class_id": final_class,
        "class_name": CLASS_NAMES[final_class],
        "confidence": float(weighted_probs[final_class]),
        "top_k_used": k,
        "total_slices": total_slices,
        "top_k_slices": [s["file"] for s in top_slices],
        "probabilities": {
            CLASS_NAMES[i]: float(weighted_probs[i])
            for i in range(len(CLASS_NAMES))
        }
    }


# ============================================================
# GradCAM 可视化
# ============================================================

def generate_gradcam(model, image_tensor, target_class=None):
    """
    生成基于特征图的注意力热力图（类GradCAM效果）
    
    由于DINOv3的特殊架构，我们使用特征图的方差和激活强度来生成热力图
    
    Args:
        model: CAMClassifier模型
        image_tensor: 输入图像张量 (1, 3, 224, 224)
        target_class: 目标类别索引，如果为None则使用预测的类别
    
    Returns:
        cam: 归一化的注意力热力图 (H, W)，值在0-1之间
        pred_class: 预测的类别索引
        confidence: 预测置信度
    """
    model.eval()
    
    with torch.no_grad():
        # 前向传播获取特征和预测
        logits, features = model(image_tensor, return_features=True)
        probs = F.softmax(logits, dim=1)
        pred_class = torch.argmax(probs, dim=1).item()
        confidence = probs[0, pred_class].item()
        
        # 如果没有指定目标类别，使用预测类别
        if target_class is None:
            target_class = pred_class
        
        # features shape: (1, C, H, W)
        features = features[0]  # (C, H, W)
        
        # 方法1: 计算特征图在通道维度的标准差（显示特征变化最大的区域）
        # 这些区域通常是模型关注的重点
        feature_std = torch.std(features, dim=0)  # (H, W)
        
        # 方法2: 计算特征图的绝对值均值（显示激活强度）
        feature_abs_mean = torch.mean(torch.abs(features), dim=0)  # (H, W)
        
        # 结合两种方法
        cam = (feature_std + feature_abs_mean) / 2.0
        cam = cam.cpu().numpy()
        
        # 归一化到0-1
        if cam.max() > cam.min():
            cam = (cam - cam.min()) / (cam.max() - cam.min())
        
        # 应用平滑
        cam = cv2.GaussianBlur(cam, (3, 3), 0)
        
        # 再次归一化
        if cam.max() > 0:
            cam = cam / cam.max()
        
        return cam, pred_class, confidence


def save_gradcam_visualization(image_path, cam, output_path, original_size=None):
    """
    保存GradCAM可视化结果
    
    Args:
        image_path: 原始图像路径
        cam: GradCAM热力图 (H, W)
        output_path: 输出路径
        original_size: 原始图像尺寸 (width, height)，如果为None则使用图像本身的尺寸
    """
    # 读取原始图像
    original_img = Image.open(image_path).convert("RGB")
    
    if original_size is None:
        original_size = original_img.size
    
    # 将原始图像调整到指定尺寸
    original_img = original_img.resize(original_size, Image.BILINEAR)
    original_img_np = np.array(original_img)
    
    # 将CAM调整到原始图像尺寸
    cam_resized = cv2.resize(cam, original_size, interpolation=cv2.INTER_LINEAR)
    
    # 应用颜色映射（jet colormap）
    cam_colored = plt.cm.jet(cam_resized)[:, :, :3]  # RGB
    cam_colored = (cam_colored * 255).astype(np.uint8)
    
    # 叠加到原始图像上（alpha混合）
    alpha = 0.5
    superimposed = cv2.addWeighted(
        original_img_np, 1 - alpha,
        cam_colored, alpha,
        0
    )
    
    # 保存结果
    result_img = Image.fromarray(superimposed)
    result_img.save(output_path)
    
    return output_path


def generate_case_gradcam_visualizations(case_id, top_k_ratio=0.3, output_dir=None):
    """
    为一个病例生成GradCAM可视化
    
    Args:
        case_id: 病例ID
        top_k_ratio: 使用前K%的切片
        output_dir: 输出目录，如果为None则使用默认目录
    
    Returns:
        dict: 包含可视化结果的信息
    """
    case_dir = os.path.join(
        PROJECT_ROOT,
        "static",
        "processed",
        case_id
    )
    
    if not os.path.exists(case_dir):
        return {"success": False, "error": "病例目录不存在"}
    
    # 设置输出目录
    if output_dir is None:
        output_dir = os.path.join(case_dir, "gradcam")
    
    os.makedirs(output_dir, exist_ok=True)
    
    # 找到所有CTP PNG
    png_files = sorted([
        f for f in os.listdir(case_dir)
        if f.lower().endswith(".png")
    ])
    
    if not png_files:
        return {"success": False, "error": "未找到CTP PNG图像"}
    
    manager = OcclusionModelManager()
    model = manager.load()
    
    transform = build_transform()
    
    slice_results = []
    
    # 逐slice预测和计算置信度
    for file in png_files:
        img_path = os.path.join(case_dir, file)
        image = Image.open(img_path).convert("RGB")
        tensor = transform(image).unsqueeze(0).to(DEVICE)
        
        with torch.no_grad():
            output = model(tensor)
            probs = torch.softmax(output, dim=1)[0].cpu().numpy()
        
        max_conf = float(np.max(probs))
        pred_class = int(np.argmax(probs))
        
        slice_results.append({
            "file": file,
            "probs": probs,
            "max_conf": max_conf,
            "pred_class": pred_class
        })
    
    # 按置信度排序
    slice_results.sort(key=lambda x: x["max_conf"], reverse=True)
    
    total_slices = len(slice_results)
    k = max(1, int(total_slices * top_k_ratio))
    
    # 选择top-k切片生成GradCAM
    top_slices = slice_results[:k]
    
    gradcam_files = []
    
    for idx, slice_info in enumerate(top_slices[:3]):  # 只为前3个最高置信度的切片生成GradCAM
        try:
            file = slice_info["file"]
            img_path = os.path.join(case_dir, file)
            
            print(f"[GradCAM] Processing slice {idx+1}/3: {file}")
            
            # 加载图像
            image = Image.open(img_path).convert("RGB")
            original_size = image.size
            
            tensor = transform(image).unsqueeze(0).to(DEVICE)
            
            # 生成GradCAM
            cam, pred_class, confidence = generate_gradcam(model, tensor)
            
            print(f"[GradCAM] Generated CAM for {file}, class={CLASS_NAMES[pred_class]}, conf={confidence:.3f}")
            
            # 保存可视化
            output_filename = f"gradcam_{file}"
            output_path = os.path.join(output_dir, output_filename)
            
            save_gradcam_visualization(
                img_path,
                cam,
                output_path,
                original_size=original_size
            )
            
            print(f"[GradCAM] Saved to {output_path}")
            
            gradcam_files.append({
                "original": file,
                "gradcam": output_filename,
                "class": CLASS_NAMES[pred_class],
                "confidence": confidence
            })
        except Exception as e:
            print(f"[WARN] Failed to generate GradCAM for {file}: {str(e)}")
            import traceback
            traceback.print_exc()
            # 继续处理下一个切片
    
    # 获取整体预测结果
    top_probs = np.array([s["probs"] for s in top_slices])
    weights = np.array([s["max_conf"] for s in top_slices])
    weights = weights / weights.sum()
    weighted_probs = np.sum(top_probs * weights[:, None], axis=0)
    final_class = int(np.argmax(weighted_probs))
    
    return {
        "success": True,
        "class_id": final_class,
        "class_name": CLASS_NAMES[final_class],
        "confidence": float(weighted_probs[final_class]),
        "gradcam_visualizations": gradcam_files,
        "output_dir": output_dir,
        "total_slices": total_slices,
        "top_k_used": k
    }