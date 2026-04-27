"""Create a donut chart for the average weekday mix of black tea family drinks."""

import argparse
from pathlib import Path

import pandas as pd


DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
DRINK_ORDER = [
    "Signature Black Tea",
    "Signature Black Milk Tea",
    "Signature Black Au Lait",
    "Taiwanese Retro",
]
DRINK_COLORS = {
    "Signature Black Tea": "#7c2d12",
    "Signature Black Milk Tea": "#c2410c",
    "Signature Black Au Lait": "#d6a663",
    "Taiwanese Retro": "#3f6212",
}


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

    black_milk_tea_mask = item.str.fullmatch(
        r"(?i)\s*(Hot\s+)?Signature Black Milk Tea\s*"
    )
    black_tea_mask = item.str.fullmatch(r"(?i)\s*(Hot\s+)?Signature Black Tea\s*")
    black_au_lait_mask = item.str.fullmatch(
        r"(?i)\s*(Hot\s+)?Signature Black Au Lait\s*"
    )
    taiwanese_retro_mask = item.str.fullmatch(r"(?i)\s*Taiwanese Retro\s*")

    daily = (
        df.groupby(["Date", "Day of Week"], as_index=False)
        .agg(
            **{
                "Signature Black Tea": ("Qty", lambda s: s[black_tea_mask.loc[s.index]].sum()),
                "Signature Black Milk Tea": (
                    "Qty",
                    lambda s: s[black_milk_tea_mask.loc[s.index]].sum(),
                ),
                "Signature Black Au Lait": (
                    "Qty",
                    lambda s: s[black_au_lait_mask.loc[s.index]].sum(),
                ),
                "Taiwanese Retro": (
                    "Qty",
                    lambda s: s[taiwanese_retro_mask.loc[s.index]].sum(),
                ),
            }
        )
    )

    weekday_daily = daily[daily["Day of Week"].isin(DAY_ORDER)].copy()
    if weekday_daily.empty:
        raise ValueError("No weekday rows found for the black tea family chart")

    average_mix = (
        weekday_daily[DRINK_ORDER]
        .mean()
        .rename_axis("Drink")
        .reset_index(name="Average Drinks Sold per Weekday")
    )
    total_average = average_mix["Average Drinks Sold per Weekday"].sum()
    average_mix["Fraction of Black Tea Family Drinks"] = (
        average_mix["Average Drinks Sold per Weekday"] / total_average
    )
    average_mix["Share Label"] = average_mix["Fraction of Black Tea Family Drinks"].map(
        lambda value: f"{value:.1%}"
    )
    average_mix["Average Drinks Sold per Weekday"] = (
        average_mix["Average Drinks Sold per Weekday"].round(2)
    )
    average_mix["Fraction of Black Tea Family Drinks"] = (
        average_mix["Fraction of Black Tea Family Drinks"].round(4)
    )
    average_mix["Weekday Dates Observed"] = weekday_daily["Date"].nunique()

    output_png.parent.mkdir(parents=True, exist_ok=True)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    average_mix.to_csv(output_csv, index=False)

    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(10, 6.4))
    values = average_mix["Average Drinks Sold per Weekday"]
    colors = [DRINK_COLORS[drink] for drink in average_mix["Drink"]]

    wedges, _, autotexts = ax.pie(
        values,
        labels=average_mix["Drink"],
        colors=colors,
        startangle=90,
        counterclock=False,
        wedgeprops={"width": 0.42, "edgecolor": "white", "linewidth": 2},
        autopct=lambda pct: f"{pct:.1f}%",
        pctdistance=0.82,
        labeldistance=1.08,
    )
    for autotext in autotexts:
        autotext.set_color("white")
        autotext.set_fontsize(11)
        autotext.set_weight("bold")

    ax.text(
        0,
        0.06,
        "Avg weekday\nblack tea drinks",
        ha="center",
        va="center",
        fontsize=11,
        color="#374151",
    )
    ax.text(
        0,
        -0.16,
        f"{total_average:.2f}",
        ha="center",
        va="center",
        fontsize=20,
        fontweight="bold",
        color="#111827",
    )
    ax.set_title(
        "Average Drinks Sold that Included Black Tea\nWeekday Mix by Drink",
        fontsize=18,
        weight="bold",
    )
    ax.axis("equal")
    fig.tight_layout()
    fig.savefig(output_png, dpi=200, bbox_inches="tight")
    plt.close(fig)

    print(f"Wrote summary CSV: {output_csv}")
    print(f"Wrote donut chart PNG: {output_png}")
    print(average_mix.to_string(index=False))


if __name__ == "__main__":
    main()
