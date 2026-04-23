"""Check whether daily boba usage scales with daily net sales."""

import argparse
from pathlib import Path

import pandas as pd

DEFAULT_INPUT_PATH = "data/clean/clean.csv"
DEFAULT_START_DATE = "2026-03-01"
DEFAULT_END_DATE = "2026-04-20"
DEFAULT_OUTPUT_DIR = "data/analysis/boba_vs_sales"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=DEFAULT_INPUT_PATH)
    parser.add_argument("--start-date", default=DEFAULT_START_DATE)
    parser.add_argument("--end-date", default=DEFAULT_END_DATE)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--skip-timeseries", action="store_true",
                        help="Skip writing the timeseries chart.")
    return parser.parse_args()


def require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def boba_cups(modifiers: str) -> float:
    total = 0.0
    for part in str(modifiers).split(","):
        token = part.strip().lower().replace("×", "x")
        if token == "boba":
            total += 1.0
        elif token.startswith("boba x"):
            parsed = pd.to_numeric(token.removeprefix("boba x").strip(), errors="coerce")
            if pd.notna(parsed):
                total += float(parsed)
    return total


def build_daily(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Qty"] = pd.to_numeric(df["Qty"], errors="coerce").fillna(0)
    df["Net Sales"] = pd.to_numeric(df["Net Sales"], errors="coerce").fillna(0)
    df = df.dropna(subset=["Date"])
    df = df.loc[(df["Date"] >= start) & (df["Date"] <= end)].copy()
    if df.empty:
        raise ValueError(f"No rows between {start.date()} and {end.date()}")

    df["Item"] = df["Item"].fillna("").astype(str).str.strip()
    df["Modifiers Applied"] = df["Modifiers Applied"].fillna("").astype(str)
    is_taiwanese_retro = df["Item"].str.fullmatch(r"(?i)\s*Taiwanese Retro\s*")
    cups_per_item = df["Modifiers Applied"].map(boba_cups) + is_taiwanese_retro.astype(float)
    df["Cups w/ Boba"] = df["Qty"] * cups_per_item

    daily = (
        df.groupby("Date", as_index=False)
        .agg(**{
            "Cups w/ Boba": ("Cups w/ Boba", "sum"),
            "Net Sales": ("Net Sales", "sum"),
        })
        .sort_values("Date")
        .reset_index(drop=True)
    )

    full = pd.DataFrame({"Date": pd.date_range(start=start, end=end, freq="D")})
    daily = full.merge(daily, on="Date", how="left").fillna(
        {"Cups w/ Boba": 0, "Net Sales": 0.0}
    )
    return daily


def analyze(daily: pd.DataFrame) -> dict:
    active = daily.loc[(daily["Cups w/ Boba"] > 0) & (daily["Net Sales"] > 0)].copy()
    cups = active["Cups w/ Boba"].to_numpy(dtype=float)
    sales = active["Net Sales"].to_numpy(dtype=float)

    pearson = active[["Cups w/ Boba", "Net Sales"]].corr().iloc[0, 1]

    # Linear regression: sales = slope * cups + intercept
    n = len(active)
    mean_c = cups.mean()
    mean_s = sales.mean()
    cov = ((cups - mean_c) * (sales - mean_s)).sum() / n
    var_c = ((cups - mean_c) ** 2).sum() / n
    slope = cov / var_c
    intercept = mean_s - slope * mean_c
    residuals = sales - (slope * cups + intercept)
    ss_res = (residuals ** 2).sum()
    ss_tot = ((sales - mean_s) ** 2).sum()
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")

    # Proportional fit through the origin: sales = k * cups
    k = (cups * sales).sum() / (cups ** 2).sum()
    residuals_prop = sales - k * cups
    ss_res_prop = (residuals_prop ** 2).sum()
    r2_prop = 1 - ss_res_prop / ss_tot if ss_tot > 0 else float("nan")

    active["Sales per Boba Cup"] = active["Net Sales"] / active["Cups w/ Boba"]

    return {
        "active": active,
        "pearson": float(pearson),
        "slope": float(slope),
        "intercept": float(intercept),
        "r2": float(r2),
        "k_proportional": float(k),
        "r2_proportional": float(r2_prop),
        "ratio_mean": float(active["Sales per Boba Cup"].mean()),
        "ratio_median": float(active["Sales per Boba Cup"].median()),
        "ratio_std": float(active["Sales per Boba Cup"].std(ddof=0)),
        "ratio_cv": float(
            active["Sales per Boba Cup"].std(ddof=0) / active["Sales per Boba Cup"].mean()
        ),
        "n_days": int(n),
    }


def save_outputs(daily: pd.DataFrame, stats: dict, output_dir: Path,
                 skip_timeseries: bool = False) -> None:
    import matplotlib.pyplot as plt

    output_dir.mkdir(parents=True, exist_ok=True)

    daily_csv = output_dir / "daily_boba_vs_sales.csv"
    out = daily.copy()
    out["Date"] = pd.to_datetime(out["Date"]).dt.strftime("%Y-%m-%d")
    out["Net Sales"] = out["Net Sales"].round(2)
    out.to_csv(daily_csv, index=False)

    summary_path = output_dir / "summary.txt"
    lines = [
        f"Days analyzed (active): {stats['n_days']}",
        f"Pearson correlation (cups, sales): {stats['pearson']:.4f}",
        "",
        "Linear fit   sales = slope * cups + intercept",
        f"  slope     = ${stats['slope']:.4f} per boba cup",
        f"  intercept = ${stats['intercept']:.2f}",
        f"  R^2       = {stats['r2']:.4f}",
        "",
        "Proportional fit (through origin)   sales = k * cups",
        f"  k   = ${stats['k_proportional']:.4f} per boba cup",
        f"  R^2 = {stats['r2_proportional']:.4f}",
        "",
        "Per-day sales / cup ratio",
        f"  mean   = ${stats['ratio_mean']:.4f}",
        f"  median = ${stats['ratio_median']:.4f}",
        f"  stdev  = ${stats['ratio_std']:.4f}",
        f"  CV     = {stats['ratio_cv']:.4f}   (lower = tighter proportionality)",
    ]
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    active = stats["active"]
    plt.style.use("seaborn-v0_8-whitegrid")

    fig, ax = plt.subplots(figsize=(9, 6))
    ax.scatter(active["Cups w/ Boba"], active["Net Sales"], s=40, color="#0f766e", alpha=0.8)
    xs = pd.Series(sorted(active["Cups w/ Boba"].tolist()))
    ax.plot(xs, stats["slope"] * xs + stats["intercept"], color="#b45309", lw=2,
            label=f"linear fit  R²={stats['r2']:.3f}")
    ax.plot(xs, stats["k_proportional"] * xs, color="#334155", lw=2, ls="--",
            label=f"proportional fit  R²={stats['r2_proportional']:.3f}")
    ax.set_title("Daily Boba Cups vs. Net Sales", fontsize=15, weight="bold")
    ax.set_xlabel("Cups w/ Boba")
    ax.set_ylabel("Net Sales ($)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_dir / "scatter_cups_vs_sales.png", dpi=200)
    plt.close(fig)

    if not skip_timeseries:
        fig, ax1 = plt.subplots(figsize=(12, 5.5))
        ax1.plot(daily["Date"], daily["Cups w/ Boba"], color="#0f766e", lw=2, label="Cups w/ Boba")
        ax1.set_ylabel("Cups w/ Boba", color="#0f766e")
        ax1.tick_params(axis="y", labelcolor="#0f766e")
        ax2 = ax1.twinx()
        ax2.plot(daily["Date"], daily["Net Sales"], color="#b45309", lw=2, label="Net Sales")
        ax2.set_ylabel("Net Sales ($)", color="#b45309")
        ax2.tick_params(axis="y", labelcolor="#b45309")
        ax1.set_title("Daily Boba Cups and Net Sales Over Time", fontsize=15, weight="bold")
        fig.autofmt_xdate()
        fig.tight_layout()
        fig.savefig(output_dir / "timeseries_cups_and_sales.png", dpi=200)
        plt.close(fig)

    print("Wrote:")
    print(f"  {daily_csv}")
    print(f"  {summary_path}")
    print(f"  {output_dir / 'scatter_cups_vs_sales.png'}")
    if not skip_timeseries:
        print(f"  {output_dir / 'timeseries_cups_and_sales.png'}")


def main() -> None:
    args = parse_args()
    start = pd.Timestamp(args.start_date)
    end = pd.Timestamp(args.end_date)
    if start > end:
        raise ValueError("--start-date must be on or before --end-date")

    df = pd.read_csv(args.input, low_memory=False)
    require_columns(df, ["Date", "Item", "Qty", "Modifiers Applied", "Net Sales"])

    daily = build_daily(df, start, end)
    stats = analyze(daily)

    print(f"Date range: {start.date()} to {end.date()}")
    print(f"Active days: {stats['n_days']}")
    print(f"Pearson r         = {stats['pearson']:.4f}")
    print(f"Linear slope      = ${stats['slope']:.4f} per cup   intercept = ${stats['intercept']:.2f}   R² = {stats['r2']:.4f}")
    print(f"Proportional k    = ${stats['k_proportional']:.4f} per cup   R² = {stats['r2_proportional']:.4f}")
    print(f"Per-day $/cup     mean=${stats['ratio_mean']:.3f}  median=${stats['ratio_median']:.3f}  CV={stats['ratio_cv']:.3f}")

    save_outputs(daily, stats, Path(args.output_dir), skip_timeseries=args.skip_timeseries)


if __name__ == "__main__":
    main()
