"""Write average boba and black tea demand by day of week."""

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
    parser = argparse.ArgumentParser(description=__doc__)
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

    item = df["Item"].fillna("").astype(str).str.strip()
    modifiers = df["Modifiers Applied"].fillna("").astype(str)

    is_taiwanese_retro = item.str.fullmatch(r"(?i)\s*Taiwanese Retro\s*")
    black_tea_mask = item.str.fullmatch(r"(?i)\s*(Hot\s+)?Signature Black Tea\s*")
    black_au_lait_mask = item.str.fullmatch(
        r"(?i)\s*(Hot\s+)?Signature Black Au Lait\s*"
    )
    black_milk_tea_mask = item.str.fullmatch(
        r"(?i)\s*(Hot\s+)?Signature Black Milk Tea\s*"
    )

    modifier_units = modifiers.apply(boba_modifier_units).fillna(0)
    boba_units_per_item = modifier_units + is_taiwanese_retro.astype(float)
    boba_mask = boba_units_per_item.gt(0)

    df["day_of_week"] = df["Date"].dt.day_name()
    df["boba_drink_qty"] = df["Qty"].where(boba_mask, 0)
    df["boba_units"] = df["Qty"] * boba_units_per_item
    df["black_tea_drinks"] = df["Qty"].where(black_tea_mask, 0)
    df["black_au_lait_drinks"] = df["Qty"].where(black_au_lait_mask, 0)
    df["black_milk_tea_drinks"] = df["Qty"].where(black_milk_tea_mask, 0)
    df["taiwanese_retro_drinks"] = df["Qty"].where(is_taiwanese_retro, 0)

    daily = (
        df.groupby(["Date", "day_of_week"], as_index=False)
        .agg(
            boba_drink_qty=("boba_drink_qty", "sum"),
            boba_units=("boba_units", "sum"),
            black_tea_drinks=("black_tea_drinks", "sum"),
            black_au_lait_drinks=("black_au_lait_drinks", "sum"),
            black_milk_tea_drinks=("black_milk_tea_drinks", "sum"),
            taiwanese_retro_drinks=("taiwanese_retro_drinks", "sum"),
        )
    )

    summary = (
        daily.groupby("day_of_week", as_index=False)
        .agg(
            avg_boba_drink_qty_per_day=("boba_drink_qty", "mean"),
            avg_boba_units_per_day=("boba_units", "mean"),
            avg_black_tea_drinks_per_day=("black_tea_drinks", "mean"),
            avg_black_au_lait_drinks_per_day=("black_au_lait_drinks", "mean"),
            avg_black_milk_tea_drinks_per_day=("black_milk_tea_drinks", "mean"),
            avg_taiwanese_retro_drinks_per_day=("taiwanese_retro_drinks", "mean"),
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
