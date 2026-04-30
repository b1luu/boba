import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.plot_cream_foam_weekday_medians import (
    build_daily_totals,
    build_weekday_summary,
)
from scripts.verify_cream_foam_counts import build_expected, normalize_summary


def write_fixture_csv(path: Path, rows: list[dict[str, object]]) -> None:
    pd.DataFrame(rows).to_csv(path, index=False)


class CreamFoamCountingTests(unittest.TestCase):
    def test_counts_defaults_modifiers_and_quantities_without_double_counting(self):
        rows = [
            {
                "Date": "2026-01-05",
                "Item": "Brown Sugar Mist",
                "Qty": 2,
                "Modifiers Applied": "50% Ice, 75% Sugar",
            },
            {
                "Date": "2026-01-05",
                "Item": "Signature Black Milk Tea",
                "Qty": 3,
                "Modifiers Applied": "50% Ice, Brown Sugar Cream Foam",
            },
            {
                "Date": "2026-01-05",
                "Item": "Brown Sugar Mist",
                "Qty": 4,
                "Modifiers Applied": "Brown Sugar Cream Foam",
            },
            {
                "Date": "2026-01-06",
                "Item": "Pistachio Mist",
                "Qty": 1,
                "Modifiers Applied": "No Ice, No Sugar",
            },
            {
                "Date": "2026-01-06",
                "Item": "Jasmine Green Milk Tea",
                "Qty": 2,
                "Modifiers Applied": "100% Ice, Pistachio Foam",
            },
            {
                "Date": "2026-01-06",
                "Item": "Pistachio Mist",
                "Qty": 5,
                "Modifiers Applied": "Pistachio Foam",
            },
        ]

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "clean.csv"
            write_fixture_csv(path, rows)

            daily = build_daily_totals(path, None, None)

        monday = daily.loc[daily["Date"].astype(str).eq("2026-01-05")].iloc[0]
        tuesday = daily.loc[daily["Date"].astype(str).eq("2026-01-06")].iloc[0]

        self.assertEqual(monday["brown_sugar_cream_foam_drinks"], 9)
        self.assertEqual(monday["pistachio_foam_drinks"], 0)
        self.assertEqual(tuesday["brown_sugar_cream_foam_drinks"], 0)
        self.assertEqual(tuesday["pistachio_foam_drinks"], 8)

    def test_modifier_matching_is_exact_enough_to_avoid_false_positives(self):
        rows = [
            {
                "Date": "2026-01-05",
                "Item": "Milk Tea",
                "Qty": 1,
                "Modifiers Applied": "Brown Sugar H\u00fan-Ku\u00e9 (Tapioca Jelly)",
            },
            {
                "Date": "2026-01-05",
                "Item": "Milk Tea",
                "Qty": 1,
                "Modifiers Applied": "Brown Sugar Cream Foam",
            },
            {
                "Date": "2026-01-05",
                "Item": "Milk Tea",
                "Qty": 1,
                "Modifiers Applied": "Pistachio",
            },
            {
                "Date": "2026-01-05",
                "Item": "Milk Tea",
                "Qty": 1,
                "Modifiers Applied": "Pistachio Foam",
            },
            {
                "Date": "2026-01-05",
                "Item": "Milk Tea",
                "Qty": 1,
                "Modifiers Applied": "Pistachio Foam x 2.0",
            },
            {
                "Date": "2026-01-05",
                "Item": "Milk Tea",
                "Qty": 1,
                "Modifiers Applied": "Brown Sugar Cream Foam \u00d7 2.0",
            },
        ]

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "clean.csv"
            write_fixture_csv(path, rows)

            daily = build_daily_totals(path, None, None)

        row = daily.iloc[0]
        self.assertEqual(row["brown_sugar_cream_foam_drinks"], 2)
        self.assertEqual(row["pistachio_foam_drinks"], 2)

    def test_weekday_summary_medians_are_calculated_from_daily_totals(self):
        rows = [
            {
                "Date": "2026-01-05",
                "Item": "Brown Sugar Mist",
                "Qty": 2,
                "Modifiers Applied": "",
            },
            {
                "Date": "2026-01-12",
                "Item": "Brown Sugar Mist",
                "Qty": 8,
                "Modifiers Applied": "",
            },
            {
                "Date": "2026-01-19",
                "Item": "Brown Sugar Mist",
                "Qty": 20,
                "Modifiers Applied": "",
            },
            {
                "Date": "2026-01-06",
                "Item": "Pistachio Mist",
                "Qty": 4,
                "Modifiers Applied": "",
            },
            {
                "Date": "2026-01-13",
                "Item": "Pistachio Mist",
                "Qty": 10,
                "Modifiers Applied": "",
            },
        ]

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "clean.csv"
            write_fixture_csv(path, rows)

            summary = build_weekday_summary(build_daily_totals(path, None, None))

        monday = summary.loc[summary["day_of_week"].astype(str).eq("Monday")].iloc[0]
        tuesday = summary.loc[summary["day_of_week"].astype(str).eq("Tuesday")].iloc[0]

        self.assertEqual(monday["dates_count"], 3)
        self.assertEqual(monday["median_brown_sugar_cream_foam_drinks"], 8)
        self.assertEqual(monday["avg_brown_sugar_cream_foam_drinks"], 10)
        self.assertEqual(tuesday["dates_count"], 2)
        self.assertEqual(tuesday["median_pistachio_foam_drinks"], 7)
        self.assertEqual(tuesday["avg_pistachio_foam_drinks"], 7)

    def test_date_range_filter_is_inclusive(self):
        rows = [
            {
                "Date": "2026-01-01",
                "Item": "Brown Sugar Mist",
                "Qty": 1,
                "Modifiers Applied": "",
            },
            {
                "Date": "2026-01-02",
                "Item": "Brown Sugar Mist",
                "Qty": 2,
                "Modifiers Applied": "",
            },
            {
                "Date": "2026-01-03",
                "Item": "Brown Sugar Mist",
                "Qty": 3,
                "Modifiers Applied": "",
            },
        ]

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "clean.csv"
            write_fixture_csv(path, rows)

            daily = build_daily_totals(
                path,
                pd.Timestamp("2026-01-02"),
                pd.Timestamp("2026-01-03"),
            )

        self.assertEqual(daily["Date"].astype(str).tolist(), ["2026-01-02", "2026-01-03"])
        self.assertEqual(daily["brown_sugar_cream_foam_drinks"].tolist(), [2, 3])


