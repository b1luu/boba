"""Write a weekday bar chart for average boba demand over a fixed date range."""

import argparse
from html import escape
import math
from pathlib import Path

import pandas as pd


DEFAULT_INPUT_PATH = "data/clean/clean.csv"
DEFAULT_START_DATE = "2026-03-01"
DEFAULT_END_DATE = "2026-04-20"
DEFAULT_OUTPUT_SVG = (
    "data/analysis/boba_weekday_avg_2026-03-01_to_2026-04-20.svg"
)
DEFAULT_OUTPUT_CSV = (
    "data/analysis/boba_weekday_avg_2026-03-01_to_2026-04-20.csv"
)
DAY_ORDER = [
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        default=DEFAULT_INPUT_PATH,
        help=f"Input cleaned CSV path (default: {DEFAULT_INPUT_PATH})",
    )
    parser.add_argument(
        "--start-date",
        default=DEFAULT_START_DATE,
        help=f"Inclusive start date in YYYY-MM-DD format (default: {DEFAULT_START_DATE})",
    )
    parser.add_argument(
        "--end-date",
        default=DEFAULT_END_DATE,
        help=f"Inclusive end date in YYYY-MM-DD format (default: {DEFAULT_END_DATE})",
    )
    parser.add_argument(
        "--output-svg",
        default=DEFAULT_OUTPUT_SVG,
        help=f"Output SVG path (default: {DEFAULT_OUTPUT_SVG})",
    )
    parser.add_argument(
        "--output-csv",
        default=DEFAULT_OUTPUT_CSV,
        help=f"Output CSV path (default: {DEFAULT_OUTPUT_CSV})",
    )
    parser.add_argument(
        "--chart-only",
        action="store_true",
        help="Render a chart-only SVG without title, subtitle, or notes.",
    )
    return parser.parse_args()


def require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def boba_modifier_units(modifiers: str) -> float:
    units = 0.0
    for modifier in str(modifiers).split(","):
        token = modifier.strip().lower().replace("\u00d7", "x")
        if token == "boba":
            units += 1
        elif token.startswith("boba x"):
            amount = token.removeprefix("boba x").strip()
            parsed = pd.to_numeric(amount, errors="coerce")
            if pd.notna(parsed):
                units += float(parsed)
    return units


