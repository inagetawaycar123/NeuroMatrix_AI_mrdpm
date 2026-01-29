#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
比较BRAN权重文件与UNet残差网络权重文件中重复键的值
"""

import os
import torch
import numpy as np

def load_weights(file_path):
    """加载权重文件"""
    print(f"📁 加载权重文件: {file_path}")
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return None
    
    try:
        checkpoint = torch.load(file_path, map_location='cpu')
        
        # 处理不同格式的权重文件
        if 'state_dict' in checkpoint:
            state_dict = checkpoint['state_dict']
            print(f"✅ 从state_dict加载权重，包含键数目: {len(state_dict.keys())}")
        elif 'model_state_dict' in checkpoint:
            state_dict = checkpoint['model_state_dict']
            print(f"✅ 从model_state_dict加载权重，包含键数目: {len(state_dict.keys())}")
        elif 'netG' in checkpoint:
            state_dict = checkpoint['netG']
            print(f"✅ 从netG加载权重，包含键数目: {len(state_dict.keys())}")
        else:
            state_dict = checkpoint
            print(f"✅ 直接加载权重文件，包含键数目: {len(state_dict.keys())}")
        
        return state_dict
    except Exception as e:
        print(f"❌ 加载权重文件失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def analyze_unet_weights(unet_weights):
    """分析UNet权重文件的结构"""
    print(f"\n" + "=" * 60)
    print("🔍 分析UNet权重文件结构")
    print("=" * 60)
    
    # 统计不同组件的键数量
    initial_net_keys = []
    denoise_fn_keys = []
    other_keys = []
    
    for k in unet_weights.keys():
        if k.startswith('initial_net.'):
            initial_net_keys.append(k)
        elif k.startswith('denoise_fn.'):
            denoise_fn_keys.append(k)
        else:
            other_keys.append(k)
    
    print(f"📊 UNet权重文件总键数目: {len(unet_weights.keys())}")
    print(f"📊 initial_net组件键数目: {len(initial_net_keys)}")
    print(f"📊 denoise_fn组件键数目: {len(denoise_fn_keys)}")
    print(f"📊 其他组件键数目: {len(other_keys)}")
    
    # 显示initial_net的键（如果有）
    if initial_net_keys:
        print(f"\n📋 initial_net的前5个键:")
        for k in initial_net_keys[:5]:
            print(f"   - {k}")
    
    # 显示denoise_fn的键（如果有）
    if denoise_fn_keys:
        print(f"\n📋 denoise_fn的前5个键:")
        for k in denoise_fn_keys[:5]:
            print(f"   - {k}")
    
    return {
        'initial_net_keys': initial_net_keys,
        'denoise_fn_keys': denoise_fn_keys,
        'other_keys': other_keys
    }

def compare_bran_with_initial_net(bran_weights, unet_weights):
    """比较BRAN权重与UNet权重文件中的initial_net权重"""
    print(f"\n" + "=" * 60)
    print("🧪 比较BRAN权重与UNet initial_net权重")
    print("=" * 60)
    
    # 获取BRAN权重的所有键
    bran_keys = set(bran_weights.keys())
    print(f"📊 BRAN权重包含键数目: {len(bran_keys)}")
    
    # 从UNet权重中提取initial_net的键
    initial_net_keys = set()
    for k in unet_weights.keys():
        if k.startswith('initial_net.'):
            # 去掉'initial_net.'前缀（长度为12）
            initial_net_keys.add(k[12:])
    print(f"📊 UNet initial_net组件包含键数目: {len(initial_net_keys)}")
    
    # 找出重复的键
    common_keys = bran_keys.intersection(initial_net_keys)
    print(f"📊 共同键数目: {len(common_keys)}")
    
    if not common_keys:
        print("⚠️ 没有共同键")
        return
    
    # 比较共同键的值
    print(f"\n" + "=" * 60)
    print("🔍 比较共同键的值")
    print("=" * 60)
    
    # 统计结果
    same_count = 0
    different_count = 0
    different_keys = []
    
    for key in common_keys:
        # 获取BRAN权重值
        bran_value = bran_weights[key]
        
        # 获取UNet initial_net权重值
        unet_key = f"initial_net.{key}"
        if unet_key not in unet_weights:
            print(f"⚠️ UNet权重中找不到键: {unet_key}")
            continue
        
        unet_value = unet_weights[unet_key]
        
        # 比较值
        if isinstance(bran_value, torch.Tensor) and isinstance(unet_value, torch.Tensor):
            # 比较张量
            if bran_value.shape != unet_value.shape:
                print(f"❌ 键 '{key}' 形状不同: BRAN={bran_value.shape}, UNet initial_net={unet_value.shape}")
                different_count += 1
                different_keys.append(key)
            else:
                try:
                    # 转换为浮点型以避免类型错误
                    bran_value_float = bran_value.float()
                    unet_value_float = unet_value.float()
                    
                    if torch.allclose(bran_value_float, unet_value_float, rtol=1e-5, atol=1e-8):
                        same_count += 1
                    else:
                        # 计算差异
                        diff = torch.mean(torch.abs(bran_value_float - unet_value_float)).item()
                        print(f"❌ 键 '{key}' 值不同，平均差异: {diff:.6f}")
                        different_count += 1
                        different_keys.append(key)
                except Exception as e:
                    print(f"⚠️ 比较键 '{key}' 时出错: {e}")
                    different_count += 1
                    different_keys.append(key)
        else:
            # 比较非张量值
            try:
                if isinstance(bran_value, (int, float)) and isinstance(unet_value, (int, float)):
                    # 数值比较
                    if abs(bran_value - unet_value) < 1e-6:
                        same_count += 1
                    else:
                        diff = abs(bran_value - unet_value)
                        print(f"❌ 键 '{key}' 值不同，差异: {diff:.6f}")
                        different_count += 1
                        different_keys.append(key)
                else:
                    # 其他类型比较
                    if bran_value == unet_value:
                        same_count += 1
                    else:
                        print(f"❌ 键 '{key}' 值不同")
                        different_count += 1
                        different_keys.append(key)
            except Exception as e:
                print(f"⚠️ 比较键 '{key}' 时出错: {e}")
                different_count += 1
                different_keys.append(key)
    
    # 输出统计结果
    print(f"\n" + "=" * 60)
    print("📊 比较结果统计")
    print("=" * 60)
    print(f"✅ 相同键数目: {same_count}")
    print(f"❌ 不同键数目: {different_count}")
    print(f"📊 总共同键数目: {len(common_keys)}")
    
    if different_keys:
        print(f"\n📋 不同的键列表: {different_keys}")
    
    return {
        'same_count': same_count,
        'different_count': different_count,
        'common_keys': list(common_keys),
        'different_keys': different_keys
    }

def main():
    """主函数"""
    print("🚀 权重比较脚本开始")
    print("=" * 60)
    
    # 权重文件路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    mrdpm_path = os.path.join(current_dir, 'mrdpm')
    
    bran_weight_path = os.path.join(mrdpm_path, 'weights', 'cbf', 'bran_pretrained_3channel.pth')
    unet_weight_path = os.path.join(mrdpm_path, 'weights', 'cbf', '200_Network_ema.pth')
    
    # 加载权重
    bran_weights = load_weights(bran_weight_path)
    unet_weights = load_weights(unet_weight_path)
    
    if bran_weights is None or unet_weights is None:
        print("❌ 权重加载失败，无法进行比较")
        return
    
    # 分析UNet权重文件结构
    analyze_unet_weights(unet_weights)
    
    # 比较BRAN权重与UNet initial_net权重
    compare_bran_with_initial_net(bran_weights, unet_weights)
    
    print(f"\n" + "=" * 60)
    print("🎉 权重比较完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
