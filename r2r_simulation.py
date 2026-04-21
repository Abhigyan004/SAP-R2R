"""
=============================================================================
SAP Record-to-Report (R2R) — Month-End / Year-End Financial Close Simulation
Course  : SAP DATA / Analytics Engineering (C_BCBDC)
Module  : Financial Accounting (FI) — General Ledger (GL)
=============================================================================
Simulates the complete R2R cycle:
  Step 1  : Post Journal Entries (FB50 / FB60)
  Step 2  : Post Accruals & Prepayments
  Step 3  : Run Depreciation (AFAB)
  Step 4  : Foreign Currency Revaluation (FAGL_FC_VAL)
  Step 5  : Intercompany Reconciliation
  Step 6  : Trial Balance Extraction (F.01)
  Step 7  : Balance Sheet & P&L Generation (S_ALR_87012284)
  Step 8  : Period Lock (OB52)
  Step 9  : Carry-Forward (F.16 / FAGLGVTR)
  Step 10 : Audit Trail & Variance Analysis
=============================================================================
"""

import pandas as pd
import numpy as np
from datetime import datetime, date
from typing import List, Dict
import json
import os

# ── Colour helpers for terminal output ────────────────────────────────────────
BOLD  = "\033[1m"
GREEN = "\033[92m"
CYAN  = "\033[96m"
YELLOW= "\033[93m"
RED   = "\033[91m"
RESET = "\033[0m"

def banner(text: str) -> None:
    print(f"\n{BOLD}{CYAN}{'='*70}{RESET}")
    print(f"{BOLD}{CYAN}  {text}{RESET}")
    print(f"{BOLD}{CYAN}{'='*70}{RESET}")

def step_header(n: int, title: str) -> None:
    print(f"\n{BOLD}{GREEN}[STEP {n:02d}] {title}{RESET}")
    print(f"{GREEN}{'-'*60}{RESET}")

def info(msg: str) -> None:
    print(f"  {CYAN}ℹ{RESET}  {msg}")

def ok(msg: str) -> None:
    print(f"  {GREEN}✔{RESET}  {msg}")

def warn(msg: str) -> None:
    print(f"  {YELLOW}⚠{RESET}  {msg}")


# ═══════════════════════════════════════════════════════════════════════════════
# DATA LAYER  — Master data & seed transactions
# ═══════════════════════════════════════════════════════════════════════════════

COMPANY_CODE  = "IN10"
COMPANY_NAME  = "KIIT Analytics Pvt. Ltd."
FISCAL_YEAR   = 2024
CLOSE_PERIOD  = 12          # December — year-end
CURRENCY      = "INR"

# Chart of Accounts (simplified)
COA: Dict[str, Dict] = {
    "100000": {"name": "Cash & Cash Equivalents",   "type": "Asset",     "fs_line": "Current Assets"},
    "101000": {"name": "Accounts Receivable",        "type": "Asset",     "fs_line": "Current Assets"},
    "150000": {"name": "Fixed Assets (Gross)",       "type": "Asset",     "fs_line": "Non-Current Assets"},
    "150100": {"name": "Accum. Depreciation",        "type": "Asset",     "fs_line": "Non-Current Assets"},
    "200000": {"name": "Accounts Payable",           "type": "Liability", "fs_line": "Current Liabilities"},
    "210000": {"name": "Accrued Liabilities",        "type": "Liability", "fs_line": "Current Liabilities"},
    "300000": {"name": "Share Capital",              "type": "Equity",    "fs_line": "Equity"},
    "310000": {"name": "Retained Earnings",          "type": "Equity",    "fs_line": "Equity"},
    "400000": {"name": "Revenue — Services",         "type": "Revenue",   "fs_line": "Income Statement"},
    "401000": {"name": "Revenue — Products",         "type": "Revenue",   "fs_line": "Income Statement"},
    "500000": {"name": "Cost of Goods Sold",         "type": "Expense",   "fs_line": "Income Statement"},
    "510000": {"name": "Salaries & Wages",           "type": "Expense",   "fs_line": "Income Statement"},
    "520000": {"name": "Depreciation Expense",       "type": "Expense",   "fs_line": "Income Statement"},
    "530000": {"name": "Prepaid Expenses",           "type": "Asset",     "fs_line": "Current Assets"},
    "540000": {"name": "Accrued Revenue",            "type": "Asset",     "fs_line": "Current Assets"},
    "550000": {"name": "FX Gain / Loss",             "type": "Revenue",   "fs_line": "Income Statement"},
    "560000": {"name": "Intercompany Receivable",    "type": "Asset",     "fs_line": "Current Assets"},
    "570000": {"name": "Intercompany Payable",       "type": "Liability", "fs_line": "Current Liabilities"},
}

