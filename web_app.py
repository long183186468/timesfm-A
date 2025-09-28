from flask import Flask, request, render_template_string, send_file, Response
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

app = Flask(__name__)

# 完全禁用CSP以避免兼容性问题
@app.after_request
def add_csp_header(response):
    # 不设置任何CSP头，让浏览器使用默认策略
    return response

HTML = """
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>TimesFM 股票预测</title>
    <style>
      body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', 'PingFang SC', 'Microsoft YaHei', sans-serif; margin: 24px; }
      .card { max-width: 1000px; width: 100%; margin: 12px auto; padding: 20px; border: 1px solid #eee; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.06); }
      h1 { margin: 0 0 16px; font-size: 20px; }
      form { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }
      input, select, button { padding: 10px 12px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; }
      button { background: #0ea5e9; color: white; border: none; cursor: pointer; }
      button:hover { background: #0284c7; }
      .meta { color: #666; font-size: 13px; margin-top: 6px; }
      .grid { display: grid; grid-template-columns: 1fr; gap: 16px; }
      @media (min-width: 900px) { .grid { grid-template-columns: 1fr 1fr; } }
      .stat { background: #f8fafc; padding: 12px; border-radius: 8px; }
      .img-wrap { background: #fff; padding: 8px; border: 1px solid #eee; border-radius: 8px; }
      .error { color: #b91c1c; background: #fef2f2; border: 1px solid #fee2e2; padding: 10px; border-radius: 8px; }
      table { width: 100%; border-collapse: collapse; font-size: 13px; }
      thead th { position: sticky; top: 0; background: #f1f5f9; }
      th, td { padding: 8px 10px; border-bottom: 1px solid #eee; text-align: right; }
      td:first-child, th:first-child { text-align: left; }
      .btn-secondary { background: #64748b; }
      .btn-secondary:hover { background: #475569; }
      pre.log { background: #0b1020; color: #d1d5db; padding: 12px; border-radius: 8px; overflow:auto; max-height: 360px; font-size: 12px; }
      #table-html table { width: 100%; table-layout: auto; }
    </style>
  </head>
  <body>
    <div class="card" style="max-width:1000px;">
      <h1>TimesFM 股票预测</h1>
      <form id="query-form" method="GET" action="/">
        <div class="card" style="margin-bottom:12px;">
          <h2 style="margin:0 0 8px; font-size:16px;">获取数据设置</h2>
          <div style="display:flex; gap:12px; flex-wrap:wrap; align-items:center;">
            <label>股票代码</label>
            <input name="symbol" value="{{ symbol }}" placeholder="603688 或 000001" />
            <label>市场</label>
            <select name="market" id="market">
              <option value="auto" {% if market=='auto' %}selected{% endif %}>自动判断</option>
              <option value="sh" {% if market=='sh' %}selected{% endif %}>沪</option>
              <option value="sz" {% if market=='sz' %}selected{% endif %}>深</option>
              <option value="cyb" {% if market=='cyb' %}selected{% endif %}>创</option>
            </select>
            <label>周期</label>
            <select name="period">
              {% for p in ['60','30','15','5','1'] %}
                <option value="{{p}}" {% if period==p %}selected{% endif %}>{{p}} 分钟</option>
              {% endfor %}
            </select>
            <label>复权</label>
            <select name="adjust">
              {% for k,v in {"":"不复权","qfq":"前复权","hfq":"后复权"}.items() %}
                <option value="{{k}}" {% if adjust==k %}selected{% endif %}>{{v}}</option>
              {% endfor %}
            </select>
            <label><input type="checkbox" name="today" value="1" {% if today=='1' %}checked{% endif %}/> 仅今日数据</label>
            <button name="action" value="fetch" type="submit" class="btn-secondary">获取数据</button>
          </div>
        </div>

        <div class="card" id="table-wrap" style="margin-top:8px; display:{% if table_html %}block{% else %}none{% endif %};">
          <h2 style="margin:0 0 8px; font-size:16px;">数据表格（最近 {{ table_rows }} 行）</h2>
          <div id="table-html" style="overflow:auto; max-height: 420px; border:1px solid #eee; border-radius:8px; width:100%;">{{ table_html|safe }}</div>
        </div>

        <div class="card">
          <h2 style="margin:0 0 8px; font-size:16px;">预测设置</h2>
          <div style="display:flex; gap:12px; flex-wrap:wrap; align-items:center;">
            <label>参考历史条数（用于建模）</label>
            <input name="lookback" value="{{ lookback }}" type="number" min="50" max="1024" />
            <label>预测未来点数（向前推多少个时间点）</label>
            <input name="horizon" value="{{ horizon }}" type="number" min="4" max="256" />
            <label><input type="checkbox" name="next3" value="1" {% if next3=='1' %}checked{% endif %}/> 预测后3个交易日</label>
            <button type="submit" name="action" value="predict">预测</button>
          </div>
        </div>
      </form>



      {% if error %}
        <div class="error">{{ error }}</div>
      {% endif %}

      {% if chart_base64 %}
      <div style="margin-top:16px;">
        <div class="img-wrap"><img src="data:image/png;base64,{{ chart_base64 }}" style="width:100%;" /></div>
        <div class="grid" style="margin-top:12px; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));">
          <div class="stat">当前价格：<b>{{ current_price }}</b></div>
          <div class="stat">趋势：<b>{{ trend }}</b></div>
          <div class="stat">预测波动率：<b>{{ volatility }}%</b></div>
          <div class="stat">最大涨幅：<b>{{ max_gain }}%</b></div>
          <div class="stat">最大跌幅：<b>{{ max_loss }}%</b></div>
          {% if current_price %}
          <div class="stat">换算价格上/下限：
            <b>{{ (current_price|float * (1 + (max_gain|float)/100))|round(2) }}</b>
            /
            <b>{{ (current_price|float * (1 + (max_loss|float)/100))|round(2) }}</b>
          </div>
          {% endif %}
        </div>
      </div>
      {% endif %}

      <!-- 移除所有JavaScript以避免CSP问题 -->
      <!--
        // 首先获取所有DOM元素
        const form = document.getElementById('query-form');
        const btnFetch = document.getElementById('btn-fetch');
        const btnApply = document.getElementById('btn-apply');
        const presetSel = document.getElementById('preset');
        const tuneLb = document.getElementById('tune-lookback');
        const tuneHz = document.getElementById('tune-horizon');
        const tuneLbVal = document.getElementById('tune-lookback-val');
        const tuneHzVal = document.getElementById('tune-horizon-val');
        const progressBox = document.getElementById('progress');
        const progressList = document.getElementById('progress-list');
        const progressBar = document.getElementById('progress-bar');
        const progressText = document.getElementById('progress-text');
        const tableWrap = document.getElementById('table-wrap');
        const tableHtml = document.getElementById('table-html');
        const modalMask = document.getElementById('fetch-modal');
        const modalText = document.getElementById('modal-text');
        const modalBar = document.getElementById('modal-progress-bar');
        const modalPct = document.getElementById('modal-progress-text');
        const predictModal = document.getElementById('predict-modal');
        const predictText = document.getElementById('predict-text');
        const predictBar = document.getElementById('predict-progress-bar');
        const predictPct = document.getElementById('predict-progress-text');
        function stepsPerDay(period){
          const m = String(period);
          return m==='60'?4: m==='30'?8: m==='15'?16: m==='5'?48: 240;
        }
        function clampLookback(v){
          const maxCtx = 1024; // 与服务端 compile 的 max_context 对齐
          v = Math.min(v, maxCtx);
          // 取 32 的倍数，贴合 TimesFM patch 长度
          return Math.max(32, Math.round(v/32)*32);
        }
        function applyPreset(){
          const period = form.querySelector('[name="period"]').value;
          const spd = stepsPerDay(period);
          const preset = presetSel.value;
          // 预测默认 3 个交易日
          const horizon = spd * 3;
          let lookback;
          if (preset==='conservative') lookback = clampLookback(spd * 20); // 更长历史
          else if (preset==='aggressive') lookback = clampLookback(spd * 8); // 更短历史，响应更快
          else lookback = clampLookback(spd * 12); // 均衡
          // 保存基准值
          form.dataset.baseHorizon = String(horizon);
          form.dataset.baseLookback = String(lookback);
          // 应用微调
          applyTuning();
          const next3 = form.querySelector('[name="next3"]');
          if (next3) next3.checked = true;
          const adjust = form.querySelector('[name="adjust"]');
          if (adjust) adjust.value = 'qfq';
        }
        function applyTuning(){
          const baseH = Number(form.dataset.baseHorizon||form.querySelector('[name="horizon"]').value||0);
          const baseL = Number(form.dataset.baseLookback||form.querySelector('[name="lookback"]').value||0);
          const pH = Number(tuneHz?.value||0)/100;
          const pL = Number(tuneLb?.value||0)/100;
          tuneHzVal.textContent = Math.round((pH)*100) + '%';
          tuneLbVal.textContent = Math.round((pL)*100) + '%';
          const period = form.querySelector('[name="period"]').value;
          const spd = stepsPerDay(period);
          let newH = Math.max(4, Math.round(baseH*(1+pH)));
          // 上限给 256，避免超出模型 compile 的上限
          newH = Math.min(newH, 256);
          let newL = clampLookback(baseL*(1+pL));
          form.querySelector('[name="horizon"]').value = newH;
          form.querySelector('[name="lookback"]').value = newL;
          // 将 next3 勾选状态与 horizon 同步（若 horizon 恰好等于 3 天步数则勾选）
          const next3 = form.querySelector('[name="next3"]');
          if (next3){
            const h3 = stepsPerDay(period) * 3;
            next3.checked = (Number(newH) === h3);
          }
        }
        btnApply?.addEventListener('click', applyPreset);
        tuneLb?.addEventListener('input', applyTuning);
        tuneHz?.addEventListener('input', applyTuning);
        // 页面加载时自动应用一次推荐
        applyPreset();

        function qs(name){ return form.querySelector('[name="' + name + '"]').value; }
        function qscb(name){ return form.querySelector('[name="' + name + '"]').checked; }

        console.log('btnFetch:', btnFetch);
        console.log('modalMask:', modalMask);
        
        btnFetch?.addEventListener('click', (e) => {
          e.preventDefault();
          console.log('获取数据按钮被点击');
          
          // 显示简单的加载提示，避免复杂的SSE和JSON.parse
          if (modalMask) {
            modalText.textContent = '正在获取数据...';
            modalBar.style.width = '50%';
            modalPct.textContent = '50%';
            modalMask.style.display = 'flex';
          }
          
          // 设置action并提交表单
          const actionInput = document.createElement('input');
          actionInput.type = 'hidden';
          actionInput.name = 'action';
          actionInput.value = 'fetch';
          form.appendChild(actionInput);
          
          form.method = 'POST';
          form.submit();
        });

        // 预测按钮事件处理
        const predictBtn = form.querySelector('button[name="action"][value="predict"]');
        predictBtn?.addEventListener('click', (e) => {
          e.preventDefault();
          console.log('预测按钮被点击');
          
          // 显示预测模态框
          predictText.textContent = '正在加载TimesFM模型...';
          predictBar.style.width = '10%';
          predictPct.textContent = '10%';
          predictModal.style.display = 'flex';
          
          // 直接提交表单，避免setTimeout引起的CSP问题
          predictText.textContent = '正在进行预测分析...';
          predictBar.style.width = '50%';
          predictPct.textContent = '50%';
          
          // 立即提交表单
          form.submit();
        });

        }); // 结束 DOMContentLoaded
      -->

      <div class="meta">提示：数据来源 akshare（新浪），支持纯数字代码（自动判断市场）。</div>
    </div>
  </body>
</html>
"""

