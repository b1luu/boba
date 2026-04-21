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



