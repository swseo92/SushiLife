import pandas as pd
import numpy as np
import h5py
import pickle
import os

# It's good practice to ensure SushiLife is in PYTHONPATH or handle imports carefully.
# Assuming execution from repo root and PYTHONPATH is set, or SushiLife is installed.
try:
    from SushiLife.DataAsset import make_data
except ImportError:
    # Fallback for direct script execution if SushiLife is not in sys.path yet
    # This might be needed if running this script directly before PYTHONPATH is set
    import sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
    from SushiLife.DataAsset import make_data

def generate_data():
    # Define sample dates
    dates = pd.to_datetime(
        [f'2003-01-{i:02d}' for i in range(1, 32)] +
        [f'2003-02-{i:02d}' for i in range(1, 29)] +
        [f'2003-03-{i:02d}' for i in range(1, 32)]
    )

    # Define sample stock codes
    codes = [f'A{i:05d}' for i in range(1, 21)]  # 20 stocks

    # Define HDF5 filename
    hdf5_filename = "SushiLife/data/stock_info.hdf5"

    # Ensure SushiLife/data directory exists
    os.makedirs("SushiLife/data", exist_ok=True)

    # If hdf5_filename exists, delete it and its corresponding .axis files
    if os.path.exists(hdf5_filename):
        print(f"Removing existing file: {hdf5_filename}")
        os.remove(hdf5_filename)

    # The make_data function seems to handle axis files internally,
    # but to be safe, let's check for specific axis files if they were created by other means.
    stock_axis_file = f"{hdf5_filename}-stock.axis" # Actual name might vary based on make_data implementation
    if os.path.exists(stock_axis_file):
        print(f"Removing existing axis file: {stock_axis_file}")
        os.remove(stock_axis_file)

    value_axis_file = f"{hdf5_filename}-value.axis" # Actual name might vary based on make_data implementation
    if os.path.exists(value_axis_file):
        print(f"Removing existing axis file: {value_axis_file}")
        os.remove(value_axis_file)

    # Generate "stock" data
    stock_fields = ["현재가", "시가", "고가", "저가", "대비", "거래량(주)", "거래대금(원)", "상장시가총액(원)", "시장구분"]
    stock_data_dict = {}
    print("Generating 'stock' data...")
    for code in codes:
        df = pd.DataFrame(index=dates)
        for field in stock_fields:
            if field == "시장구분":
                df[field] = np.random.choice(["코스피", "코스닥"], size=len(dates))
            elif field in ["거래량(주)", "거래대금(원)", "상장시가총액(원)"]:
                df[field] = np.abs(np.random.rand(len(dates)) * 1000000 + 100000).astype(np.int64)
            else:  # 현재가, 시가, 고가, 저가, 대비
                df[field] = np.abs(np.random.rand(len(dates)) * 50000 + 1000).astype(np.float64)

        # Ensure OCHL consistency (Open, Close, High, Low)
        # 현재가 is effectively '종가' (close) in this context
        df["고가"] = df[["시가", "현재가"]].max(axis=1) + np.abs(np.random.rand(len(dates)) * 100)
        df["저가"] = df[["시가", "현재가"]].min(axis=1) - np.abs(np.random.rand(len(dates)) * 100)
        df["저가"] = df["저가"].clip(lower=1) # Prices must be positive

        # Ensure 고가 is the highest and 저가 is the lowest
        df["고가"] = df[["고가", "시가", "현재가"]].max(axis=1)
        df["저가"] = df[["저가", "시가", "현재가"]].min(axis=1)
        df["저가"] = df["저가"].clip(lower=1)


        stock_data_dict[code] = df
    make_data(hdf5_filename, "stock", stock_data_dict, dtype="stock", dates=list(dates))
    print("'stock' data generated.")

    # Generate "value" data
    value_fields = ["상장시가총액(원)", "지배주주순이익(원)(직전4분기)", "지배주주지분(원)", "현금흐름(원)(직전4분기)", "매출액(원)(직전4분기)"]
    value_data_dict = {}
    print("Generating 'value' data...")
    for code in codes:
        df = pd.DataFrame(index=dates)
        for field in value_fields:
            df[field] = np.abs(np.random.rand(len(dates)) * 1e9 + 1e7).astype(np.float64)
        value_data_dict[code] = df
    make_data(hdf5_filename, "value", value_data_dict, fields=value_fields, dates=list(dates))
    print("'value' data generated.")

    print("Dummy data generation script finished successfully.")

if __name__ == "__main__":
    generate_data()
