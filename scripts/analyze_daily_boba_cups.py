"""Analyze daily cups-with-boba sales and generate summary tables and charts."""

import argparse
from pathlib import Path

import pandas as pd

DAY_ORDER = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        default="data/analysis/daily_boba_cups_2026-03-01_to_2026-04-20.csv",
        help="Path to the input CSV dataset.",
    )
    parser.add_argument(
        "--output-dir",
        default="data/analysis/daily_boba_cups_report",
        help="Directory where summary CSVs and charts will be written.",
    )
    return parser.parse_args()


def require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def load_and_prepare(input_path: Path) -> pd.DataFrame:
    df = pd.read_csv(input_path)
    require_columns(df, ["Date", "Cups w/ Boba"])

    # Step 1: convert Date to datetime.
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Cups w/ Boba"] = pd.to_numeric(df["Cups w/ Boba"], errors="coerce")
    df = df.dropna(subset=["Date", "Cups w/ Boba"]).copy()

    # Step 2: create an ordered weekday column.
    df["Day of Week"] = pd.Categorical(
        df["Date"].dt.day_name(),
        categories=DAY_ORDER,
        ordered=True,
    )

    return df.sort_values("Date").reset_index(drop=True)


def compute_summary(df: pd.DataFrame) -> tuple[pd.DataFrame, float]:
    weekday_summary = (
        df.groupby("Day of Week", observed=True, as_index=False)
        .agg(
            **{
                "Average Cups Sold": ("Cups w/ Boba", "mean"),
                "Total Cups Sold": ("Cups w/ Boba", "sum"),
                "Days Observed": ("Date", "nunique"),
            }
        )
        .sort_values("Day of Week")
        .reset_index(drop=True)
    )
    weekday_summary["Average Cups Sold"] = weekday_summary["Average Cups Sold"].round(2)

    overall_daily_average = round(float(df["Cups w/ Boba"].mean()), 2)
    return weekday_summary, overall_daily_average


def build_key_insight(
    weekday_summary: pd.DataFrame,
    overall_daily_average: float,
) -> tuple[str, str, str]:
    highest_row = weekday_summary.loc[weekday_summary["Average Cups Sold"].idxmax()]
    lowest_row = weekday_summary.loc[weekday_summary["Average Cups Sold"].idxmin()]

    highest_day = str(highest_row["Day of Week"])
    lowest_day = str(lowest_row["Day of Week"])
    highest_avg = float(highest_row["Average Cups Sold"])
    lowest_avg = float(lowest_row["Average Cups Sold"])

    insight = (
        f"{highest_day} has the strongest average boba demand at {highest_avg:.2f} cups per day, "
        f"while {lowest_day} is the weakest at {lowest_avg:.2f}. "
        f"The overall daily average is {overall_daily_average:.2f} cups, with demand rising into the weekend."
    )
    return highest_day, lowest_day, insight


def save_charts(
    df: pd.DataFrame,
    weekday_summary: pd.DataFrame,
    output_dir: Path,
) -> tuple[Path, Path]:
    import matplotlib.pyplot as plt

    plt.style.use("seaborn-v0_8-whitegrid")

    line_chart_path = output_dir / "cups_with_boba_over_time.png"
    bar_chart_path = output_dir / "average_cups_with_boba_by_weekday.png"

    fig, ax = plt.subplots(figsize=(12, 5.5))
    ax.plot(
        df["Date"],
        df["Cups w/ Boba"],
        color="#0f766e",
        linewidth=2.2,
        marker="o",
        markersize=4,
    )
    ax.set_title("Cups with Boba Sold per Day", fontsize=16, weight="bold")
    ax.set_xlabel("Date")
    ax.set_ylabel("Cups w/ Boba")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(line_chart_path, dpi=200, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5.5))
    colors = ["#0f766e"] * 5 + ["#b45309", "#b45309"]
    ax.bar(
        weekday_summary["Day of Week"].astype(str),
        weekday_summary["Average Cups Sold"],
        color=colors,
        width=0.65,
    )
    ax.set_title("Average Cups with Boba Sold by Weekday", fontsize=16, weight="bold")
    ax.set_xlabel("Day of Week")
    ax.set_ylabel("Average Cups w/ Boba")
    for idx, value in enumerate(weekday_summary["Average Cups Sold"]):
        ax.text(idx, value + 0.6, f"{value:.2f}", ha="center", va="bottom", fontsize=10)
    fig.tight_layout()
    fig.savefig(bar_chart_path, dpi=200, bbox_inches="tight")
    plt.close(fig)

    return line_chart_path, bar_chart_path


def save_report_artifacts(
    weekday_summary: pd.DataFrame,
    overall_daily_average: float,
    highest_day: str,
    lowest_day: str,
    insight: str,
    output_dir: Path,
) -> tuple[Path, Path]:
    summary_csv_path = output_dir / "weekday_summary.csv"
    report_text_path = output_dir / "summary.txt"

    weekday_summary.to_csv(summary_csv_path, index=False)

    report_lines = [
        f"Overall daily average: {overall_daily_average:.2f} cups",
        f"Highest average day: {highest_day}",
        f"Lowest average day: {lowest_day}",
        f"Key insight: {insight}",
    ]
    report_text_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    return summary_csv_path, report_text_path


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = load_and_prepare(input_path)
    weekday_summary, overall_daily_average = compute_summary(df)
    highest_day, lowest_day, insight = build_key_insight(
        weekday_summary,
        overall_daily_average,
    )

    summary_csv_path, report_text_path = save_report_artifacts(
        weekday_summary,
        overall_daily_average,
        highest_day,
        lowest_day,
        insight,
        output_dir,
    )
    line_chart_path, bar_chart_path = save_charts(df, weekday_summary, output_dir)

    print("Prepared dataset preview:")
    print(df.head().to_string(index=False))
    print()
    print("Weekday summary:")
    print(weekday_summary.to_string(index=False))
    print()
    print(f"Overall daily average: {overall_daily_average:.2f} cups")
    print(f"Highest average day: {highest_day}")
    print(f"Lowest average day: {lowest_day}")
    print(f"Key insight: {insight}")
    print()
    print(f"Wrote weekday summary CSV: {summary_csv_path}")
    print(f"Wrote summary text: {report_text_path}")
    print(f"Wrote line chart: {line_chart_path}")
    print(f"Wrote weekday bar chart: {bar_chart_path}")


if __name__ == "__main__":
    main()
