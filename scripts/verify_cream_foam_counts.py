"""Verify cream foam counts, daily totals, and weekday median outputs."""

import argparse
from pathlib import Path

import pandas as pd
from pandas.testing import assert_frame_equal


DEFAULT_INPUT_PATH = "data/clean/clean.csv"
DEFAULT_DAILY_PATH = "data/analysis/daily_cream_foam_drinks.csv"
DEFAULT_SUMMARY_PATH = "data/analysis/cream_foam_weekday_medians.csv"
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
        "--daily-csv",
        default=DEFAULT_DAILY_PATH,
        help=f"Generated daily totals CSV to verify (default: {DEFAULT_DAILY_PATH})",
    )
    parser.add_argument(
        "--summary-csv",
        default=DEFAULT_SUMMARY_PATH,
        help=f"Generated weekday summary CSV to verify (default: {DEFAULT_SUMMARY_PATH})",
    )
    parser.add_argument(
        "--expected-brown-median",
        type=float,
        default=8.0,
        help="Expected overall daily median for Brown Sugar Cream Foam.",
    )
    parser.add_argument(
        "--expected-pistachio-median",
        type=float,
        default=7.0,
        help="Expected overall daily median for Pistachio Foam.",
    )
    parser.add_argument(
        "--skip-expected-median-check",
        action="store_true",
        help="Only verify generated files against the source data, without fixed medians.",
    )
    return parser.parse_args()


def require_columns(df: pd.DataFrame, columns: list[str], path: Path) -> None:
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise ValueError(f"{path} is missing required columns: {missing}")


def has_modifier(modifiers: pd.Series, modifier_name: str) -> pd.Series:
    escaped = modifier_name.replace(" ", r"\s+")
    return modifiers.str.contains(
        rf"(?i)(?:^|,\s*){escaped}(?:\s*(?:x|\u00d7)\s*[0-9.]+)?(?:\s*,|$)",
        regex=True,
    )


def build_expected(input_path: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, float]]:
    df = pd.read_csv(input_path, low_memory=False)
    require_columns(df, ["Date", "Item", "Qty", "Modifiers Applied"], input_path)

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Qty"] = pd.to_numeric(df["Qty"], errors="coerce").fillna(0)
    df = df.dropna(subset=["Date"]).copy()
    if df.empty:
        raise ValueError(f"{input_path} has no rows with valid dates")

    item = df["Item"].fillna("").astype(str).str.strip()
    modifiers = df["Modifiers Applied"].fillna("").astype(str)

    brown_default = item.str.fullmatch(r"(?i)\s*Brown Sugar Mist\s*")
    brown_modifier = has_modifier(modifiers, "Brown Sugar Cream Foam")
    pistachio_default = item.str.fullmatch(r"(?i)\s*Pistachio Mist\s*")
    pistachio_modifier = has_modifier(modifiers, "Pistachio Foam")

    brown = brown_default | brown_modifier
    pistachio = pistachio_default | pistachio_modifier

    df["Date"] = df["Date"].dt.date
    df["day_of_week"] = pd.to_datetime(df["Date"]).dt.day_name()
    df["brown_sugar_cream_foam_drinks"] = df["Qty"].where(brown, 0)
    df["pistachio_foam_drinks"] = df["Qty"].where(pistachio, 0)

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

    counts = {
        "source_rows": float(len(df)),
        "source_dates": float(daily["Date"].nunique()),
        "brown_default_rows": float(brown_default.sum()),
        "brown_modifier_rows": float(brown_modifier.sum()),
        "brown_union_rows": float(brown.sum()),
        "brown_default_qty": float(df.loc[brown_default, "Qty"].sum()),
        "brown_modifier_qty": float(df.loc[brown_modifier, "Qty"].sum()),
        "brown_union_qty": float(df.loc[brown, "Qty"].sum()),
        "brown_default_and_modifier_rows": float((brown_default & brown_modifier).sum()),
        "pistachio_default_rows": float(pistachio_default.sum()),
        "pistachio_modifier_rows": float(pistachio_modifier.sum()),
        "pistachio_union_rows": float(pistachio.sum()),
        "pistachio_default_qty": float(df.loc[pistachio_default, "Qty"].sum()),
        "pistachio_modifier_qty": float(df.loc[pistachio_modifier, "Qty"].sum()),
        "pistachio_union_qty": float(df.loc[pistachio, "Qty"].sum()),
        "pistachio_default_and_modifier_rows": float(
            (pistachio_default & pistachio_modifier).sum()
        ),
        "overall_brown_median": float(daily["brown_sugar_cream_foam_drinks"].median()),
        "overall_pistachio_median": float(daily["pistachio_foam_drinks"].median()),
    }
    return daily, summary, counts


