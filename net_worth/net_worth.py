#!/usr/bin/env python3
"""
Net worth projection: $20k debt, 3-year training period, then full-time employment.
Adjust the CONFIG values to match actual figures.

Assumes initial_savings = 0. With positive initial savings the training-phase
debt model would need adjustment (savings drawn before new debt accrues).
"""

import math
import polars as pl

# ── CONFIG ────────────────────────────────────────────────────────────────────

INITIAL_DEBT       = 20_000   # current debt ($)

POST_REFI_RATE     =  0.08   # annual interest rate on debt

# Training phase
TRAINING_YEARS     =      3
WEEKLY_INCOME_T    =    185  # part-time / stipend income (≈ $800/mo)
WEEKLY_EXPENSES_T  =    346  # living costs (≈ $1,500/mo)

# Working phase (after training)
WEEKLY_TAKE_HOME   =    877  # after-tax weekly pay (≈ $3,800/mo)
WEEKLY_EXPENSES_W  =    508  # living costs (≈ $2,200/mo)

# Savings compound at this annual rate once there's a surplus
ANNUAL_RETURN      =  0.07

YEARS_TO_PROJECT   =     10

# ── HELPERS ──────────────────────────────────────────────────────────────────

def _fv_principal(p: float, r: float, k: pl.Series) -> pl.Series:
    """p*(1+r)^k — future value of a lump sum."""
    return p * (1 + r) ** k


def _fv_annuity(pmt: float, r: float, k: pl.Series) -> pl.Series:
    """pmt*((1+r)^k - 1)/r — future value of end-of-period payments."""
    if r == 0:
        return pmt * k
    return pmt * ((1 + r) ** k - 1) / r


# ── SIMULATION ────────────────────────────────────────────────────────────────

