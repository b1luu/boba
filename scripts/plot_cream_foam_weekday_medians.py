"""Calculate and chart median daily cream foam drink demand by weekday."""

import argparse
from html import escape
import math
from pathlib import Path

import pandas as pd


DEFAULT_INPUT_PATH = "data/clean/clean.csv"
DEFAULT_OUTPUT_SVG = "data/analysis/cream_foam_weekday_medians.svg"
DEFAULT_OUTPUT_PNG = "data/analysis/cream_foam_weekday_medians.png"
DEFAULT_OUTPUT_CSV = "data/analysis/cream_foam_weekday_medians.csv"
DEFAULT_OUTPUT_DAILY_CSV = "data/analysis/daily_cream_foam_drinks.csv"
DAY_ORDER = [
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
]
SERIES = [
    {
        "label": "Brown Sugar Cream Foam",
        "column": "brown_sugar_cream_foam_drinks",
        "median_column": "median_brown_sugar_cream_foam_drinks",
        "color": "#7c3f1d",
    },
    {
        "label": "Pistachio Foam",
        "column": "pistachio_foam_drinks",
        "median_column": "median_pistachio_foam_drinks",
        "color": "#4f7d35",
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        default=DEFAULT_INPUT_PATH,
        help=f"Input cleaned CSV path (default: {DEFAULT_INPUT_PATH})",
    )
    parser.add_argument(
        "--output-svg",
        default=DEFAULT_OUTPUT_SVG,
        help=f"Output SVG path (default: {DEFAULT_OUTPUT_SVG})",
    )
    parser.add_argument(
        "--output-png",
        default=DEFAULT_OUTPUT_PNG,
        help=f"Output PNG path (default: {DEFAULT_OUTPUT_PNG})",
    )
    parser.add_argument(
        "--output-csv",
        default=DEFAULT_OUTPUT_CSV,
        help=f"Output weekday summary CSV path (default: {DEFAULT_OUTPUT_CSV})",
    )
    parser.add_argument(
        "--output-daily-csv",
        default=DEFAULT_OUTPUT_DAILY_CSV,
        help=f"Output daily totals CSV path (default: {DEFAULT_OUTPUT_DAILY_CSV})",
    )
    parser.add_argument(
        "--start-date",
        default=None,
        help="Optional inclusive start date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--end-date",
        default=None,
        help="Optional inclusive end date in YYYY-MM-DD format.",
    )
    return parser.parse_args()


def require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def has_modifier(modifiers: pd.Series, modifier_name: str) -> pd.Series:
    escaped = modifier_name.replace(" ", r"\s+")
    return modifiers.str.contains(
        rf"(?i)(?:^|,\s*){escaped}(?:\s*(?:x|×)\s*[0-9.]+)?(?:\s*,|$)",
        regex=True,
    )


def nice_axis_max(value: float) -> float:
    if value <= 10:
        return 10.0
    for step in [5.0, 10.0, 25.0, 50.0]:
        ceiling = step * math.ceil(value / step)
        if ceiling / step <= 12:
            return float(ceiling)
    return float(((value + 99) // 100) * 100)


def build_daily_totals(
    input_path: Path,
    start_date: pd.Timestamp | None,
    end_date: pd.Timestamp | None,
) -> pd.DataFrame:
    df = pd.read_csv(input_path, low_memory=False)
    require_columns(df, ["Date", "Item", "Qty", "Modifiers Applied"])

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Qty"] = pd.to_numeric(df["Qty"], errors="coerce").fillna(0)
    df = df.dropna(subset=["Date"]).copy()

    if start_date is not None:
        df = df.loc[df["Date"] >= start_date].copy()
    if end_date is not None:
        df = df.loc[df["Date"] <= end_date].copy()
    if df.empty:
        raise ValueError("No rows found for the selected date range")

    item = df["Item"].fillna("").astype(str).str.strip()
    modifiers = df["Modifiers Applied"].fillna("").astype(str)

    brown_sugar_mask = item.str.fullmatch(
        r"(?i)\s*Brown Sugar Mist\s*"
    ) | has_modifier(modifiers, "Brown Sugar Cream Foam")
    pistachio_mask = item.str.fullmatch(
        r"(?i)\s*Pistachio Mist\s*"
    ) | has_modifier(modifiers, "Pistachio Foam")

    df["day_of_week"] = df["Date"].dt.day_name()
    df["brown_sugar_cream_foam_drinks"] = df["Qty"].where(brown_sugar_mask, 0)
    df["pistachio_foam_drinks"] = df["Qty"].where(pistachio_mask, 0)

    daily = (
        df.groupby(["Date", "day_of_week"], as_index=False)
        .agg(
            brown_sugar_cream_foam_drinks=(
                "brown_sugar_cream_foam_drinks",
                "sum",
            ),
            pistachio_foam_drinks=("pistachio_foam_drinks", "sum"),
        )
        .sort_values("Date")
        .reset_index(drop=True)
    )
    daily["Date"] = daily["Date"].dt.date
    return daily


def build_weekday_summary(daily: pd.DataFrame) -> pd.DataFrame:
    summary = daily.groupby("day_of_week", as_index=False).agg(
        dates_count=("Date", "nunique"),
        median_brown_sugar_cream_foam_drinks=(
            "brown_sugar_cream_foam_drinks",
            "median",
        ),
        median_pistachio_foam_drinks=("pistachio_foam_drinks", "median"),
        avg_brown_sugar_cream_foam_drinks=(
            "brown_sugar_cream_foam_drinks",
            "mean",
        ),
        avg_pistachio_foam_drinks=("pistachio_foam_drinks", "mean"),
    )
    summary["day_of_week"] = pd.Categorical(
        summary["day_of_week"],
        categories=DAY_ORDER,
        ordered=True,
    )
    summary = summary.sort_values("day_of_week").reset_index(drop=True)

    numeric_cols = summary.select_dtypes(include="number").columns
    summary[numeric_cols] = summary[numeric_cols].round(2)
    return summary


def render_svg(
    summary: pd.DataFrame,
    daily: pd.DataFrame,
    overall_brown_median: float,
    overall_pistachio_median: float,
) -> str:
    width = 1120
    height = 760
    chart_left = 92
    chart_top = 150
    chart_width = 930
    chart_height = 420
    chart_bottom = chart_top + chart_height
    chart_right = chart_left + chart_width

    max_value = max(
        float(summary["median_brown_sugar_cream_foam_drinks"].max()),
        float(summary["median_pistachio_foam_drinks"].max()),
    )
    axis_max = nice_axis_max(max_value)
    tick_count = 5
    tick_step = axis_max / tick_count
    band_width = chart_width / len(summary)
    group_width = band_width * 0.64
    bar_gap = 8
    bar_width = (group_width - bar_gap) / 2

    min_date = daily["Date"].min()
    max_date = daily["Date"].max()
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">Median Cream Foam Drinks Sold by Day of Week</title>',
        '<desc id="desc">Grouped bar chart showing median daily drink counts for Brown Sugar Cream Foam and Pistachio Foam by day of week.</desc>',
        '<rect width="100%" height="100%" fill="#ffffff" />',
        '<text x="60" y="58" font-family="Inter, Arial, sans-serif" font-size="28" font-weight="700" fill="#172033">Median Cream Foam Drinks Sold by Day of Week</text>',
        (
            f'<text x="60" y="88" font-family="Inter, Arial, sans-serif" '
            f'font-size="15" fill="#4b5563">{escape(str(min_date))} to '
            f'{escape(str(max_date))} | Brown Sugar Mist and Pistachio Mist counted by default</text>'
        ),
        (
            f'<text x="60" y="116" font-family="Inter, Arial, sans-serif" '
            f'font-size="13" fill="#6b7280">Overall daily medians: Brown Sugar Cream Foam '
            f'{overall_brown_median:g} drinks, Pistachio Foam {overall_pistachio_median:g} drinks.</text>'
        ),
        f'<text x="24" y="{chart_top + chart_height / 2:.2f}" text-anchor="middle" transform="rotate(-90 24 {chart_top + chart_height / 2:.2f})" font-family="Inter, Arial, sans-serif" font-size="14" font-weight="600" fill="#374151">Median Drinks Sold</text>',
    ]

    legend_x = 705
    for idx, series in enumerate(SERIES):
        x = legend_x + idx * 185
        lines.append(
            f'<rect x="{x}" y="102" width="15" height="15" rx="2" fill="{series["color"]}" />'
        )
        lines.append(
            f'<text x="{x + 23}" y="115" font-family="Inter, Arial, sans-serif" font-size="13" fill="#374151">{escape(series["label"])}</text>'
        )

    for tick in range(tick_count + 1):
        value = tick * tick_step
        y = chart_bottom - (value / axis_max) * chart_height
        lines.append(
            f'<line x1="{chart_left}" y1="{y:.2f}" x2="{chart_right}" y2="{y:.2f}" stroke="#d8dee8" stroke-width="1" />'
        )
        lines.append(
            f'<text x="{chart_left - 14}" y="{y + 5:.2f}" text-anchor="end" font-family="Inter, Arial, sans-serif" font-size="12" fill="#6b7280">{value:.0f}</text>'
        )

    lines.append(
        f'<line x1="{chart_left}" y1="{chart_bottom}" x2="{chart_right}" y2="{chart_bottom}" stroke="#374151" stroke-width="1.5" />'
    )

    for day_idx, row in summary.iterrows():
        group_x = chart_left + day_idx * band_width + (band_width - group_width) / 2
        day = str(row["day_of_week"])
        dates_count = int(row["dates_count"])
        for series_idx, series in enumerate(SERIES):
            value = float(row[series["median_column"]])
            bar_height = 0 if axis_max == 0 else (value / axis_max) * chart_height
            x = group_x + series_idx * (bar_width + bar_gap)
            y = chart_bottom - bar_height
            lines.append(
                f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_width:.2f}" height="{bar_height:.2f}" rx="4" ry="4" fill="{series["color"]}" />'
            )
            lines.append(
                f'<text x="{x + bar_width / 2:.2f}" y="{y - 8:.2f}" text-anchor="middle" font-family="Inter, Arial, sans-serif" font-size="12" font-weight="700" fill="#111827">{value:g}</text>'
            )

        lines.append(
            f'<text x="{group_x + group_width / 2:.2f}" y="{chart_bottom + 28:.2f}" text-anchor="middle" font-family="Inter, Arial, sans-serif" font-size="13" fill="#111827">{escape(day)}</text>'
        )
        lines.append(
            f'<text x="{group_x + group_width / 2:.2f}" y="{chart_bottom + 49:.2f}" text-anchor="middle" font-family="Inter, Arial, sans-serif" font-size="12" fill="#6b7280">n={dates_count}</text>'
        )

    lines.extend(
        [
            f'<text x="{chart_left + chart_width / 2:.2f}" y="{chart_bottom + 88:.2f}" text-anchor="middle" font-family="Inter, Arial, sans-serif" font-size="14" font-weight="600" fill="#374151">Day of Week</text>',
            '<text x="60" y="704" font-family="Inter, Arial, sans-serif" font-size="13" fill="#4b5563">Counting rule: a drink qualifies when the item is Brown Sugar Mist/Pistachio Mist, or when the matching foam appears in Modifiers Applied. Quantities are summed per date, then medians are calculated.</text>',
            "</svg>",
        ]
    )
    return "\n".join(lines)


def load_font(size: int, bold: bool = False):
    from PIL import ImageFont

    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial Bold.ttf" if bold else "",
        "/Library/Fonts/Arial.ttf",
    ]
    for path in candidates:
        if not path:
            continue
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def render_png(
    summary: pd.DataFrame,
    daily: pd.DataFrame,
    overall_brown_median: float,
    overall_pistachio_median: float,
    output_path: Path,
) -> None:
    from PIL import Image, ImageDraw

    width = 1120
    height = 760
    scale = 2
    image = Image.new("RGB", (width * scale, height * scale), "#ffffff")
    draw = ImageDraw.Draw(image)

    def xy(values: tuple[float, ...]) -> tuple[int, ...]:
        return tuple(round(value * scale) for value in values)

    title_font = load_font(28 * scale, bold=True)
    body_font = load_font(14 * scale)
    small_font = load_font(12 * scale)
    label_font = load_font(13 * scale)
    value_font = load_font(12 * scale, bold=True)

    chart_left = 92
    chart_top = 150
    chart_width = 930
    chart_height = 420
    chart_bottom = chart_top + chart_height
    chart_right = chart_left + chart_width

    max_value = max(
        float(summary["median_brown_sugar_cream_foam_drinks"].max()),
        float(summary["median_pistachio_foam_drinks"].max()),
    )
    axis_max = nice_axis_max(max_value)
    tick_count = 5
    tick_step = axis_max / tick_count
    band_width = chart_width / len(summary)
    group_width = band_width * 0.64
    bar_gap = 8
    bar_width = (group_width - bar_gap) / 2

    min_date = daily["Date"].min()
    max_date = daily["Date"].max()
    draw.text(
        xy((60, 52)),
        "Median Cream Foam Drinks Sold by Day of Week",
        fill="#172033",
        font=title_font,
        anchor="ls",
    )
    draw.text(
        xy((60, 88)),
        f"{min_date} to {max_date} | Brown Sugar Mist and Pistachio Mist counted by default",
        fill="#4b5563",
        font=body_font,
        anchor="ls",
    )
    draw.text(
        xy((60, 116)),
        (
            "Overall daily medians: Brown Sugar Cream Foam "
            f"{overall_brown_median:g} drinks, Pistachio Foam "
            f"{overall_pistachio_median:g} drinks."
        ),
        fill="#6b7280",
        font=label_font,
        anchor="ls",
    )

    legend_x = 705
    for idx, series in enumerate(SERIES):
        x = legend_x + idx * 185
        draw.rounded_rectangle(
            xy((x, 102, x + 15, 117)),
            radius=2 * scale,
            fill=series["color"],
        )
        draw.text(
            xy((x + 23, 115)),
            series["label"],
            fill="#374151",
            font=label_font,
            anchor="ls",
        )

    for tick in range(tick_count + 1):
        value = tick * tick_step
        y = chart_bottom - (value / axis_max) * chart_height
        draw.line(
            xy((chart_left, y, chart_right, y)),
            fill="#d8dee8",
            width=scale,
        )
        draw.text(
            xy((chart_left - 14, y + 5)),
            f"{value:.0f}",
            fill="#6b7280",
            font=small_font,
            anchor="rs",
        )

    draw.line(
        xy((chart_left, chart_bottom, chart_right, chart_bottom)),
        fill="#374151",
        width=round(1.5 * scale),
    )

    for day_idx, row in summary.iterrows():
        group_x = chart_left + day_idx * band_width + (band_width - group_width) / 2
        day = str(row["day_of_week"])
        dates_count = int(row["dates_count"])
        for series_idx, series in enumerate(SERIES):
            value = float(row[series["median_column"]])
            bar_height = 0 if axis_max == 0 else (value / axis_max) * chart_height
            x = group_x + series_idx * (bar_width + bar_gap)
            y = chart_bottom - bar_height
            draw.rounded_rectangle(
                xy((x, y, x + bar_width, chart_bottom)),
                radius=4 * scale,
                fill=series["color"],
            )
            draw.text(
                xy((x + bar_width / 2, y - 8)),
                f"{value:g}",
                fill="#111827",
                font=value_font,
                anchor="ms",
            )

        draw.text(
            xy((group_x + group_width / 2, chart_bottom + 28)),
            day,
            fill="#111827",
            font=label_font,
            anchor="mm",
        )
        draw.text(
            xy((group_x + group_width / 2, chart_bottom + 49)),
            f"n={dates_count}",
            fill="#6b7280",
            font=small_font,
            anchor="mm",
        )

    draw.text(
        xy((chart_left + chart_width / 2, chart_bottom + 88)),
        "Day of Week",
        fill="#374151",
        font=body_font,
        anchor="mm",
    )
    draw.text(
        xy((60, 704)),
        (
            "Counting rule: item is Brown Sugar Mist/Pistachio Mist, or matching "
            "foam appears in Modifiers Applied. Quantities are summed per date, "
            "then medians are calculated."
        ),
        fill="#4b5563",
        font=label_font,
        anchor="ls",
    )

    y_axis = Image.new("RGBA", (80 * scale, 420 * scale), (255, 255, 255, 0))
    y_draw = ImageDraw.Draw(y_axis)
    y_draw.text(
        (40 * scale, 210 * scale),
        "Median Drinks Sold",
        fill="#374151",
        font=body_font,
        anchor="mm",
    )
    y_axis = y_axis.rotate(90, expand=True)
    image.paste(y_axis, xy((-172, 318)), y_axis)

    image = image.resize((width, height), Image.Resampling.LANCZOS)
    image.save(output_path)


