import os
import torch
import torch.nn as nn
import numpy as np
from torchvision import transforms
from PIL import Image

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

    def forward(self, x):
        features = self.backbone.get_intermediate_layers(
            x, n=1, reshape=True,
            return_class_token=False, norm=True
        )
        features = torch.cat(features, dim=1)
        pooled = self.pool(features)[:, :, 0, 0]
        return self.head(pooled)


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

        print("✓ 模型加载完成")
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