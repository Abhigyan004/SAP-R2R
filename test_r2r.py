"""
Unit tests for SAP R2R Simulation
Run: python -m pytest tests/test_r2r.py -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
import pandas as pd

# ── import functions under test ───────────────────────────────────────────────
from r2r_simulation import (
    generate_raw_journal_entries,
    step2_accruals,
    step3_depreciation,
    step4_fx_revaluation,
    step6_trial_balance,
    COA,
)


# ─────────────────────────────────────────────────────────────────────────────
class TestJournalEntries:

    def test_raw_entries_count(self):
        df = generate_raw_journal_entries()
        assert len(df) == 10, "Should generate exactly 10 raw journal entries"

    def test_all_gl_accounts_valid(self):
        df = generate_raw_journal_entries()
        for gl in pd.concat([df["gl_debit"], df["gl_credit"]]).unique():
            assert gl in COA, f"GL account {gl} not found in Chart of Accounts"

    def test_amounts_positive(self):
        df = generate_raw_journal_entries()
        assert (df["amount_inr"] > 0).all(), "All amounts must be positive"

    def test_status_posted(self):
        df = generate_raw_journal_entries()
        assert (df["status"] == "Posted").all()


# ─────────────────────────────────────────────────────────────────────────────
class TestAccruals:

    def test_accruals_add_three_entries(self):
        base = generate_raw_journal_entries()
        combined = step2_accruals(base)
        assert len(combined) == len(base) + 3

    def test_accrual_statuses(self):
        base = generate_raw_journal_entries()
        combined = step2_accruals(base)
        new_rows = combined.tail(3)
        assert set(new_rows["status"].tolist()) == {"Accrual", "Prepaid"}


# ─────────────────────────────────────────────────────────────────────────────
class TestDepreciation:

    def test_depreciation_entry_added(self):
        base = generate_raw_journal_entries()
        result = step3_depreciation(base)
        assert len(result) == len(base) + 1

    def test_depreciation_accounts(self):
        base = generate_raw_journal_entries()
        result = step3_depreciation(base)
        dep_row = result[result["status"] == "Depreciation"].iloc[0]
        assert dep_row["gl_debit"]  == "520000", "Should debit Depreciation Expense"
        assert dep_row["gl_credit"] == "150100", "Should credit Accum. Depreciation"

    def test_depreciation_amount(self):
        base = generate_raw_journal_entries()
        result = step3_depreciation(base)
        dep_row = result[result["status"] == "Depreciation"].iloc[0]
        expected = round((12_00_000 * 0.20) / 12, 2)
        assert dep_row["amount_inr"] == expected, f"Expected ₹{expected}"


# ─────────────────────────────────────────────────────────────────────────────
class TestFXRevaluation:

    def test_fx_entry_added(self):
        base = generate_raw_journal_entries()
        result = step4_fx_revaluation(base)
        assert len(result) == len(base) + 1

    def test_fx_gain_positive(self):
        base = generate_raw_journal_entries()
        result = step4_fx_revaluation(base)
        fx_row = result[result["status"] == "FX Reval"].iloc[0]
        # closing_rate(83.65) > booking_rate(83.10) → gain
        assert fx_row["amount_inr"] > 0

    def test_fx_credit_account(self):
        base = generate_raw_journal_entries()
        result = step4_fx_revaluation(base)
        fx_row = result[result["status"] == "FX Reval"].iloc[0]
        assert fx_row["gl_credit"] == "550000"  # FX Gain/Loss


# ─────────────────────────────────────────────────────────────────────────────
class TestTrialBalance:

    def _full_journal(self):
        j = generate_raw_journal_entries()
        j = step2_accruals(j)
        j = step3_depreciation(j)
        j = step4_fx_revaluation(j)
        return j

    def test_trial_balance_returns_dataframe(self):
        tb = step6_trial_balance(self._full_journal())
        assert isinstance(tb, pd.DataFrame)

    def test_trial_balance_balanced(self):
        tb = step6_trial_balance(self._full_journal())
        total_dr = tb["Debit (₹)"].sum()
        total_cr = tb["Credit (₹)"].sum()
        assert abs(total_dr - total_cr) < 0.01, "Trial Balance must balance"


# ─────────────────────────────────────────────────────────────────────────────
class TestChartOfAccounts:

    def test_coa_has_all_types(self):
        types = {v["type"] for v in COA.values()}
        assert "Asset"     in types
        assert "Liability" in types
        assert "Equity"    in types
        assert "Revenue"   in types
        assert "Expense"   in types

    def test_coa_keys_are_six_digits(self):
        for k in COA:
            assert len(k) == 6 and k.isdigit(), f"GL {k} must be 6-digit string"
