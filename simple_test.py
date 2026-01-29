import torch
import numpy as np
import os
import sys

# 添加mrdpm目录到Python路径
mrdpm_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mrdpm')
sys.path.insert(0, mrdpm_path)

# 从mrdpm模块导入define_G函数
try:
    from models.networks_unet256 import define_G
except ImportError:
    print("Error: Failed to import define_G from mrdpm.models.networks_unet256")
    print("Current sys.path:", sys.path)
    raise

def load_test_input():
    """加载测试输入图像"""
    test_input = torch.randn(1, 3, 256, 256)
    return test_input

def load_ema_initial_weights(network, weights_path):
    """从200_Network_ema.pth中提取并加载initial_net权重"""
    if not os.path.exists(weights_path):
        raise FileNotFoundError(f"Weight file not found: {weights_path}")
    
    weights = torch.load(weights_path, map_location='cpu')
    print(f"Loaded EMA weights with {len(weights)} keys")
    
    # 提取initial_net部分的权重
    initial_net_weights = {}
    for key, value in weights.items():
        if key.startswith('initial_net.'):
            new_key = key[12:]
            initial_net_weights[new_key] = value
    
    print(f"Extracted initial_net weights with {len(initial_net_weights)} keys")
    
    # 加载权重到网络
    network.load_state_dict(initial_net_weights)
    return network

def test_forward_pass(network, input_data):
    """测试前向传播"""
    print("\n=== Testing Forward Pass ===")
    
    network.eval()
    with torch.no_grad():
        # 检查输入数据
        print(f"Input shape: {input_data.shape}")
        print(f"Input has NaN: {torch.isnan(input_data).any()}")
        
        # 访问encoder
        encoder = network.encoder
        
        # 手动执行前向传播
        d1x = encoder.down1x(input_data)
        print(f"d1x has NaN: {torch.isnan(d1x).any()}")
        
        d1_input = torch.cat((input_data, d1x), 1)
        d1 = encoder.down1(d1_input)
        print(f"d1 has NaN: {torch.isnan(d1).any()}")
        
        d2x = encoder.down2x(d1)
        print(f"d2x has NaN: {torch.isnan(d2x).any()}")
        
        d2_input = torch.cat((d1, d2x), 1)
        d2 = encoder.down2(d2_input)
        print(f"d2 has NaN: {torch.isnan(d2).any()}")
        
        d3x = encoder.down3x(d2)
        print(f"d3x has NaN: {torch.isnan(d3x).any()}")
        
        d3_input = torch.cat((d2, d3x), 1)
        d3 = encoder.down3(d3_input)
        print(f"d3 has NaN: {torch.isnan(d3).any()}")
        
        d4x = encoder.down4x(d3)
        print(f"d4x has NaN: {torch.isnan(d4x).any()}")
        
        d4_input = torch.cat((d3, d4x), 1)
        d4 = encoder.down4(d4_input)
        print(f"d4 has NaN: {torch.isnan(d4).any()}")
        
        d5x = encoder.down5x(d4)
        print(f"d5x has NaN: {torch.isnan(d5x).any()}")
        
        d5_input = torch.cat((d4, d5x), 1)
        d5 = encoder.down5(d5_input)
        print(f"d5 has NaN: {torch.isnan(d5).any()}")
        
        d6x = encoder.down6x(d5)
        print(f"d6x has NaN: {torch.isnan(d6x).any()}")
        print(f"d6x min: {d6x.min().item()}, max: {d6x.max().item()}, mean: {d6x.mean().item()}")
        
        d6_input = torch.cat((d5, d6x), 1)
        d6 = encoder.down6(d6_input)
        print(f"d6 has NaN: {torch.isnan(d6).any()}")
        print(f"d6 min: {d6.min().item()}, max: {d6.max().item()}, mean: {d6.mean().item()}")
        print(f"d6 shape: {d6.shape}")
        
        d7x = encoder.down7x(d6)
        print(f"d7x has NaN: {torch.isnan(d7x).any()}")
        print(f"d7x min: {d7x.min().item()}, max: {d7x.max().item()}, mean: {d7x.mean().item()}")
        
        d7_input = torch.cat((d6, d7x), 1)
        d7 = encoder.down7(d7_input)
        print(f"d7 has NaN: {torch.isnan(d7).any()}")
        print(f"d7 min: {d7.min().item()}, max: {d7.max().item()}, mean: {d7.mean().item()}")
        print(f"d7 shape: {d7.shape}")
        
        # 检查down8x的权重
        print("\n=== Checking down8x Weights ===")
        down8x = encoder.down8x
        for name, param in down8x.named_parameters():
            print(f"{name} has NaN: {torch.isnan(param).any()}")
            print(f"{name} min: {param.min().item()}, max: {param.max().item()}, mean: {param.mean().item()}")
        
        d8x = encoder.down8x(d7)
        print(f"\nd8x has NaN: {torch.isnan(d8x).any()}")
        if torch.isnan(d8x).any():
            print(f"d8x min: {d8x.min().item()}, max: {d8x.max().item()}, mean: {d8x.mean().item()}")
        
        d8_input = torch.cat((d7, d8x), 1)
        d8 = encoder.down8(d8_input)
        print(f"d8 has NaN: {torch.isnan(d8).any()}")
        
        # 执行decoder
        u1 = network.up1(d8, d7)
        print(f"u1 has NaN: {torch.isnan(u1).any()}")
        
        u2 = network.up2(u1, d6)
        print(f"u2 has NaN: {torch.isnan(u2).any()}")
        
        u3 = network.up3(u2, d5)
        print(f"u3 has NaN: {torch.isnan(u3).any()}")
        
        u4 = network.up4(u3, d4)
        print(f"u4 has NaN: {torch.isnan(u4).any()}")
        
        u5 = network.up5(u4, d3)
        print(f"u5 has NaN: {torch.isnan(u5).any()}")
        
        u6 = network.up6(u5, d2)
        print(f"u6 has NaN: {torch.isnan(u6).any()}")
        
        u7 = network.up7(u6, d1)
        print(f"u7 has NaN: {torch.isnan(u7).any()}")
        
        u8 = network.up8(u7, input_data)
        print(f"u8 has NaN: {torch.isnan(u8).any()}")
        
        return u8

def main():
    """主函数"""
    print("=== Simple Test for EMA Weights ===")
    
    # 加载测试输入
    test_input = load_test_input()
    print(f"Test input shape: {test_input.shape}")
    
    # 定义网络
    net = define_G(3, 1, 32, use_dropout=True, init_type='kaiming', gpu_ids=[])
    print("Network defined successfully")
    
    # 加载EMA权重文件
    ema_weights_path = os.path.join(mrdpm_path, 'weights', 'cbf', '200_Network_ema.pth')
    print(f"EMA weights path: {ema_weights_path}")
    
    if not os.path.exists(ema_weights_path):
        raise FileNotFoundError(f"EMA weights file not found: {ema_weights_path}")
    
    # 加载权重
    net = load_ema_initial_weights(net, ema_weights_path)
    print("Loaded initial_net weights from EMA file")
    
    # 测试前向传播
    output = test_forward_pass(net, test_input)
    print(f"Final output has NaN: {torch.isnan(output).any()}")

if __name__ == "__main__":
    main()
