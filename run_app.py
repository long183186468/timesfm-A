#!/usr/bin/env python3
"""
TimesFM 股票预测 Web 应用启动脚本
"""

import sys
import os
import subprocess
import importlib.util

def check_dependencies():
    """检查必要的依赖是否已安装"""
    required_packages = [
        'flask', 'flask_cors', 'torch', 'numpy', 
        'pandas', 'matplotlib', 'akshare'
    ]
    
    missing_packages = []
    for package in required_packages:
        if importlib.util.find_spec(package) is None:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ 缺少以下依赖包:")
        for pkg in missing_packages:
            print(f"   - {pkg}")
        print("\n请运行以下命令安装依赖:")
        print("pip install -r requirements.txt")
        return False
    
    print("✅ 所有依赖包已安装")
    return True

def check_timesfm_model():
    """检查 TimesFM 模型是否可用"""
    try:
        import timesfm
        print("✅ TimesFM 模型可用")
        return True
    except ImportError:
        print("❌ TimesFM 模型未安装")
        print("请运行: pip install -e .")
        return False

def main():
    """主函数"""
    print("🚀 TimesFM 股票预测 Web 应用")
    print("=" * 40)
    
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    # 检查 TimesFM 模型
    if not check_timesfm_model():
        sys.exit(1)
    
    print("\n🌐 启动 Web 应用...")
    print("访问地址: http://localhost:8000")
    print("按 Ctrl+C 停止服务")
    print("-" * 40)
    
    # 启动应用
    try:
        from web_app_vue import app
        app.run(host='0.0.0.0', port=8000, debug=False)
    except KeyboardInterrupt:
        print("\n👋 应用已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
