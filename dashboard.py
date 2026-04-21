"""
R2R Analytics Dashboard — generates HTML report with charts
SAP DATA / Analytics Engineering (C_BCBDC)
"""

import pandas as pd
import numpy as np
import os

# ── Synthetic data matching the simulation ────────────────────────────────────
MONTHS = ["Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
np.random.seed(42)

revenue_data  = [7_20_000, 7_85_000, 8_10_000, 8_90_000, 9_40_000, 11_40_000]
expense_data  = [5_60_000, 5_90_000, 6_10_000, 6_50_000, 7_00_000,  4_80_000]
net_profit    = [r - e for r, e in zip(revenue_data, expense_data)]

gl_balances = {
    "Cash":            9_15_000,
    "Accounts Rec.":   8_50_500,
    "Fixed Assets":   11_80_000,
    "Prepaid":            30_000,
    "Accrued Rev.":      60_000,
}

close_steps = [
    ("Journal Entries",        "FB50/FB60",      "✔ Complete"),
    ("Accruals & Prepayments", "FBS1",           "✔ Complete"),
    ("Depreciation Run",       "AFAB",           "✔ Complete"),
    ("FX Revaluation",         "FAGL_FC_VAL",    "✔ Complete"),
    ("IC Reconciliation",      "FAGLF03",        "✔ Complete"),
    ("Trial Balance",          "F.01",           "✔ Complete"),
    ("Financial Statements",   "S_ALR_87012284", "✔ Complete"),
    ("Period Lock",            "OB52",           "✔ Complete"),
    ("Carry-Forward",          "F.16/FAGLGVTR",  "✔ Complete"),
    ("Audit Trail",            "FB03/GR55",      "✔ Complete"),
]

HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>SAP R2R Financial Close Dashboard — FY 2024</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f0f2f5; color: #222; }}
  header {{ background: linear-gradient(135deg,#0057a8,#0096d6); color:#fff; padding:24px 40px; }}
  header h1 {{ font-size:22px; font-weight:700; }}
  header p  {{ font-size:13px; opacity:.85; margin-top:4px; }}
  .badge {{ display:inline-block; background:#fff; color:#0057a8; border-radius:20px;
            padding:3px 12px; font-size:12px; font-weight:600; margin-top:8px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr));
           gap:18px; padding:24px 40px 0; }}
  .kpi {{ background:#fff; border-radius:10px; padding:20px 24px;
          box-shadow:0 2px 8px rgba(0,0,0,.08); border-left:5px solid #0057a8; }}
  .kpi .label {{ font-size:12px; color:#666; text-transform:uppercase; letter-spacing:.5px; }}
  .kpi .value {{ font-size:28px; font-weight:700; color:#0057a8; margin-top:4px; }}
  .kpi .sub   {{ font-size:12px; color:#888; margin-top:2px; }}
  .charts {{ display:grid; grid-template-columns:1fr 1fr; gap:18px; padding:18px 40px; }}
  .chart-card {{ background:#fff; border-radius:10px; padding:20px 24px;
                 box-shadow:0 2px 8px rgba(0,0,0,.08); }}
  .chart-card h3 {{ font-size:14px; font-weight:600; color:#333; margin-bottom:14px; }}
  canvas {{ max-height:260px; }}
  .full {{ grid-column:1/-1; }}
  .steps-table {{ width:100%; border-collapse:collapse; margin-top:8px; font-size:13px; }}
  .steps-table th {{ background:#0057a8; color:#fff; padding:8px 12px; text-align:left; }}
  .steps-table td {{ padding:7px 12px; border-bottom:1px solid #eee; }}
  .steps-table tr:nth-child(even) td {{ background:#f7f9fc; }}
  .complete {{ color:#1a8a1a; font-weight:600; }}
  footer {{ text-align:center; padding:20px; font-size:12px; color:#aaa; margin-top:10px; }}
</style>
</head>
<body>

<header>
  <h1>📊 SAP R2R — Month-End / Year-End Financial Close Dashboard</h1>
  <p>Company: IN10 — KIIT Analytics Pvt. Ltd. &nbsp;|&nbsp; Period: December 2024 (FY Close)</p>
  <span class="badge">Course: SAP DATA / Analytics Engineering (C_BCBDC)</span>
</header>

<!-- KPI Cards -->
<div class="grid">
  <div class="kpi">
    <div class="label">Total Revenue (Dec)</div>
    <div class="value">₹11.40L</div>
    <div class="sub">+21.3% vs prior month</div>
  </div>
  <div class="kpi" style="border-color:#28a745;">
    <div class="label">Net Profit (Dec)</div>
    <div class="value" style="color:#28a745;">₹6.60L</div>
    <div class="sub">Margin: 57.9%</div>
  </div>
  <div class="kpi" style="border-color:#fd7e14;">
    <div class="label">Total Assets</div>
    <div class="value" style="color:#fd7e14;">₹31.36L</div>
    <div class="sub">Balance Sheet Balanced ✔</div>
  </div>
  <div class="kpi" style="border-color:#6f42c1;">
    <div class="label">Close Steps Completed</div>
    <div class="value" style="color:#6f42c1;">10 / 10</div>
    <div class="sub">100% — All steps done</div>
  </div>
</div>

<!-- Charts -->
<div class="charts">

  <!-- Revenue vs Expenses -->
  <div class="chart-card">
    <h3>Revenue vs Expenses — H2 FY2024 (₹)</h3>
    <canvas id="revExpChart"></canvas>
  </div>

  <!-- Net Profit Trend -->
  <div class="chart-card">
    <h3>Net Profit Trend — H2 FY2024 (₹)</h3>
    <canvas id="profitChart"></canvas>
  </div>

  <!-- GL Asset Distribution -->
  <div class="chart-card">
    <h3>Asset Distribution — Dec 2024</h3>
    <canvas id="assetDoughnut"></canvas>
  </div>

  <!-- Close Steps -->
  <div class="chart-card">
    <h3>Close Activity Completion (10 Steps)</h3>
    <table class="steps-table">
      <thead><tr><th>#</th><th>Activity</th><th>T-Code</th><th>Status</th></tr></thead>
      <tbody>
        {''.join(f'<tr><td>{i+1}</td><td>{s[0]}</td><td><code>{s[1]}</code></td><td class="complete">{s[2]}</td></tr>' for i,s in enumerate(close_steps))}
      </tbody>
    </table>
  </div>

</div>

<footer>SAP R2R Simulation &nbsp;|&nbsp; C_BCBDC Capstone Project &nbsp;|&nbsp; FY 2024</footer>

<script>
const months = {MONTHS};
const revenue = {revenue_data};
const expenses = {expense_data};
const profit = {net_profit};

// Revenue vs Expenses bar chart
new Chart(document.getElementById('revExpChart'), {{
  type: 'bar',
  data: {{
    labels: months,
    datasets: [
      {{ label: 'Revenue', data: revenue,  backgroundColor: 'rgba(0,87,168,0.75)', borderRadius: 4 }},
      {{ label: 'Expenses', data: expenses, backgroundColor: 'rgba(253,126,20,0.75)', borderRadius: 4 }},
    ]
  }},
  options: {{ responsive:true, plugins:{{ legend:{{ position:'bottom' }} }},
              scales:{{ y:{{ ticks:{{ callback:v=>'₹'+v.toLocaleString('en-IN') }} }} }} }}
}});

// Net Profit line chart
new Chart(document.getElementById('profitChart'), {{
  type: 'line',
  data: {{
    labels: months,
    datasets: [{{
      label: 'Net Profit',
      data: profit,
      borderColor: '#28a745',
      backgroundColor: 'rgba(40,167,69,0.12)',
      pointBackgroundColor: '#28a745',
      fill: true,
      tension: 0.4
    }}]
  }},
  options: {{ responsive:true, plugins:{{ legend:{{ position:'bottom' }} }},
              scales:{{ y:{{ ticks:{{ callback:v=>'₹'+v.toLocaleString('en-IN') }} }} }} }}
}});

// Asset doughnut
new Chart(document.getElementById('assetDoughnut'), {{
  type: 'doughnut',
  data: {{
    labels: {list(gl_balances.keys())},
    datasets: [{{
      data: {list(gl_balances.values())},
      backgroundColor: ['#0057a8','#0096d6','#28a745','#fd7e14','#6f42c1'],
      borderWidth: 2
    }}]
  }},
  options: {{ responsive:true, plugins:{{ legend:{{ position:'bottom' }} }} }}
}});
</script>
</body>
</html>
""".replace("{MONTHS}", str(MONTHS)) \
   .replace("{revenue_data}", str(revenue_data)) \
   .replace("{expense_data}", str(expense_data)) \
   .replace("{net_profit}", str(net_profit))

os.makedirs("reports", exist_ok=True)
with open("reports/r2r_dashboard.html", "w", encoding="utf-8") as f:
    f.write(HTML)

print("✔  Dashboard saved to reports/r2r_dashboard.html")