np.random.seed(42)

def generate_raw_journal_entries() -> pd.DataFrame:
    """Simulate raw postings that arrive during the period (FB50/FB60)."""
    entries = [
        # Doc#, Date,         GL Debit,  GL Credit, Amount (INR),  Reference
        ("1001", "2024-12-05", "101000", "400000",  5_80_000,  "INV-2024-1201"),
        ("1002", "2024-12-07", "500000", "200000",  2_10_000,  "PO-2024-5501"),
        ("1003", "2024-12-10", "100000", "101000",  4_00_000,  "RCPT-4001"),
        ("1004", "2024-12-12", "510000", "100000",  1_50_000,  "PAYROLL-DEC"),
        ("1005", "2024-12-15", "101000", "401000",  3_20_000,  "INV-2024-1202"),
        ("1006", "2024-12-18", "200000", "100000",  1_80_000,  "PMT-VEND-01"),
        ("1007", "2024-12-20", "560000", "570000",  90_000,    "IC-2024-01"),
        ("1008", "2024-12-22", "100000", "300000",  5_00_000,  "CAP-INJ-DEC"),
        ("1009", "2024-12-28", "500000", "200000",  75_000,    "PO-2024-5502"),
        ("1010", "2024-12-30", "101000", "400000",  2_40_000,  "INV-2024-1203"),
    ]
    rows = []
    for doc, dt, dr, cr, amt, ref in entries:
        rows.append({"doc_no": doc, "posting_date": dt, "gl_debit": dr,
                     "gl_credit": cr, "amount_inr": amt, "reference": ref,
                     "status": "Posted"})
    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 1 — POST JOURNAL ENTRIES
# ═══════════════════════════════════════════════════════════════════════════════

def step1_post_journal_entries(journal_df: pd.DataFrame) -> pd.DataFrame:
    step_header(1, "Post Journal Entries  [SAP T-Code: FB50 / FB60]")
    info(f"Company Code : {COMPANY_CODE} — {COMPANY_NAME}")
    info(f"Fiscal Year  : {FISCAL_YEAR}  |  Period : {CLOSE_PERIOD} (December)")
    print()
    print(journal_df.to_string(index=False))
    ok(f"✔  {len(journal_df)} journal entries posted successfully.")
    return journal_df


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 2 — ACCRUALS & PREPAYMENTS
# ═══════════════════════════════════════════════════════════════════════════════

def step2_accruals(journal_df: pd.DataFrame) -> pd.DataFrame:
    step_header(2, "Post Accruals & Prepayments  [SAP T-Code: FBS1]")
    accruals = [
        {"doc_no": "A001", "posting_date": "2024-12-31", "gl_debit": "510000",
         "gl_credit": "210000", "amount_inr": 45_000,  "reference": "ACC-DEC-BONUS",  "status": "Accrual"},
        {"doc_no": "A002", "posting_date": "2024-12-31", "gl_debit": "530000",
         "gl_credit": "100000", "amount_inr": 30_000,  "reference": "PREPAID-INS-Q1", "status": "Prepaid"},
        {"doc_no": "A003", "posting_date": "2024-12-31", "gl_debit": "540000",
         "gl_credit": "400000", "amount_inr": 60_000,  "reference": "ACC-REV-DEC",    "status": "Accrual"},
    ]
    acc_df = pd.DataFrame(accruals)
    print(acc_df.to_string(index=False))
    ok(f"✔  {len(acc_df)} accrual/prepayment entries posted.")
    combined = pd.concat([journal_df, acc_df], ignore_index=True)
    return combined


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 3 — DEPRECIATION RUN
# ═══════════════════════════════════════════════════════════════════════════════

