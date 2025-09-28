from flask import Flask, request, render_template_string, send_file, Response, jsonify
import os
import io
import base64
import akshare as ak
import pandas as pd
import numpy as np
import timesfm
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # 允许跨域请求

HTML = """
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>TimesFM 股票预测</title>
    <script src="https://cdn.jsdelivr.net/npm/vue@3/dist/vue.global.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/axios/dist/axios.min.js"></script>
    <style>
      body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', 'PingFang SC', 'Microsoft YaHei', sans-serif; margin: 0; background: #f8fafc; }
      .card { 
        width: 100%; 
        margin: 16px 0; 
        padding: 24px; 
        background: white;
        border: 1px solid #e5e7eb; 
        border-radius: 12px; 
        box-shadow: 0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06); 
      }
      h1 { margin: 0 0 16px; font-size: 20px; }
      form { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }
      input, select, button { padding: 10px 12px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; }
      button { background: #0ea5e9; color: white; border: none; cursor: pointer; }
      button:hover { background: #0284c7; }
      button:disabled { background: #94a3b8; cursor: not-allowed; }
      .btn-secondary { background: #64748b; }
      .btn-secondary:hover { background: #475569; }
      .error { color: #ef4444; background: #fee; padding: 12px; border-radius: 8px; margin-top: 16px; }
      .success { color: #10b981; background: #f0fdf4; padding: 12px; border-radius: 8px; margin-top: 16px; }
      .meta { color: #666; font-size: 13px; margin-top: 6px; }
      .modal-mask { position: fixed; inset: 0; background: rgba(0,0,0,.35); display: flex; align-items: center; justify-content: center; z-index: 1000; }
      .modal { width: 520px; max-width: 92vw; background: #fff; border-radius: 12px; box-shadow: 0 12px 30px rgba(0,0,0,.2); padding: 18px; }
      .progress-bar { height: 10px; background: #e5e7eb; border-radius: 8px; overflow: hidden; margin-top: 10px; }
      .progress-fill { height: 10px; background: #0ea5e9; transition: width .3s ease; }
      table { width: 100%; border-collapse: collapse; }
      th, td { padding: 8px; text-align: left; border-bottom: 1px solid #eee; }
      th { background: #f8fafc; font-weight: bold; }
      .img-wrap { margin-top: 16px; }
      .img-wrap img { width: 100%; border-radius: 8px; }
    </style>
  </head>
  <body>
    <div id="app">
      <div style="max-width: 1200px; margin: 0 auto; padding: 24px;">
        <h1 style="text-align: center; margin-bottom: 32px; font-size: 24px; color: #1f2937;">TimesFM 股票价格预测系统</h1>
        
        <div class="card">
          <h2 style="margin:0 0 8px; font-size:16px;">获取数据设置</h2>
          <form @submit.prevent="fetchData">
            <label>股票代码</label>
            <input v-model="form.symbol" placeholder="如 000001" required />
            <label>市场</label>
            <select v-model="form.market">
              <option value="auto">自动判断</option>
              <option value="sh">沪</option>
              <option value="sz">深</option>
              <option value="bj">创</option>
            </select>
            <label>周期</label>
            <select v-model="form.period">
              <option value="1">1分钟</option>
              <option value="5">5分钟</option>
              <option value="15">15分钟</option>
              <option value="30">30分钟</option>
              <option value="60">60分钟</option>
            </select>
            <label>复权</label>
            <select v-model="form.adjust">
              <option value="">不复权</option>
              <option value="qfq">前复权</option>
              <option value="hfq">后复权</option>
            </select>
            <label>数据量设置</label>
            <select v-model="form.dataAmount" @change="updateDataAmount">
              <option value="auto">智能获取（推荐）</option>
              <option value="short">短线数据（最近30天）</option>
              <option value="medium">中线数据（最近90天）</option>
              <option value="long">长线数据（最近180天）</option>
              <option value="max">最大数据（最近365天）</option>
            </select>
            <div style="font-size:12px; color:#666; margin-top:4px;">
              预计获取：{{ getEstimatedDataPoints() }} 个数据点
            </div>
            <label><input type="checkbox" v-model="form.today" /> 仅今日数据</label>
            <button type="submit" :disabled="loading">获取数据</button>
          </form>
        </div>

        <div class="card" v-if="tableData.length > 0">
          <h2 style="margin:0 0 16px; font-size:16px;">{{ company || symbol }} - 数据表格（最近 {{ tableData.length }} 行）</h2>
          <div style="overflow:auto; max-height: 420px; border:1px solid #e5e7eb; border-radius:8px; background: #f8fafc;">
            <table>
              <thead>
                <tr>
                  <th>时间</th>
                  <th>开盘</th>
                  <th>最高</th>
                  <th>最低</th>
                  <th>收盘</th>
                  <th>成交量</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in tableData" :key="row.datetime">
                  <td>{{ row.datetime }}</td>
                  <td>{{ row.open }}</td>
                  <td>{{ row.high }}</td>
                  <td>{{ row.low }}</td>
                  <td>{{ row.close }}</td>
                  <td>{{ row.volume }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="card" v-if="tableData.length > 0">
          <h2 style="margin:0 0 8px; font-size:16px;">预测设置</h2>
          <form @submit.prevent="predict">
            <label>预测策略</label>
            <select v-model="form.strategy" @change="applyStrategy">
              <option value="short_term">短线交易（1-5天）</option>
              <option value="medium_term">中线持有（1-2周）</option>
              <option value="long_term">长线投资（1个月+）</option>
              <option value="custom">自定义参数</option>
            </select>
            <label>参考历史条数（建议：{{ getRecommendedLookback() }}）</label>
            <input v-model.number="form.lookback" type="number" min="64" max="1024" step="32" />
            <label>预测未来点数</label>
            <input v-model.number="form.horizon" type="number" min="4" max="256" />
            <label><input type="checkbox" v-model="form.next3" /> 预测后3个交易日</label>
            <div style="font-size:12px; color:#666; margin-top:8px;">
              💡 提示：{{ getStrategyTip() }}
            </div>
            <button type="submit" :disabled="loading">预测</button>
          </form>
        </div>

        <div v-if="error" class="error">{{ error }}</div>
        <div v-if="success" class="success">{{ success }}</div>

        <div class="card" v-if="prediction">
          <h2 style="margin:0 0 8px; font-size:16px;">预测结果</h2>
          <div>
            <div>当前价格：<b>{{ prediction.current_price }}</b></div>
            <div>趋势：<b>{{ prediction.trend }}</b></div>
            <div>预测波动率：<b>{{ prediction.volatility }}</b></div>
            <div>最大涨幅：<b>{{ prediction.max_gain }}</b> → {{ prediction.upper_price }}</div>
            <div>最大跌幅：<b>{{ prediction.max_loss }}</b> → {{ prediction.lower_price }}</div>
          </div>
          <div class="img-wrap" v-if="prediction.chart">
            <img :src="'data:image/png;base64,' + prediction.chart" />
          </div>
        </div>

        <!-- 模态框 -->
        <div class="modal-mask" v-if="modalVisible">
          <div class="modal">
            <h3 style="margin: 0 0 6px; font-size: 16px;">{{ modalTitle }}</h3>
            <div style="color:#64748b; font-size:13px;">{{ modalText }}</div>
            <div class="progress-bar">
              <div class="progress-fill" :style="{width: progress + '%'}"></div>
            </div>
            <div style="color:#64748b; font-size:13px; margin-top:6px;">{{ progress }}%</div>
          </div>
        </div>

        <div class="meta" style="text-align: center; margin-top: 32px;">提示：数据来源 akshare（新浪），支持纯数字代码（自动判断市场）。</div>
      </div>
    </div>

    <script>
      const { createApp } = Vue;
      
      createApp({
        data() {
          return {
            form: {
              symbol: '000001',
              market: 'auto',
              period: '60',
              adjust: 'qfq',
              today: false,
              lookback: 200,
              horizon: 12,
              next3: true,
              strategy: 'medium_term',
              dataAmount: 'auto'
            },
            loading: false,
            modalVisible: false,
            modalTitle: '',
            modalText: '',
            progress: 0,
            error: '',
            success: '',
            company: '',
            symbol: '',
            tableData: [],
            prediction: null
          }
        },
        methods: {
          // 获取推荐的lookback值
          getRecommendedLookback() {
            const period = parseInt(this.form.period);
            const strategy = this.form.strategy;
            
            // 根据周期和策略计算推荐值
            let baseDays;
            switch(strategy) {
              case 'short_term': baseDays = 20; break;  // 20个交易日
              case 'medium_term': baseDays = 60; break; // 60个交易日
              case 'long_term': baseDays = 120; break;  // 120个交易日
              default: return this.form.lookback;
            }
            
            // 转换为对应周期的数据点数，确保是32的倍数
            const pointsPerDay = period === 60 ? 4 : period === 30 ? 8 : period === 15 ? 16 : period === 5 ? 48 : 240;
            const points = Math.round(baseDays * pointsPerDay / 32) * 32;
            return Math.min(Math.max(points, 64), 1024);
          },
          
          // 获取策略提示
          getStrategyTip() {
            switch(this.form.strategy) {
              case 'short_term': 
                return '短线策略：使用较少历史数据，快速响应市场变化，适合日内交易';
              case 'medium_term': 
                return '中线策略：平衡历史数据和响应速度，适合波段操作';
              case 'long_term': 
                return '长线策略：使用更多历史数据，关注长期趋势，适合价值投资';
              default: 
                return '自定义策略：根据个人经验调整参数';
            }
          },
          
          // 应用预测策略
          applyStrategy() {
            if (this.form.strategy !== 'custom') {
              this.form.lookback = this.getRecommendedLookback();
              
              // 根据策略调整预测长度
              const period = parseInt(this.form.period);
              const pointsPerDay = period === 60 ? 4 : period === 30 ? 8 : period === 15 ? 16 : period === 5 ? 48 : 240;
              
              switch(this.form.strategy) {
                case 'short_term': 
                  this.form.horizon = pointsPerDay * 3; // 3天
                  this.form.next3 = true;
                  break;
                case 'medium_term': 
                  this.form.horizon = pointsPerDay * 7; // 7天
                  this.form.next3 = false;
                  break;
                case 'long_term': 
                  this.form.horizon = pointsPerDay * 15; // 15天
                  this.form.next3 = false;
                  break;
              }
            }
          },
          
          // 获取预计数据点数
          getEstimatedDataPoints() {
            const period = parseInt(this.form.period);
            const pointsPerDay = period === 60 ? 4 : period === 30 ? 8 : period === 15 ? 16 : period === 5 ? 48 : 240;
            
            let days;
            switch(this.form.dataAmount) {
              case 'short': days = 30; break;
              case 'medium': days = 90; break;
              case 'long': days = 180; break;
              case 'max': days = 365; break;
              case 'auto': 
              default:
                // 智能模式：根据最长线策略需求计算
                days = 180; // 默认180天，足够支持所有策略
                break;
            }
            
            return days * pointsPerDay;
          },
          
          // 更新数据量设置
          updateDataAmount() {
            // 当数据量改变时，可以给出提示
            console.log('数据量设置已更新为:', this.form.dataAmount);
          },
          
          async fetchData() {
            this.loading = true;
            this.error = '';
            this.success = '';
            this.modalVisible = true;
            this.modalTitle = '正在获取数据';
            this.modalText = `股票代码：${this.form.symbol}`;
            this.progress = 20;
            
            try {
              const response = await axios.post('/api/fetch', this.form);
              this.progress = 100;
              this.company = response.data.company;
              this.symbol = response.data.symbol;
              this.tableData = response.data.data;
              this.success = `成功获取 ${this.tableData.length} 条数据`;
              this.modalVisible = false;
            } catch (err) {
              this.error = err.response?.data?.error || '获取数据失败';
              this.modalVisible = false;
            } finally {
              this.loading = false;
            }
          },
          
          async predict() {
            this.loading = true;
            this.error = '';
            this.success = '';
            this.modalVisible = true;
            this.modalTitle = '正在预测分析';
            this.modalText = '正在加载TimesFM模型...';
            this.progress = 30;
            
            try {
              this.modalText = '运行预测中...';
              this.progress = 60;
              const response = await axios.post('/api/predict', {
                ...this.form,
                data: this.tableData
              });
              this.progress = 100;
              this.prediction = response.data;
              this.success = '预测完成';
              this.modalVisible = false;
            } catch (err) {
              this.error = err.response?.data?.error || '预测失败';
              this.modalVisible = false;
            } finally {
              this.loading = false;
            }
          }
        }
      }).mount('#app');
    </script>
  </body>
</html>
"""

