"""Plot weekday black tea family components and validate estimated tea-base usage."""

import argparse
from pathlib import Path

import pandas as pd


DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
BLACK_TEA_PLUS_MILK_TEA_ML = 350
AU_LAIT_PLUS_RETRO_ML = 200


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        default="data/clean/clean.csv",
        help="Input cleaned sales CSV.",
    )
    parser.add_argument(
        "--output-png",
        default="data/analysis/black_tea_inventory_validation_weekdays.png",
        help="Output PNG path.",
    )
    parser.add_argument(
        "--output-csv",
        default="data/analysis/black_tea_inventory_validation_weekdays.csv",
        help="Output CSV path.",
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

    df["Black Tea + Black Milk Tea"] = df["Qty"].where(
        black_tea_mask | black_milk_tea_mask,
        0,
    )
    df["Au Lait + Taiwanese Retro"] = df["Qty"].where(
        black_au_lait_mask | taiwanese_retro_mask,
        0,
    )

    daily = (
        df.groupby(["Date", "Day of Week"], as_index=False)
        .agg(
            **{
                "Black Tea + Black Milk Tea": ("Black Tea + Black Milk Tea", "sum"),
                "Au Lait + Taiwanese Retro": ("Au Lait + Taiwanese Retro", "sum"),
            }
        )
    )

    summary = (
        daily[daily["Day of Week"].isin(DAY_ORDER)]
        .groupby("Day of Week", as_index=False)
        .agg(
            **{
                "Avg Black Tea + Black Milk Tea Drinks": (
                    "Black Tea + Black Milk Tea",
                    "mean",
                ),
                "Avg Au Lait + Taiwanese Retro Drinks": (
                    "Au Lait + Taiwanese Retro",
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

    summary["Avg Drinks Sold that Included Black Tea"] = (
        summary["Avg Black Tea + Black Milk Tea Drinks"]
        + summary["Avg Au Lait + Taiwanese Retro Drinks"]
    )
    summary["Estimated Black Tea Base ml per Day"] = (
        summary["Avg Black Tea + Black Milk Tea Drinks"] * BLACK_TEA_PLUS_MILK_TEA_ML
        + summary["Avg Au Lait + Taiwanese Retro Drinks"] * AU_LAIT_PLUS_RETRO_ML
    )
    summary["Estimated Black Tea Base liters per Day"] = (
        summary["Estimated Black Tea Base ml per Day"] / 1000
    )

    for column in [
        "Avg Black Tea + Black Milk Tea Drinks",
        "Avg Au Lait + Taiwanese Retro Drinks",
        "Avg Drinks Sold that Included Black Tea",
        "Estimated Black Tea Base ml per Day",
        "Estimated Black Tea Base liters per Day",
    ]:
        summary[column] = summary[column].round(2)

    output_png.parent.mkdir(parents=True, exist_ok=True)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(output_csv, index=False)

    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(10.5, 6.2))

    x = range(len(summary))
    bottom = summary["Avg Black Tea + Black Milk Tea Drinks"]
    top = summary["Avg Au Lait + Taiwanese Retro Drinks"]

    ax.bar(
        x,
        bottom,
        width=0.65,
        color="#0f766e",
        label="Black Tea + Black Milk Tea",
    )
    ax.bar(
        x,
        top,
        width=0.65,
        bottom=bottom,
        color="#b45309",
        label="Au Lait + Taiwanese Retro",
    )

    ax.set_xticks(list(x))
    ax.set_xticklabels(summary["Day of Week"].astype(str))
    ax.set_xlabel("Day of Week")
    ax.set_ylabel("Average Drinks Sold")
    ax.set_title(
        "Average Drinks Sold that Included Black Tea\nwith Inventory Mix Validation",
        fontsize=16,
        weight="bold",
    )
    ax.legend(frameon=False, loc="upper left")

    for idx, total in enumerate(summary["Avg Drinks Sold that Included Black Tea"]):
        ax.text(
            idx,
            total + 0.2,
            f"{total:.2f}",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
        )

    validation_lines = [
        "Validation assumptions:",
        f"- Black Tea + Black Milk Tea: {BLACK_TEA_PLUS_MILK_TEA_ML} ml each",
        f"- Au Lait + Taiwanese Retro: {AU_LAIT_PLUS_RETRO_ML} ml each",
    ]
    fig.text(
        0.67,
        0.18,
        "\n".join(validation_lines),
        ha="left",
        va="top",
        fontsize=10,
        color="#374151",
    )

    fig.tight_layout()
    fig.savefig(output_png, dpi=200, bbox_inches="tight")
    plt.close(fig)

    print(f"Wrote validation CSV: {output_csv}")
    print(f"Wrote stacked bar chart PNG: {output_png}")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