def step3_depreciation(journal_df: pd.DataFrame) -> pd.DataFrame:
    step_header(3, "Depreciation Run  [SAP T-Code: AFAB]")
    asset_book_value = 12_00_000
    dep_rate = 0.20          # 20% SLM annual
    monthly_dep = round((asset_book_value * dep_rate) / 12, 2)
    info(f"Asset Book Value   : ₹{asset_book_value:,.0f}")
    info(f"Depreciation Rate  : {dep_rate*100:.0f}% SLM per annum")
    info(f"Monthly Charge     : ₹{monthly_dep:,.2f}")

    dep_entry = {
        "doc_no": "D001", "posting_date": "2024-12-31", "gl_debit": "520000",
        "gl_credit": "150100", "amount_inr": monthly_dep,
        "reference": "AFAB-DEC-2024", "status": "Depreciation"
    }
    ok(f"✔  Depreciation of ₹{monthly_dep:,.2f} posted (Dr 520000 / Cr 150100).")
    return pd.concat([journal_df, pd.DataFrame([dep_entry])], ignore_index=True)


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 4 — FOREIGN CURRENCY REVALUATION
# ═══════════════════════════════════════════════════════════════════════════════

def step4_fx_revaluation(journal_df: pd.DataFrame) -> pd.DataFrame:
    step_header(4, "Foreign Currency Revaluation  [SAP T-Code: FAGL_FC_VAL]")
    usd_balance   = 10_000      # USD
    booking_rate  = 83.10       # INR/USD at transaction date
    closing_rate  = 83.65       # INR/USD at period-end
    fx_gain_loss  = round(usd_balance * (closing_rate - booking_rate), 2)
    direction     = "Gain" if fx_gain_loss > 0 else "Loss"

    info(f"USD Balance (AR)   : USD {usd_balance:,}")
    info(f"Booking Rate       : ₹{booking_rate}")
    info(f"Closing Rate       : ₹{closing_rate}")
    info(f"FX {direction:<6}         : ₹{abs(fx_gain_loss):,.2f}")

    fx_entry = {
        "doc_no": "F001", "posting_date": "2024-12-31", "gl_debit": "101000",
        "gl_credit": "550000", "amount_inr": fx_gain_loss,
        "reference": "FXREVAL-DEC-2024", "status": "FX Reval"
    }
    ok(f"✔  FX {direction} of ₹{abs(fx_gain_loss):,.2f} posted.")
    return pd.concat([journal_df, pd.DataFrame([fx_entry])], ignore_index=True)


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 5 — INTERCOMPANY RECONCILIATION
# ═══════════════════════════════════════════════════════════════════════════════

def step5_intercompany_recon(journal_df: pd.DataFrame) -> None:
    step_header(5, "Intercompany Reconciliation  [SAP T-Code: FAGLF03]")
    ic_data = {
        "Entity": ["IN10 — KIIT Analytics",  "IN20 — KIIT Tech"],
        "IC Receivable (₹)": [90_000, 0],
        "IC Payable (₹)":    [0, 90_000],
        "Difference (₹)":    [0, 0],
        "Status":            ["Matched ✔", "Matched ✔"],
    }
    ic_df = pd.DataFrame(ic_data)
    print(ic_df.to_string(index=False))
    ok("✔  Intercompany balances reconciled — zero difference.")


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 6 — TRIAL BALANCE
# ═══════════════════════════════════════════════════════════════════════════════

def step6_trial_balance(journal_df: pd.DataFrame) -> pd.DataFrame:
    step_header(6, "Trial Balance Extraction  [SAP T-Code: F.01]")

    # Build debit/credit sums per GL
    debit_totals  = journal_df.groupby("gl_debit")["amount_inr"].sum().rename("total_debit")
    credit_totals = journal_df.groupby("gl_credit")["amount_inr"].sum().rename("total_credit")

    tb = pd.DataFrame(index=list(COA.keys()))
    tb.index.name = "gl_account"
    tb = tb.join(debit_totals, how="left").join(credit_totals, how="left").fillna(0)
    tb["account_name"] = tb.index.map(lambda x: COA.get(x, {}).get("name", "Unknown"))
    tb["account_type"] = tb.index.map(lambda x: COA.get(x, {}).get("type", ""))
    tb["net_balance"]  = tb["total_debit"] - tb["total_credit"]

    # Filter only accounts with activity
    active_tb = tb[tb["total_debit"] + tb["total_credit"] != 0].copy()
    active_tb = active_tb[["account_name", "account_type", "total_debit", "total_credit", "net_balance"]]
    active_tb.columns = ["Account Name", "Type", "Debit (₹)", "Credit (₹)", "Net Balance (₹)"]

    print(active_tb.to_string())
    total_dr = active_tb["Debit (₹)"].sum()
    total_cr = active_tb["Credit (₹)"].sum()
    print(f"\n  {'Total':>50}  {total_dr:>15,.2f}  {total_cr:>15,.2f}")
    if abs(total_dr - total_cr) < 0.01:
        ok("✔  Trial Balance is BALANCED.")
    else:
        warn(f"⚠  Imbalance detected: ₹{abs(total_dr - total_cr):,.2f}")
    return active_tb


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 7 — FINANCIAL STATEMENTS
# ═══════════════════════════════════════════════════════════════════════════════

