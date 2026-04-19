import os
import torch
import torch.nn as nn
from torchvision import transforms
from PIL import Image
import numpy as np

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")


# ============================================================
#  模型定义 (与训练时保持一致)
# ============================================================
def load_model(weights, model_name, repo_dir):
    if weights and not os.path.exists(weights):
        raise FileNotFoundError(f"权重文件不存在: {weights}")
    if not os.path.exists(repo_dir):
        raise FileNotFoundError(f"模型目录不存在: {repo_dir}")
    return torch.hub.load(repo_dir, model_name, source='local', weights=weights)


class CAMClassifier(nn.Module):
    def __init__(self, num_classes=3, freeze_ratio=0.75, weights_path=None,
                 repo_dir='dinov3', dropout_rate=0.0, head_type='simple'):
        super().__init__()
        self.model_name = 'dinov3_vitb16'
        self.backbone = load_model(weights_path, self.model_name, repo_dir)

        for p in self.backbone.parameters():
            p.requires_grad = False

        total_blocks = len(self.backbone.blocks)
        block_params = [(i, sum(p.numel() for p in blk.parameters()))
                        for i, blk in enumerate(self.backbone.blocks)]
        total_params = sum(p for _, p in block_params)
        target_train = total_params * (1 - freeze_ratio)

        cumsum, unfreeze_start = 0, total_blocks
        for idx in reversed(range(total_blocks)):
            cumsum += block_params[idx][1]
            unfreeze_start = idx
            if cumsum >= target_train:
                break

        for blk_idx in range(unfreeze_start, total_blocks):
            for p in self.backbone.blocks[blk_idx].parameters():
                p.requires_grad = True

        self.embed_dim = self.backbone.norm.normalized_shape[0]
        self.feature_extractor_layers = 1
        self.pool = nn.AdaptiveMaxPool2d((1, 1))
        self.last_conv_features = None

        if head_type == 'mlp':
            self.head = nn.Sequential(
                nn.Dropout(p=dropout_rate),
                nn.Linear(self.embed_dim, 256),
                nn.ReLU(inplace=True),
                nn.Dropout(p=dropout_rate * 0.5),
                nn.Linear(256, num_classes)
            )
        else:
            self.head = nn.Sequential(
                nn.Dropout(p=dropout_rate),
                nn.Linear(self.embed_dim, num_classes)
            )

    def forward_features(self, x):
        features = self.backbone.get_intermediate_layers(
            x, n=self.feature_extractor_layers, reshape=True,
            return_class_token=False, norm=True)
        features = torch.cat(features, dim=1)
        self.last_conv_features = features
        return features

    def forward(self, x):
        features = self.forward_features(x)
        pooled = self.pool(features)[:, :, 0, 0]
        return self.head(pooled)


# ============================================================
#  模型加载器（单例模式，避免重复加载）
# ============================================================
class ModelManager:
    """管理模型的加载与复用，避免每次预测都重新加载"""

    _instance = None  # 单例实例
    _model = None     # 已加载的模型

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load(
        self,
        model_path: str,
        dinov3_weights: str,
        repo_dir: str,
        num_classes: int = 3,
        freeze_ratio: float = 0.35,
        dropout_rate: float = 0.35,
        head_type: str = 'mlp',
    ) -> "CAMClassifier":
        """
        加载模型权重，返回已加载的模型。
        若模型已加载（路径相同），直接返回缓存模型。
        """
        # 若已加载相同路径的模型，直接返回
        if self._model is not None and self._loaded_path == model_path:
            print("✓ 使用已缓存的模型")
            return self._model

        print(f"正在加载模型: {model_path}")

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"模型文件不存在: {model_path}")

        model = CAMClassifier(
            num_classes=num_classes,
            freeze_ratio=freeze_ratio,
            weights_path=dinov3_weights,
            repo_dir=repo_dir,
            dropout_rate=dropout_rate,
            head_type=head_type,
        ).to(device)

        checkpoint = torch.load(model_path, map_location=device)
        model.load_state_dict(checkpoint)
        model.eval()

        self._model = model
        self._loaded_path = model_path
        print("✓ 模型加载成功\n")
        return model


# ============================================================
#  图像预处理
# ============================================================
def build_transform() -> transforms.Compose:
    """与训练时验证集保持一致的预处理流程"""
    return transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406],
                             [0.229, 0.224, 0.225]),
    ])


