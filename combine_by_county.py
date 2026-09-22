"""Combine Iowa alcohol sales with the external county-level datasets, aligned by county and month.

The external datasets are yearly, so each yearly row is expanded into its 12 months
to line up with the alcohol sales data (which has an exact date per sale).
"""

from pathlib import Path

import pandas as pd
import pyarrow.dataset as ds

ALCOHOL_PATH = Path(__file__).parent / "data_actually_clean" / "iowa_liquor_sales_cleaned.parquet"
EXTERNAL_DIR = Path(__file__).parent / "external_data_clean"
OUTPUT_PATH = Path(__file__).parent / "data_actually_clean" / "county_month_combined.parquet"


def normalize_county(name: str) -> str:
    """Turn "Black Hawk County, Iowa" / "BLACK HAWK" / "Black Hawk" into one common form."""
    name = str(name).upper().strip()
    name = name.replace(", IOWA", "").replace(" COUNTY", "")
    return name.strip()


def expand_year_to_months(df: pd.DataFrame, year_col: str) -> pd.DataFrame:
    """Repeat each yearly row across all 12 months of that year."""
    months = pd.DataFrame({"month": range(1, 13)})
    df = df.merge(months, how="cross")
    df["year_month"] = df[year_col].astype(int).astype(str) + "-" + df["month"].astype(str).str.zfill(2)
    return df.drop(columns=["month", year_col])


def load_alcohol_by_county_month() -> pd.DataFrame:
    """Aggregate alcohol sales to one row per county-month,
    while also counting unique active stores.
    """

    columns = [
        "county_name",
        "ordered_on",
        "store_no",
        "sales_dollars",
        "sales_bottles",
        "sales_liters",
        "sales_gallons"
    ]

    dataset = ds.dataset(
        ALCOHOL_PATH,
        format="parquet"
    )

    totals = None

    # Save unique county-month-store combinations from each batch
    store_records = []

    for batch in dataset.to_batches(
        columns=columns,
        batch_size=1_000_000
    ):

        df = batch.to_pandas()

        df["ordered_on"] = pd.to_datetime(
            df["ordered_on"],
            errors="coerce"
        )

        df["county"] = (
            df["county_name"]
            .map(normalize_county)
        )

        df["year_month"] = (
            df["ordered_on"]
            .dt.to_period("M")
            .astype(str)
        )

        # -----------------------------
        # Sales aggregation
        # -----------------------------
        batch_totals = (
            df.groupby(
                ["county", "year_month"],
                as_index=False
            )
            .agg(
                sales_dollars=(
                    "sales_dollars",
                    "sum"
                ),
                sales_bottles=(
                    "sales_bottles",
                    "sum"
                ),
                sales_liters=(
                    "sales_liters",
                    "sum"
                ),
                sales_gallons=(
                    "sales_gallons",
                    "sum"
                )
            )
        )

        if totals is None:
            totals = batch_totals

        else:
            totals = (
                pd.concat(
                    [totals, batch_totals],
                    ignore_index=True
                )
                .groupby(
                    ["county", "year_month"],
                    as_index=False
                )
                .sum()
            )

        # -----------------------------
        # Store tracking
        # -----------------------------
        batch_stores = (
            df[
                [
                    "county",
                    "year_month",
                    "store_no"
                ]
            ]
            .dropna(subset=["store_no"])
            .drop_duplicates()
        )

        store_records.append(batch_stores)

    # Combine store records from all batches
    all_stores = pd.concat(
        store_records,
        ignore_index=True
    )

    # Important:
    # the same store can appear in multiple batches
    all_stores = all_stores.drop_duplicates(
        subset=[
            "county",
            "year_month",
            "store_no"
        ]
    )

    # Count unique active stores in each county-month
    store_counts = (
        all_stores
        .groupby(
            ["county", "year_month"]
        )
        ["store_no"]
        .nunique()
        .reset_index(
            name="num_stores"
        )
    )

    # Merge store counts onto sales totals
    totals = totals.merge(
        store_counts,
        on=["county", "year_month"],
        how="left"
    )

    return totals


def load_breathalcohol() -> pd.DataFrame:
    df = pd.read_parquet(EXTERNAL_DIR / "iowa_breathalcohol_by_county_year.parquet")
    df["county"] = df["county"].map(normalize_county)
    return expand_year_to_months(df, "year")[["county", "year_month", "avg_alcohol_level_g210L", "num_tests"]]


def load_population() -> pd.DataFrame:
    df = pd.read_parquet(EXTERNAL_DIR / "city_population_in_iowa_by_county_and_year_705_rows.parquet")
    df["county"] = df["county"].map(normalize_county)
    df["year"] = pd.to_datetime(df["calendar_year"]).dt.year
    # Sum every city's population up to a county total for that year.
    county_year = df.groupby(["county", "year"], as_index=False)["estimate"].sum()
    county_year = county_year.rename(columns={"estimate": "county_population"})
    return expand_year_to_months(county_year, "year")


def load_employment() -> pd.DataFrame:
    df = pd.read_parquet(
        EXTERNAL_DIR
        / "employment_status_for_iowa_civilian_population_16_years_old_and_over_acs_1_year_estimate_1188_rows.parquet"
    )
    df = df[df["geography_type"] == "County"].copy()
    df["county"] = df["geography_name"].map(normalize_county)
    df["year"] = df["data_collection_period"].astype(int)
    # One row per variable per county-year -> one column per variable.
    wide = df.pivot_table(index=["county", "year"], columns="variable", values="estimate", aggfunc="first")
    wide = wide.reset_index()
    wide.columns.name = None
    return expand_year_to_months(wide, "year")


if __name__ == "__main__":
    combined = load_alcohol_by_county_month()
    for loader in (load_breathalcohol, load_population):
        combined = combined.merge(loader(), on=["county", "year_month"], how="left")

    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    print("Input file:")
    print(ALCOHOL_PATH.resolve())

    print("\nOutput file:")
    print(OUTPUT_PATH.resolve())
    combined.to_parquet(OUTPUT_PATH, index=False)
    print(f"wrote {len(combined)} rows -> {OUTPUT_PATH.relative_to(Path(__file__).parent)}")