def step7_financial_statements(journal_df: pd.DataFrame) -> None:
    step_header(7, "Financial Statements  [SAP T-Code: S_ALR_87012284]")

    debit_totals  = journal_df.groupby("gl_debit")["amount_inr"].sum()
    credit_totals = journal_df.groupby("gl_credit")["amount_inr"].sum()

    def net(gl: str) -> float:
        d = debit_totals.get(gl, 0)
        c = credit_totals.get(gl, 0)
        t = COA.get(gl, {}).get("type", "")
        if t in ("Asset", "Expense"):
            return d - c
        return c - d

    # ─── Income Statement ───────────────────────────────────────────────────
    revenue          = net("400000") + net("401000") + net("550000")
    cogs             = net("500000")
    salaries         = net("510000")
    depreciation_exp = net("520000")
    total_expenses   = cogs + salaries + depreciation_exp
    net_profit       = revenue - total_expenses

    print(f"\n  {'─'*50}")
    print(f"  {'INCOME STATEMENT — Dec 2024':^50}")
    print(f"  {'─'*50}")
    print(f"  {'Revenue (Services + Products + FX)':40} ₹{revenue:>12,.2f}")
    print(f"  {'Less: Cost of Goods Sold':40} ₹{cogs:>12,.2f}")
    print(f"  {'Less: Salaries & Wages':40} ₹{salaries:>12,.2f}")
    print(f"  {'Less: Depreciation':40} ₹{depreciation_exp:>12,.2f}")
    print(f"  {'─'*55}")
    print(f"  {BOLD}{'Net Profit / (Loss)':40} ₹{net_profit:>12,.2f}{RESET}")

    # ─── Balance Sheet ──────────────────────────────────────────────────────
    cash         = net("100000")
    ar           = net("101000") + net("540000") + net("560000")
    prepaid      = net("530000")
    fixed_assets = net("150000") - net("150100")
    total_assets = cash + ar + prepaid + fixed_assets

    ap           = net("200000") + net("210000") + net("570000")
    share_cap    = net("300000")
    ret_earn     = net("310000") + net_profit
    total_le     = ap + share_cap + ret_earn

    print(f"\n  {'─'*50}")
    print(f"  {'BALANCE SHEET — as at 31-Dec-2024':^50}")
    print(f"  {'─'*50}")
    print(f"  {'ASSETS':}")
    print(f"  {'  Cash & Cash Equivalents':40} ₹{cash:>12,.2f}")
    print(f"  {'  Accounts Receivable (incl. accrued)':40} ₹{ar:>12,.2f}")
    print(f"  {'  Prepaid Expenses':40} ₹{prepaid:>12,.2f}")
    print(f"  {'  Net Fixed Assets':40} ₹{fixed_assets:>12,.2f}")
    print(f"  {'  Total Assets':40} ₹{total_assets:>12,.2f}")
    print(f"  {'LIABILITIES & EQUITY':}")
    print(f"  {'  Accounts Payable (incl. accrued)':40} ₹{ap:>12,.2f}")
    print(f"  {'  Share Capital':40} ₹{share_cap:>12,.2f}")
    print(f"  {'  Retained Earnings (+ Net Profit)':40} ₹{ret_earn:>12,.2f}")
    print(f"  {'  Total L + E':40} ₹{total_le:>12,.2f}")
    print(f"  {'─'*55}")
    bal_diff = total_assets - total_le
    if abs(bal_diff) < 1:
        ok("✔  Balance Sheet BALANCES (Assets = L + E).")
    else:
        warn(f"  Difference: ₹{bal_diff:,.2f} — check postings.")


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 8 — PERIOD LOCK
# ═══════════════════════════════════════════════════════════════════════════════

def step8_period_lock() -> None:
    step_header(8, "Period Lock  [SAP T-Code: OB52]")
    lock_data = {
        "Company Code": [COMPANY_CODE]*3,
        "Acct Type":    ["A — Assets", "D — Debtors", "K — Creditors"],
        "From Period":  [1, 1, 1],
        "To Period":    [12, 12, 12],
        "Year":         [FISCAL_YEAR]*3,
        "Status":       ["LOCKED ✔"]*3,
    }
    print(pd.DataFrame(lock_data).to_string(index=False))
    ok("✔  Posting period 12 / 2024 is now LOCKED for all account types.")


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 9 — BALANCE CARRY-FORWARD
# ═══════════════════════════════════════════════════════════════════════════════