# 股票代码自动补全
def normalize_symbol(symbol: str, market: str = 'auto') -> str:
    if not symbol:
        return symbol
    if len(symbol) == 8 and (symbol.startswith('sh') or symbol.startswith('sz')):
        return symbol
    if len(symbol) != 6:
        return symbol
    
    # 用户明确指定市场
    if market == 'sh':
        return 'sh' + symbol
    elif market == 'sz':
        return 'sz' + symbol
    elif market == 'bj':
        return symbol  # 北交所暂不支持
    
    # 自动判断
    code_int = int(symbol)
    if 600000 <= code_int <= 609999:
        return 'sh' + symbol
    elif 0 <= code_int <= 2999:
        return 'sz' + symbol
    elif 300000 <= code_int <= 309999:
        return 'sz' + symbol
    elif code_int >= 688000:
        return 'sh' + symbol
    else:
        return 'sh' + symbol

# 全局变量存储模型实例
_MODEL = None
_CFG = None
_LOCK = None
_FONT_READY = False

def _ensure_cn_font():
    global _FONT_READY
    if _FONT_READY:
        return
    try:
        # 直接使用英文，避免中文字体问题
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'sans-serif']
        plt.rcParams['axes.unicode_minus'] = False
        _FONT_READY = True
    except Exception:
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False