def normalize_symbol(symbol: str, market: str = 'auto') -> str:
    """将纯数字股票代码自动补全为带交易所前缀的代码。

    规则（常见 A 股）：
    - 以 600/601/603/605/688/689 开头：上交所 -> sh
    - 以 000/001/002/003/300/301 开头：深交所 -> sz
    - 已带 sh/sz 前缀则原样返回
    - 其他情况默认加 sz 前缀
    """
    s = (symbol or "").strip().lower()
    if not s:
        return s
    if s.startswith("sh") or s.startswith("sz"):
        return s
    # 根据市场强制前缀（创科/创业板视作深市）
    if market in ("sh", "sz", "cyb"):
        if market == "cyb":
            market = "sz"
        if s.isdigit() and len(s) == 6:
            return market + s
    if s.isdigit() and len(s) == 6:
        if s.startswith(("600", "601", "603", "605", "688", "689")):
            return "sh" + s
        if s.startswith(("000", "001", "002", "003", "300", "301")):
            return "sz" + s
        # 兜底
        return "sz" + s
    return s

def fetch_data(symbol: str, period: str, adjust: str, only_today: bool, logs: list) -> pd.DataFrame:
    logs.append(f"[fetch] 请求: symbol={symbol}, period={period}, adjust={adjust}, only_today={only_today}")
    
    # 添加重试机制处理网络连接问题
    import time
    import ssl
    from urllib3.exceptions import SSLError
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            df = ak.stock_zh_a_minute(symbol=symbol, period=period, adjust=adjust)
            break
        except (SSLError, ssl.SSLError, ConnectionError, TimeoutError) as e:
            logs.append(f"[fetch] 第{attempt+1}次尝试失败: {str(e)[:100]}...")
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2  # 递增等待时间
                logs.append(f"[fetch] 等待{wait_time}秒后重试...")
                time.sleep(wait_time)
            else:
                logs.append("[fetch] 所有重试均失败，尝试降级策略")
                # 最后一次尝试：使用不同的数据源或参数
                try:
                    # 尝试不使用复权参数
                    if adjust:
                        logs.append("[fetch] 尝试不使用复权参数...")
                        df = ak.stock_zh_a_minute(symbol=symbol, period=period)
                    else:
                        raise ValueError(f"网络连接失败，无法获取数据：{symbol}")
                except Exception as final_e:
                    logs.append(f"[fetch] 最终失败: {str(final_e)}")
                    raise ValueError(f"网络连接问题，无法获取数据：{symbol}。请检查网络连接或稍后重试。")
        except Exception as e:
            logs.append(f"[fetch] 其他错误: {str(e)}")
            raise ValueError(f"获取数据时出错：{str(e)}")
    
    if df is None or df.empty:
        logs.append("[fetch] akshare 返回空数据")
        raise ValueError(f"无法获取数据：{symbol}，周期{period}分钟，复权{adjust or '不复权'}")
    logs.append(f"[fetch] 原始形状: {df.shape}, 列: {list(df.columns)}")
    
    # 规范化时间列
    df['datetime'] = pd.to_datetime(df['day'])
    df = df.sort_values('datetime').reset_index(drop=True)
    
    # 数值列转换
    for col in ['open', 'high', 'low', 'close', 'volume']:
        before_na = df[col].isna().sum()
        df[col] = pd.to_numeric(df[col], errors='coerce')
        after_na = df[col].isna().sum()
        if after_na != before_na:
            logs.append(f"[fetch] 列{col} 转为数值后 NaN 增加: +{after_na-before_na}")
    df = df.dropna(subset=['close'])
    logs.append(f"[fetch] 清洗后形状: {df.shape}")
    
    # 基于系统时间过滤
    if only_today:
        from datetime import datetime as _dt
        now = _dt.now()
        df = df[(df['datetime'].dt.date == now.date()) & (df['datetime'] <= now)]
        logs.append(f"[fetch] 仅今日过滤后形状: {df.shape}, 时间范围: {df['datetime'].min()} ~ {df['datetime'].max() if len(df)>0 else None}")
    return df