def load_image(image_path: str) -> torch.Tensor:
    """
    读取单张图片并转换为模型输入张量。

    Args:
        image_path: 图片文件路径

    Returns:
        shape 为 (1, 3, 224, 224) 的张量
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"图片文件不存在: {image_path}")

    image = Image.open(image_path).convert('RGB')
    transform = build_transform()
    tensor = transform(image)          # (3, 224, 224)
    tensor = tensor.unsqueeze(0)       # (1, 3, 224, 224)
    return tensor


# ============================================================
#  单张图片预测（核心函数）
# ============================================================
def predict_single_image(
    image_path: str,
    model_path: str,
    dinov3_weights: str = (
        'src/ckpt/dinov3_vitb16_pretrain_lvd1689m-73cec8be.pth'
    ),
    repo_dir: str = (
        'src/dinov3'
    ),
    num_classes: int = 3,
    freeze_ratio: float = 0.35,
    dropout_rate: float = 0.35,
    head_type: str = 'mlp',
    class_names: list = None,
    verbose: bool = True,
) -> dict:
    """
    对单张图片执行分类预测。

    Args:
        image_path   : 待预测图片的路径
        model_path   : 训练好的模型权重路径 (.pth)
        dinov3_weights: DINOv3 预训练权重路径
        repo_dir     : DINOv3 模型仓库目录
        num_classes  : 分类数量
        freeze_ratio : 冻结比例（需与训练时一致）
        dropout_rate : Dropout 率（需与训练时一致）
        head_type    : 分类头类型（需与训练时一致）
        class_names  : 类别名称列表
        verbose      : 是否打印详细信息

    Returns:
        result (dict):
            - image_path      : 图片路径
            - predicted_class : 预测类别索引 (int)
            - predicted_label : 预测类别名称 (str)
            - confidence      : 最高类别的置信度 (float)
            - probabilities   : 各类别概率字典 {label: prob}

    Example:
        result = predict_single_image(
            image_path  = '/data/images/sample.png',
            model_path  = '/data/models/best_model.pth',
        )
        print(result['predicted_label'])   # e.g. 'Class_1_LVO'
        print(result['confidence'])        # e.g. 0.9231
    """
    if class_names is None:
        class_names = ['Class_0', 'Class_1_LVO', 'Class_2_MEVO']

    # ---------- 1. 加载模型（带缓存） ----------
    manager = ModelManager()
    model = manager.load(
        model_path=model_path,
        dinov3_weights=dinov3_weights,
        repo_dir=repo_dir,
        num_classes=num_classes,
        freeze_ratio=freeze_ratio,
        dropout_rate=dropout_rate,
        head_type=head_type,
    )

    # ---------- 2. 加载并预处理图片 ----------
    image_tensor = load_image(image_path).to(device)  # (1, 3, 224, 224)

    # ---------- 3. 推理 ----------
    with torch.no_grad():
        output = model(image_tensor)                  # (1, num_classes)
        probs  = torch.softmax(output, dim=1)[0]      # (num_classes,)
        pred_idx = torch.argmax(probs).item()

    # ---------- 4. 整理结果 ----------
    result = {
        'image_path'      : image_path,
        'predicted_class' : pred_idx,
        'predicted_label' : class_names[pred_idx],
        'confidence'      : probs[pred_idx].item(),
        'probabilities'   : {
            class_names[j]: probs[j].item()
            for j in range(len(class_names))
        },
    }

    # ---------- 5. 打印输出 ----------
    if verbose:
        _print_result(result)

    return result


# ============================================================
#  格式化打印
# ============================================================
def _print_result(result: dict) -> None:
    """美观地打印单张图片的预测结果"""
    sep = "=" * 50
    print(sep)
    print("  单图预测结果")
    print(sep)
    print(f"  图片路径  : {result['image_path']}")
    print(f"  预测类别  : {result['predicted_label']}")
    print(f"  类别索引  : {result['predicted_class']}")
    print(f"  置信度    : {result['confidence']:.4f} "
          f"({result['confidence'] * 100:.2f}%)")
    print()
    print("  各类别概率:")
    print("  " + "-" * 35)
    for label, prob in result['probabilities'].items():
        bar = "█" * int(prob * 20)          # 简易进度条
        marker = " ◀ 预测" if label == result['predicted_label'] else ""
        print(f"  {label:<20s}: {prob:.4f}  {bar}{marker}")
    print(sep)


# ============================================================
#  直接运行入口
# ============================================================
if __name__ == '__main__':
    # ===== 在这里修改路径即可 =====
    IMAGE_PATH  = '/data/jrz/project02_mevo_ctp/exp_dinov3/src/dataset01-tmax_qc/sample.png'
    MODEL_PATH  = 'src/model_fold5.pth'
    # ==============================

    result = predict_single_image(
        image_path=IMAGE_PATH,
        model_path=MODEL_PATH,
    )

    # 也可以直接访问返回值中的字段
    print(f"\n最终预测: {result['predicted_label']}  (置信度 {result['confidence']:.4f})")