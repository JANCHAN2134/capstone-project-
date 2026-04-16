import streamlit as st
import streamlit.components.v1 as components
import json
import pandas as pd


def plot_data(df: pd.DataFrame):
    """
    Renders an interactive Chart.js chart.
    Automatically detects forecast data (column named 'type' with 'historical'/'forecast')
    and renders a combined actual + forecast chart with dashed projection line.
    """
    if df is None or df.empty:
        return

    if df.shape[1] < 2:
        st.info("Need at least 2 columns to visualize.")
        return

    # ── Detect forecast mode ───────────────────────────────────────────────
    is_forecast = "type" in df.columns and df["type"].isin(["historical", "forecast"]).any()

    x_col = df.columns[0]
    y_col = next(
        (c for c in df.columns[1:] if pd.api.types.is_numeric_dtype(df[c])),
        None
    )
    if y_col is None:
        st.info("No numeric column found to chart.")
        return

    if is_forecast:
        _render_forecast_chart(df, x_col, y_col)
    else:
        _render_standard_chart(df, x_col, y_col)


# ---------- STANDARD CHART ----------
def _render_standard_chart(df, x_col, y_col):
    labels = df[x_col].astype(str).tolist()
    values = df[y_col].tolist()
    max_n  = len(labels)
    default_n = min(10, max_n)

    html = f"""
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; font-family: 'DM Sans', system-ui, sans-serif; }}
body {{ background: transparent; padding: 8px 4px; }}
.ctrl-bar {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; align-items: center; }}
.ctrl-bar select, .ctrl-bar input {{
  font-size: 13px; padding: 5px 10px; border-radius: 8px;
  border: 1px solid #ddd; background: #fff; color: #333; cursor: pointer; outline: none;
  transition: border-color 0.2s;
}}
.ctrl-bar select:hover, .ctrl-bar input:hover {{ border-color: #1565c0; }}
.badge {{
  font-size: 11px; padding: 3px 10px; border-radius: 999px;
  background: #e3f2fd; color: #1565c0; font-weight: 600;
}}
.ctrl-label {{ font-size: 12px; color: #888; font-weight: 500; }}
.metric-row {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 16px; }}
.metric {{
  background: linear-gradient(135deg, #f8faff, #f0f4ff);
  border-radius: 10px; padding: 12px 16px;
  border: 1px solid #e3eaf8;
}}
.metric-label {{ font-size: 11px; color: #888; margin-bottom: 4px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px; }}
.metric-value {{ font-size: 22px; font-weight: 600; color: #1a1a2e; }}
.legend {{ display: flex; flex-wrap: wrap; gap: 14px; font-size: 12px; color: #666; margin-top: 8px; }}
.legend span {{ display: flex; align-items: center; gap: 5px; font-weight: 500; }}
.dot {{ width: 10px; height: 10px; border-radius: 2px; flex-shrink: 0; }}
.chart-wrap {{ position: relative; width: 100%; }}
</style>

<div class="metric-row" id="metrics"></div>
<div class="ctrl-bar">
  <select id="chartType">
    <option value="bar">Bar chart</option>
    <option value="horizontalBar">Horizontal bar</option>
    <option value="line">Line chart</option>
    <option value="pie">Pie chart</option>
    <option value="doughnut">Doughnut</option>
  </select>
  <select id="sortOrder">
    <option value="none">Original order</option>
    <option value="desc">High → Low</option>
    <option value="asc">Low → High</option>
  </select>
  <span class="ctrl-label">Top</span>
  <input type="number" id="topN" value="{default_n}" min="1" max="{max_n}" style="width:64px;" />
  <span class="ctrl-label">rows</span>
  <span class="badge" id="rowBadge">{default_n} rows</span>
</div>
<div class="legend" id="legend"></div>
<div class="chart-wrap" id="chartWrap" style="height:320px; margin-top:10px;">
  <canvas id="myChart"></canvas>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<script>
const RAW_LABELS = {json.dumps(labels)};
const RAW_DATA   = {json.dumps(values)};
const X_COL      = {json.dumps(x_col)};
const Y_COL      = {json.dumps(y_col)};
const COLORS = ['#1565c0','#00897b','#e53935','#f57c00','#8e24aa','#0277bd','#558b2f','#d81b60','#00838f','#3949ab'];
let chart = null;

function fmt(v) {{
  if (Math.abs(v) >= 1e6) return (v/1e6).toFixed(1)+'M';
  if (Math.abs(v) >= 1e3) return (v/1e3).toFixed(1)+'k';
  return Number(v).toLocaleString(undefined, {{maximumFractionDigits:2}});
}}

function getFiltered() {{
  const n = Math.min(parseInt(document.getElementById('topN').value)||10, RAW_LABELS.length);
  const order = document.getElementById('sortOrder').value;
  let pairs = RAW_LABELS.map((l,i)=>[l, RAW_DATA[i]]);
  if (order==='desc') pairs.sort((a,b)=>b[1]-a[1]);
  if (order==='asc')  pairs.sort((a,b)=>a[1]-b[1]);
  return {{ labels: pairs.slice(0,n).map(p=>p[0]), data: pairs.slice(0,n).map(p=>p[1]) }};
}}

function updateMetrics(f) {{
  const total = f.data.reduce((a,b)=>a+b,0);
  const avg   = total/f.data.length;
  const max   = Math.max(...f.data);
  const maxL  = f.labels[f.data.indexOf(max)];
  document.getElementById('metrics').innerHTML =
    `<div class="metric"><div class="metric-label">Total ${{Y_COL}}</div><div class="metric-value">${{fmt(total)}}</div></div>
     <div class="metric"><div class="metric-label">Average</div><div class="metric-value">${{fmt(avg)}}</div></div>
     <div class="metric"><div class="metric-label">Top ${{X_COL}}</div><div class="metric-value">${{maxL}}</div></div>`;
}}

function buildChart() {{
  const type   = document.getElementById('chartType').value;
  const f      = getFiltered();
  const isPie  = type==='pie'||type==='doughnut';
  const isHoriz= type==='horizontalBar';
  const actual = isHoriz?'bar':type;

  document.getElementById('rowBadge').textContent = f.labels.length+' rows';
  document.getElementById('chartWrap').style.height = (isHoriz ? Math.max(320, f.labels.length*36+60) : 320)+'px';
  updateMetrics(f);

  const leg = document.getElementById('legend');
  leg.innerHTML = isPie
    ? f.labels.map((l,i)=>`<span><span class="dot" style="background:${{COLORS[i%COLORS.length]}}"></span>${{l}}</span>`).join('')
    : `<span><span class="dot" style="background:#1565c0"></span>${{Y_COL}}</span>`;

  const cfg = {{
    type: actual,
    data: {{
      labels: f.labels,
      datasets: [{{
        label: Y_COL,
        data: f.data,
        backgroundColor: isPie ? COLORS.slice(0,f.data.length) : 'rgba(21,101,192,0.85)',
        borderColor:     isPie ? '#fff' : '#1565c0',
        borderWidth:     isPie ? 2 : 1,
        borderRadius:    isPie ? 0 : 5,
        hoverBackgroundColor: isPie ? COLORS.slice(0,f.data.length) : '#0d47a1',
        fill: actual==='line'?'origin':undefined,
        tension: actual==='line'?0.35:undefined,
        pointRadius: actual==='line'?4:undefined,
        pointHoverRadius: actual==='line'?7:undefined,
        backgroundColor: actual==='line'?'rgba(21,101,192,0.08)':undefined,
      }}]
    }},
    options: {{
      indexAxis: isHoriz?'y':'x',
      responsive: true,
      maintainAspectRatio: false,
      plugins: {{
        legend: {{ display: false }},
        tooltip: {{ callbacks: {{ label: ctx=>` ${{fmt(isHoriz?ctx.parsed.x:ctx.parsed.y)}}` }} }}
      }},
      scales: isPie?{{}}:{{
        x: {{ ticks: {{ autoSkip: false, maxRotation: isHoriz?0:45, font:{{size:12}} }}, grid:{{display:false}} }},
        y: {{ ticks: {{ font:{{size:12}} }}, grid:{{color:'rgba(0,0,0,0.05)'}} }}
      }}
    }}
  }};

  if (chart) chart.destroy();
  chart = new Chart(document.getElementById('myChart'), cfg);
}}

document.getElementById('chartType').addEventListener('change', buildChart);
document.getElementById('sortOrder').addEventListener('change', buildChart);
document.getElementById('topN').addEventListener('input', buildChart);
buildChart();
</script>
"""
    components.html(html, height=560, scrolling=False)