# 全局仅加载一次模型（默认使用 GPU，如环境具备）
_MODEL = None
_CFG = None
_LOCK = None

_FONT_READY = False

def _ensure_cn_font():
    global _FONT_READY
    if _FONT_READY:
        return
    try:
        # 优先使用本地已安装字体
        preferred = [
            'Noto Sans SC',
            'Source Han Sans SC',
            'Microsoft YaHei',
            'SimHei',
        ]
        available = set(f.name for f in font_manager.fontManager.ttflist)
        chosen = None
        for name in preferred:
            if name in available:
                chosen = name
                break
        if not chosen:
            # 下载 Noto Sans SC 到本地并注册
            import os, pathlib, urllib.request
            fonts_dir = os.path.join(os.path.dirname(__file__), '.fonts')
            pathlib.Path(fonts_dir).mkdir(parents=True, exist_ok=True)
            target = os.path.join(fonts_dir, 'NotoSansSC-Regular.otf')
            if not os.path.exists(target):
                url = 'https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/SimplifiedChinese/NotoSansSC-Regular.otf'
                urllib.request.urlretrieve(url, target)
            font_manager.fontManager.addfont(target)
            chosen = 'Noto Sans SC'
        plt.rcParams['font.sans-serif'] = [chosen, 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        _FONT_READY = True
    except Exception:
        # 回退到默认字体（可能会有方块，但不影响功能）
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False

# 确保在应用启动时即设置中文字体，避免首次作图出现缺字警告
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
                _CFG = timesfm.ForecastConfig(
                    max_context=1024,
                    max_horizon=256,
                    normalize_inputs=True,
                    use_continuous_quantile_head=True,
                    force_flip_invariance=True,
                    infer_is_positive=True,
                    fix_quantile_crossing=True,
                )
                _MODEL.compile(_CFG)

def run_forecast(series: np.ndarray, horizon: int):
    _ensure_model_loaded()
    # 预测时序列化访问，避免并发造成资源冲突
    with _LOCK:
        point, quant = _MODEL.forecast(horizon=horizon, inputs=[series])
    return point[0], quant[0]

def plot_chart(history: np.ndarray, pred: np.ndarray, q: np.ndarray):
    _ensure_cn_font()
    plt.figure(figsize=(20,10))
    x_hist = np.arange(len(history))
    x_pred = np.arange(len(history), len(history)+len(pred))
    # Use English labels to avoid missing glyph issues in legend
    plt.plot(x_hist, history, label='History', color='#2563eb', linewidth=2.0)
    plt.plot(x_pred, pred, label='Forecast', color='#dc2626', linewidth=2.2)
    # q 的形状可能为 (horizon, num_quantiles) 或 (num_quantiles, horizon)
    # 统一取横轴与 x_pred 相同长度的切片
    if q.shape[0] == len(pred):
        # 形如 (horizon, num_quantiles)
        lower = q[:, 1]
        upper = q[:, -1]
    else:
        # 形如 (num_quantiles, horizon)
        lower = q[1, :]
        upper = q[-1, :]
    plt.fill_between(x_pred, lower, upper, color='#fecaca', alpha=0.6, label='Prediction Interval')
    plt.axvline(len(history)-1, color='#64748b', linestyle='--', alpha=0.7)
    plt.legend()
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    plt.close()
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')

@app.route('/', methods=['GET', 'POST'])
def index():
    # 支持GET和POST请求
    def get_param(name, default=''):
        return request.form.get(name) or request.args.get(name, default)
    
    raw_symbol = get_param('symbol', '603688').strip()
    market = get_param('market', 'auto')
    symbol = normalize_symbol(raw_symbol, market)
    period = get_param('period', '60')
    adjust = get_param('adjust', 'qfq')
    today = get_param('today', '0')
    lookback = int(get_param('lookback', '100'))
    horizon = int(get_param('horizon', '12'))
    action = get_param('action', 'data')
    # 是否按后3个交易日自动计算 horizon
    next3 = get_param('next3', '1')

    error = None
    logs = []
    chart_base64 = None
    table_html = None
    table_rows = 0
    current_price = ''
    trend = ''
    volatility = ''
    max_gain = ''
    max_loss = ''

    if symbol and (action == 'fetch' or action == 'predict'):
        try:
            df = fetch_data(symbol, period, adjust, only_today=(today=='1'), logs=logs)
            # 始终先展示数据表格
            show_rows = min(200, len(df))
            table_rows = show_rows
            table_html = (
                df.tail(show_rows)
                  [["datetime","open","high","low","close","volume"]]
                  .to_html(index=False, border=0)
            )

            # 仅当 action 为 predict 才进行预测
            if action == 'predict':
                logs.append(f"[predict] 开始预测: lookback={lookback}, horizon={horizon}")
                series = df['close'].tail(lookback).to_numpy()
                # 将“后3天”换算为步数（A股每交易日4小时）
                if next3 == '1':
                    per_day_steps = {'1':240, '5':48, '15':16, '30':8, '60':4}.get(str(period), 4)
                    horizon_steps = per_day_steps * 3
                else:
                    horizon_steps = horizon
                if len(series) < 10:
                    raise ValueError('有效数据不足（<10）')
                pred, q = run_forecast(series, horizon_steps)
                chart_base64 = plot_chart(series, pred, q)
                current = series[-1]
                current_price = f"{current:.2f}"
                changes_pct = (pred - current) / current * 100
                trend = '上升' if changes_pct[-1] > changes_pct[0] else ('下降' if changes_pct[-1] < changes_pct[0] else '震荡')
                volatility = f"{np.std(changes_pct):.2f}"
                max_gain = f"{np.max(changes_pct):.2f}"
                max_loss = f"{np.min(changes_pct):.2f}"
                logs.append("[predict] 预测完成")
        except Exception as e:
            import traceback
            error = str(e)
            logs.append("[error] " + error)
            logs.append(traceback.format_exc())

    return render_template_string(
        HTML,
        symbol=raw_symbol,
        market=market,
        period=period,
        adjust=adjust,
        today=today,
        next3=next3,
        action=action,
        lookback=lookback,
        horizon=horizon,
        error=error,
        chart_base64=chart_base64,
        table_html=table_html,
        table_rows=table_rows,
        current_price=current_price,
        trend=trend,
        volatility=volatility,
        max_gain=max_gain,
        max_loss=max_loss,
    )

@app.get('/fetch_stream')
def fetch_stream():
    def sse_pack(obj):
        import json
        return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"

    symbol = normalize_symbol(request.args.get('symbol','603688'), request.args.get('market','auto'))
    period = request.args.get('period','60')
    adjust = request.args.get('adjust','qfq')
    today = request.args.get('today','0') == '1'
    lookback = int(request.args.get('lookback','100'))

    def gen():
        logs = []
        try:
            # 尝试获取公司名称（若失败则忽略）
            company = None
            try:
                import time
                import ssl
                from urllib3.exceptions import SSLError
                
                try_symbol = symbol
                if try_symbol.startswith('sh') or try_symbol.startswith('sz'):
                    try_symbol_num = try_symbol[2:]
                else:
                    try_symbol_num = try_symbol
                
                # 添加重试机制获取公司信息
                max_retries = 2
                for attempt in range(max_retries):
                    try:
                        info = ak.stock_individual_info_em(symbol=try_symbol_num)
                        if info is not None and not info.empty:
                            # akshare 返回的是 key-value 格式，查找公司简称
                            if 'item' in info.columns and 'value' in info.columns:
                                simple_name_row = info[info['item'] == '公司简称']
                                if not simple_name_row.empty:
                                    company = str(simple_name_row['value'].iloc[0])
                                    break
                                else:
                                    # 尝试其他可能的名称字段
                                    for name_key in ['公司名称', '简称']:
                                        name_row = info[info['item'] == name_key]
                                        if not name_row.empty:
                                            company = str(name_row['value'].iloc[0])
                                            break
                        break
                    except (SSLError, ssl.SSLError, ConnectionError, TimeoutError) as e:
                        if attempt < max_retries - 1:
                            time.sleep(1)  # 短暂等待后重试
                        else:
                            print(f"[DEBUG] 获取公司名称网络失败: {e}")
                            company = None
                    except Exception as e:
                        print(f"[DEBUG] 获取公司名称其他错误: {e}")
                        company = None
                        break
            except Exception as e:
                print(f"[DEBUG] 获取公司名称失败: {e}")
                company = None
            yield sse_pack({'type':'open','symbol': symbol, 'company': company})
            yield sse_pack({'type':'log','text':f'开始获取: {symbol} {period}min {adjust}', 'progress': 10})
            df = fetch_data(symbol, period, adjust, only_today=today, logs=logs)
            yield sse_pack({'type':'log','text':f'清洗完成: {len(df)} 行', 'progress': 70})
            show_rows = min(200, len(df))
            table_html = (
                df.tail(show_rows)
                  [["datetime","open","high","low","close","volume"]]
                  .to_html(index=False, border=0)
            )
            yield sse_pack({'type':'log','text':'渲染表格...', 'progress': 90})
            yield sse_pack({'type':'done','table_html': table_html, 'company': company, 'symbol': symbol, 'table_rows': show_rows})
        except Exception as e:
            yield sse_pack({'type':'error','text': str(e)})
    return Response(gen(), mimetype='text/event-stream')

if __name__ == '__main__':
    from waitress import serve
    serve(app, host='0.0.0.0', port=8000)
