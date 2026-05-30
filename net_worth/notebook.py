import marimo

__generated_with = "0.23.8"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    from net_worth import simulate

    return mo, simulate


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
def _(df):
    from matplotlib.figure import Figure
    import matplotlib.ticker as mticker

    fig = Figure(figsize=(8, 4))
    ax = fig.add_subplot(111)
    ax.plot(df["year"], df["net_worth"], label="Net worth", color="seagreen", linewidth=2)
    ax.axhline(0, color="black", linewidth=0.5, linestyle="--")
    ax.set_xlabel("Year")
    ax.set_xlim(left=0)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax.legend()
    fig.tight_layout()
    fig
    return


if __name__ == "__main__":
    app.run()
