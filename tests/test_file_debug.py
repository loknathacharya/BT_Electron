#!/usr/bin/env python3
"""
Debug actual file processing
"""

import pandas as pd
import sys
import os
from pathlib import Path

# Add the backend directory to the path so we can import the functions
sys.path.append(str(Path(__file__).parent.parent / "backend"))

# Import the actual function from backend
from main import _standardize_ohlcv_columns

def debug_actual_file():
    """Debug processing of actual CSV files"""
    print("🔍 Debugging actual file processing...")

    # List available CSV files
    test_dir = Path(__file__).parent.parent
    csv_files = list(test_dir.glob("*.csv"))
    print(f"Found CSV files: {[f.name for f in csv_files]}")

    # Test each CSV file
    for csv_file in csv_files:
        print(f"\n📄 Testing file: {csv_file.name}")
        print("=" * 50)

        try:
            # Step 1: Read the file
            print("Step 1: Reading file...")
            df = pd.read_csv(csv_file, low_memory=False)
            print(f"  Raw columns: {list(df.columns)}")
            print(f"  Raw shape: {df.shape}")
            print(f"  First row: {df.iloc[0].to_dict()}")

            # Step 2: Standardize columns (using actual backend function)
            print("\nStep 2: Standardizing columns...")
            df_before = df.copy()
            print(f"  Before standardization: {list(df.columns)}")

            try:
                df = _standardize_ohlcv_columns(df)
                print(f"  After standardization: {list(df.columns)}")
            except Exception as e:
                print(f"  ❌ Standardization failed: {e}")
                # Fallback to manual standardization for debugging
                df.columns = df.columns.str.lower().str.strip()
                print(f"  Lowercase columns: {list(df.columns)}")

                col_map = {
                     'ticker': 'ticker', 'symbol': 'ticker', 'instrument': 'ticker', 'sym': 'ticker', 'asset': 'ticker',
                     'date': 'date', 'datetime': 'date', 'timestamp': 'date', 'time': 'date',
                     'open': 'open', 'o': 'open', 'open_price': 'open', 'price_open': 'open',
                     'high': 'high', 'h': 'high', 'high_price': 'high', 'price_high': 'high',
                     'low': 'low', 'l': 'low', 'low_price': 'low', 'price_low': 'low',
                     'close': 'close', 'c': 'close', 'adj close': 'close', 'adj_close': 'close', 'adjusted close': 'close', 'close_price': 'close', 'price_close': 'close',
                     'volume': 'volume', 'v': 'volume', 'vol': 'volume'
                 }
                rename_map = {c: col_map[c] for c in df.columns if c in col_map}
                print(f"  Rename map: {rename_map}")
                df = df.rename(columns=rename_map)
                print(f"  After rename: {list(df.columns)}")

                title_map = {
                    'ticker': 'Ticker', 'date': 'Date',
                    'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close',
                    'volume': 'Volume'
                }
                df = df.rename(columns={k: v for k, v in title_map.items() if k in df.columns})
                print(f"  Final columns: {list(df.columns)}")

            # Step 3: Check required columns
            required = ['Date', 'Open', 'High', 'Low', 'Close']
            missing = [c for c in required if c not in df.columns]
            if missing:
                print(f"  ❌ Missing required columns: {missing}")
            else:
                print(f"  ✅ All required columns present: {required}")

            # Step 4: Check data types
            print("\nStep 3: Checking data types...")
            for col in required:
                if col in df.columns:
                    print(f"  {col}: {df[col].dtype} - Sample values: {df[col].head(3).tolist()}")

            # Step 5: Try date parsing
            if 'Date' in df.columns:
                print("\nStep 4: Testing date parsing...")
                from pandas.api.types import is_datetime64_any_dtype, is_numeric_dtype

                def _parse_dates(series: pd.Series) -> pd.Series:
                    s = series.copy()

                    # Numeric epoch (heuristic for ms vs s)
                    if is_numeric_dtype(s):
                        median_val = pd.to_numeric(s, errors='coerce').dropna().median()
                        if pd.notna(median_val) and median_val > 10**11:
                            return pd.to_datetime(s, unit='ms', errors='coerce')
                        else:
                            return pd.to_datetime(s, unit='s', errors='coerce')

                    # Strings: try various formats
                    s = s.astype(str).str.strip()

                    # Try parsing with timezone info first
                    parsed = pd.to_datetime(s, errors='coerce', utc=False)
                    if parsed.isna().all():
                        # Try parsing just the date part
                        s = s.str.split().str[0]
                        parsed = pd.to_datetime(s, format='%Y-%m-%d', errors='coerce')
                    if parsed.isna().all():
                        # Try flexible parsing
                        parsed = pd.to_datetime(s, errors='coerce', dayfirst=False, utc=False)
                    return parsed

                try:
                    df['Date'] = _parse_dates(df['Date'])
                    if is_datetime64_any_dtype(df['Date']):
                        print("  ✅ Date parsing successful")
                        print(f"  Sample dates: {df['Date'].head(3).tolist()}")
                    else:
                        print("  ❌ Date parsing failed")
                        print(f"  Date column values: {df['Date'].head(3).tolist()}")
                except Exception as e:
                    print(f"  ❌ Date parsing error: {e}")

        except Exception as e:
            print(f"  ❌ Error processing file: {e}")

if __name__ == "__main__":
    debug_actual_file()