def step9_carry_forward() -> None:
    step_header(9, "Balance Carry-Forward  [SAP T-Code: F.16 / FAGLGVTR]")
    cf_data = {
        "GL Account": ["100000", "101000", "150000", "200000", "310000"],
        "Description": ["Cash", "AR", "Fixed Assets", "AP", "Retained Earnings"],
        "Closing Bal FY2024 (₹)": [9_15_000, 8_50_500, 11_80_000, 1_05_000, 4_80_000],
        "Opening Bal FY2025 (₹)": [9_15_000, 8_50_500, 11_80_000, 1_05_000, 4_80_000],
        "Status": ["Carried Forward ✔"] * 5,
    }
    print(pd.DataFrame(cf_data).to_string(index=False))
    ok("✔  Balance sheet accounts carried forward to FY 2025.")
    info("   P&L accounts zeroed out and net profit transferred to Retained Earnings.")


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 10 — AUDIT TRAIL & VARIANCE ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

def step10_audit_variance(journal_df: pd.DataFrame) -> None:
    step_header(10, "Audit Trail & Variance Analysis  [SAP T-Code: FB03 / GR55]")

    # Simple month-over-month variance (simulate prior period)
    np.random.seed(7)
    prior_revenue  = 9_40_000
    actual_revenue = journal_df[journal_df["gl_credit"].isin(["400000","401000"])]["amount_inr"].sum()
    variance       = actual_revenue - prior_revenue
    pct            = (variance / prior_revenue) * 100

    print(f"\n  {'Metric':<35} {'Prior Month':>15} {'Current Month':>15} {'Variance':>12} {'%':>8}")
    print(f"  {'-'*85}")
    print(f"  {'Revenue (INR)':35} {prior_revenue:>15,.0f} {actual_revenue:>15,.0f} {variance:>12,.0f} {pct:>7.1f}%")

    # Audit log
    audit_log = {
        "Timestamp":   [datetime.now().strftime("%Y-%m-%d %H:%M:%S")] * 5,
        "Action":      ["Journal Post", "Accrual Post", "Depreciation Run",
                        "FX Revaluation", "Period Lock"],
        "T-Code":      ["FB50", "FBS1", "AFAB", "FAGL_FC_VAL", "OB52"],
        "User":        ["FI_USER_01"] * 5,
        "Status":      ["Completed ✔"] * 5,
    }
    print(f"\n  Audit Log:")
    print(pd.DataFrame(audit_log).to_string(index=False))
    ok("✔  Audit trail complete. All close activities logged.")


# ═══════════════════════════════════════════════════════════════════════════════
# SAVE OUTPUTS
# ═══════════════════════════════════════════════════════════════════════════════

def save_outputs(journal_df: pd.DataFrame, tb_df: pd.DataFrame) -> None:
    os.makedirs("data",    exist_ok=True)
    os.makedirs("reports", exist_ok=True)
    journal_df.to_csv("data/journal_entries.csv",  index=False)
    tb_df.to_csv("reports/trial_balance.csv",      index=False)
    info("Saved: data/journal_entries.csv")
    info("Saved: reports/trial_balance.csv")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════════

def run_r2r_close() -> None:
    banner("SAP R2R — Month-End / Year-End Financial Close Simulation")
    info(f"Company  : {COMPANY_CODE} — {COMPANY_NAME}")
    info(f"Period   : December {FISCAL_YEAR}  (Year-End Close)")
    info(f"Currency : {CURRENCY}")

    raw       = generate_raw_journal_entries()
    journal   = step1_post_journal_entries(raw)
    journal   = step2_accruals(journal)
    journal   = step3_depreciation(journal)
    journal   = step4_fx_revaluation(journal)
    step5_intercompany_recon(journal)
    tb        = step6_trial_balance(journal)
    step7_financial_statements(journal)
    step8_period_lock()
    step9_carry_forward()
    step10_audit_variance(journal)
    save_outputs(journal, tb)

    banner("R2R FINANCIAL CLOSE — COMPLETED SUCCESSFULLY")
    ok("All 10 steps executed. Financial close for FY 2024 is complete.")


if __name__ == "__main__":
    run_r2r_close()