def simulate(
    *,
    initial_debt: float,
    post_refi_rate: float,
    training_years: int,
    weekly_income_t: float,
    weekly_expenses_t: float,
    weekly_take_home: float,
    weekly_expenses_w: float,
    annual_return: float,
    years_to_project: int,
) -> pl.DataFrame:
    training_weeks = int(training_years) * 52
    total_weeks    = int(years_to_project) * 52
    working_weeks  = total_weeks - training_weeks

    r_s  = (1 + annual_return)  ** (1 / 52) - 1
    r1   = (1 + post_refi_rate) ** (1 / 52) - 1

    cf_t = float(weekly_income_t - weekly_expenses_t)   # negative: training deficit
    cf_w = float(weekly_take_home - weekly_expenses_w)  # positive: working surplus

    # ── Training phase ───────────────────────────────────────────────────────
    # Recurrence (deficit, no savings): debt_k = debt_{k-1}*(1+r) - cf_t
    # Closed form: debt_k = D0*(1+r)^k - cf_t*((1+r)^k - 1)/r

    k_t = pl.Series(range(1, training_weeks + 1), dtype=pl.Float64)
    debt_training = _fv_principal(float(initial_debt), r1, k_t) - _fv_annuity(cf_t, r1, k_t)
    D_train = float(debt_training[-1])
    savings_training = pl.Series([0.0] * training_weeks)

    # ── Working phase ─────────────────────────────────────────────────────────
    # Surplus clears debt first, then compounds into savings.
    # Debt: debt_j = D_train*(1+r1)^j - cf_w*((1+r1)^j - 1)/r1, clamped ≥ 0
    # Debt clears at j_clear = ⌈log(cf_w / (cf_w - D_train*r1)) / log(1+r1)⌉

    j = pl.Series(range(1, working_weeks + 1), dtype=pl.Float64)
    debt_working = (
        _fv_principal(D_train, r1, j) - _fv_annuity(cf_w, r1, j)
    ).clip(lower_bound=0.0)

    if D_train * r1 < cf_w:
        j_clear = math.ceil(math.log(cf_w / (cf_w - D_train * r1)) / math.log(1 + r1))
    else:
        j_clear = working_weeks + 1  # debt never clears within projection window

    if j_clear <= working_weeks:
        # On the clearance week, leftover surplus after paying off the final balance
        # seeds savings; subsequent weeks compound that plus full cf_w contributions.
        D_penult      = D_train * (1 + r1) ** (j_clear - 1) - cf_w * ((1 + r1) ** (j_clear - 1) - 1) / r1
        first_savings = max(0.0, cf_w - D_penult * (1 + r1))

        k_s = (j - j_clear).clip(lower_bound=0.0)
        savings_working = (
            _fv_principal(first_savings, r_s, k_s) + _fv_annuity(cf_w, r_s, k_s)
        ) * (j >= j_clear).cast(pl.Float64)
    else:
        savings_working = pl.Series([0.0] * working_weeks)

    # ── Assemble annual snapshots ─────────────────────────────────────────────
    return (
        pl.concat([
            pl.DataFrame({
                "week":    pl.Series([0], dtype=pl.Int32),
                "phase":   pl.Series(["training"]),
                "savings": pl.Series([0.0]),
                "debt":    pl.Series([float(initial_debt)]),
            }),
            pl.DataFrame({
                "week":    pl.Series(range(1, training_weeks + 1), dtype=pl.Int32),
                "phase":   pl.Series(["training"] * training_weeks),
                "savings": savings_training,
                "debt":    debt_training,
            }),
            pl.DataFrame({
                "week":    (j + training_weeks).cast(pl.Int32),
                "phase":   pl.Series(["working"] * working_weeks),
                "savings": savings_working,
                "debt":    debt_working,
            }),
        ])
        .with_columns((pl.col("savings") - pl.col("debt")).alias("net_worth"))
        .filter(pl.col("week") % 52 == 0)
        .with_columns((pl.col("week") // 52).alias("year"))
        .select(["year", "savings", "debt", "net_worth", "phase"])
    )


# ── OUTPUT ────────────────────────────────────────────────────────────────────

def main(
    *,
    initial_debt: float,
    post_refi_rate: float,
    training_years: int,
    weekly_income_t: float,
    weekly_expenses_t: float,
    weekly_take_home: float,
    weekly_expenses_w: float,
    annual_return: float,
    years_to_project: int,
) -> None:
    df = simulate(
        initial_debt=initial_debt,
        post_refi_rate=post_refi_rate,
        training_years=training_years,
        weekly_income_t=weekly_income_t,
        weekly_expenses_t=weekly_expenses_t,
        weekly_take_home=weekly_take_home,
        weekly_expenses_w=weekly_expenses_w,
        annual_return=annual_return,
        years_to_project=years_to_project,
    )

    print("Personal Net Worth Projection")
    print(f"  Initial debt    : ${initial_debt:>10,.0f}  (rate: {post_refi_rate:.0%})")
    print(f"  Training income : ${weekly_income_t:>10,.0f}/wk  over {training_years} years")
    print(f"  Working income  : ${weekly_take_home:>10,.0f}/wk  after tax")
    print()

    fmt = "{:>5}  {:>13}  {:>13}  {:>13}  {}"
    print(fmt.format("Year", "Savings ($)", "Debt ($)", "Net Worth ($)", "Phase"))
    print("─" * 68)

    debt_cleared_year = next(iter(df.filter(pl.col("debt") < 0.5)["year"]), None)
    nw_positive_year  = next(iter(df.filter(pl.col("net_worth") > 0)["year"]), None)

    for row in df.iter_rows(named=True):
        note = ""
        if row["year"] == debt_cleared_year:
            note = "  ← debt cleared"
        elif row["year"] == nw_positive_year:
            note = "  ← net worth positive"

        print(fmt.format(
            row["year"],
            f"{row['savings']:>11,.0f}",
            f"{row['debt']:>11,.0f}",
            f"{row['net_worth']:>11,.0f}",
            row["phase"] + note,
        ))

    print()
    last = df.row(-1, named=True)
    print(f"Projection end (year {last['year']}): net worth ${last['net_worth']:,.0f}")
    if debt_cleared_year:
        print(f"Debt cleared: year {debt_cleared_year}")
    if nw_positive_year:
        print(f"Net worth positive: year {nw_positive_year}")


if __name__ == "__main__":
    main(
        initial_debt=INITIAL_DEBT,
        post_refi_rate=POST_REFI_RATE,
        training_years=TRAINING_YEARS,
        weekly_income_t=WEEKLY_INCOME_T,
        weekly_expenses_t=WEEKLY_EXPENSES_T,
        weekly_take_home=WEEKLY_TAKE_HOME,
        weekly_expenses_w=WEEKLY_EXPENSES_W,
        annual_return=ANNUAL_RETURN,
        years_to_project=YEARS_TO_PROJECT,
    )
