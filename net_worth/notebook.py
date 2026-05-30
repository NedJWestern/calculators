import marimo

__generated_with = "0.23.8"
app = marimo.App(width="medium")


@app.cell
def _():
    import math
    import marimo as mo
    import polars as pl

    return math, mo, pl


@app.cell
def _(math, pl):
    def _fv_principal(p: float, r: float, k: pl.Series) -> pl.Series:
        return p * (1 + r) ** k

    def _fv_annuity(pmt: float, r: float, k: pl.Series) -> pl.Series:
        if r == 0:
            return pmt * k
        return pmt * ((1 + r) ** k - 1) / r

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

        r_s = (1 + annual_return)  ** (1 / 52) - 1
        r1  = (1 + post_refi_rate) ** (1 / 52) - 1

        cf_t = float(weekly_income_t - weekly_expenses_t)
        cf_w = float(weekly_take_home - weekly_expenses_w)

        # Training phase
        k_t = pl.Series(range(1, training_weeks + 1), dtype=pl.Float64)
        debt_training = _fv_principal(float(initial_debt), r1, k_t) - _fv_annuity(cf_t, r1, k_t)
        D_train = float(debt_training[-1])
        savings_training = pl.Series([0.0] * training_weeks)

        # Working phase
        j = pl.Series(range(1, working_weeks + 1), dtype=pl.Float64)
        debt_working = (
            _fv_principal(D_train, r1, j) - _fv_annuity(cf_w, r1, j)
        ).clip(lower_bound=0.0)

        if D_train * r1 < cf_w:
            j_clear = math.ceil(math.log(cf_w / (cf_w - D_train * r1)) / math.log(1 + r1))
        else:
            j_clear = working_weeks + 1

        if j_clear <= working_weeks:
            D_penult      = D_train * (1 + r1) ** (j_clear - 1) - cf_w * ((1 + r1) ** (j_clear - 1) - 1) / r1
            first_savings = max(0.0, cf_w - D_penult * (1 + r1))
            k_s = (j - j_clear).clip(lower_bound=0.0)
            savings_working = (
                _fv_principal(first_savings, r_s, k_s) + _fv_annuity(cf_w, r_s, k_s)
            ) * (j >= j_clear).cast(pl.Float64)
        else:
            savings_working = pl.Series([0.0] * working_weeks)

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

    return (simulate,)


@app.cell
def _(mo):
    initial_debt       = mo.ui.number(value=20_000, start=0, step=1000, label="Initial debt ($)")
    post_refi_rate     = mo.ui.slider(value=0.09, start=0.01, stop=0.25, step=0.01, show_value=True, label="Annual rate")
    training_years     = mo.ui.slider(value=3, start=1, stop=10, step=1, show_value=True, label="Training years")
    weekly_income_t    = mo.ui.number(value=350, start=0, step=10, label="Training income ($/wk)")
    weekly_expenses_t  = mo.ui.number(value=350, start=0, step=10, label="Training expenses ($/wk)")
    weekly_take_home   = mo.ui.number(value=1000, start=0, step=10, label="Working take-home ($/wk)")
    weekly_expenses_w  = mo.ui.number(value=450, start=0, step=10, label="Working expenses ($/wk)")
    annual_return      = mo.ui.slider(value=0.09, start=0.01, stop=0.15, step=0.01, show_value=True, label="Annual investment return")
    years_to_project   = mo.ui.slider(value=6, start=5, stop=20, step=1, show_value=True, label="Years to project")
    mo.vstack([
        initial_debt, post_refi_rate,
        training_years, weekly_income_t, weekly_expenses_t,
        weekly_take_home, weekly_expenses_w, annual_return, years_to_project,
    ])
    return (
        annual_return,
        initial_debt,
        post_refi_rate,
        training_years,
        weekly_expenses_t,
        weekly_expenses_w,
        weekly_income_t,
        weekly_take_home,
        years_to_project,
    )


@app.cell
def _(
    annual_return,
    initial_debt,
    post_refi_rate,
    simulate,
    training_years,
    weekly_expenses_t,
    weekly_expenses_w,
    weekly_income_t,
    weekly_take_home,
    years_to_project,
):
    df = simulate(
        initial_debt=initial_debt.value,
        post_refi_rate=post_refi_rate.value,
        training_years=training_years.value,
        weekly_income_t=weekly_income_t.value,
        weekly_expenses_t=weekly_expenses_t.value,
        weekly_take_home=weekly_take_home.value,
        weekly_expenses_w=weekly_expenses_w.value,
        annual_return=annual_return.value,
        years_to_project=years_to_project.value,
    )
    return (df,)


@app.cell
def _(df, pl):
    from matplotlib.figure import Figure
    import matplotlib.ticker as mticker

    training_end = df.filter(pl.col("phase") == "training")["year"].max()
    x_max        = df["year"].max()

    fig = Figure(figsize=(8, 4))
    ax = fig.add_subplot(111)

    ax.axvspan(0,            training_end, color="sandybrown", alpha=0.15, zorder=0)
    ax.axvspan(training_end, x_max,        color="steelblue",  alpha=0.10, zorder=0)
    ax.axvline(training_end, color="gray", linewidth=1, linestyle="--", zorder=1)

    t = ax.get_xaxis_transform()
    ax.text(training_end / 2,               0.97, "Training", ha="center", va="top", transform=t, color="saddlebrown", fontsize=9)
    ax.text((training_end + x_max) / 2 + 0.5, 0.97, "Working",  ha="center", va="top", transform=t, color="steelblue",   fontsize=9)

    ax.plot(df["year"], df["net_worth"], label="Net worth", color="seagreen", linewidth=2, zorder=2)
    ax.axhline(0, color="black", linewidth=0.5, linestyle="--", zorder=1)
    ax.set_xlabel("Year")
    ax.set_xlim(left=0)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax.legend()
    fig.tight_layout()
    fig
    return


if __name__ == "__main__":
    app.run()
