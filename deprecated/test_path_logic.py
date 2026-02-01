#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
验证路径替换逻辑
"""
import re

def test_path_replacement():
    """测试路径替换逻辑"""
    
    # 模拟原始 HTML
    html = '''<!doctype html>
<html lang="zh-CN">
  <head>
    <script type="module" crossorigin src="/assets/index-CKfC5faa.js"></script>
    <link rel="stylesheet" crossorigin href="/assets/index-C-3TA9pv.css">
  </head>
  <body>
    <div id="root"></div>
  </body>
</html>'''
    
    print("📄 原始 HTML:")
    print(html)
    print("\n" + "="*60 + "\n")
    
    # 应用替换逻辑（与 app.py 中的完全相同）
    html = re.sub(r'href="\/assets\/', 'href="/static/dist/assets/', html)
    html = re.sub(r'src="\/assets\/', 'src="/static/dist/assets/', html)
    
    print("✅ 修复后的 HTML:")
    print(html)
    print("\n" + "="*60 + "\n")
    
    # 验证
    if '/static/dist/assets/index-CKfC5faa.js' in html and '/static/dist/assets/index-C-3TA9pv.css' in html:
        print("✅ 路径替换成功！")
        print("   - /assets/index-CKfC5faa.js → /static/dist/assets/index-CKfC5faa.js")
        print("   - /assets/index-C-3TA9pv.css → /static/dist/assets/index-C-3TA9pv.css")
        return True
    else:
        print("❌ 路径替换失败！")
        return False

if __name__ == '__main__':
    success = test_path_replacement()
    exit(0 if success else 1)
