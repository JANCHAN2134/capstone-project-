import streamlit as st
import streamlit.components.v1 as components
import json
import pandas as pd


def plot_data(df: pd.DataFrame):
    """
    Renders a Power-BI-style interactive chart inside Streamlit using Chart.js.
    Features: chart type switcher, sort order, top-N filter, metric cards,
    hover tooltips, custom legend. No matplotlib needed.
    """
    if df is None or df.empty:
        return

    if df.shape[1] < 2:
        st.info("Need at least 2 columns to visualize.")
        return

    x_col = df.columns[0]
    y_col = next(
        (c for c in df.columns[1:] if pd.api.types.is_numeric_dtype(df[c])),
        None
    )
    if y_col is None:
        st.info("No numeric column found to chart.")
        return

    labels = df[x_col].astype(str).tolist()
    values = df[y_col].tolist()
    max_n  = len(labels)
    default_n = min(10, max_n)

    html = f"""
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; font-family: system-ui, sans-serif; }}
body {{ background: transparent; padding: 8px 4px; }}
.ctrl-bar {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; align-items: center; }}
.ctrl-bar select, .ctrl-bar input {{
  font-size: 13px; padding: 5px 10px; border-radius: 8px;
  border: 1px solid #ccc; background: #fff; color: #222; cursor: pointer; outline: none;
}}
.ctrl-bar select:hover, .ctrl-bar input:hover {{ border-color: #888; }}
.badge {{ font-size: 11px; padding: 3px 10px; border-radius: 999px; background: #e8f0fb; color: #185FA5; font-weight: 500; }}
.ctrl-label {{ font-size: 12px; color: #666; }}
.metric-row {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 14px; }}
.metric {{ background: #f5f5f5; border-radius: 8px; padding: 10px 14px; }}
.metric-label {{ font-size: 11px; color: #888; margin-bottom: 3px; }}
.metric-value {{ font-size: 20px; font-weight: 500; color: #222; }}
.legend {{ display: flex; flex-wrap: wrap; gap: 14px; font-size: 12px; color: #666; margin-top: 6px; }}
.legend span {{ display: flex; align-items: center; gap: 5px; }}
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
    <option value="desc">Sort high to low</option>
    <option value="asc">Sort low to high</option>
  </select>
  <span class="ctrl-label">Top</span>
  <input type="number" id="topN" value="{default_n}" min="1" max="{max_n}" style="width:64px;" />
  <span class="ctrl-label">rows</span>
  <span class="badge" id="rowBadge">{default_n} rows</span>
</div>

<div class="legend" id="legend"></div>
<div class="chart-wrap" id="chartWrap" style="height:320px; margin-top:10px;">
  <canvas id="myChart" role="img" aria-label="Chart of {x_col} vs {y_col}">{x_col} vs {y_col} chart.</canvas>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<script>
const RAW_LABELS = {json.dumps(labels)};
const RAW_DATA   = {json.dumps(values)};
const X_COL      = {json.dumps(x_col)};
const Y_COL      = {json.dumps(y_col)};
const COLORS = ['#378ADD','#1D9E75','#D85A30','#BA7517','#D4537E','#534AB7','#639922','#E24B4A','#0F6E56','#3C3489','#993C1D','#3B6D11','#0C447C','#85B7EB','#5DCAA5'];
let chart = null;

function fmt(v) {{
  if (Math.abs(v) >= 1e6) return (v/1e6).toFixed(1) + 'M';
  if (Math.abs(v) >= 1e3) return (v/1e3).toFixed(1) + 'k';
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
    : `<span><span class="dot" style="background:#378ADD"></span>${{Y_COL}}</span>`;

  const cfg = {{
    type: actual,
    data: {{
      labels: f.labels,
      datasets: [{{
        label: Y_COL,
        data: f.data,
        backgroundColor: isPie ? COLORS.slice(0,f.data.length) : '#378ADD',
        borderColor:     isPie ? '#fff' : '#185FA5',
        borderWidth:     isPie ? 2 : 1,
        borderRadius:    isPie ? 0 : 4,
        hoverBackgroundColor: isPie ? COLORS.slice(0,f.data.length) : '#185FA5',
        fill: actual==='line'?false:undefined,
        tension: actual==='line'?0.35:undefined,
        pointRadius: actual==='line'?4:undefined,
        pointHoverRadius: actual==='line'?7:undefined,
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
        y: {{ ticks: {{ font:{{size:12}} }}, grid:{{color:'rgba(0,0,0,0.06)'}} }}
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
    components.html(html, height=540, scrolling=False)
