# Boba Analysis

This repo contains lightweight sales-cleaning and analysis scripts for two main outputs:
- boba demand summaries and charts
- black tea family mix summaries and charts

All examples in this README use placeholders only, not real data.

## Pipeline

The analysis flow is:

```text
data/raw/raw.csv
  -> scripts/prepare_data.py
data/clean/clean.csv
  -> scripts/count_boba_orders.py
  -> scripts/day_of_week_demand.py
  -> scripts/plot_boba_weekday_bar.py
  -> scripts/plot_black_tea_weekday_bar.py
  -> scripts/plot_black_tea_inventory_validation.py
data/analysis/*.csv
data/analysis/*.png
data/analysis/*.svg
```

What each stage does:
- `scripts/prepare_data.py`: cleans the Square export, keeps positive-sale rows, removes non-product rows, normalizes text, and writes `data/clean/clean.csv`
- `scripts/count_boba_orders.py`: counts rows and quantities that include boba modifiers
- `scripts/day_of_week_demand.py`: writes weekday demand summaries for boba and black tea drink families
- `scripts/plot_boba_weekday_bar.py`: renders an average boba demand weekday bar chart
- `scripts/plot_black_tea_weekday_bar.py`: renders the black tea family donut chart
- `scripts/plot_black_tea_inventory_validation.py`: renders a black tea family validation chart grouped by tea-base assumptions

## Start With Clean Data

```bash
./.venv/bin/python scripts/prepare_data.py
```

Default paths:
- input: `data/raw/raw.csv`
- output: `data/clean/clean.csv`

Required columns in the raw export:
- `Date`
- `Category`
- `Item`
- `Qty`
- `Modifiers Applied`
- `Net Sales`

## Boba Analysis

Scripts:
- `scripts/count_boba_orders.py`
- `scripts/day_of_week_demand.py`
- `scripts/plot_boba_weekday_bar.py`

Relevant boba logic:
- `Boba` counts as one normal boba serving
- `Boba x 2` counts as two servings
- `Boba x 3` counts as three servings
- `Taiwanese Retro` contributes one default boba serving per drink

### Run Boba Summary

```bash
./.venv/bin/python scripts/day_of_week_demand.py
```

### Run Boba Chart

```bash
./.venv/bin/python scripts/plot_boba_weekday_bar.py
```

Default boba chart outputs:
- `data/analysis/boba_weekday_avg_2026-03-01_to_2026-04-20.svg`
- `data/analysis/boba_weekday_avg_2026-03-01_to_2026-04-20.csv`

### Example Boba Output Template

Template structure only. Values below are placeholders, not real data.

```csv
day_of_week,dates_count,avg_estimated_cups_of_boba_sold_per_day
Sunday,NN,XX.XX
Monday,NN,XX.XX
Tuesday,NN,XX.XX
Wednesday,NN,XX.XX
Thursday,NN,XX.XX
Friday,NN,XX.XX
Saturday,NN,XX.XX
```

Interpretation:
- `dates_count` is the number of calendar dates included for that weekday in the selected range
- `avg_estimated_cups_of_boba_sold_per_day` is the mean daily boba-serving estimate for that weekday

## Black Tea Mix

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

### Run It

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

### Example Output Template

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
