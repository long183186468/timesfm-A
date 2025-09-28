# TimesFM 股票预测 Web 应用

基于 Google TimesFM 时间序列预测模型的股票价格预测 Web 应用。

## 功能特性

- 🔍 **智能股票代码识别**: 自动识别沪深股市代码，支持手动选择市场
- 📊 **多策略预测**: 提供短线、中线、长线三种预测策略
- 📈 **可视化图表**: 生成包含历史数据和预测结果的交互式图表
- 🎛️ **参数微调**: 支持预设参数和微调滑块
- 📋 **数据展示**: 实时显示获取的股票数据表格
- 🚀 **现代化界面**: 基于 Vue.js 的响应式用户界面

## 快速开始

### 1. 环境准备

```bash
# 创建 conda 环境
conda create -n timesfm python=3.9
conda activate timesfm

# 安装依赖
pip install -r requirements.txt

# 安装 TimesFM 模型
pip install -e .
```

### 2. 运行应用

```bash
python run_app.py
```

访问 http://localhost:8000 即可使用应用。

## 原始 TimesFM 信息

TimesFM (Time Series Foundation Model) 是 Google Research 开发的时间序列预测预训练模型。

- 论文: [A decoder-only foundation model for time-series forecasting](https://arxiv.org/abs/2310.10688)
- 模型: [TimesFM Hugging Face Collection](https://huggingface.co/collections/google/timesfm-release-66e4be5fdb56e960c1e482a6)
- 最新版本: TimesFM 2.5 (200M参数)
