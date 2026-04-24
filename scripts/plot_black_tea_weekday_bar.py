"""Create a weekday bar chart for average drinks sold that included black tea."""

import argparse
from pathlib import Path

import pandas as pd


DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        default="data/clean/clean.csv",
        help="Input cleaned sales CSV.",
    )
    parser.add_argument(
        "--output-png",
        default="data/analysis/average_drinks_sold_that_included_black_tea_weekdays.png",
        help="Output PNG path.",
    )
    parser.add_argument(
        "--output-csv",
        default="data/analysis/average_drinks_sold_that_included_black_tea_weekdays.csv",
        help="Output summary CSV path.",
    )
    return parser.parse_args()


def main() -> None:
    import matplotlib.pyplot as plt

    args = parse_args()
    input_path = Path(args.input)
    output_png = Path(args.output_png)
    output_csv = Path(args.output_csv)

    df = pd.read_csv(input_path, usecols=["Date", "Item", "Qty"])
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Qty"] = pd.to_numeric(df["Qty"], errors="coerce").fillna(0)
    df = df.dropna(subset=["Date"]).copy()

    item = df["Item"].fillna("").astype(str).str.strip()
    df["Day of Week"] = df["Date"].dt.day_name()

    black_tea_mask = item.str.fullmatch(r"(?i)\s*(Hot\s+)?Signature Black Tea\s*")
    black_au_lait_mask = item.str.fullmatch(
        r"(?i)\s*(Hot\s+)?Signature Black Au Lait\s*"
    )
    black_milk_tea_mask = item.str.fullmatch(
        r"(?i)\s*(Hot\s+)?Signature Black Milk Tea\s*"
    )
    taiwanese_retro_mask = item.str.fullmatch(r"(?i)\s*Taiwanese Retro\s*")
    black_tea_family_mask = (
        black_tea_mask
        | black_au_lait_mask
        | black_milk_tea_mask
        | taiwanese_retro_mask
    )

    df["Black Tea Family Drinks"] = df["Qty"].where(black_tea_family_mask, 0)

    daily = (
        df.groupby(["Date", "Day of Week"], as_index=False)
        .agg(**{"Black Tea Family Drinks": ("Black Tea Family Drinks", "sum")})
    )

    summary = (
        daily[daily["Day of Week"].isin(DAY_ORDER)]
        .groupby("Day of Week", as_index=False)
        .agg(
            **{
                "Average Drinks Sold that Included Black Tea": (
                    "Black Tea Family Drinks",
                    "mean",
                ),
                "Days Observed": ("Date", "nunique"),
            }
        )
    )
    summary["Day of Week"] = pd.Categorical(
        summary["Day of Week"], categories=DAY_ORDER, ordered=True
    )
    summary = summary.sort_values("Day of Week").reset_index(drop=True)
    summary["Average Drinks Sold that Included Black Tea"] = (
        summary["Average Drinks Sold that Included Black Tea"].round(2)
    )

    output_png.parent.mkdir(parents=True, exist_ok=True)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(output_csv, index=False)

    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(10, 5.8))
    values = summary["Average Drinks Sold that Included Black Tea"]
    ax.bar(summary["Day of Week"].astype(str), values, color="#1f7a6f", width=0.65)
    ax.set_title("Average Drinks Sold that Included Black Tea", fontsize=18, weight="bold")
    ax.set_xlabel("Day of Week")
    ax.set_ylabel("Average Drinks Sold")
    for idx, value in enumerate(values):
        ax.text(idx, value + 0.15, f"{value:.2f}", ha="center", va="bottom", fontsize=10)
    fig.tight_layout()
    fig.savefig(output_png, dpi=200, bbox_inches="tight")
    plt.close(fig)

    print(f"Wrote summary CSV: {output_csv}")
    print(f"Wrote bar chart PNG: {output_png}")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