def nice_axis_max(value: float) -> float:
    if value <= 10:
        return 10.0
    for step in [5.0, 10.0, 25.0, 50.0]:
        ceiling = step * math.ceil(value / step)
        if ceiling / step <= 12:
            return float(ceiling)
    return float(((value + 99) // 100) * 100)


def build_summary(
    input_path: Path,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
) -> pd.DataFrame:
    df = pd.read_csv(input_path, low_memory=False)
    require_columns(df, ["Date", "Item", "Qty", "Modifiers Applied"])

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Qty"] = pd.to_numeric(df["Qty"], errors="coerce").fillna(0)
    df = df.dropna(subset=["Date"]).copy()

    df = df.loc[(df["Date"] >= start_date) & (df["Date"] <= end_date)].copy()
    if df.empty:
        raise ValueError(
            f"No rows found between {start_date.date()} and {end_date.date()}"
        )

    item = df["Item"].fillna("").astype(str).str.strip()
    modifiers = df["Modifiers Applied"].fillna("").astype(str)
    is_taiwanese_retro = item.str.fullmatch(r"(?i)\s*Taiwanese Retro\s*")

    modifier_units = modifiers.apply(boba_modifier_units).fillna(0)
    df["boba_units"] = df["Qty"] * (modifier_units + is_taiwanese_retro.astype(float))
    df["day_of_week"] = df["Date"].dt.day_name()

    daily = (
        df.groupby(["Date", "day_of_week"], as_index=False)
        .agg(boba_units=("boba_units", "sum"))
    )

    summary = (
        daily.groupby("day_of_week", as_index=False)
        .agg(
            dates_count=("Date", "nunique"),
            avg_estimated_cups_of_boba_sold_per_day=("boba_units", "mean"),
        )
    )
    summary["day_of_week"] = pd.Categorical(
        summary["day_of_week"],
        categories=DAY_ORDER,
        ordered=True,
    )
    summary = summary.sort_values("day_of_week").reset_index(drop=True)
    summary["avg_estimated_cups_of_boba_sold_per_day"] = (
        summary["avg_estimated_cups_of_boba_sold_per_day"].round(2)
    )
    return summary


def render_svg(
    summary: pd.DataFrame,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
) -> str:
    width = 1100
    height = 760
    chart_left = 110
    chart_top = 170
    chart_width = 880
    chart_height = 380
    chart_bottom = chart_top + chart_height
    chart_right = chart_left + chart_width
    footer_y = 640

    max_value = float(summary["avg_estimated_cups_of_boba_sold_per_day"].max())
    axis_max = nice_axis_max(max_value)
    tick_count = 5
    tick_step = axis_max / tick_count
    band_width = chart_width / len(summary)
    bar_width = band_width * 0.62

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">Average Estimated Cups of Boba Sold per Day by Weekday</title>',
        '<desc id="desc">Bar chart for March 1, 2026 through April 20, 2026. One cup equals one normal boba serving. Boba equals one cup, Boba x 2 equals two cups, Boba x 3 equals three cups, and Taiwanese Retro contributes one default cup per drink.</desc>',
        '<rect width="100%" height="100%" fill="#fbfaf7" />',
        '<text x="60" y="64" font-family="Inter, Arial, sans-serif" font-size="28" font-weight="700" fill="#1f2937">Average Estimated Cups of Boba Sold per Day by Weekday</text>',
        (
            f'<text x="60" y="95" font-family="Inter, Arial, sans-serif" '
            f'font-size="16" fill="#4b5563">{escape(str(start_date.date()))} to '
            f'{escape(str(end_date.date()))} | Cleaned positive-sale transactions only</text>'
        ),
        (
            '<text x="60" y="124" font-family="Inter, Arial, sans-serif" '
            'font-size="13" fill="#6b7280">Definition: 1 cup = 1 normal boba serving. '
            'Boba = 1 cup, Boba x 2 = 2 cups, Boba x 3 = 3 cups, Taiwanese Retro = 1 cup '
            'per drink. Daily totals are summed by date, then averaged within each weekday.</text>'
        ),
    ]

    for tick in range(tick_count + 1):
        value = tick * tick_step
        y = chart_bottom - (value / axis_max) * chart_height
        lines.append(
            f'<line x1="{chart_left}" y1="{y:.2f}" x2="{chart_right}" y2="{y:.2f}" stroke="#d1d5db" stroke-width="1" />'
        )
        lines.append(
            f'<text x="{chart_left - 14}" y="{y + 5:.2f}" text-anchor="end" font-family="Inter, Arial, sans-serif" font-size="12" fill="#6b7280">{value:.0f}</text>'
        )

    lines.append(
        f'<line x1="{chart_left}" y1="{chart_bottom}" x2="{chart_right}" y2="{chart_bottom}" stroke="#374151" stroke-width="1.5" />'
    )

    for idx, row in summary.iterrows():
        value = float(row["avg_estimated_cups_of_boba_sold_per_day"])
        bar_height = 0 if axis_max == 0 else (value / axis_max) * chart_height
        x = chart_left + idx * band_width + (band_width - bar_width) / 2
        y = chart_bottom - bar_height
        day = str(row["day_of_week"])
        dates_count = int(row["dates_count"])
        bar_color = "#0f766e" if day not in {"Saturday", "Sunday"} else "#b45309"

        lines.append(
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_width:.2f}" height="{bar_height:.2f}" rx="4" ry="4" fill="{bar_color}" />'
        )
        lines.append(
            f'<text x="{x + bar_width / 2:.2f}" y="{y - 10:.2f}" text-anchor="middle" font-family="Inter, Arial, sans-serif" font-size="13" font-weight="600" fill="#111827">{value:.2f}</text>'
        )
        lines.append(
            f'<text x="{x + bar_width / 2:.2f}" y="{chart_bottom + 28:.2f}" text-anchor="middle" font-family="Inter, Arial, sans-serif" font-size="13" fill="#111827">{escape(day)}</text>'
        )
        lines.append(
            f'<text x="{x + bar_width / 2:.2f}" y="{chart_bottom + 48:.2f}" text-anchor="middle" font-family="Inter, Arial, sans-serif" font-size="12" fill="#6b7280">n={dates_count} dates</text>'
        )

    lines.extend(
        [
            f'<text x="{chart_left}" y="{footer_y}" font-family="Inter, Arial, sans-serif" font-size="14" font-weight="600" fill="#1f2937">Reading note</text>',
            f'<text x="{chart_left}" y="{footer_y + 24}" font-family="Inter, Arial, sans-serif" font-size="13" fill="#4b5563">This chart estimates topping demand, not unique customers. A cup means one normal boba serving counted from drink quantity and explicit boba modifiers.</text>',
            f'<text x="{chart_left}" y="{footer_y + 46}" font-family="Inter, Arial, sans-serif" font-size="13" fill="#4b5563">Weekday values are averages across actual calendar dates in the selected range, shown under each bar as n.</text>',
            "</svg>",
        ]
    )
    return "\n".join(lines)


