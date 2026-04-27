# Boba Analysis

This repo includes a small analysis script for visualizing the average weekday mix of black-tea-based drinks as a donut chart.

## Black Tea Mix Donut Chart

Script:
- `scripts/plot_black_tea_weekday_bar.py`

Inputs:
- `data/clean/clean.csv`
- Required columns: `Date`, `Item`, `Qty`

Included drink categories:
- `Signature Black Tea`
- `Signature Black Milk Tea`
- `Signature Black Au Lait`
- `Taiwanese Retro`

The script filters to weekdays (`Monday` through `Friday`), computes the average daily quantity for each of those four drinks, and renders a donut chart showing each drink's fraction of the black tea family total.

## Run It

```bash
./.venv/bin/python scripts/plot_black_tea_weekday_bar.py
```

Default outputs:
- `data/analysis/average_drinks_sold_that_included_black_tea_weekdays.png`
- `data/analysis/average_drinks_sold_that_included_black_tea_weekdays.csv`

Optional arguments:

```bash
./.venv/bin/python scripts/plot_black_tea_weekday_bar.py \
  --input data/clean/clean.csv \
  --output-png data/analysis/black_tea_mix_donut.png \
  --output-csv data/analysis/black_tea_mix_donut.csv
```

## Example Output Template

Template CSV structure only. Values below are placeholders, not real data.

```csv
Drink,Average Drinks Sold per Weekday,Fraction of Black Tea Family Drinks,Share Label,Weekday Dates Observed
Signature Black Tea,XX.XX,0.0000,00.0%,NN
Signature Black Milk Tea,XX.XX,0.0000,00.0%,NN
Signature Black Au Lait,XX.XX,0.0000,00.0%,NN
Taiwanese Retro,XX.XX,0.0000,00.0%,NN
```

Interpretation:
- `Average Drinks Sold per Weekday` is the mean weekday daily quantity for that drink.
- `Fraction of Black Tea Family Drinks` is that drink's share of the four-drink total.
- `Share Label` is the display percentage used on the chart.
- `Weekday Dates Observed` is the number of weekday dates included in the calculation.

## Notes

- `Hot Signature Black Tea` and `Hot Signature Black Milk Tea` are included through the script's item matching rules.
- The chart is meant to show mix share, not day-by-day variation.