def main() -> None:
    args = parse_args()
    start_date = pd.Timestamp(args.start_date) if args.start_date else None
    end_date = pd.Timestamp(args.end_date) if args.end_date else None
    if start_date is not None and end_date is not None and start_date > end_date:
        raise ValueError("--start-date must be on or before --end-date")

    daily = build_daily_totals(Path(args.input), start_date, end_date)
    summary = build_weekday_summary(daily)
    overall_brown_median = daily["brown_sugar_cream_foam_drinks"].median()
    overall_pistachio_median = daily["pistachio_foam_drinks"].median()

    output_csv = Path(args.output_csv)
    output_daily_csv = Path(args.output_daily_csv)
    output_svg = Path(args.output_svg)
    output_png = Path(args.output_png)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    output_daily_csv.parent.mkdir(parents=True, exist_ok=True)
    output_svg.parent.mkdir(parents=True, exist_ok=True)
    output_png.parent.mkdir(parents=True, exist_ok=True)

    summary.to_csv(output_csv, index=False)
    daily.to_csv(output_daily_csv, index=False)
    output_svg.write_text(
        render_svg(
            summary,
            daily,
            overall_brown_median,
            overall_pistachio_median,
        ),
        encoding="utf-8",
    )
    render_png(
        summary,
        daily,
        overall_brown_median,
        overall_pistachio_median,
        output_png,
    )

    print(f"Wrote weekday summary CSV: {output_csv}")
    print(f"Wrote daily totals CSV: {output_daily_csv}")
    print(f"Wrote SVG chart: {output_svg}")
    print(f"Wrote PNG chart: {output_png}")
    print("Overall median brown sugar cream foam drinks per day:", overall_brown_median)
    print("Overall median pistachio foam drinks per day:", overall_pistachio_median)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
