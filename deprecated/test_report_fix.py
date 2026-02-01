#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试报告页面的路径修复
"""
import re
import urllib.request

def test_report_page():
    """测试报告页面资源路径"""
    url = "http://127.0.0.1:5000/report/55?file_id=397ecb0d"
    
    print("📋 正在请求报告页面...")
    try:
        with urllib.request.urlopen(url) as response:
            html = response.read().decode('utf-8')
            
            # 检查是否有资源路径
            asset_links = re.findall(r'href="([^"]*assets[^"]*)"', html)
            asset_scripts = re.findall(r'src="([^"]*assets[^"]*)"', html)
            
            print(f"✅ 页面加载成功")
            print(f"\n🔍 找到的 CSS 文件:")
            for link in asset_links:
                print(f"   {link}")
            
            print(f"\n🔍 找到的 JS 文件:")
            for script in asset_scripts:
                print(f"   {script}")
            
            # 检查路径是否正确
            all_paths = asset_links + asset_scripts
            if all_paths:
                if all('/static/dist/assets/' in path for path in all_paths):
                    print("\n✅ 所有资源路径都已正确修复！")
                    return True
                else:
                    print("\n❌ 发现错误的路径:")
                    for path in all_paths:
                        if '/static/dist/assets/' not in path:
                            print(f"   ❌ {path}")
                    return False
            else:
                print("\n⚠️  未找到资源文件引用")
                return False
    except Exception as e:
        print(f"❌ 页面加载失败: {e}")
        return False

if __name__ == '__main__':
    try:
        success = test_report_page()
        exit(0 if success else 1)
    except Exception as e:
        print(f"❌ 测试出错: {e}")
        exit(1)
