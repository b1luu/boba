"""Summarize average boba and black tea demand by day of week."""

import argparse
from pathlib import Path

import pandas as pd


DEFAULT_INPUT_PATH = "data/clean/clean.csv"
DEFAULT_OUTPUT_PATH = "data/analysis/day_of_week_demand.csv"
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
    parser = argparse.ArgumentParser(
        description="Write average boba and black tea demand by day of week."
    )
    parser.add_argument(
        "--input",
        default=DEFAULT_INPUT_PATH,
        help=f"Input cleaned CSV path (default: {DEFAULT_INPUT_PATH})",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT_PATH,
        help=f"Output CSV path (default: {DEFAULT_OUTPUT_PATH})",
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
            units += pd.to_numeric(amount, errors="coerce")
    return units


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    df = pd.read_csv(input_path, low_memory=False)
    require_columns(df, ["Date", "Item", "Qty", "Modifiers Applied"])

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Qty"] = pd.to_numeric(df["Qty"], errors="coerce").fillna(0)
    df = df.dropna(subset=["Date"]).copy()

    item = df["Item"].fillna("").astype(str)
    modifiers = df["Modifiers Applied"].fillna("").astype(str)

    is_taiwanese_retro = item.str.fullmatch(r"(?i)\s*Taiwanese Retro\s*")
    black_tea_mask = item.str.contains(r"(?i)\bblack\b", regex=True) | is_taiwanese_retro

    modifier_units = modifiers.apply(boba_modifier_units).fillna(0)
    included_boba_units = is_taiwanese_retro.astype(float)
    boba_units_per_item = pd.concat(
        [modifier_units, included_boba_units], axis=1
    ).max(axis=1)
    boba_mask = boba_units_per_item.gt(0)

    df["day_of_week"] = df["Date"].dt.day_name()
    df["sale_qty"] = df["Qty"]
    df["boba_line_item"] = boba_mask.astype(int)
    df["boba_drink_qty"] = df["Qty"].where(boba_mask, 0)
    df["boba_units"] = df["Qty"] * boba_units_per_item
    df["black_tea_line_item"] = black_tea_mask.astype(int)
    df["black_tea_qty"] = df["Qty"].where(black_tea_mask, 0)
    df["taiwanese_retro_qty"] = df["Qty"].where(is_taiwanese_retro, 0)

    daily = (
        df.groupby(["Date", "day_of_week"], as_index=False)
        .agg(
            total_line_items=("Item", "size"),
            total_qty=("sale_qty", "sum"),
            boba_line_items=("boba_line_item", "sum"),
            boba_drink_qty=("boba_drink_qty", "sum"),
            boba_units=("boba_units", "sum"),
            black_tea_line_items=("black_tea_line_item", "sum"),
            black_tea_qty=("black_tea_qty", "sum"),
            taiwanese_retro_qty=("taiwanese_retro_qty", "sum"),
        )
    )

    summary = (
        daily.groupby("day_of_week", as_index=False)
        .agg(
            dates_count=("Date", "nunique"),
            total_qty=("total_qty", "sum"),
            avg_total_qty_per_day=("total_qty", "mean"),
            boba_drink_qty=("boba_drink_qty", "sum"),
            avg_boba_drink_qty_per_day=("boba_drink_qty", "mean"),
            boba_units=("boba_units", "sum"),
            avg_boba_units_per_day=("boba_units", "mean"),
            black_tea_qty=("black_tea_qty", "sum"),
            avg_black_tea_qty_per_day=("black_tea_qty", "mean"),
            taiwanese_retro_qty=("taiwanese_retro_qty", "sum"),
            avg_taiwanese_retro_qty_per_day=("taiwanese_retro_qty", "mean"),
            boba_line_items=("boba_line_items", "sum"),
            black_tea_line_items=("black_tea_line_items", "sum"),
        )
    )

    summary["day_of_week"] = pd.Categorical(
        summary["day_of_week"],
        categories=DAY_ORDER,
        ordered=True,
    )
    summary = summary.sort_values("day_of_week")

    numeric_cols = summary.select_dtypes(include="number").columns
    summary[numeric_cols] = summary[numeric_cols].round(2)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(output_path, index=False)
    print(f"Wrote weekday demand summary: {output_path}")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
