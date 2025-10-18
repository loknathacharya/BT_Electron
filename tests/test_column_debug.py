#!/usr/bin/env python3
"""
Debug column standardization for user's file
"""

import pandas as pd
import sys
from pathlib import Path

# Add the backend directory to the path so we can import the function
sys.path.append(str(Path(__file__).parent.parent / "backend"))

def debug_column_standardization():
    """Debug the column standardization process"""
    print("🔍 Debugging column standardization...")

    # Create a sample dataframe with the user's column structure
    sample_data = {
        'ticker': ['AAPL', 'AAPL', 'MSFT'],
        'date': ['2024-12-2', '2024-12-3', '2024-12-4'],
        'open': [150.0, 152.0, 155.0],
        'high': [155.0, 157.0, 160.0],
        'low': [149.0, 151.0, 154.0],
        'close': [153.0, 155.0, 158.0],
        'volume': [1000, 1200, 1100]
    }

    df = pd.DataFrame(sample_data)
    print("Original columns:", list(df.columns))
    print("Original dtypes:", df.dtypes.to_dict())

    # Test the standardization function
    def _standardize_ohlcv_columns(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df.columns = df.columns.str.lower().str.strip()

        col_map = {
             'ticker': 'ticker', 'symbol': 'ticker', 'instrument': 'ticker', 'sym': 'ticker', 'asset': 'ticker',
             'date': 'date', 'datetime': 'date', 'timestamp': 'date', 'time': 'date',
             'open': 'open', 'o': 'open',
             'high': 'high', 'h': 'high',
             'low': 'low', 'l': 'low',
             'close': 'close', 'c': 'close', 'adj close': 'close', 'adj_close': 'close', 'adjusted close': 'close',
             'volume': 'volume', 'v': 'volume', 'vol': 'volume'
         }
        rename_map = {c: col_map[c] for c in df.columns if c in col_map}
        print("Rename map:", rename_map)
        df = df.rename(columns=rename_map)

        title_map = {
            'ticker': 'Ticker', 'date': 'Date',
            'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close',
            'volume': 'Volume'
        }
        df = df.rename(columns={k: v for k, v in title_map.items() if k in df.columns})
        return df

    # Apply standardization
    df_standardized = _standardize_ohlcv_columns(df)
    print("Standardized columns:", list(df_standardized.columns))
    print("Standardized dtypes:", df_standardized.dtypes.to_dict())

    # Check if required columns are present
    required = ['Date', 'Open', 'High', 'Low', 'Close']
    missing = [c for c in required if c not in df_standardized.columns]
    if missing:
        print(f"❌ Missing required columns: {missing}")
    else:
        print(f"✅ All required columns present: {required}")

    return df_standardized

if __name__ == "__main__":
    debug_column_standardization()