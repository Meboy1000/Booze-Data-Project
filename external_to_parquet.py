"""Convert all CSVs in external_data/ to Parquet in external_data_clean/."""

from pathlib import Path

import pandas as pd

EXTERNAL_DIR = Path(__file__).parent / "external_data"
CLEAN_DIR = Path(__file__).parent / "external_data_clean"

if __name__ == "__main__":
    CLEAN_DIR.mkdir(exist_ok=True)
    for csv_path in EXTERNAL_DIR.glob("*.csv"):
        parquet_path = CLEAN_DIR / (csv_path.stem + ".parquet")
        df = pd.read_csv(csv_path, low_memory=False)
        df.to_parquet(parquet_path, index=False)
        print(f"converted {csv_path.name} -> {parquet_path.relative_to(Path(__file__).parent)}")