def render_svg_chart_only(summary: pd.DataFrame) -> str:
    width = 980
    height = 700
    chart_left = 90
    chart_top = 88
    chart_width = 845
    chart_height = 430
    chart_bottom = chart_top + chart_height
    chart_right = chart_left + chart_width

    max_value = float(summary["avg_estimated_cups_of_boba_sold_per_day"].max())
    axis_max = nice_axis_max(max_value)
    tick_count = 5
    tick_step = axis_max / tick_count
    band_width = chart_width / len(summary)
    bar_width = band_width * 0.62

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">Average Estimated Cups of Boba Sold per Day by Weekday</title>',
        '<desc id="desc">Chart-only bar chart. One cup equals one normal boba serving. Boba equals one cup, Boba x 2 equals two cups, Boba x 3 equals three cups, and Taiwanese Retro contributes one default cup per drink.</desc>',
        '<rect width="100%" height="100%" fill="#ffffff" />',
        f'<text x="{width / 2:.2f}" y="42" text-anchor="middle" font-family="Inter, Arial, sans-serif" font-size="28" font-weight="700" fill="#1f2937">Average Estimated Cups of Boba Sold by Weekday</text>',
        f'<text x="28" y="{chart_top + chart_height / 2:.2f}" text-anchor="middle" transform="rotate(-90 28 {chart_top + chart_height / 2:.2f})" font-family="Inter, Arial, sans-serif" font-size="14" font-weight="600" fill="#374151">Cups Sold</text>',
    ]

    for tick in range(tick_count + 1):
        value = tick * tick_step
        y = chart_bottom - (value / axis_max) * chart_height
        lines.append(
            f'<line x1="{chart_left}" y1="{y:.2f}" x2="{chart_right}" y2="{y:.2f}" stroke="#d1d5db" stroke-width="1" />'
        )
        lines.append(
            f'<text x="{chart_left - 14}" y="{y + 5:.2f}" text-anchor="end" font-family="Inter, Arial, sans-serif" font-size="12" fill="#6b7280">{value:.0f}</text>'
        )

    lines.append(
        f'<line x1="{chart_left}" y1="{chart_bottom}" x2="{chart_right}" y2="{chart_bottom}" stroke="#374151" stroke-width="1.5" />'
    )

    for idx, row in summary.iterrows():
        value = float(row["avg_estimated_cups_of_boba_sold_per_day"])
        bar_height = 0 if axis_max == 0 else (value / axis_max) * chart_height
        x = chart_left + idx * band_width + (band_width - bar_width) / 2
        y = chart_bottom - bar_height
        day = str(row["day_of_week"])
        dates_count = int(row["dates_count"])
        bar_color = "#0f766e" if day not in {"Saturday", "Sunday"} else "#b45309"

        lines.append(
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_width:.2f}" height="{bar_height:.2f}" rx="4" ry="4" fill="{bar_color}" />'
        )
        lines.append(
            f'<text x="{x + bar_width / 2:.2f}" y="{y - 10:.2f}" text-anchor="middle" font-family="Inter, Arial, sans-serif" font-size="13" font-weight="600" fill="#111827">{value:.2f}</text>'
        )
        lines.append(
            f'<text x="{x + bar_width / 2:.2f}" y="{chart_bottom + 30:.2f}" text-anchor="middle" font-family="Inter, Arial, sans-serif" font-size="13" fill="#111827">{escape(day)}</text>'
        )
        lines.append(
            f'<text x="{x + bar_width / 2:.2f}" y="{chart_bottom + 54:.2f}" text-anchor="middle" font-family="Inter, Arial, sans-serif" font-size="12" fill="#6b7280">n={dates_count} dates</text>'
        )

    lines.append(
        f'<text x="{chart_left + chart_width / 2:.2f}" y="{chart_bottom + 92:.2f}" text-anchor="middle" font-family="Inter, Arial, sans-serif" font-size="14" font-weight="600" fill="#374151">Day of Week</text>'
    )
    lines.append("</svg>")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_svg = Path(args.output_svg)
    output_csv = Path(args.output_csv)
    start_date = pd.Timestamp(args.start_date)
    end_date = pd.Timestamp(args.end_date)

    if start_date > end_date:
        raise ValueError("--start-date must be on or before --end-date")

    summary = build_summary(input_path, start_date, end_date)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    output_svg.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(output_csv, index=False)
    output_svg.write_text(
        (
            render_svg_chart_only(summary)
            if args.chart_only
            else render_svg(summary, start_date, end_date)
        ),
        encoding="utf-8",
    )

    print(f"Wrote chart data: {output_csv}")
    print(f"Wrote SVG chart: {output_svg}")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