def normalize_daily(df: pd.DataFrame, path: Path) -> pd.DataFrame:
    require_columns(
        df,
        [
            "Date",
            "day_of_week",
            "brown_sugar_cream_foam_drinks",
            "pistachio_foam_drinks",
        ],
        path,
    )
    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.date
    df = df.sort_values("Date").reset_index(drop=True)
    for col in ["brown_sugar_cream_foam_drinks", "pistachio_foam_drinks"]:
        df[col] = pd.to_numeric(df[col], errors="raise")
    return df


def normalize_summary(df: pd.DataFrame, path: Path) -> pd.DataFrame:
    require_columns(
        df,
        [
            "day_of_week",
            "dates_count",
            "median_brown_sugar_cream_foam_drinks",
            "median_pistachio_foam_drinks",
            "avg_brown_sugar_cream_foam_drinks",
            "avg_pistachio_foam_drinks",
        ],
        path,
    )
    df = df.copy()
    df["day_of_week"] = pd.Categorical(
        df["day_of_week"],
        categories=DAY_ORDER,
        ordered=True,
    )
    df = df.sort_values("day_of_week").reset_index(drop=True)
    df["day_of_week"] = df["day_of_week"].astype(str)
    for col in df.columns:
        if col != "day_of_week":
            df[col] = pd.to_numeric(df[col], errors="raise")
    return df


def assert_close(actual: float, expected: float, label: str) -> None:
    if abs(actual - expected) > 1e-9:
        raise AssertionError(f"{label}: expected {expected}, got {actual}")


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    daily_path = Path(args.daily_csv)
    summary_path = Path(args.summary_csv)

    expected_daily, expected_summary, counts = build_expected(input_path)
    actual_daily = normalize_daily(pd.read_csv(daily_path), daily_path)
    actual_summary = normalize_summary(pd.read_csv(summary_path), summary_path)

    expected_daily = normalize_daily(expected_daily, input_path)
    expected_summary = normalize_summary(expected_summary, input_path)

    assert_frame_equal(
        actual_daily,
        expected_daily,
        check_dtype=False,
        check_exact=False,
        atol=1e-9,
        rtol=0,
    )
    assert_frame_equal(
        actual_summary,
        expected_summary,
        check_dtype=False,
        check_exact=False,
        atol=1e-9,
        rtol=0,
    )

    assert_close(
        counts["brown_union_qty"],
        float(actual_daily["brown_sugar_cream_foam_drinks"].sum()),
        "brown raw qualifying qty vs daily total",
    )
    assert_close(
        counts["pistachio_union_qty"],
        float(actual_daily["pistachio_foam_drinks"].sum()),
        "pistachio raw qualifying qty vs daily total",
    )

    if not args.skip_expected_median_check:
        assert_close(
            counts["overall_brown_median"],
            args.expected_brown_median,
            "overall Brown Sugar Cream Foam median",
        )
        assert_close(
            counts["overall_pistachio_median"],
            args.expected_pistachio_median,
            "overall Pistachio Foam median",
        )

    print("Cream foam verification passed.")
    print(f"Source rows checked: {int(counts['source_rows'])}")
    print(f"Sales dates checked: {int(counts['source_dates'])}")
    print()
    print("Raw qualifying counts:")
    print(
        "Brown Sugar Cream Foam:",
        f"default rows={int(counts['brown_default_rows'])},",
        f"modifier rows={int(counts['brown_modifier_rows'])},",
        f"union rows={int(counts['brown_union_rows'])},",
        f"union qty={counts['brown_union_qty']:g}",
    )
    print(
        "Pistachio Foam:",
        f"default rows={int(counts['pistachio_default_rows'])},",
        f"modifier rows={int(counts['pistachio_modifier_rows'])},",
        f"union rows={int(counts['pistachio_union_rows'])},",
        f"union qty={counts['pistachio_union_qty']:g}",
    )
    print()
    print("Overall daily medians:")
    print(f"Brown Sugar Cream Foam: {counts['overall_brown_median']:g}")
    print(f"Pistachio Foam: {counts['overall_pistachio_median']:g}")
    print()
    print("Verified files:")
    print(f"- {daily_path}")
    print(f"- {summary_path}")


if __name__ == "__main__":
    main()
