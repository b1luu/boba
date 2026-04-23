"""Export daily cups-with-boba totals to a simple CSV."""

import argparse
from pathlib import Path

import pandas as pd


DEFAULT_INPUT_PATH = "data/clean/clean.csv"
DEFAULT_START_DATE = "2026-03-01"
DEFAULT_END_DATE = "2026-04-20"
DEFAULT_OUTPUT_PATH = "data/analysis/daily_boba_cups_2026-03-01_to_2026-04-20.csv"


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
        "--output",
        default=DEFAULT_OUTPUT_PATH,
        help=f"Output CSV path (default: {DEFAULT_OUTPUT_PATH})",
    )
    return parser.parse_args()


def require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def boba_cups(modifiers: str) -> float:
    total = 0.0
    for part in str(modifiers).split(","):
        token = part.strip().lower().replace("\u00d7", "x")
        if token == "boba":
            total += 1.0
        elif token.startswith("boba x"):
            parsed = pd.to_numeric(token.removeprefix("boba x").strip(), errors="coerce")
            if pd.notna(parsed):
                total += float(parsed)
    return total


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    start_date = pd.Timestamp(args.start_date)
    end_date = pd.Timestamp(args.end_date)

    if start_date > end_date:
        raise ValueError("--start-date must be on or before --end-date")

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

    df["Item"] = df["Item"].fillna("").astype(str).str.strip()
    df["Modifiers Applied"] = df["Modifiers Applied"].fillna("").astype(str)
    is_taiwanese_retro = df["Item"].str.fullmatch(r"(?i)\s*Taiwanese Retro\s*")
    cups_per_item = df["Modifiers Applied"].map(boba_cups) + is_taiwanese_retro.astype(float)
    df["Cups w/ Boba"] = df["Qty"] * cups_per_item

    daily = (
        df.groupby("Date", as_index=False)
        .agg(**{"Cups w/ Boba": ("Cups w/ Boba", "sum")})
        .sort_values("Date")
    )

    full_dates = pd.DataFrame({"Date": pd.date_range(start=start_date, end=end_date, freq="D")})
    daily = full_dates.merge(daily, on="Date", how="left").fillna({"Cups w/ Boba": 0})

    if (daily["Cups w/ Boba"] % 1 == 0).all():
        daily["Cups w/ Boba"] = daily["Cups w/ Boba"].astype(int)
    else:
        daily["Cups w/ Boba"] = daily["Cups w/ Boba"].round(2)

    daily["Date"] = daily["Date"].dt.strftime("%Y-%m-%d")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    daily.to_csv(output_path, index=False)

    print(f"Wrote daily boba cups dataset: {output_path}")
    print(daily.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