_ensure_cn_font()

def _ensure_model_loaded():
    global _MODEL, _CFG, _LOCK
    if _LOCK is None:
        import threading
        _LOCK = threading.Lock()
    if _MODEL is None:
        with _LOCK:
            if _MODEL is None:
                _MODEL = timesfm.TimesFM_2p5_200M_torch()
                _MODEL.load_checkpoint()
                # 针对60日K线股票数据优化的配置
                _CFG = timesfm.ForecastConfig(
                    max_context=1024,  # 支持最多1024个时间点的历史数据
                    max_horizon=256,   # 支持最多256个时间点的预测
                    normalize_inputs=True,  # 标准化输入，对股价数据很重要
                    use_continuous_quantile_head=True,  # 启用概率预测，提供不确定性估计
                    force_flip_invariance=False,  # 股票数据有方向性，不强制翻转不变性
                    infer_is_positive=True,  # 股价通常为正值
                    fix_quantile_crossing=True,  # 修复分位数交叉问题
                )
                _MODEL.compile(_CFG)

def run_forecast(series: np.ndarray, horizon: int):
    _ensure_model_loaded()
    with _LOCK:
        point, quant = _MODEL.forecast(horizon=horizon, inputs=[series])
    return point[0], quant[0]

def plot_chart(history: np.ndarray, pred: np.ndarray, q: np.ndarray):
    _ensure_cn_font()
    plt.figure(figsize=(20,10))
    x_hist = np.arange(len(history))
    x_pred = np.arange(len(history), len(history) + len(pred))
    
    plt.plot(x_hist, history, label='Historical Data', color='blue', linewidth=2)
    plt.plot(x_pred, pred, label='Forecast', color='red', linewidth=2)
    
    if q is not None and len(q) > 0:
        lower = q[:len(pred), 0]
        upper = q[:len(pred), -1]
        plt.fill_between(x_pred, lower, upper, alpha=0.3, color='red', label='Prediction Interval')
    
    plt.xlabel('Time Steps')
    plt.ylabel('Price')
    plt.title('Stock Price Prediction')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    plt.close()
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')

