#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MRDPM模型修复测试脚本
直接测试MRDPM模型的推理功能，验证修复效果
"""

import os
import sys
import numpy as np
from PIL import Image
import torch
import torchvision.transforms as transforms

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_mrdpm_inference():
    """测试MRDPM模型推理"""
    print("=" * 60)
    print("🚀 开始测试MRDPM模型修复")
    print("=" * 60)
    
    try:
        # 1. 导入MRDPMModel类
        from ai_inference import MRDPMModel
        print("✅ 成功导入MRDPMModel类")
        
        # 2. 初始化模型
        print("\n🔧 初始化MRDPM模型...")
        # 注意：请根据实际情况修改权重文件路径
        bran_pretrained_path = "G:\\NeuroMatrix_AI\\weights_mrdpm\\tmax\\bran_pretrained_3channel.pth"
        residual_weight_path = "G:\\NeuroMatrix_AI\\weights_mrdpm\\tmax\\200_Network_ema.pth"  # 实际的EMA残差权重文件
        
        # 检查文件是否存在
        if not os.path.exists(bran_pretrained_path):
            print(f"❌ BRAN预训练权重文件不存在: {bran_pretrained_path}")
            return False
        
        if not os.path.exists(residual_weight_path):
            print(f"❌ 残差权重文件不存在: {residual_weight_path}")
            return False
        
        # 初始化模型
        mrdpm_model = MRDPMModel(bran_pretrained_path, residual_weight_path)
        
        if mrdpm_model.model is None:
            print("❌ MRDPM模型初始化失败")
            return False
        
        print("✅ MRDPM模型初始化成功")
        
        # 3. 创建测试数据
        print("\n📊 创建测试数据...")
        
        # 创建随机RGB图像 (256x256)
        test_rgb = np.random.rand(256, 256, 3) * 255
        test_rgb = test_rgb.astype(np.uint8)
        rgb_image = Image.fromarray(test_rgb)
        
        # 创建简单的掩码（中心方块）
        test_mask = np.zeros((256, 256), dtype=np.uint8)
        test_mask[64:192, 64:192] = 255
        mask_image = Image.fromarray(test_mask)
        
        print(f"✅ 测试数据创建完成")
        print(f"   RGB图像形状: {test_rgb.shape}")
        print(f"   掩码图像形状: {test_mask.shape}")
        
        # 4. 执行推理测试
        print("\n🔍 执行MRDPM模型推理...")
        
        # 创建保存目录
        test_output_dir = "G:\\test_mrdpm_fix"
        os.makedirs(test_output_dir, exist_ok=True)
        
        # 执行推理
        result = mrdpm_model.inference(rgb_image, mask_image, save_path=os.path.join(test_output_dir, "test_initial.png"))
        
        if result is not None:
            print(f"✅ MRDPM模型推理成功")
            print(f"   输出形状: {result.shape}")
            print(f"   输出范围: [{result.min():.3f}, {result.max():.3f}]")
            
            # 保存结果
            result_path = os.path.join(test_output_dir, "test_result.npy")
            np.save(result_path, result)
            print(f"✅ 推理结果已保存: {result_path}")
            
            # 生成可视化图像
            result_normalized = (result - result.min()) / (result.max() - result.min())
            result_8bit = (result_normalized * 255).astype(np.uint8)
            result_image = Image.fromarray(result_8bit)
            result_image_path = os.path.join(test_output_dir, "test_result.png")
            result_image.save(result_image_path)
            print(f"✅ 可视化结果已保存: {result_image_path}")
            
            return True
        else:
            print("❌ MRDPM模型推理失败")
            return False
            
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        print("\n" + "=" * 60)
        print("📋 MRDPM模型修复测试完成")
        print("=" * 60)

if __name__ == "__main__":
    test_mrdpm_inference()