class CreamFoamVerificationTests(unittest.TestCase):
    def test_build_expected_matches_generated_summary_shape_and_values(self):
        rows = [
            {
                "Date": "2026-01-05",
                "Item": "Brown Sugar Mist",
                "Qty": 2,
                "Modifiers Applied": "",
            },
            {
                "Date": "2026-01-05",
                "Item": "Milk Tea",
                "Qty": 3,
                "Modifiers Applied": "Pistachio Foam",
            },
            {
                "Date": "2026-01-12",
                "Item": "Milk Tea",
                "Qty": 4,
                "Modifiers Applied": "Brown Sugar Cream Foam",
            },
        ]

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "clean.csv"
            write_fixture_csv(path, rows)

            daily, summary, counts = build_expected(path)

        monday = normalize_summary(summary, Path("summary.csv")).iloc[0]
        self.assertEqual(len(daily), 2)
        self.assertEqual(counts["brown_union_rows"], 2)
        self.assertEqual(counts["pistachio_union_rows"], 1)
        self.assertEqual(counts["brown_union_qty"], 6)
        self.assertEqual(counts["pistachio_union_qty"], 3)
        self.assertEqual(monday["day_of_week"], "Monday")
        self.assertEqual(monday["median_brown_sugar_cream_foam_drinks"], 3)
        self.assertEqual(monday["median_pistachio_foam_drinks"], 1.5)

    def test_missing_required_column_fails_fast(self):
        rows = [
            {
                "Date": "2026-01-05",
                "Item": "Brown Sugar Mist",
                "Qty": 1,
            }
        ]

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "clean.csv"
            write_fixture_csv(path, rows)

            with self.assertRaisesRegex(ValueError, "Modifiers Applied"):
                build_daily_totals(path, None, None)


if __name__ == "__main__":
    unittest.main()