@app.route('/')
def index():
    # Vue使用{{}}语法，需要原样返回HTML，不经过Jinja2处理
    return HTML

@app.route('/api/fetch', methods=['POST'])
def api_fetch():
    try:
        data = request.json
        symbol = normalize_symbol(data.get('symbol', ''), data.get('market', 'auto'))
        period = data.get('period', '60')
        adjust = data.get('adjust', 'qfq')
        only_today = data.get('today', False)
        data_amount = data.get('dataAmount', 'auto')
        
        # 获取公司名称
        company = None
        try:
            import time
            try_symbol = symbol
            if try_symbol.startswith('sh') or try_symbol.startswith('sz'):
                try_symbol_num = try_symbol[2:]
            else:
                try_symbol_num = try_symbol
            
            info = ak.stock_individual_info_em(symbol=try_symbol_num)
            if info is not None and not info.empty:
                if 'item' in info.columns and 'value' in info.columns:
                    simple_name_row = info[info['item'] == '公司简称']
                    if not simple_name_row.empty:
                        company = str(simple_name_row['value'].iloc[0])
                    else:
                        for name_key in ['公司名称', '简称']:
                            name_row = info[info['item'] == name_key]
                            if not name_row.empty:
                                company = str(name_row['value'].iloc[0])
                                break
        except Exception:
            pass
        
        # 获取数据
        df = ak.stock_zh_a_minute(symbol=symbol, period=period, adjust=adjust)
        if df is None or df.empty:
            raise ValueError(f"无法获取数据：{symbol}")
        
        # 数据处理
        if 'day' in df.columns:
            df['datetime'] = pd.to_datetime(df['day'])
        elif 'time' in df.columns:
            df['datetime'] = pd.to_datetime(df['time'])
        else:
            raise ValueError("数据格式异常：缺少时间列")
        
        for col in ['open','high','low','close','volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        df = df.dropna(subset=['open','high','low','close'])
        
        if only_today:
            today = pd.Timestamp.now().date()
            df = df[df['datetime'].dt.date == today]
        
        # 根据数据量设置决定返回多少条数据
        if data_amount == 'short':
            show_rows = min(720, len(df))  # 30天 * 24小时 (最大按1分钟计算)
        elif data_amount == 'medium':
            show_rows = min(2160, len(df))  # 90天 * 24小时
        elif data_amount == 'long':
            show_rows = min(4320, len(df))  # 180天 * 24小时
        elif data_amount == 'max':
            show_rows = min(8760, len(df))  # 365天 * 24小时
        else:  # auto模式
            # 智能模式：确保有足够数据支持长线策略（180天）
            period_int = int(period)
            points_per_day = 240 if period_int == 1 else 48 if period_int == 5 else 16 if period_int == 15 else 8 if period_int == 30 else 4
            min_points_needed = 180 * points_per_day  # 180天的数据点
            show_rows = min(max(min_points_needed, 1000), len(df))  # 至少1000条，最多180天所需
        
        table_data = df.tail(show_rows)[['datetime','open','high','low','close','volume']].to_dict('records')
        
        # 格式化数据
        for row in table_data:
            row['datetime'] = row['datetime'].strftime('%Y-%m-%d %H:%M')
        
        return jsonify({
            'company': company,
            'symbol': symbol,
            'data': table_data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/predict', methods=['POST'])
def api_predict():
    try:
        data = request.json
        lookback = data.get('lookback', 200)
        horizon = data.get('horizon', 12)
        next3 = data.get('next3', True)
        period = data.get('period', '60')
        table_data = data.get('data', [])
        
        if not table_data:
            raise ValueError("没有数据可供预测")
        
        # 转换回DataFrame
        df = pd.DataFrame(table_data)
        df['datetime'] = pd.to_datetime(df['datetime'])
        
        # 预测
        series = df['close'].tail(lookback).to_numpy()
        
        if next3:
            per_day_steps = {'1':240, '5':48, '15':16, '30':8, '60':4}.get(str(period), 4)
            horizon_steps = per_day_steps * 3
        else:
            horizon_steps = horizon
        
        pred, q = run_forecast(series, horizon_steps)
        
        # 生成图表
        chart_base64 = plot_chart(series, pred, q)
        
        # 计算指标
        current_price = f"{series[-1]:.2f}"
        price_change = pred[-1] - series[-1]
        trend = "上升" if price_change > 0 else "下降" if price_change < 0 else "持平"
        volatility = f"{np.std(pred) / series[-1] * 100:.2f}%"
        
        if q is not None and len(q) > 0:
            max_price = np.max(q[:, -1])
            min_price = np.min(q[:, 0])
            max_gain = (max_price - series[-1]) / series[-1] * 100
            max_loss = (min_price - series[-1]) / series[-1] * 100
            max_gain_str = f"{max_gain:.2f}%"
            max_loss_str = f"{max_loss:.2f}%"
            upper_price = f"{max_price:.2f}"
            lower_price = f"{min_price:.2f}"
        else:
            max_gain_str = "--"
            max_loss_str = "--"
            upper_price = "--"
            lower_price = "--"
        
        return jsonify({
            'current_price': current_price,
            'trend': trend,
            'volatility': volatility,
            'max_gain': max_gain_str,
            'max_loss': max_loss_str,
            'upper_price': upper_price,
            'lower_price': lower_price,
            'chart': chart_base64
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)
