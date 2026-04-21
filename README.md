# SAP R2R — Month-End / Year-End Financial Close Simulation

> **Capstone Project** | SAP DATA / Analytics Engineering — Course C_BCBDC  
> **Option**: End-to-End Scenario | **Topic**: Record-to-Report (R2R)

---

## 📋 Project Overview

This project simulates the complete **Record-to-Report (R2R)** financial close cycle in SAP FI (Financial Accounting). It covers all 10 close activities — from raw journal posting to period lock and balance carry-forward — using Python to replicate the data flows and outputs that a SAP ERP system would produce.

### Fictitious Company
| Field | Value |
|---|---|
| Company Code | IN10 |
| Company Name | KIIT Analytics Pvt. Ltd. |
| Fiscal Year | 2024 |
| Close Period | December 2024 (Year-End) |
| Currency | INR |

---

## 🔄 R2R Process — 10 Steps Simulated

| Step | Activity | SAP T-Code |
|---|---|---|
| 1 | Post Journal Entries | FB50 / FB60 |
| 2 | Post Accruals & Prepayments | FBS1 |
| 3 | Depreciation Run | AFAB |
| 4 | Foreign Currency Revaluation | FAGL_FC_VAL |
| 5 | Intercompany Reconciliation | FAGLF03 |
| 6 | Trial Balance Extraction | F.01 |
| 7 | Balance Sheet & P&L Generation | S_ALR_87012284 |
| 8 | Period Lock | OB52 |
| 9 | Balance Carry-Forward | F.16 / FAGLGVTR |
| 10 | Audit Trail & Variance Analysis | FB03 / GR55 |

---

## 📁 Project Structure

```
R2R_SAP_Project/
├── src/
│   ├── r2r_simulation.py      # Main simulation engine (all 10 steps)
│   └── dashboard.py           # HTML analytics dashboard generator
├── tests/
│   └── test_r2r.py            # Unit tests (pytest)
├── data/
│   └── journal_entries.csv    # Generated after simulation run
├── reports/
│   ├── trial_balance.csv      # Generated after simulation run
│   └── r2r_dashboard.html     # Interactive dashboard
├── docs/
│   └── project_report.md      # Project documentation
├── requirements.txt
└── README.md
```

---

## 🚀 How to Run

### 1. Clone the Repository
```bash
git clone https://github.com/<your-username>/SAP-R2R-Financial-Close.git
cd SAP-R2R-Financial-Close
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Simulation
```bash
python src/r2r_simulation.py
```

### 4. Generate the Dashboard
```bash
python src/dashboard.py
# Then open reports/r2r_dashboard.html in your browser
```

### 5. Run Unit Tests
```bash
python -m pytest tests/test_r2r.py -v
```

---

## 📊 Key Outputs

### Trial Balance (Dec 2024)
Balanced trial balance across all GL accounts after all close adjustments.

### Income Statement
| Item | Amount (₹) |
|---|---|
| Revenue (Services + Products + FX) | ~11,40,000 |
| Less: COGS + Salaries + Depreciation | ~4,80,000 |
| **Net Profit** | **~6,60,000** |

### Balance Sheet
Assets = Liabilities + Equity (Balanced ✔)

---

## 🛠 Tech Stack

| Tool | Purpose |
|---|---|
| Python 3.10+ | Core simulation language |
| pandas | Data manipulation & GL ledger |
| numpy | Numeric calculations |
| pytest | Unit testing |
| HTML + Chart.js | Interactive analytics dashboard |
| SAP FI concepts | R2R process knowledge |

---

## 📌 SAP Concepts Covered

- **Chart of Accounts (CoA)** — GL account master data
- **Posting Periods** — Period-specific journal control (OB52)
- **Accrual Engine** — FBS1 reversing entries
- **Asset Accounting** — SLM depreciation (AFAB)
- **FAGL** — New General Ledger with segment reporting
- **Intercompany Eliminations** — IC reconciliation
- **Financial Statement Versions** — P&L and Balance Sheet
- **Year-End Close** — Carry-forward (FAGLGVTR / F.16)

---

## 👤 Student Details

| Field | Value |
|---|---|
| Name | *(Your Name)* |
| Roll Number | *(Your Roll Number)* |
| Batch / Program | SAP DATA / Analytics Engineering (C_BCBDC) |

---

## 📄 License
This project is submitted as an academic capstone. All company data is fictitious.
