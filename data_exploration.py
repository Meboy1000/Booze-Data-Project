import pyarrow.parquet as pq
import pandas as pd

# Load data
file_path = "data_actually_clean/iowa_liquor_sales_combined.parquet"
parquet_file = pq.ParquetFile(file_path)

# Basic information
print("Columns:")
print(parquet_file.schema.names)

print("\nNumber of rows:")
print(parquet_file.metadata.num_rows)

print("\nNumber of columns:")
print(parquet_file.metadata.num_columns)


# Counters
negative_dollars = 0
zero_dollars = 0
negative_liters = 0
zero_liters = 0
both_negative = 0

zero_liters_positive_dollars = 0
zero_liters_zero_volume = 0
zero_liters_positive_volume = 0

# Missing values
missing_counts = pd.Series(
    0,
    index=parquet_file.schema.names,
    dtype="int64"
)

# Zero-liter problems by year
zero_liters_by_year = {}

# Store example problem rows
weird_examples = []


# Go through data one row group at a time
for i in range(parquet_file.num_row_groups):

    df = parquet_file.read_row_group(i).to_pandas()

    # -----------------------------
    # Missing values
    # -----------------------------

    missing_counts += df.isna().sum()


    # -----------------------------
    # Negative and zero sales
    # -----------------------------

    negative_dollars += (df["sales_dollars"] < 0).sum()
    zero_dollars += (df["sales_dollars"] == 0).sum()

    negative_liters += (df["sales_liters"] < 0).sum()
    zero_liters += (df["sales_liters"] == 0).sum()

    both_negative += (
        (df["sales_dollars"] < 0) &
        (df["sales_liters"] < 0)
    ).sum()


    # -----------------------------
    # Zero liters but positive sales
    # -----------------------------

    problem = (
        (df["sales_liters"] == 0) &
        (df["sales_dollars"] > 0)
    )

    zero_liters_positive_dollars += problem.sum()

    zero_liters_zero_volume += (
        problem &
        (df["bottle_volume_ml"] == 0)
    ).sum()

    zero_liters_positive_volume += (
        problem &
        (df["bottle_volume_ml"] > 0)
    ).sum()


    # -----------------------------
    # Count zero-liter problems by year
    # -----------------------------

    problem_rows = df[problem].copy()

    if len(problem_rows) > 0:

        problem_rows["year"] = pd.to_datetime(
            problem_rows["ordered_on"]
        ).dt.year

        counts = problem_rows["year"].value_counts()

        for year, count in counts.items():

            zero_liters_by_year[year] = (
                zero_liters_by_year.get(year, 0)
                + count
            )


    # -----------------------------
    # Save 20 example problem rows
    # -----------------------------

    weird = df[
        problem &
        (df["bottle_volume_ml"] > 0)
    ].copy()

    if len(weird) > 0 and len(weird_examples) < 20:

        # Calculate what sales_liters should be
        weird["calculated_liters"] = (
            weird["bottle_volume_ml"]
            * weird["sales_bottles"]
            / 1000
        )

        needed = 20 - len(weird_examples)

        weird_examples.extend(
            weird.head(needed).to_dict("records")
        )


# ==================================================
# RESULTS
# ==================================================

print("\n--- Unusual Values ---")

print("Negative sales dollars:", negative_dollars)
print("Zero sales dollars:", zero_dollars)

print("Negative sales liters:", negative_liters)
print("Zero sales liters:", zero_liters)

print(
    "Both dollars and liters negative:",
    both_negative
)

print(
    "Only dollars negative:",
    negative_dollars - both_negative
)

print(
    "Only liters negative:",
    negative_liters - both_negative
)

print(
    "Zero liters but positive dollars:",
    zero_liters_positive_dollars
)

print(
    "Zero liters + zero bottle volume:",
    zero_liters_zero_volume
)

print(
    "Zero liters + positive bottle volume:",
    zero_liters_positive_volume
)


# ==================================================
# MISSING VALUES
# ==================================================

print("\n--- Missing Values ---")

print(
    missing_counts.sort_values(
        ascending=False
    )
)


# Percent missing
total_rows = parquet_file.metadata.num_rows

missing_percent = (
    missing_counts
    / total_rows
    * 100
)

print("\n--- Percent Missing ---")

print(
    missing_percent
    .sort_values(ascending=False)
    .round(2)
)


# ==================================================
# ZERO LITER PROBLEMS BY YEAR
# ==================================================

print("\n--- Zero Liter Problems by Year ---")

for year in sorted(zero_liters_by_year):

    print(
        year,
        zero_liters_by_year[year]
    )


# ==================================================
# EXAMPLE PROBLEM ROWS
# ==================================================

print("\n--- Zero Liter Examples ---")

examples = pd.DataFrame(weird_examples)

if len(examples) > 0:

    print(
        examples[
            [
                "ordered_on",
                "im_desc",
                "bottle_volume_ml",
                "sales_bottles",
                "sales_dollars",
                "sales_liters",
                "calculated_liters"
            ]
        ].to_string(index=False)
    )
print("Finished")