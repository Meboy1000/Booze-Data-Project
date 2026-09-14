import pyarrow.parquet as pq
import pyarrow as pa
import pandas as pd
from pathlib import Path


input_file = Path(
    "data_actually_clean/iowa_liquor_sales_combined.parquet"
)

output_file = Path(
    "data_actually_clean/iowa_liquor_sales_cleaned.parquet"
)

parquet_file = pq.ParquetFile(input_file)



starting_rows = parquet_file.metadata.num_rows

dropped_missing_sales = 0
dropped_missing_county = 0
fixed_liters = 0

writer = None


# Clean row by row, parquet feature

for i in range(parquet_file.num_row_groups):

    print(
        f"Cleaning row group "
        f"{i + 1}/{parquet_file.num_row_groups}"
    )

    df = parquet_file.read_row_group(i).to_pandas()


    #Drop state bottle cost and state bottle retail, there is so little data about both there is no point in keeping them

    df = df.drop(
        columns=[
            "state_bottle_cost",
            "state_bottle_retail"
        ]
    )


    # Convert date

    df["ordered_on"] = pd.to_datetime(
        df["ordered_on"],
        errors="coerce"
    )


    #Drop rows missing sales dollars, there are so few of them they're worth dropping

    missing_sales = df["sales_dollars"].isna()

    dropped_missing_sales += missing_sales.sum()

    df = df[~missing_sales].copy()


    #Drop rows without county level information

    missing_county = (
        df["county_fips_code"].isna() |
        df["county_name"].isna()
    )

    dropped_missing_county += missing_county.sum()

    df = df[~missing_county].copy()


    # Fix zero liter transactions

    fix = (
        (df["sales_liters"] == 0) &
        (df["sales_dollars"] > 0) &
        (df["bottle_volume_ml"] > 0) &
        (df["sales_bottles"] > 0)
    )

    fixed_liters += fix.sum()

    df.loc[fix, "sales_liters"] = (
        df.loc[fix, "bottle_volume_ml"]
        * df.loc[fix, "sales_bottles"]
        / 1000
    )


    #Keep negative sales, they're rollbacks
   




    table = pa.Table.from_pandas(
        df,
        preserve_index=False
    )

    if writer is None:

        writer = pq.ParquetWriter(
            output_file,
            table.schema,
            compression="snappy"
        )

    writer.write_table(table)


#Output file

if writer is not None:
    writer.close()


#Summary

ending_rows = (
    starting_rows
    - dropped_missing_sales
    - dropped_missing_county
)

print("\n==============================")
print("CLEANING COMPLETE")
print("==============================")

print("Starting rows:", starting_rows)

print(
    "Dropped for missing sales dollars:",
    dropped_missing_sales
)

print(
    "Dropped for missing county:",
    dropped_missing_county
)

print(
    "Fixed zero sales_liters:",
    fixed_liters
)

print("Final rows:", ending_rows)

print(
    "Rows removed:",
    starting_rows - ending_rows
)

print(
    "Output file:",
    output_file
)