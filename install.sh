#!/bin/bash

echo "🚀 TimesFM 股票预测应用安装脚本"
echo "=================================="

# 检查 Python 版本
python_version=$(python3 --version 2>&1 | grep -Po '(?<=Python )\d+\.\d+')
if [[ $(echo "$python_version >= 3.8" | bc -l) -eq 0 ]]; then
    echo "❌ 需要 Python 3.8 或更高版本，当前版本: $python_version"
    exit 1
fi

echo "✅ Python 版本检查通过: $python_version"

# 安装依赖
echo "📦 安装 Python 依赖包..."
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ 依赖安装失败"
    exit 1
fi

# 安装 TimesFM 模型
echo "🤖 安装 TimesFM 模型..."
pip install -e .

if [ $? -ne 0 ]; then
    echo "❌ TimesFM 模型安装失败"
    exit 1
fi

echo "✅ 安装完成！"
echo ""
echo "🎉 使用方法:"
echo "   python run_app.py"
echo "   或者"
echo "   python web_app_vue.py"
echo ""
echo "📖 访问地址: http://localhost:8000"
