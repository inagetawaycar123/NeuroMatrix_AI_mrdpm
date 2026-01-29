import torch
import numpy as np
import os
import sys

# 添加mrdpm目录到Python路径
mrdpm_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mrdpm')
sys.path.insert(0, mrdpm_path)

def check_ema_weights():
    """检查200_Network_ema.pth权重文件"""
    print("=== Checking EMA Weights ===")
    
    # 加载EMA权重文件
    ema_weights_path = os.path.join(mrdpm_path, 'weights', 'cbf', '200_Network_ema.pth')
    print(f"EMA weights path: {ema_weights_path}")
    
    if not os.path.exists(ema_weights_path):
        raise FileNotFoundError(f"Weight file not found: {ema_weights_path}")
    
    weights = torch.load(ema_weights_path, map_location='cpu')
    print(f"Loaded EMA weights with {len(weights)} keys")
    
    # 提取initial_net部分的权重
    initial_net_weights = {}
    for key, value in weights.items():
        if key.startswith('initial_net.'):
            initial_net_weights[key] = value
    
    print(f"Found {len(initial_net_weights)} initial_net keys")
    
    # 检查initial_net权重是否有NaN值
    has_nan = False
    print("\n=== Checking Initial Net Weights ===")
    for key, value in initial_net_weights.items():
        if torch.isnan(value).any():
            print(f"❌ NaN found in: {key}")
            has_nan = True
        elif torch.isinf(value).any():
            print(f"❌ Inf found in: {key}")
            has_nan = True
    
    if not has_nan:
        print("✅ No NaN or Inf values found in initial_net weights")
    
    # 检查denoise_fn部分的权重
    denoise_fn_weights = {}
    for key, value in weights.items():
        if key.startswith('denoise_fn.'):
            denoise_fn_weights[key] = value
    
    print(f"\nFound {len(denoise_fn_weights)} denoise_fn keys")
    
    # 检查denoise_fn权重是否有NaN值
    has_nan_denoise = False
    print("\n=== Checking Denoise Fn Weights ===")
    for key, value in denoise_fn_weights.items():
        if torch.isnan(value).any():
            print(f"❌ NaN found in: {key}")
            has_nan_denoise = True
        elif torch.isinf(value).any():
            print(f"❌ Inf found in: {key}")
            has_nan_denoise = True
    
    if not has_nan_denoise:
        print("✅ No NaN or Inf values found in denoise_fn weights")
    
    # 检查BRAN权重文件
    print("\n=== Checking BRAN Weights ===")
    bran_weights_path = os.path.join(mrdpm_path, 'weights', 'cbf', 'bran_pretrained_3channel.pth')
    print(f"BRAN weights path: {bran_weights_path}")
    
    if not os.path.exists(bran_weights_path):
        raise FileNotFoundError(f"Weight file not found: {bran_weights_path}")
    
    bran_weights = torch.load(bran_weights_path, map_location='cpu')
    print(f"Loaded BRAN weights with {len(bran_weights)} keys")
    
    # 检查BRAN权重是否有NaN值
    has_nan_bran = False
    for key, value in bran_weights.items():
        if torch.isnan(value).any():
            print(f"❌ NaN found in: {key}")
            has_nan_bran = True
        elif torch.isinf(value).any():
            print(f"❌ Inf found in: {key}")
            has_nan_bran = True
    
    if not has_nan_bran:
        print("✅ No NaN or Inf values found in BRAN weights")

if __name__ == "__main__":
    check_ema_weights()
