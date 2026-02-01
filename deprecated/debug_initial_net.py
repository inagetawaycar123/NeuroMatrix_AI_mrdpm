import torch
import numpy as np
import os
import sys

# 添加mrdpm目录到Python路径
mrdpm_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mrdpm')
sys.path.insert(0, mrdpm_path)

# 从mrdpm模块导入define_G函数
try:
    from models.network import define_G
except ImportError:
    print("Error: Failed to import define_G from mrdpm.models.network")
    print("Current sys.path:", sys.path)
    raise

def load_test_input():
    """加载测试输入图像"""
    test_input = torch.randn(1, 3, 256, 256)
    return test_input

def load_bran_weights(network, weights_path):
    """加载bran_pretrained_3channel.pth权重"""
    if not os.path.exists(weights_path):
        raise FileNotFoundError(f"Weight file not found: {weights_path}")
    
    weights = torch.load(weights_path, map_location='cpu')
    print(f"Loaded BRAN weights with {len(weights)} keys")
    
    # 加载权重到网络
    network.load_state_dict(weights)
    return network

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

def debug_forward_pass(network, input_data):
    """调试前向传播，检查每一层的输出"""
    print("\n=== Debugging Forward Pass ===")
    
    # 保存原始的forward方法
    original_forward = network.forward
    
    # 定义一个包装的forward方法，用于调试
    def debug_forward(x):
        print(f"Input shape: {x.shape}")
        print(f"Input has NaN: {torch.isnan(x).any()}")
        print(f"Input min: {x.min().item()}, max: {x.max().item()}, mean: {x.mean().item()}")
        
        # 检查encoder的前向传播
        print("\n--- Encoder ---\n")
        
        # 访问encoder
        encoder = network.encoder
        
        # 检查down1x
        d1x = encoder.down1x(x)
        print(f"d1x shape: {d1x.shape}")
        print(f"d1x has NaN: {torch.isnan(d1x).any()}")
        print(f"d1x min: {d1x.min().item()}, max: {d1x.max().item()}, mean: {d1x.mean().item()}")
        
        # 检查down1
        d1_input = torch.cat((x, d1x), 1)
        print(f"d1_input shape: {d1_input.shape}")
        print(f"d1_input has NaN: {torch.isnan(d1_input).any()}")
        
        d1 = encoder.down1(d1_input)
        print(f"d1 shape: {d1.shape}")
        print(f"d1 has NaN: {torch.isnan(d1).any()}")
        print(f"d1 min: {d1.min().item()}, max: {d1.max().item()}, mean: {d1.mean().item()}")
        
        # 检查down2x
        d2x = encoder.down2x(d1)
        print(f"d2x shape: {d2x.shape}")
        print(f"d2x has NaN: {torch.isnan(d2x).any()}")
        print(f"d2x min: {d2x.min().item()}, max: {d2x.max().item()}, mean: {d2x.mean().item()}")
        
        # 检查down2
        d2_input = torch.cat((d1, d2x), 1)
        print(f"d2_input shape: {d2_input.shape}")
        print(f"d2_input has NaN: {torch.isnan(d2_input).any()}")
        
        d2 = encoder.down2(d2_input)
        print(f"d2 shape: {d2.shape}")
        print(f"d2 has NaN: {torch.isnan(d2).any()}")
        print(f"d2 min: {d2.min().item()}, max: {d2.max().item()}, mean: {d2.mean().item()}")
        
        # 继续检查其他层...
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
        
        d6_input = torch.cat((d5, d6x), 1)
        d6 = encoder.down6(d6_input)
        print(f"d6 has NaN: {torch.isnan(d6).any()}")
        
        d7x = encoder.down7x(d6)
        print(f"d7x has NaN: {torch.isnan(d7x).any()}")
        
        d7_input = torch.cat((d6, d7x), 1)
        d7 = encoder.down7(d7_input)
        print(f"d7 has NaN: {torch.isnan(d7).any()}")
        
        d8x = encoder.down8x(d7)
        print(f"d8x has NaN: {torch.isnan(d8x).any()}")
        
        d8_input = torch.cat((d7, d8x), 1)
        d8 = encoder.down8(d8_input)
        print(f"d8 has NaN: {torch.isnan(d8).any()}")
        
        # 检查decoder的前向传播
        print("\n--- Decoder ---\n")
        
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
        
        u8 = network.up8(u7, x)
        print(f"u8 has NaN: {torch.isnan(u8).any()}")
        
        hs = []
        hs.append(u7)
        hs.append(u6)
        hs.append(u5)
        
        return u8, hs
    
    # 替换forward方法
    network.forward = debug_forward
    
    # 执行前向传播
    output = network(input_data)
    
    # 恢复原始的forward方法
    network.forward = original_forward
    
    return output

def main():
    """主调试函数"""
    print("=== Debugging Initial Net ===")
    
    # 加载测试输入
    test_input = load_test_input()
    print(f"Test input shape: {test_input.shape}")
    
    # 场景1：使用bran_pretrained_3channel.pth
    print("\n=== Scenario 1: Using bran_pretrained_3channel.pth ===")
    bran_weights_path = os.path.join(mrdpm_path, 'weights', 'cbf', 'bran_pretrained_3channel.pth')
    network1 = define_G(3, 1, 32, use_dropout=True, init_type='kaiming', gpu_ids=[])
    network1 = load_bran_weights(network1, bran_weights_path)
    print("\nForward pass with BRAN weights:")
    output1 = debug_forward_pass(network1, test_input)
    print(f"\nFinal output has NaN: {torch.isnan(output1[0]).any()}")
    
    # 场景2：使用200_Network_ema.pth中的initial_net
    print("\n=== Scenario 2: Using initial_net from 200_Network_ema.pth ===")
    ema_weights_path = os.path.join(mrdpm_path, 'weights', 'cbf', '200_Network_ema.pth')
    network2 = define_G(3, 1, 32, use_dropout=True, init_type='kaiming', gpu_ids=[])
    network2 = load_ema_initial_weights(network2, ema_weights_path)
    print("\nForward pass with EMA initial_net weights:")
    output2 = debug_forward_pass(network2, test_input)
    print(f"\nFinal output has NaN: {torch.isnan(output2[0]).any()}")

if __name__ == "__main__":
    main()
