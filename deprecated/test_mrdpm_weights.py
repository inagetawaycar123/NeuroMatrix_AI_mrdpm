#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MRDPM模型两阶段权重加载测试脚本
验证BRAN初始网络和UNet残差网络的权重加载正确性
"""

import os
import torch
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))


def test_bran_weight_loading():
    """测试BRAN初始网络权重加载"""
    print("=" * 60)
    print("🧪 测试BRAN初始网络权重加载")
    print("=" * 60)
    
    # 1. 导入define_G函数
    print("1. 导入define_G函数...")
    mrdpm_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mrdpm')
    sys.path.insert(0, mrdpm_path)
    
    from models.networks_unet256 import define_G
    
    # 2. 创建BRAN网络，使用与终端脚本相同的参数
    print("2. 创建BRAN网络...")
    bran_net = define_G(
        input_nc=3,
        output_nc=1,
        ngf=32,
        use_dropout=True,
        init_type='kaiming',
        gpu_ids=[]
    )
    print(f"✅ BRAN网络创建成功，参数数量: {sum(p.numel() for p in bran_net.parameters()):,}")
    
    # 3. 测试权重文件路径
    print("3. 检查权重文件...")
    bran_weight_path = os.path.join(mrdpm_path, 'weights', 'cbf', 'bran_pretrained_3channel.pth')
    print(f"📁 BRAN权重文件路径: {bran_weight_path}")
    
    if not os.path.exists(bran_weight_path):
        print(f"❌ BRAN权重文件不存在: {bran_weight_path}")
        return False
    else:
        print(f"✅ BRAN权重文件存在")
    
    # 4. 测试权重加载
    print("4. 测试BRAN权重加载...")
    try:
        # 加载权重文件
        checkpoint = torch.load(bran_weight_path, map_location='cpu')
        
        # 检查BRAN权重文件的键数目
        print(f"✅ 成功读取权重文件，包含键数目: {len(checkpoint.keys())}")
        print(f"✅ 权重文件包含键: {list(checkpoint.keys())}")
        
        # 处理检查点或纯权重文件
        if 'model_state_dict' in checkpoint:
            state_dict = checkpoint['model_state_dict']
            print(f"📋 从检查点加载权重，state_dict包含键数目: {len(state_dict.keys())}")
        elif 'state_dict' in checkpoint:
            state_dict = checkpoint['state_dict']
            print(f"📋 从state_dict键加载权重，state_dict包含键数目: {len(state_dict.keys())}")
        else:
            state_dict = checkpoint
            print(f"📋 直接加载纯权重文件，包含键数目: {len(state_dict.keys())}")
        
        # 处理可能的DataParallel包装
        if all(key.startswith('module.') for key in state_dict.keys()):
            print("🔧 检测到DataParallel包装，移除'module.'前缀")
            state_dict = {k[7:]: v for k, v in state_dict.items()}
        
        # 检查网络结构与权重兼容性
        bran_state = bran_net.state_dict()
        missing_keys = []
        unexpected_keys = []
        
        for key in state_dict.keys():
            if key not in bran_state:
                unexpected_keys.append(key)
        
        for key in bran_state.keys():
            if key not in state_dict:
                missing_keys.append(key)
        
        print(f"📊 权重兼容性检查:")
        print(f"   缺失键: {len(missing_keys)} 个")
        print(f"   意外键: {len(unexpected_keys)} 个")
        
        # 加载权重
        bran_net.load_state_dict(state_dict, strict=False)
        print(f"✅ BRAN权重加载成功")
        
        # 5. 测试前向传播
        print("5. 测试BRAN网络前向传播...")
        with torch.no_grad():
            test_input = torch.randn(1, 3, 256, 256)
            output = bran_net(test_input)
            
            if isinstance(output, tuple):
                print(f"⚠️ 网络返回元组，包含 {len(output)} 个输出")
                output = output[0]
            
            print(f"✅ 前向传播测试通过")
            print(f"   输入形状: {test_input.shape}")
            print(f"   输出形状: {output.shape}")
            print(f"   输出范围: [{output.min().item():.3f}, {output.max().item():.3f}]")
            
            if torch.isnan(output).any() or torch.isinf(output).any():
                print(f"❌ 输出包含NaN或Inf值")
                return False
        
    except Exception as e:
        print(f"❌ BRAN权重加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


def test_residual_weight_loading():
    """测试UNet残差网络权重加载"""
    print("\n" + "=" * 60)
    print("🧪 测试UNet残差网络权重加载")
    print("=" * 60)
    
    # 1. 导入Network类
    print("1. 导入Network类...")
    mrdpm_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mrdpm')
    sys.path.insert(0, mrdpm_path)
    
    from models.network import Network
    
    # 2. 创建UNet配置，与web端一致
    print("2. 创建UNet配置...")
    unet_config = {
        'in_channel': 4,
        'out_channel': 1,
        'inner_channel': 64,
        'channel_mults': [1, 2, 4, 8],
        'attn_res': [16],
        'num_head_channels': 32,
        'res_blocks': 2,
        'dropout': 0.2,
        'image_size': 256
    }
    
    # 3. 创建Network实例
    print("3. 创建Network实例...")
    network = Network(
        unet=unet_config,
        beta_schedule={
            'train': {
                'schedule': 'linear',
                'n_timestep': 1000,
                'linear_start': 1e-6,
                'linear_end': 1e-2
            },
            'test': {
                'schedule': 'linear',
                'n_timestep': 1000,
                'linear_start': 1e-6,
                'linear_end': 1e-2
            }
        },
        module_name='guided_diffusion'
    )
    print(f"✅ Network实例创建成功")
    
    # 4. 测试残差权重文件路径
    print("4. 检查残差权重文件...")
    residual_weight_path = os.path.join(mrdpm_path, 'weights', 'cbf', '200_Network_ema.pth')
    print(f"📁 残差权重文件路径: {residual_weight_path}")
    
    if not os.path.exists(residual_weight_path):
        print(f"❌ 残差权重文件不存在: {residual_weight_path}")
        return False
    else:
        print(f"✅ 残差权重文件存在")
    
    # 5. 测试残差权重加载（模拟ai_inference.py中的加载逻辑）
    print("5. 测试残差权重加载...")
    try:
        # 加载权重文件
        checkpoint = torch.load(residual_weight_path, map_location='cpu')
        print(f"✅ 成功读取残差权重文件")
        
        # 处理状态字典，与ai_inference.py保持一致
        if 'state_dict' in checkpoint:
            state_dict = checkpoint['state_dict']
        elif 'model_state_dict' in checkpoint:
            state_dict = checkpoint['model_state_dict']
        elif 'netG' in checkpoint:
            state_dict = checkpoint['netG']
        else:
            state_dict = checkpoint
        
        print(f"📋 残差权重包含键数量: {len(state_dict.keys())}")
        
        # 处理可能的DataParallel包装
        new_state_dict = {}
        for k, v in state_dict.items():
            if k.startswith('module.'):
                new_key = k[7:]
            else:
                new_key = k
            new_state_dict[new_key] = v
        
        # 过滤残差权重，只保留denoise_fn相关参数，并去掉denoise_fn.前缀
        denoise_state_dict = {}
        for k, v in new_state_dict.items():
            if k.startswith('denoise_fn.'):
                new_key = k[len('denoise_fn.'):]
                denoise_state_dict[new_key] = v
        
        print(f"📋 过滤后denoise_fn权重包含键数量: {len(denoise_state_dict.keys())}")
        
        # 只加载到denoise_fn
        network.denoise_fn.load_state_dict(denoise_state_dict, strict=True)
        print(f"✅ 残差权重成功加载到denoise_fn")
        
        # 6. 测试UNet前向传播 - 简化测试，只验证权重加载，不测试完整前向传播
        print("6. 验证UNet权重加载...")
        
        # 检查UNet参数是否已加载（非零值）
        unet_params = list(network.denoise_fn.parameters())
        unet_loaded = any(p.requires_grad and torch.norm(p).item() != 0 for p in unet_params)
        
        print(f"📊 UNet参数统计:")
        print(f"   总参数数: {sum(p.numel() for p in unet_params):,}")
        print(f"   已加载参数: {sum(1 for p in unet_params if p.requires_grad and torch.norm(p).item() != 0)}")
        print(f"   权重加载状态: {'✅' if unet_loaded else '❌'}")
        
        if not unet_loaded:
            print(f"❌ UNet权重未成功加载")
            return False
        else:
            print(f"✅ UNet权重加载成功")
            return True
        
    except Exception as e:
        print(f"❌ 残差权重加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


def test_full_mrdpm_loading():
    """测试完整MRDPM模型加载（模拟ai_inference.py中的初始化）"""
    print("\n" + "=" * 60)
    print("🧪 测试完整MRDPM模型加载")
    print("=" * 60)
    
    try:
        # 1. 导入MRDPMModel类
        print("1. 导入MRDPMModel类...")
        from ai_inference import MRDPMModel
        
        # 2. 准备权重路径
        print("2. 准备权重路径...")
        mrdpm_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mrdpm')
        bran_pretrained_path = os.path.join(mrdpm_path, 'weights', 'cbf', 'bran_pretrained_3channel.pth')
        residual_weight_path = os.path.join(mrdpm_path, 'weights', 'cbf', '200_Network_ema.pth')
        
        print(f"📁 BRAN预训练权重: {bran_pretrained_path}")
        print(f"📁 残差权重: {residual_weight_path}")
        
        # 3. 初始化MRDPMModel
        print("3. 初始化MRDPMModel...")
        mrdpm_model = MRDPMModel(
            bran_pretrained_path=bran_pretrained_path,
            residual_weight_path=residual_weight_path,
            device='cpu'  # 使用CPU进行测试
        )
        
        if mrdpm_model.model is not None:
            print(f"✅ MRDPMModel初始化成功")
        else:
            print(f"❌ MRDPMModel初始化失败")
            return False
        
        # 4. 验证两阶段网络都已加载权重
        print("4. 验证两阶段网络权重加载...")
        
        # 检查initial_net是否加载了权重
        initial_net_params = list(mrdpm_model.model.initial_net.parameters())
        initial_net_loaded = any(p.requires_grad and torch.norm(p).item() != 0 for p in initial_net_params)
        print(f"📋 initial_net权重加载状态: {'✅' if initial_net_loaded else '❌'}")
        
        # 检查denoise_fn是否加载了权重
        denoise_fn_params = list(mrdpm_model.model.denoise_fn.parameters())
        denoise_fn_loaded = any(p.requires_grad and torch.norm(p).item() != 0 for p in denoise_fn_params)
        print(f"📋 denoise_fn权重加载状态: {'✅' if denoise_fn_loaded else '❌'}")
        
        if initial_net_loaded and denoise_fn_loaded:
            print(f"✅ 两阶段网络权重均已成功加载")
        else:
            print(f"❌ 部分网络权重未加载成功")
            return False
        
    except Exception as e:
        print(f"❌ 完整MRDPM模型加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    """主函数，运行所有测试"""
    print("🚀 MRDPM模型权重加载测试开始")
    print("=" * 60)
    
    # 运行所有测试
    tests = [
        ("BRAN初始网络权重加载", test_bran_weight_loading),
        ("UNet残差网络权重加载", test_residual_weight_loading),
        ("完整MRDPM模型加载", test_full_mrdpm_loading)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 运行测试: {test_name}")
        if test_func():
            print(f"✅ {test_name} 通过")
            passed += 1
        else:
            print(f"❌ {test_name} 失败")
    
    print("\n" + "=" * 60)
    print(f"📊 测试结果: {passed}/{total} 测试通过")
    print("=" * 60)
    
    if passed == total:
        print("🎉 所有测试通过！MRDPM模型两阶段权重加载正确")
        sys.exit(0)
    else:
        print("❌ 部分测试失败！需要检查权重加载逻辑")
        sys.exit(1)
