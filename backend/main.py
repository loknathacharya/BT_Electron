#!/usr/bin/env python3
"""
Python backend service for BYOD Strategy Backtesting Application
"""
import json
import sys
import os
import sqlite3
from pathlib import Path

class DatabaseService:
    """SQLite database service for trading data"""

    def __init__(self, db_path=None):
        if db_path is None:
            # Default to application data directory
            app_data = Path.home() / '.byod_backtesting'
            app_data.mkdir(exist_ok=True)
            db_path = app_data / 'trading_data.db'

        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize database with required tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS price_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        timestamp INTEGER NOT NULL,
                        open REAL NOT NULL,
                        high REAL NOT NULL,
                        low REAL NOT NULL,
                        close REAL NOT NULL,
                        volume INTEGER,
                        created_at INTEGER DEFAULT (strftime('%s', 'now')),
                        UNIQUE(symbol, timestamp)
                    )
                ''')

                conn.execute('''
                    CREATE TABLE IF NOT EXISTS strategies (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        description TEXT,
                        rules_json TEXT NOT NULL,
                        parameters_json TEXT,
                        created_at INTEGER DEFAULT (strftime('%s', 'now')),
                        updated_at INTEGER DEFAULT (strftime('%s', 'now'))
                    )
                ''')

                conn.execute('''
                    CREATE TABLE IF NOT EXISTS backtest_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        strategy_id INTEGER NOT NULL,
                        symbol TEXT NOT NULL,
                        start_date INTEGER NOT NULL,
                        end_date INTEGER NOT NULL,
                        initial_capital REAL NOT NULL,
                        final_equity REAL NOT NULL,
                        total_return REAL NOT NULL,
                        max_drawdown REAL NOT NULL,
                        win_rate REAL NOT NULL,
                        total_trades INTEGER NOT NULL,
                        results_json TEXT NOT NULL,
                        created_at INTEGER DEFAULT (strftime('%s', 'now')),
                        FOREIGN KEY (strategy_id) REFERENCES strategies (id)
                    )
                ''')

                conn.execute('''
                    CREATE TABLE IF NOT EXISTS trades (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        backtest_id INTEGER NOT NULL,
                        entry_timestamp INTEGER NOT NULL,
                        exit_timestamp INTEGER,
                        entry_price REAL NOT NULL,
                        exit_price REAL,
                        quantity REAL NOT NULL,
                        side TEXT NOT NULL,
                        pnl REAL,
                        commission REAL DEFAULT 0,
                        status TEXT DEFAULT 'open',
                        FOREIGN KEY (backtest_id) REFERENCES backtest_results (id)
                    )
                ''')

                print(f"Database initialized at: {self.db_path}")
                print(f"Database size: {self.db_path.stat().st_size} bytes")

        except Exception as e:
            print(f"Database initialization error: {e}")
            raise

    def test_connection(self):
        """Test database connection and return status"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                table_count = cursor.fetchone()[0]

                return {
                    'status': 'connected',
                    'database_path': str(self.db_path),
                    'database_size': self.db_path.stat().st_size,
                    'tables_count': table_count,
                    'tables': ['price_data', 'strategies', 'backtest_results', 'trades']
                }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }

# Global database service instance
db_service = DatabaseService()

import pandas as pd
from pandas.api.types import is_datetime64_any_dtype, is_numeric_dtype
from io import BytesIO
import os

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
    df = df.rename(columns=rename_map)

    title_map = {
        'ticker': 'Ticker', 'date': 'Date',
        'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close',
        'volume': 'Volume'
    }
    df = df.rename(columns={k: v for k, v in title_map.items() if k in df.columns})
    return df

def _parse_dates(series: pd.Series) -> pd.Series:
    s = series.copy()

    # Numeric epoch (heuristic for ms vs s)
    if is_numeric_dtype(s):
        median_val = pd.to_numeric(s, errors='coerce').dropna().median()
        if pd.notna(median_val) and median_val > 10**11:
            return pd.to_datetime(s, unit='ms', errors='coerce')
        else:
            return pd.to_datetime(s, unit='s', errors='coerce')

    # Strings: take left date part before space and try ISO first, then flexible
    s = s.astype(str).str.strip()
    s = s.str.split().str[0]
    parsed = pd.to_datetime(s, format='%Y-%m-%d', errors='coerce')
    if parsed.isna().all():
        parsed = pd.to_datetime(s, errors='coerce', dayfirst=False, utc=False)
    return parsed

def _read_any_ohlcv(file_path: str) -> pd.DataFrame:
    name = os.path.basename(file_path).lower()
    if name.endswith(".parquet"):
        return pd.read_parquet(file_path)
    elif name.endswith(".xlsx") or name.endswith(".xls"):
        return pd.read_excel(file_path)
    else:
        return pd.read_csv(file_path, low_memory=False)

def preview_file(file_path: str) -> dict:
    try:
        df = _read_any_ohlcv(file_path)
    except Exception as e:
        raise ValueError(f"Failed to read file '{file_path}': {e}")

    df = _standardize_ohlcv_columns(df)

    required = ['Date', 'Open', 'High', 'Low', 'Close']
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"OHLCV file is missing required columns: {missing}. Found: {list(df.columns)}")

    # Ticker is optional - if not present, we'll use a default value
    if 'Ticker' not in df.columns:
        df['Ticker'] = 'DEFAULT'  # Default symbol for files without ticker column

    # Parse dates
    df['Date'] = _parse_dates(df['Date'])
    if not is_datetime64_any_dtype(df['Date']):
        raise ValueError("Date column could not be reliably converted to datetime.")

    # Numeric coercion
    for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    before = len(df)
    df.dropna(subset=['Date', 'Close', 'Low', 'Open', 'High'], inplace=True)
    after = len(df)
    dropped = before - after

    # Sort (Ticker should now always be present after our check above)
    df = df.sort_values(['Ticker', 'Date']).reset_index(drop=True)

    # JSON-safe preview: format Date as ISO, first 10 rows
    df_preview = df.head(10).copy()
    df_preview['Date'] = df_preview['Date'].dt.strftime('%Y-%m-%d')
    preview_records = df_preview.to_dict(orient='records')

    return {
        "filename": os.path.basename(file_path),
        "rows_total": int(after),
        "rows_dropped": int(dropped),
        "columns": list(df.columns),
        "preview": preview_records
    }

def handle_request(request):
    """Handle incoming requests from Electron main process"""
    try:
        if request.get('action') == 'health-check':
            db_status = db_service.test_connection()
            return {
                'status': 'ok',
                'database': db_status,
                'python_version': sys.version,
                'message': 'Python backend is running'
            }
        elif request.get('action') == 'ping':
            return {
                'ok': True,
                'from': 'python',
                'message': 'Python backend responding to ping'
            }
        elif request.get('action') == 'preview-file':
            file_path = request.get('data', {}).get('file_path')
            if not file_path or not os.path.exists(file_path):
                return {'error': 'Invalid or missing file path'}
            return preview_file(file_path)
        elif request.get('action') == 'import-data':
            data = request.get('data', {})
            file_path = data.get('file_path')
            symbol = data.get('symbol', 'DEFAULT')

            if not file_path or not os.path.exists(file_path):
                return {'error': 'Invalid or missing file path'}

            try:
                # Read and process the file
                df = _read_any_ohlcv(file_path)
                df = _standardize_ohlcv_columns(df)

                # Ensure Ticker column exists
                if 'Ticker' not in df.columns:
                    df['Ticker'] = symbol

                # Parse dates and convert to timestamp
                df['Date'] = _parse_dates(df['Date'])
                if not is_datetime64_any_dtype(df['Date']):
                    return {'error': 'Date column could not be reliably converted to datetime'}

                # Convert dates to timestamps (seconds since epoch)
                df['Date'] = df['Date'].astype('int64') // 10**9

                # Numeric coercion
                for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')

                # Drop rows with missing required data
                before = len(df)
                print(f"Before dropna: {before} rows")
                print(f"Sample data before dropna: {df.head(2).to_dict()}")

                df.dropna(subset=['Date', 'Close', 'Low', 'Open', 'High'], inplace=True)
                after = len(df)

                print(f"After dropna: {after} rows, dropped: {before - after}")

                if after == 0:
                    return {'error': f'No valid data rows after cleaning. Before: {before}, After: {after}'}

                # Insert into database
                rows_imported = 0
                with sqlite3.connect(db_service.db_path) as conn:
                    for _, row in df.iterrows():
                        try:
                            # Debug: Print row data to see what's happening
                            print(f"Inserting row: Ticker={row.get('Ticker')}, Date={row.get('Date')}, Open={row.get('Open')}")

                            conn.execute('''
                                INSERT OR REPLACE INTO price_data
                                (symbol, timestamp, open, high, low, close, volume)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                str(row['Ticker']),
                                int(row['Date']),
                                float(row['Open']),
                                float(row['High']),
                                float(row['Low']),
                                float(row['Close']),
                                int(row['Volume']) if pd.notna(row['Volume']) and row['Volume'] != '' else None
                            ))
                            rows_imported += 1
                        except Exception as e:
                            print(f"Error inserting row {rows_imported}: {e}, row data: {dict(row)}")
                            continue

                return {
                    'success': True,
                    'rows_imported': rows_imported,
                    'symbol': symbol,
                    'total_rows': after,
                    'rows_dropped': before - after
                }

            except Exception as e:
                return {'error': f'Import failed: {str(e)}'}
        else:
            return {
                'error': 'Unknown action',
                'action': request.get('action')
            }
    except Exception as e:
        return {
            'error': str(e)
        }

def main():
    """Main entry point for the Python backend service"""
    print("Python backend process started", flush=True)

    try:
        for line in sys.stdin:
            if line.strip():
                try:
                    request = json.loads(line.strip())
                    response = handle_request(request)
                    print(json.dumps(response), flush=True)
                except json.JSONDecodeError as e:
                    print(json.dumps({'error': f'Invalid JSON: {e}'}), flush=True)
                except Exception as e:
                    print(json.dumps({'error': f'Processing error: {e}'}), flush=True)
    except KeyboardInterrupt:
        print("Python backend shutting down", flush=True)
    except Exception as e:
        print(json.dumps({'error': f'Fatal error: {e}'}), flush=True)

if __name__ == '__main__':
    main()