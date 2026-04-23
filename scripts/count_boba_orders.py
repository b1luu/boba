"""Count orders that include boba in the modifiers column."""

import argparse
from pathlib import Path

import pandas as pd


DEFAULT_INPUT_PATH = "data/clean/clean.csv"
DEFAULT_MODIFIER_COLUMN = "Modifiers Applied"
DEFAULT_QTY_COLUMN = "Qty"
DEFAULT_PATTERN = r"\bboba\b"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Count line items and quantities with boba modifiers."
    )
    parser.add_argument(
        "--input",
        default=DEFAULT_INPUT_PATH,
        help=f"Input CSV path (default: {DEFAULT_INPUT_PATH})",
    )
    parser.add_argument(
        "--modifier-column",
        default=DEFAULT_MODIFIER_COLUMN,
        help=f"Modifier column name (default: {DEFAULT_MODIFIER_COLUMN})",
    )
    parser.add_argument(
        "--qty-column",
        default=DEFAULT_QTY_COLUMN,
        help=f"Quantity column name (default: {DEFAULT_QTY_COLUMN})",
    )
    parser.add_argument(
        "--pattern",
        default=DEFAULT_PATTERN,
        help=f"Regex pattern to match boba modifiers (default: {DEFAULT_PATTERN})",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=20,
        help="Number of boba modifier names to show in the breakdown (default: 20)",
    )
    return parser.parse_args()


def require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)

    df = pd.read_csv(input_path, low_memory=False)
    require_columns(df, [args.modifier_column, args.qty_column])

    qty = pd.to_numeric(df[args.qty_column], errors="coerce").fillna(0)
    modifiers = df[args.modifier_column].fillna("").astype(str)
    boba_mask = modifiers.str.contains(args.pattern, case=False, regex=True, na=False)

    total_rows = len(df)
    boba_rows = int(boba_mask.sum())
    total_qty = float(qty.sum())
    boba_qty = float(qty[boba_mask].sum())
    row_share = boba_rows / total_rows if total_rows else 0
    qty_share = boba_qty / total_qty if total_qty else 0

    print(f"Input file: {input_path}")
    print(f"Total line items: {total_rows}")
    print(f"Line items with boba: {boba_rows} ({row_share:.1%})")
    print(f"Total quantity: {total_qty:g}")
    print(f"Quantity with boba: {boba_qty:g} ({qty_share:.1%})")

    boba_line_items = df.loc[boba_mask, [args.modifier_column]].copy()
    boba_line_items[args.qty_column] = qty[boba_mask]
    boba_modifiers = (
        boba_line_items.assign(
            modifier=boba_line_items[args.modifier_column].str.split(",")
        )
        .explode("modifier")
        .drop(columns=[args.modifier_column])
    )
    boba_modifiers["modifier"] = boba_modifiers["modifier"].fillna("").str.strip()
    boba_modifiers = boba_modifiers[
        boba_modifiers["modifier"].str.contains(
            args.pattern, case=False, regex=True, na=False
        )
    ]

    if boba_modifiers.empty:
        return

    breakdown = (
        boba_modifiers.groupby("modifier", as_index=False)
        .agg(line_items=(args.qty_column, "size"), quantity=(args.qty_column, "sum"))
        .sort_values(["quantity", "line_items"], ascending=False)
        .head(args.top)
    )

    print("\nBoba modifier breakdown:")
    print(breakdown.to_string(index=False))


if __name__ == "__main__":
    main()
