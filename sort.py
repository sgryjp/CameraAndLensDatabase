"""Script to sort cameras.csv and lenses.csv."""
import pandas as pd

if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("-o", "--overwrite", action="store_true")
    args = parser.parse_args()

    cameras = pd.read_csv("cameras.csv")
    cameras = cameras.sort_values(
        by=["Brand", "Mount", "Name"],
        kind="mergesort",
        key=lambda col: col.str.lower() if pd.api.types.is_string_dtype(col) else col,
    )
    filename = "cameras.csv" if args.overwrite else "cameras.sorted.csv"
    cameras.to_csv(filename, index=None, float_format="%g")

    lenses = pd.read_csv("lenses.csv")
    lenses = lenses.sort_values(
        by=[
            "Brand",
            "Mount",
            "Min. Focal Length (mm)",
            "Max. Focal Length (mm)",
            "Name",
        ],
        kind="mergesort",
        key=lambda col: col.str.lower() if pd.api.types.is_string_dtype(col) else col,
    )
    filename = "lenses.csv" if args.overwrite else "lenses.sorted.csv"
    lenses.to_csv(filename, index=None, float_format="%g")
