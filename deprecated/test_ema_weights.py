import torch
import numpy as np
import os
import sys

# 添加mrdpm目录到Python路径
mrdpm_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mrdpm')
sys.path.insert(0, mrdpm_path)

# 从mrdpm模块导入define_G函数
try:
    from mrdpm.models.network import define_G
except ImportError:
    print("Error: Failed to import define_G from mrdpm.models.network")
    print("Current sys.path:", sys.path)
    raise

def load_test_input():
    """加载测试输入图像"""
    test_input = torch.randn(1, 3, 256, 256)
    return test_input

def test_ema_weights():
    """测试EMA权重文件中的initial_net权重"""
    print("=== Testing EMA Weights ===")
    
    # 加载测试输入
    test_input = load_test_input()
    print(f"Test input shape: {test_input.shape}")
    
    # 定义网络
    net = define_G(3, 1, 32, use_dropout=True, init_type='kaiming', gpu_ids=[])
    print("Network defined successfully")
    
    # 加载EMA权重文件
    ema_weights_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'weights', 'cbf', '200_Network_ema.pth')
    if not os.path.exists(ema_weights_path):
        # 尝试其他路径
        ema_weights_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'weights', 'cbf', '200_Network_ema.pth')
    
    print(f"EMA weights path: {ema_weights_path}")
    
    if not os.path.exists(ema_weights_path):
        raise FileNotFoundError(f"EMA weights file not found: {ema_weights_path}")
    
    # 加载权重
    weights = torch.load(ema_weights_path, map_location='cpu')
    print(f"Loaded EMA weights with {len(weights)} keys")
    
    # 提取initial_net权重
    initial_net_weights = {}
    for key, value in weights.items():
        if key.startswith('initial_net.'):
            new_key = key[11:]  # 移除'initial_net.'前缀
            initial_net_weights[new_key] = value
    
    print(f"Extracted initial_net weights with {len(initial_net_weights)} keys")
    
    # 加载权重到网络
    net.load_state_dict(initial_net_weights)
    print("Loaded initial_net weights from EMA file")
    
    # 测试前向传播
    net.eval()
    with torch.no_grad():
        output = net(test_input)
        print(f"Forward pass output shape: {output.shape}")
        print(f"Output has NaN: {torch.isnan(output).any()}")
        print(f"Output min: {output.min().item()}, max: {output.max().item()}, mean: {output.mean().item()}")

if __name__ == "__main__":
    test_ema_weights()