# ---------- FORECAST CHART ----------
def _render_forecast_chart(df, x_col, y_col):
    """
    Renders a special historical + forecast chart with:
    - Solid blue line for historical data
    - Dashed orange line for forecast
    - Shaded confidence band
    - Vertical separator at the forecast boundary
    """
    hist_df  = df[df["type"] == "historical"]
    fore_df  = df[df["type"] == "forecast"]

    all_labels   = df[x_col].astype(str).tolist()
    hist_vals    = [None] * len(df)
    fore_vals    = [None] * len(df)

    label_to_idx = {l: i for i, l in enumerate(all_labels)}

    for _, row in hist_df.iterrows():
        idx = label_to_idx.get(str(row[x_col]))
        if idx is not None:
            hist_vals[idx] = row[y_col]

    for _, row in fore_df.iterrows():
        idx = label_to_idx.get(str(row[x_col]))
        if idx is not None:
            fore_vals[idx] = row[y_col]

    # Stitch last historical point to first forecast point
    hist_end_idx = max([i for i, v in enumerate(hist_vals) if v is not None], default=-1)
    if hist_end_idx >= 0 and fore_vals[hist_end_idx + 1 if hist_end_idx + 1 < len(fore_vals) else hist_end_idx] is None:
        fore_vals[hist_end_idx] = hist_vals[hist_end_idx]

    cutoff_label = str(hist_df[x_col].iloc[-1]) if not hist_df.empty else ""
    last_hist_val = float(hist_df[y_col].iloc[-1]) if not hist_df.empty else 0
    last_fore_val = float(fore_df[y_col].iloc[-1]) if not fore_df.empty else 0

    html = f"""
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; font-family: 'DM Sans', system-ui, sans-serif; }}
body {{ background: transparent; padding: 8px 4px; }}
.forecast-header {{
  display: flex; align-items: center; gap: 12px; margin-bottom: 16px;
  padding: 10px 16px; background: #fff8e1; border-radius: 8px; border-left: 3px solid #ff8f00;
}}
.fh-label {{ font-size: 12px; color: #888; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px; }}
.fh-val {{ font-size: 20px; font-weight: 600; color: #e65100; }}
.fh-divider {{ width: 1px; height: 40px; background: #e0e0e0; }}
.legend-row {{ display: flex; gap: 20px; font-size: 12px; color: #555; margin-bottom: 10px; }}
.leg-item {{ display: flex; align-items: center; gap: 6px; font-weight: 500; }}
.leg-dot-blue {{ width: 24px; height: 3px; background: #1565c0; border-radius: 2px; }}
.leg-dot-orange {{ width: 24px; height: 3px; background: #ff8f00; border-radius: 2px; border-top: 2px dashed #ff8f00; }}
.chart-wrap {{ position: relative; width: 100%; height: 340px; }}
</style>

<div class="forecast-header">
  <div>
    <div class="fh-label">Last Historical {y_col.title()}</div>
    <div class="fh-val">{_fmt(last_hist_val)}</div>
  </div>
  <div class="fh-divider"></div>
  <div>
    <div class="fh-label">End of Forecast ({y_col.title()})</div>
    <div class="fh-val">{_fmt(last_fore_val)}</div>
  </div>
  <div class="fh-divider"></div>
  <div>
    <div class="fh-label">Forecast Months</div>
    <div class="fh-val">{len(fore_df)}</div>
  </div>
</div>

<div class="legend-row">
  <div class="leg-item"><div class="leg-dot-blue"></div> Historical {y_col.title()}</div>
  <div class="leg-item"><div class="leg-dot-orange"></div> Forecast (Linear Model)</div>
</div>

<div class="chart-wrap">
  <canvas id="forecastChart"></canvas>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<script>
const ALL_LABELS  = {json.dumps(all_labels)};
const HIST_VALS   = {json.dumps(hist_vals)};
const FORE_VALS   = {json.dumps(fore_vals)};
const CUTOFF      = {json.dumps(cutoff_label)};
const Y_COL       = {json.dumps(y_col)};

function fmt(v) {{
  if (v === null || v === undefined) return '';
  if (Math.abs(v) >= 1e6) return (v/1e6).toFixed(1)+'M';
  if (Math.abs(v) >= 1e3) return (v/1e3).toFixed(1)+'k';
  return Number(v).toLocaleString(undefined, {{maximumFractionDigits:2}});
}}

// Vertical cutoff annotation plugin
const cutoffPlugin = {{
  id: 'cutoffLine',
  afterDraw(chart) {{
    const idx = ALL_LABELS.indexOf(CUTOFF);
    if (idx < 0) return;
    const x = chart.scales.x.getPixelForValue(idx);
    const {{top, bottom}} = chart.chartArea;
    const ctx = chart.ctx;
    ctx.save();
    ctx.beginPath();
    ctx.setLineDash([5, 4]);
    ctx.strokeStyle = 'rgba(0,0,0,0.25)';
    ctx.lineWidth = 1.5;
    ctx.moveTo(x, top);
    ctx.lineTo(x, bottom);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = 'rgba(0,0,0,0.45)';
    ctx.font = '11px DM Sans, sans-serif';
    ctx.fillText('Forecast →', x + 5, top + 14);
    ctx.restore();
  }}
}};

new Chart(document.getElementById('forecastChart'), {{
  type: 'line',
  plugins: [cutoffPlugin],
  data: {{
    labels: ALL_LABELS,
    datasets: [
      {{
        label: 'Historical',
        data: HIST_VALS,
        borderColor: '#1565c0',
        backgroundColor: 'rgba(21,101,192,0.08)',
        fill: true,
        tension: 0.3,
        pointRadius: 3,
        pointHoverRadius: 6,
        borderWidth: 2,
        spanGaps: false,
      }},
      {{
        label: 'Forecast',
        data: FORE_VALS,
        borderColor: '#ff8f00',
        backgroundColor: 'rgba(255,143,0,0.08)',
        fill: true,
        tension: 0.3,
        pointRadius: 4,
        pointHoverRadius: 7,
        borderWidth: 2.5,
        borderDash: [6, 4],
        spanGaps: false,
      }}
    ]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    interaction: {{ mode: 'index', intersect: false }},
    plugins: {{
      legend: {{ display: false }},
      tooltip: {{
        callbacks: {{
          label: ctx => ctx.dataset.label + ': ' + fmt(ctx.parsed.y)
        }}
      }}
    }},
    scales: {{
      x: {{ ticks: {{ maxRotation: 45, font: {{size: 11}} }}, grid: {{display: false}} }},
      y: {{ ticks: {{ font: {{size: 11}}, callback: v => fmt(v) }}, grid: {{color: 'rgba(0,0,0,0.05)'}} }}
    }}
  }}
}});
</script>
"""
    components.html(html, height=500, scrolling=False)


def _fmt(v):
    """Python-side formatter for metric cards in forecast chart."""
    if v >= 1_000_000:
        return f"{v/1_000_000:.1f}M"
    if v >= 1_000:
        return f"{v/1_000:.1f}k"
    return f"{v:,.0f}"
