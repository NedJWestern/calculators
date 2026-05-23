#!/usr/bin/env python3
"""
Net worth projection: $20k debt, 3-year training period, then full-time employment.
Adjust the CONFIG values to match actual figures.
"""

# ── CONFIG ────────────────────────────────────────────────────────────────────

INITIAL_DEBT       = 20_000   # current debt ($)
INITIAL_SAVINGS    =      0   # current savings/assets ($)

# Refinancing
PRE_REFI_RATE      =  0.18   # current annual rate (e.g. 18% credit card)
POST_REFI_RATE     =  0.08   # refinanced annual rate (e.g. 8% personal loan)
REFI_MONTH         =      1  # month refinancing takes effect (1 = immediately)

# Training phase
TRAINING_YEARS     =      3
MONTHLY_INCOME_T   =    800  # part-time / stipend income
MONTHLY_EXPENSES_T =  1_500  # living costs (rent, food, transport)

# Working phase (after training)
MONTHLY_TAKE_HOME  =  3_800  # after-tax monthly pay
MONTHLY_EXPENSES_W =  2_200  # living costs

# Savings compound at this annual rate once there's a surplus
ANNUAL_RETURN      =  0.07

YEARS_TO_PROJECT   =     15

# ── SIMULATION ────────────────────────────────────────────────────────────────

def simulate():
    debt    = float(INITIAL_DEBT)
    savings = float(INITIAL_SAVINGS)
    r_month = (1 + ANNUAL_RETURN) ** (1 / 12) - 1

    snapshots = []

    for month in range(1, YEARS_TO_PROJECT * 12 + 1):
        in_training = month <= TRAINING_YEARS * 12
        annual_rate = POST_REFI_RATE if month >= REFI_MONTH else PRE_REFI_RATE

        income   = MONTHLY_INCOME_T   if in_training else MONTHLY_TAKE_HOME
        expenses = MONTHLY_EXPENSES_T if in_training else MONTHLY_EXPENSES_W

        # Interest accrues on outstanding debt
        if debt > 0:
            debt += debt * (annual_rate / 12)

        cash        = income - expenses
        new_savings = 0.0

        if cash >= 0:
            # Surplus: eliminate debt first, invest the rest
            paydown     = min(cash, debt)
            debt       -= paydown
            new_savings  = cash - paydown
        else:
            # Deficit: draw savings first, then take on more debt
            if savings >= -cash:
                savings += cash
            else:
                debt    += (-cash - savings)
                savings  = 0.0

        # Existing savings compound; new cash added at month end (no growth in arrival month)
        savings = savings * (1 + r_month) + new_savings

        if month % 12 == 0:
            snapshots.append({
                "year":      month // 12,
                "savings":   savings,
                "debt":      max(0.0, debt),
                "net_worth": savings - debt,
                "phase":     "training" if in_training else "working",
            })

    return snapshots


# ── OUTPUT ────────────────────────────────────────────────────────────────────

def main():
    snapshots = simulate()

    print("Personal Net Worth Projection")
    print(f"  Initial debt    : ${INITIAL_DEBT:>10,.0f}  ({PRE_REFI_RATE:.0%} → refinanced to {POST_REFI_RATE:.0%})")
    print(f"  Training income : ${MONTHLY_INCOME_T:>10,.0f}/mo  over {TRAINING_YEARS} years")
    print(f"  Working income  : ${MONTHLY_TAKE_HOME:>10,.0f}/mo  after tax")
    print()

    fmt = "{:>5}  {:>13}  {:>13}  {:>13}  {}"
    print(fmt.format("Year", "Savings ($)", "Debt ($)", "Net Worth ($)", "Phase"))
    print("─" * 68)

    debt_cleared_year = None
    nw_positive_year  = None

    for s in snapshots:
        note = ""
        if s["debt"] < 0.5 and debt_cleared_year is None:
            debt_cleared_year = s["year"]
            note = "  ← debt cleared"
        if s["net_worth"] > 0 and nw_positive_year is None:
            nw_positive_year = s["year"]
            if not note:
                note = "  ← net worth positive"

        print(fmt.format(
            s["year"],
            f"{s['savings']:>11,.0f}",
            f"{s['debt']:>11,.0f}",
            f"{s['net_worth']:>11,.0f}",
            s["phase"] + note,
        ))

    print()
    final = snapshots[-1]
    print(f"Projection end (year {final['year']}): net worth ${final['net_worth']:,.0f}")
    if debt_cleared_year:
        print(f"Debt cleared: year {debt_cleared_year}")
    if nw_positive_year:
        print(f"Net worth positive: year {nw_positive_year}")


if __name__ == "__main__":
    main()
