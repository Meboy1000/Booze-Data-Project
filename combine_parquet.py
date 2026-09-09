"""Combine all Parquet files in data_clean/ into a single Parquet file in data_actually_clean/."""

from pathlib import Path

import pyarrow.dataset as ds
import pyarrow.parquet as pq

CLEAN_DIR = Path(__file__).parent / "data_clean"
OUTPUT_DIR = Path(__file__).parent / "data_actually_clean"
COMBINED_PATH = OUTPUT_DIR / "iowa_liquor_sales_combined.parquet"

if __name__ == "__main__":
    OUTPUT_DIR.mkdir(exist_ok=True)
    files = list(CLEAN_DIR.glob("*.parquet"))
    dataset = ds.dataset(files, format="parquet")
    pq.write_table(dataset.to_table(), COMBINED_PATH)
    print(f"combined {len(files)} files -> {COMBINED_PATH.relative_to(Path(__file__).parent)}")
