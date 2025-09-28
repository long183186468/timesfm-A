# TimesFM 股票预测 Web 应用

基于 Google TimesFM 时间序列预测模型的股票价格预测 Web 应用。

## 功能特性

- 🔍 **智能股票代码识别**: 自动识别沪深股市代码，支持手动选择市场
- 📊 **多策略预测**: 提供短线、中线、长线三种预测策略
- 📈 **可视化图表**: 生成包含历史数据和预测结果的交互式图表
- 🎛️ **参数微调**: 支持预设参数和微调滑块
- 📋 **数据展示**: 实时显示获取的股票数据表格
- 🚀 **现代化界面**: 基于 Vue.js 的响应式用户界面

## 技术栈

- **后端**: Flask + TimesFM 模型
- **前端**: Vue.js 3 + Axios
- **数据源**: AKShare (A股数据)
- **可视化**: Matplotlib
- **机器学习**: Google TimesFM 2.5 (200M参数)

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
python web_app_vue.py
```

访问 http://localhost:8000 即可使用应用。

### 3. 使用说明

1. **输入股票代码**: 输入6位数字股票代码（如：000001）
2. **选择市场**: 自动识别或手动选择（沪市/深市/创业板）
3. **设置参数**: 
   - 数据量：选择获取的历史数据范围
   - 预测策略：短线/中线/长线/自定义
   - 微调参数：通过滑块精细调整
4. **获取数据**: 点击"获取数据"按钮，查看股票历史数据
5. **执行预测**: 点击"开始预测"按钮，生成预测图表

## 预测策略说明

- **短线策略**: 适合日内交易，关注短期波动
- **中线策略**: 适合周级别操作，平衡风险收益
- **长线策略**: 适合月级别投资，关注趋势方向
- **自定义策略**: 手动设置回看长度和预测步数

## 文件结构

```
timesfm/
├── web_app_vue.py          # 主应用文件（Vue.js版本）
├── web_app.py              # 备用应用文件（纯HTML版本）
├── test_timesfm.py         # TimesFM模型测试文件
├── requirements.txt        # Python依赖列表
├── src/                    # TimesFM源代码
├── v1/                     # TimesFM v1版本
└── README.md              # 原始TimesFM说明
```

## 注意事项

- 首次运行会自动下载 TimesFM 模型（约200MB）
- 股票数据来源于公开API，请合理使用
- 预测结果仅供参考，投资有风险
- 建议在GPU环境下运行以获得更好性能

## 开发说明

本项目基于 Google TimesFM 开源模型开发，添加了股票数据获取、Web界面和预测可视化功能。

### 主要模块

- `fetch_data()`: 股票数据获取和预处理
- `run_forecast()`: TimesFM模型预测
- `plot_chart()`: 图表生成和可视化
- Vue.js前端: 用户交互和状态管理

## 许可证

本项目遵循原 TimesFM 项目的许可证。
