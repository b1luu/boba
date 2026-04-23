from pathlib import Path
import pandas as pd

INPUT_PATH = "data/raw/raw.csv" 
OUTPUT_PATH = "data/raw/clean.csv"

REQUIRED_COLS = {
    "Date",
    "Category",
    "Item",
    "Qty",
    "Modifiers Applied",
    "Net Sales",
}

CJK_PATTERN = r"[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF]"

def clean_text_columns(df: pd.DataFrame) -> pd.DataFrame:
    for col in ["Category", "Item"]:
        df[col] = (
            df[col
            .fillna("")
            .str.replace(CJK_PATTERN, "",regex=True)
            .str.replace(r"\s+", " ",regrex=True)]
            .str.strip()
        )
    return df


df = pd.read_csv(INPUT_PATH, usecols=REQUIRED_COLS)

print(df.head())



