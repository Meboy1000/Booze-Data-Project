"""Unzip zip files from data/ into data_intermediate/, then convert those CSVs to Parquet in data_clean/."""

import zipfile
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent / "data"
INTERMEDIATE_DIR = Path(__file__).parent / "data_intermediate"
CLEAN_DIR = Path(__file__).parent / "data_clean"

# These are identifier codes, not numbers. Some years' files contain letters
# (e.g. "x904631"), so force them to string everywhere for a consistent schema.
ID_COLUMNS = [
    "store_zip_code",
    "county_fips_code",
    "category_code",
    "vendor_number",
    "item_no",
]


def unzip_all(data_dir: Path, intermediate_dir: Path) -> None:
    intermediate_dir.mkdir(exist_ok=True)
    for zip_path in data_dir.glob("*.zip"):
        try:
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(intermediate_dir)
            print(f"unzipped {zip_path.name}")
        except zipfile.BadZipFile:
            print(f"SKIPPED (corrupt zip): {zip_path.name}")


def convert_all(intermediate_dir: Path, clean_dir: Path) -> None:
    clean_dir.mkdir(exist_ok=True)
    for csv_path in intermediate_dir.glob("*.csv"):
        parquet_path = clean_dir / (csv_path.stem + ".parquet")
        df = pd.read_csv(csv_path, low_memory=False, dtype={col: str for col in ID_COLUMNS})
        df.to_parquet(parquet_path, index=False)
        print(f"converted {csv_path.name} -> {parquet_path.relative_to(Path(__file__).parent)}")


if __name__ == "__main__":
    unzip_all(DATA_DIR, INTERMEDIATE_DIR)
    convert_all(INTERMEDIATE_DIR, CLEAN_DIR)
