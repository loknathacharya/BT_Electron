#!/usr/bin/env python3
"""
Python backend service for BYOD Strategy Backtesting Application
"""
import json
import sys
import os
import sqlite3
import time
import datetime
from pathlib import Path
import pandas as pd
from pandas.api.types import is_datetime64_any_dtype, is_numeric_dtype

class DatabaseService:
    """SQLite database service for trading data with separate user and market databases"""

    def __init__(self, db_dir=None):
        if db_dir is None:
            # Default to application data directory
            self.db_dir = Path.home() / '.byod_backtesting'
            try:
                self.db_dir.mkdir(exist_ok=True)
                print(f"Database directory created/verified: {self.db_dir}", file=sys.stderr)
            except Exception as e:
                print(f"Failed to create database directory {self.db_dir}: {e}", file=sys.stderr)
                # Fallback to current directory
                self.db_dir = Path.cwd() / '.byod_backtesting'
                self.db_dir.mkdir(exist_ok=True)
                print(f"Using fallback database directory: {self.db_dir}", file=sys.stderr)
        else:
            # Use provided directory
            self.db_dir = Path(db_dir)
            self.db_dir.mkdir(exist_ok=True)
            print(f"Using custom database directory: {self.db_dir}", file=sys.stderr)

        # Separate databases as per Implementation Plan
        self.user_db_path = self.db_dir / 'user_data.db'
        self.market_db_path = self.db_dir / 'market_data.db'
        
        print(f"User database path: {self.user_db_path}", file=sys.stderr)
        print(f"Market database path: {self.market_db_path}", file=sys.stderr)
        
        self.init_user_database()
        self.init_market_database()

    def get_database_paths(self):
        """Return paths to both databases"""
        return {
            'user_db': str(self.user_db_path),
            'market_db': str(self.market_db_path),
            'db_dir': str(self.db_dir)
        }

    def init_user_database(self):
        """Initialize user database with required tables"""
        try:
            print(f"Initializing user database at: {self.user_db_path}", file=sys.stderr)

            # Check if file exists and get its size before connecting
            if self.user_db_path.exists():
                print(f"User database file already exists, size: {self.user_db_path.stat().st_size} bytes", file=sys.stderr)
            else:
                print("User database file does not exist, will be created", file=sys.stderr)

            with sqlite3.connect(self.user_db_path) as conn:
                # Apply performance optimizations from Implementation Plan benchmarks
                print("Applying SQLite performance optimizations to user database...", file=sys.stderr)
                conn.execute('PRAGMA journal_mode = WAL')
                conn.execute('PRAGMA synchronous = NORMAL')
                conn.execute('PRAGMA cache_size = 10000')
                conn.execute('PRAGMA temp_store = MEMORY')
                conn.execute('PRAGMA mmap_size = 268435456')  # 256MB memory mapping
                print("User database optimizations applied", file=sys.stderr)
                
                print("Connected to user database successfully", file=sys.stderr)

                # Create user tables
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

                # Verify tables were created
                cursor = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                table_count = cursor.fetchone()[0]
                print(f"User database initialized successfully with {table_count} tables", file=sys.stderr)

                # Get final database size
                final_size = self.user_db_path.stat().st_size
                print(f"User database final size: {final_size} bytes", file=sys.stderr)

        except Exception as e:
            print(f"User database initialization error: {e}", file=sys.stderr)
            print(f"Error type: {type(e).__name__}", file=sys.stderr)
            import traceback
            print(f"Traceback: {traceback.format_exc()}", file=sys.stderr)
            raise

    def init_market_database(self):
        """Initialize market database with required tables"""
        try:
            print(f"Initializing market database at: {self.market_db_path}", file=sys.stderr)

            # Check if file exists and get its size before connecting
            if self.market_db_path.exists():
                print(f"Market database file already exists, size: {self.market_db_path.stat().st_size} bytes", file=sys.stderr)
            else:
                print("Market database file does not exist, will be created", file=sys.stderr)

            with sqlite3.connect(self.market_db_path) as conn:
                # Apply performance optimizations from Implementation Plan benchmarks
                print("Applying SQLite performance optimizations to market database...", file=sys.stderr)
                conn.execute('PRAGMA journal_mode = WAL')
                conn.execute('PRAGMA synchronous = NORMAL')
                conn.execute('PRAGMA cache_size = 10000')
                conn.execute('PRAGMA temp_store = MEMORY')
                conn.execute('PRAGMA mmap_size = 268435456')  # 256MB memory mapping
                print("Market database optimizations applied", file=sys.stderr)
                
                print("Connected to market database successfully", file=sys.stderr)

                # Create market tables
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

                # Create symbols metadata table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS symbols (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT UNIQUE NOT NULL,
                        name TEXT,
                        data_start INTEGER,
                        data_end INTEGER,
                        total_rows INTEGER DEFAULT 0,
                        last_updated INTEGER DEFAULT (strftime('%s', 'now')),
                        metadata_json TEXT
                    )
                ''')

                # Create data uploads tracking table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS data_uploads (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        filename TEXT NOT NULL,
                        file_size INTEGER NOT NULL,
                        symbol TEXT NOT NULL,
                        rows_processed INTEGER DEFAULT 0,
                        status TEXT DEFAULT 'pending',
                        created_at INTEGER DEFAULT (strftime('%s', 'now')),
                        completed_at INTEGER,
                        error_message TEXT,
                        metadata_json TEXT
                    )
                ''')

                # Create intraday data table for future support
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS ohlcv_intraday (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        timestamp INTEGER NOT NULL,
                        timeframe TEXT NOT NULL,
                        open REAL NOT NULL,
                        high REAL NOT NULL,
                        low REAL NOT NULL,
                        close REAL NOT NULL,
                        volume INTEGER,
                        created_at INTEGER DEFAULT (strftime('%s', 'now')),
                        UNIQUE(symbol, timestamp, timeframe)
                    )
                ''')

                # Create datasets metadata table for tracking uploaded/available datasets
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS datasets (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        description TEXT,
                        symbols_json TEXT,
                        date_range_start INTEGER,
                        date_range_end INTEGER,
                        symbol_count INTEGER DEFAULT 0,
                        total_rows INTEGER DEFAULT 0,
                        created_at INTEGER DEFAULT (strftime('%s', 'now')),
                        last_updated INTEGER DEFAULT (strftime('%s', 'now')),
                        last_updated_at_ts INTEGER DEFAULT (strftime('%s', 'now')),
                        metadata_json TEXT
                    )
                ''')

                # Verify tables were created
                cursor = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                table_count = cursor.fetchone()[0]
                print(f"Market database initialized successfully with {table_count} tables", file=sys.stderr)

                # Get final database size
                final_size = self.market_db_path.stat().st_size
                print(f"Market database final size: {final_size} bytes", file=sys.stderr)

        except Exception as e:
            print(f"Market database initialization error: {e}", file=sys.stderr)
            print(f"Error type: {type(e).__name__}", file=sys.stderr)
            import traceback
            print(f"Traceback: {traceback.format_exc()}", file=sys.stderr)
            raise

    def test_connection(self):
        """Test database connection and return status for both databases"""
        try:
            print(f"DEBUG: Testing connection to user database: {self.user_db_path}", file=sys.stderr)
            # Test user database
            with sqlite3.connect(self.user_db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                user_table_count = cursor.fetchone()[0]
            print(f"DEBUG: User database connection successful, {user_table_count} tables", file=sys.stderr)

            print(f"DEBUG: Testing connection to market database: {self.market_db_path}", file=sys.stderr)
            # Test market database
            with sqlite3.connect(self.market_db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                market_table_count = cursor.fetchone()[0]
            print(f"DEBUG: Market database connection successful, {market_table_count} tables", file=sys.stderr)

            return {
                'status': 'connected',
                'databases': {
                    'user_db': {
                        'path': str(self.user_db_path),
                        'size': self.user_db_path.stat().st_size,
                        'tables_count': user_table_count,
                        'tables': ['strategies', 'backtest_results', 'trades']
                    },
                    'market_db': {
                        'path': str(self.market_db_path),
                        'size': self.market_db_path.stat().st_size,
                        'tables_count': market_table_count,
                        'tables': ['price_data', 'symbols', 'data_uploads', 'ohlcv_intraday']
                    }
                },
                'total_tables': user_table_count + market_table_count
            }
        except Exception as e:
            print(f"DEBUG: Connection test failed: {e}", file=sys.stderr)
            return {
                'status': 'error',
                'error': str(e)
            }

    def get_symbol_data_range(self, symbol: str) -> dict:
        """Get the existing date range for a symbol in the database"""
        try:
            print(f"DEBUG: get_symbol_data_range called for {symbol}", file=sys.stderr)
            print(f"DEBUG: Using market database path: {self.market_db_path}", file=sys.stderr)
            with sqlite3.connect(self.market_db_path) as conn:
                cursor = conn.execute('''
                    SELECT MIN(timestamp) as min_timestamp, MAX(timestamp) as max_timestamp, COUNT(*) as total_rows
                    FROM price_data
                    WHERE symbol = ?
                ''', (symbol,))
                
                result = cursor.fetchone()
                print(f"DEBUG: Query result: {result}", file=sys.stderr)
                if result[0] is None:  # No data exists for this symbol
                    return {
                        'has_data': False,
                        'min_timestamp': None,
                        'max_timestamp': None,
                        'total_rows': 0
                    }
                
                return {
                    'has_data': True,
                    'min_timestamp': result[0],
                    'max_timestamp': result[1],
                    'total_rows': result[2]
                }
        except Exception as e:
            print(f"DEBUG: Error getting symbol data range for {symbol}: {e}", file=sys.stderr)
            return {
                'has_data': False,
                'min_timestamp': None,
                'max_timestamp': None,
                'total_rows': 0,
                'error': str(e)
            }

    def filter_incremental_data(self, df: pd.DataFrame, symbol: str) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Filter dataframe to only include new data for incremental updates"""
        print(f"DEBUG: filter_incremental_data called for {symbol}", file=sys.stderr)
        print(f"DEBUG: Input dataframe shape: {df.shape}", file=sys.stderr)
        
        # Get existing data range for the symbol
        existing_range = self.get_symbol_data_range(symbol)
        print(f"DEBUG: Existing range: {existing_range}", file=sys.stderr)
        
        if not existing_range['has_data']:
            # No existing data, return all data as new
            print(f"DEBUG: No existing data, returning all data as new", file=sys.stderr)
            return df, pd.DataFrame()
        
        # Convert timestamp column to datetime for comparison
        df_copy = df.copy()
        df_copy['Date_dt'] = pd.to_datetime(df_copy['Date'], unit='s')
        
        # Get existing date range as datetime
        existing_min = pd.to_datetime(existing_range['min_timestamp'], unit='s')
        existing_max = pd.to_datetime(existing_range['max_timestamp'], unit='s')
        print(f"DEBUG: Existing date range: {existing_min} to {existing_max}", file=sys.stderr)
        
        # Find new data (timestamps outside existing range)
        new_data_mask = (
            (df_copy['Date_dt'] > existing_max) |
            (df_copy['Date_dt'] < existing_min)
        )
        
        # Also find data that might fill gaps within the range
        # This handles cases where there are missing dates in the middle
        all_dates = df_copy['Date_dt'].unique()
        existing_dates = pd.date_range(existing_min, existing_max, freq='D')
        
        # Find dates that don't exist in the database
        missing_dates = set(all_dates) - set(existing_dates)
        gap_fill_mask = df_copy['Date_dt'].isin(missing_dates)
        
        # Combine both conditions for new data
        new_data_mask = new_data_mask | gap_fill_mask
        
        new_data = df_copy[new_data_mask].copy()
        existing_data = df_copy[~new_data_mask].copy()
        
        # Drop the temporary datetime column
        new_data = new_data.drop(columns=['Date_dt'])
        existing_data = existing_data.drop(columns=['Date_dt'])
        
        print(f"DEBUG: Filtered - new data: {len(new_data)}, existing data: {len(existing_data)}", file=sys.stderr)
        
        return new_data, existing_data

    def get_import_summary(self, symbol: str) -> dict:
        """Get summary of existing data for a symbol"""
        try:
            with sqlite3.connect(self.market_db_path) as conn:
                cursor = conn.execute('''
                    SELECT data_start, data_end, total_rows, last_updated, metadata_json
                    FROM symbols
                    WHERE symbol = ?
                ''', (symbol,))
                
                result = cursor.fetchone()
                if result:
                    return {
                        'symbol': symbol,
                        'data_start': result[0],
                        'data_end': result[1],
                        'total_rows': result[2],
                        'last_updated': result[3],
                        'metadata_json': json.loads(result[4]) if result[4] else {}
                    }
                else:
                    return {
                        'symbol': symbol,
                        'data_start': None,
                        'data_end': None,
                        'total_rows': 0,
                        'last_updated': None,
                        'metadata_json': {}
                    }
        except Exception as e:
            print(f"Error getting import summary for {symbol}: {e}", file=sys.stderr)
            return {
                'symbol': symbol,
                'error': str(e)
            }

    def create_dataset(self, name: str, description: str = '', symbols = None) -> dict:
        """Create or update a dataset record with metadata"""
        try:
            if not name:
                return {'error': 'Dataset name is required'}
            
            with sqlite3.connect(self.market_db_path) as conn:
                # Get current data summary
                cursor = conn.execute('''
                    SELECT DISTINCT symbol, MIN(timestamp) as start_ts, MAX(timestamp) as end_ts, COUNT(*) as cnt
                    FROM price_data
                    GROUP BY symbol
                    ORDER BY symbol
                ''')
                
                data = cursor.fetchall()
                all_symbols = [row[0] for row in data]
                min_ts = min([row[1] for row in data]) if data else None
                max_ts = max([row[2] for row in data]) if data else None
                total_rows = sum([row[3] for row in data]) if data else 0
                
                # Create or update dataset record
                symbols_json = json.dumps(all_symbols)
                now_ts = int(time.time())
                
                cursor = conn.execute('''
                    INSERT OR REPLACE INTO datasets 
                    (name, description, symbols_json, date_range_start, date_range_end, 
                     symbol_count, total_rows, last_updated_at_ts)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (name, description, symbols_json, min_ts, max_ts, len(all_symbols), total_rows, now_ts))
                
                conn.commit()
                
                return {
                    'success': True,
                    'dataset': {
                        'name': name,
                        'description': description,
                        'symbols': all_symbols,
                        'date_range_start': min_ts,
                        'date_range_end': max_ts,
                        'symbol_count': len(all_symbols),
                        'total_rows': total_rows,
                        'last_updated': now_ts
                    }
                }
        except Exception as e:
            print(f"Error creating dataset '{name}': {e}", file=sys.stderr)
            return {'error': str(e)}

    def get_all_datasets(self) -> dict:
        """Get list of all available datasets with metadata"""
        try:
            with sqlite3.connect(self.market_db_path) as conn:
                cursor = conn.execute('''
                    SELECT id, name, description, symbols_json, date_range_start, date_range_end,
                           symbol_count, total_rows, created_at, last_updated_at_ts
                    FROM datasets
                    ORDER BY last_updated_at_ts DESC
                ''')
                
                datasets = []
                for row in cursor.fetchall():
                    datasets.append({
                        'id': row[0],
                        'name': row[1],
                        'description': row[2],
                        'symbols': json.loads(row[3]) if row[3] else [],
                        'date_range_start': row[4],
                        'date_range_end': row[5],
                        'symbol_count': row[6],
                        'total_rows': row[7],
                        'created_at': row[8],
                        'last_updated': row[9]
                    })
                
                return {
                    'success': True,
                    'datasets': datasets,
                    'count': len(datasets)
                }
        except Exception as e:
            print(f"Error retrieving datasets: {e}", file=sys.stderr)
            return {'error': str(e), 'datasets': []}

    def get_dataset(self, name: str) -> dict:
        """Get specific dataset by name"""
        try:
            with sqlite3.connect(self.market_db_path) as conn:
                cursor = conn.execute('''
                    SELECT id, name, description, symbols_json, date_range_start, date_range_end,
                           symbol_count, total_rows, created_at, last_updated_at_ts
                    FROM datasets
                    WHERE name = ?
                ''', (name,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'success': True,
                        'dataset': {
                            'id': row[0],
                            'name': row[1],
                            'description': row[2],
                            'symbols': json.loads(row[3]) if row[3] else [],
                            'date_range_start': row[4],
                            'date_range_end': row[5],
                            'symbol_count': row[6],
                            'total_rows': row[7],
                            'created_at': row[8],
                            'last_updated': row[9]
                        }
                    }
                else:
                    return {'error': f'Dataset "{name}" not found'}
        except Exception as e:
            print(f"Error retrieving dataset '{name}': {e}", file=sys.stderr)
            return {'error': str(e)}

# Global database service instance
db_service = DatabaseService()

class ValidationError(Exception):
    """Custom exception for validation errors"""
    def __init__(self, message, row_index=None, column=None, value=None):
        super().__init__(message)
        self.row_index = row_index
        self.column = column
        self.value = value

class DataValidationPipeline:
    """Comprehensive data validation pipeline for OHLCV data"""

    def __init__(self):
        self.errors = []
        self.warnings = []

    def validate_dataframe(self, df: pd.DataFrame) -> tuple[bool, list, list]:
        """Run all validations on the dataframe"""
        self.errors = []
        self.warnings = []

        # Required columns validation
        self._validate_required_columns(df)

        # Data type validation
        self._validate_data_types(df)

        # Price validation
        self._validate_price_data(df)

        # Date validation
        self._validate_dates(df)

        # Duplicate validation
        self._validate_duplicates(df)

        # Volume validation (if present)
        self._validate_volume(df)

        return len(self.errors) == 0, self.errors, self.warnings

    def _validate_required_columns(self, df: pd.DataFrame):
        """Validate that all required columns are present"""
        required_columns = ['Date', 'Open', 'High', 'Low', 'Close']
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            self.errors.append(f"Missing required columns: {', '.join(missing_columns)}")

    def _validate_data_types(self, df: pd.DataFrame):
        """Validate data types for each column"""
        # Numeric columns should be convertible to float
        numeric_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in numeric_columns:
            if col in df.columns:
                try:
                    pd.to_numeric(df[col], errors='coerce')
                except Exception as e:
                    self.errors.append(f"Column '{col}' contains non-numeric data: {str(e)}")

    def _validate_price_data(self, df: pd.DataFrame):
        """Validate price relationships and values"""
        if all(col in df.columns for col in ['Open', 'High', 'Low', 'Close']):
            # Check for negative prices
            for col in ['Open', 'High', 'Low', 'Close']:
                negative_prices = df[col] < 0
                if negative_prices.any():
                    count = negative_prices.sum()
                    self.errors.append(f"Column '{col}' contains {count} negative price(s)")

            # Check price relationships: High >= Open, High >= Close, Low <= Open, Low <= Close
            if not (df['High'] >= df['Open']).all():
                violations = (~(df['High'] >= df['Open'])).sum()
                self.warnings.append(f"High < Open in {violations} row(s)")

            if not (df['High'] >= df['Close']).all():
                violations = (~(df['High'] >= df['Close'])).sum()
                self.warnings.append(f"High < Close in {violations} row(s)")

            if not (df['Low'] <= df['Open']).all():
                violations = (~(df['Low'] <= df['Open'])).sum()
                self.warnings.append(f"Low > Open in {violations} row(s)")

            if not (df['Low'] <= df['Close']).all():
                violations = (~(df['Low'] <= df['Close'])).sum()
                self.warnings.append(f"Low > Close in {violations} row(s)")

    def _validate_dates(self, df: pd.DataFrame):
        """Validate date column"""
        if 'Date' in df.columns:
            # Check for invalid dates
            if df['Date'].isna().any():
                na_count = df['Date'].isna().sum()
                self.errors.append(f"Date column contains {na_count} invalid date(s)")

            # Check for duplicate timestamps
            if df['Date'].duplicated().any():
                dup_count = df['Date'].duplicated().sum()
                self.warnings.append(f"Date column contains {dup_count} duplicate timestamp(s)")

    def _validate_duplicates(self, df: pd.DataFrame):
        """Validate for duplicate rows"""
        if 'Date' in df.columns and 'Ticker' in df.columns:
            duplicates = df.duplicated(subset=['Ticker', 'Date'], keep=False)
            if duplicates.any():
                dup_count = duplicates.sum()
                self.warnings.append(f"Found {dup_count} duplicate row(s) based on Ticker and Date")

    def _validate_volume(self, df: pd.DataFrame):
        """Validate volume data if present"""
        if 'Volume' in df.columns:
            # Check for negative volume
            negative_volume = df['Volume'] < 0
            if negative_volume.any():
                count = negative_volume.sum()
                self.errors.append(f"Volume column contains {count} negative value(s)")

            # Check for zero volume (might be valid for some instruments)
            zero_volume = df['Volume'] == 0
            if zero_volume.any():
                count = zero_volume.sum()
                self.warnings.append(f"Volume column contains {count} zero value(s)")

class ProgressReporter:
    """Handles progress reporting to Electron frontend"""

    def __init__(self, total_rows=0):
        self.total_rows = total_rows
        self.current_row = 0
        self.start_time = time.time()
        self.last_report_time = 0

    def report_progress(self, current_row, errors=None):
        """Report progress to stdout for Electron to capture"""
        self.current_row = current_row
        current_time = time.time()

        # Only report every 0.5 seconds to avoid spam
        if current_time - self.last_report_time < 0.5 and current_row < self.total_rows:
            return

        if self.total_rows > 0:
            progress = int((current_row / self.total_rows) * 100)
        else:
            # Estimate progress based on file size for files without known row count
            progress = min(95, int((current_row / max(1, current_row + 1000)) * 100))  # Cap at 95% until final

        elapsed_time = current_time - self.start_time

        report = {
            'type': 'import-progress',
            'progress': progress,
            'currentRow': current_row,
            'totalRows': self.total_rows,
            'elapsedTime': round(elapsed_time, 2)
        }

        if errors:
            report['errors'] = errors

        print(json.dumps(report), flush=True)
        self.last_report_time = current_time

    def report_summary(self, summary_data):
        """Report final summary"""
        summary_data['type'] = 'import-summary'
        response_json = json.dumps(summary_data)
        print(f"IMPORT: Sending final response: {response_json}", file=sys.stderr)
        print(response_json, flush=True)
        print(f"IMPORT: Final response sent", file=sys.stderr)

def _apply_custom_column_mapping(df: pd.DataFrame, column_mapping: dict) -> pd.DataFrame:
    """Apply custom column mapping from frontend"""
    df = df.copy()

    # Map the columns according to the frontend mapping
    rename_map = {}
    field_name_map = {
        'timestamp': 'Date',
        'open': 'Open',
        'high': 'High',
        'low': 'Low',
        'close': 'Close',
        'volume': 'Volume',
        'ticker': 'Ticker'
    }
    
    for target_field, source_column in column_mapping.items():
        if source_column in df.columns:
            if target_field in field_name_map:
                rename_map[source_column] = field_name_map[target_field]

    # Apply the renaming
    df = df.rename(columns=rename_map)

    # Also handle case-insensitive matching - check if columns exist in different cases
    for standard_name in field_name_map.values():
        if standard_name not in df.columns:
            # Look for column with different case
            for col in df.columns:
                if col.lower() == standard_name.lower():
                    df[standard_name] = df[col]
                    df = df.drop(columns=[col])
                    break

    # Validate that we have the required columns
    required_columns = ['Date', 'Open', 'High', 'Low', 'Close']
    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        raise ValueError(f"Missing required columns after mapping: {missing_columns}. Available columns: {list(df.columns)}")

    return df

def _generate_column_mapping(df: pd.DataFrame) -> dict:
    """Generate intelligent column mapping with confidence scores"""
    mapping = {}
    confidence_scores = {}
    
    # Define comprehensive column patterns for each field type
    field_patterns = {
        'timestamp': [
            # Date patterns
            'date', 'datetime', 'timestamp', 'time', 'trade_date', 'trade_time',
            'dt', 'trade_dt', 'execution_date', 'execution_time',
            # Unix timestamp patterns
            'unix_timestamp', 'epoch', 'timestamp_ms', 'timestamp_s',
            # Excel date patterns
            'excel_date', 'serial_date',
            # Other date formats
            'trade_date', 'settlement_date', 'expiration_date'
        ],
        'open': [
            'open', 'o', 'open_price', 'price_open', 'open_px', 'px_open',
            'trade_open', 'entry', 'open_trade', 'open_exec',
            'open_bid', 'bid_open', 'open_ask', 'ask_open',
            'open_last', 'last_open', 'open_close', 'close_open'
        ],
        'high': [
            'high', 'h', 'high_price', 'price_high', 'high_px', 'px_high',
            'trade_high', 'high_trade', 'high_exec', 'high_bid', 'bid_high',
            'high_ask', 'ask_high', 'high_last', 'last_high'
        ],
        'low': [
            'low', 'l', 'low_price', 'price_low', 'low_px', 'px_low',
            'trade_low', 'low_trade', 'low_exec', 'low_bid', 'bid_low',
            'low_ask', 'ask_low', 'low_last', 'last_low'
        ],
        'close': [
            'close', 'c', 'close_price', 'price_close', 'close_px', 'px_close',
            'trade_close', 'close_trade', 'close_exec', 'close_bid', 'bid_close',
            'close_ask', 'ask_close', 'close_last', 'last_close',
            'adj_close', 'adj_close_price', 'adjusted_close', 'price_adj_close',
            'settle', 'settlement', 'settlement_price'
        ],
        'volume': [
            'volume', 'vol', 'v', 'volume traded', 'traded_volume',
            'trade_volume', 'vol traded', 'qty', 'quantity', 'shares',
            'volume_shares', 'trade_qty', 'exec_qty', 'exec_volume',
            'bid_size', 'ask_size', 'size', 'trade_size'
        ],
        'ticker': [
            'ticker', 'symbol', 'instrument', 'sym', 'asset', 'code',
            'ticker_symbol', 'stock_symbol', 'instrument_code', 'asset_code',
            'security', 'security_id', 'isin', 'cusip', 'sedol',
            'company', 'company_name', 'name', 'security_name'
        ]
    }
    
    # Convert all columns to lowercase for case-insensitive matching
    original_columns = df.columns.tolist()
    lower_columns = [col.lower().strip() for col in original_columns]
    
    # Create a mapping from normalized column names to original names
    column_map = {lower: original for lower, original in zip(lower_columns, original_columns)}
    
    # Try to match each field type
    for field_type, patterns in field_patterns.items():
        best_match = None
        best_score = 0
        
        for pattern in patterns:
            # Exact match
            if pattern in column_map:
                best_match = column_map[pattern]
                best_score = 100
                break
            
            # Partial match (contains)
            for col_lower in lower_columns:
                if pattern in col_lower:
                    score = len(pattern) / len(col_lower) * 80  # Score based on pattern length ratio
                    if score > best_score:
                        best_score = score
                        best_match = column_map[col_lower]
        
        if best_match and best_score >= 50:  # Minimum confidence threshold
            mapping[field_type] = best_match
            confidence_scores[field_type] = best_score
    
    return {
        "mapping": mapping,
        "confidence_scores": confidence_scores
    }

def _standardize_ohlcv_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = df.columns.str.lower().str.strip()

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

def _read_any_ohlcv(file_path: str) -> pd.DataFrame:
    name = os.path.basename(file_path).lower()
    if name.endswith(".parquet"):
        return pd.read_parquet(file_path)
    elif name.endswith(".xlsx") or name.endswith(".xls"):
        return pd.read_excel(file_path)
    else:
        return pd.read_csv(file_path, low_memory=False)

def preview_file(file_path: str, request_id: str | None = None) -> dict:
    try:
        df = _read_any_ohlcv(file_path)
    except Exception as e:
        raise ValueError(f"Failed to read file '{file_path}': {e}")

    # Generate intelligent auto-mapping before standardization
    auto_mapping_result = _generate_column_mapping(df)
    auto_mapping = auto_mapping_result.get("mapping", {})
    confidence_scores = auto_mapping_result.get("confidence_scores", {})
    
    # Apply auto-mapping if we have sufficient confidence
    if auto_mapping:
        df = _apply_custom_column_mapping(df, auto_mapping)
    else:
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
            print(f"Converting column {col}: {df[col].head(3).tolist()}", file=sys.stderr)
            df[col] = pd.to_numeric(df[col], errors='coerce')
            print(f"After conversion: {df[col].head(3).tolist()}", file=sys.stderr)

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
        "preview": preview_records,
        "auto_mapping": auto_mapping,
        "confidence_scores": confidence_scores,
        "requestId": request_id
    }

def handle_request(request, db_service_override=None):
    """Handle incoming requests from Electron main process
    
    Args:
        request: dict with action, data, and requestId
        db_service_override: optional DatabaseService instance for testing (uses global if None)
    """
    # Use provided db_service or fall back to global
    current_db_service = db_service_override or db_service
    
    # Initialize request_id early to avoid unbound variable issues
    request_id = request.get('requestId', 'unknown')

    try:
        if request.get('action') == 'health-check':
            db_status = current_db_service.test_connection()
            return {
                'status': 'ok',
                'database': db_status,
                'python_version': sys.version,
                'message': 'Python backend is running',
                'requestId': request_id
            }
        elif request.get('action') == 'ping':
            return {
                'ok': True,
                'from': 'python',
                'message': 'Python backend responding to ping',
                'requestId': request_id
            }
        elif request.get('action') == 'preview-file':
            file_path = request.get('data', {}).get('file_path')
            if not file_path or not os.path.exists(file_path):
                return {'error': 'Invalid or missing file path', 'requestId': request_id}
            return preview_file(file_path, request_id)
        elif request.get('action') == 'get-price-data':
            """Get price data from database for viewing"""
            try:
                symbol = request.get('data', {}).get('symbol', 'ALL')
                limit = request.get('data', {}).get('limit', 1000)
                offset = request.get('data', {}).get('offset', 0)
                start_date = request.get('data', {}).get('start_date')
                end_date = request.get('data', {}).get('end_date')
                
                with sqlite3.connect(current_db_service.market_db_path) as conn:
                    # Build base query
                    base_query = '''
                        SELECT symbol, timestamp, open, high, low, close, volume
                        FROM price_data
                    '''
                    
                    # Build WHERE clause conditions
                    conditions = []
                    params = []
                    
                    if symbol != 'ALL':
                        conditions.append('symbol = ?')
                        params.append(symbol)
                    
                    if start_date:
                        conditions.append('timestamp >= ?')
                        params.append(int(start_date))
                    
                    if end_date:
                        conditions.append('timestamp <= ?')
                        params.append(int(end_date))
                    
                    # Add WHERE clause if there are conditions
                    if conditions:
                        base_query += ' WHERE ' + ' AND '.join(conditions)
                    
                    # Add ORDER BY and LIMIT
                    base_query += ' ORDER BY timestamp DESC LIMIT ? OFFSET ?'
                    params.extend([limit, offset])
                    
                    # Execute query
                    cursor = conn.execute(base_query, params)
                    columns = [desc[0] for desc in cursor.description]
                    rows = cursor.fetchall()
                    
                    # Convert rows to dictionaries and format dates
                    data = []
                    for row in rows:
                        data.append({
                            'symbol': row[0],
                            'timestamp': row[1],
                            'date': datetime.datetime.fromtimestamp(row[1]).strftime('%Y-%m-%d'),
                            'open': row[2],
                            'high': row[3],
                            'low': row[4],
                            'close': row[5],
                            'volume': row[6]
                        })
                    
                    # Get symbols list - always fetch all available symbols in database
                    # regardless of which symbol is being queried
                    cursor = conn.execute('SELECT DISTINCT symbol FROM price_data ORDER BY symbol')
                    symbols = [row[0] for row in cursor.fetchall()]
                    
                    return {
                        'data': data,
                        'total_count': len(data),
                        'symbols': symbols,
                        'symbol': symbol,
                        'start_date': start_date,
                        'end_date': end_date,
                        'requestId': request_id
                    }
            except Exception as e:
                return {
                    'error': f'Failed to fetch price data: {str(e)}',
                    'requestId': request_id
                }
        elif request.get('action') == 'get-datasets':
            """Get list of all available datasets"""
            try:
                result = current_db_service.get_all_datasets()
                result['requestId'] = request_id
                return result
            except Exception as e:
                return {
                    'error': f'Failed to fetch datasets: {str(e)}',
                    'requestId': request_id
                }
        elif request.get('action') == 'get-dataset':
            """Get specific dataset by name"""
            try:
                # Check both 'dataset_name' and 'name' for compatibility
                data = request.get('data', {})
                dataset_name = data.get('dataset_name') or data.get('name')
                if not dataset_name:
                    return {
                        'error': 'Dataset name is required',
                        'requestId': request_id
                    }
                result = current_db_service.get_dataset(dataset_name)
                result['requestId'] = request_id
                return result
            except Exception as e:
                return {
                    'error': f'Failed to fetch dataset: {str(e)}',
                    'requestId': request_id
                }
        elif request.get('action') == 'create-dataset':
            """Create a new dataset with metadata"""
            try:
                data = request.get('data', {})
                # Check both 'dataset_name' and 'name' for compatibility
                dataset_name = data.get('dataset_name') or data.get('name')
                description = data.get('dataset_description') or data.get('description', '')
                
                if not dataset_name:
                    return {
                        'error': 'Dataset name is required',
                        'requestId': request_id
                    }
                
                result = current_db_service.create_dataset(dataset_name, description)
                result['requestId'] = request_id
                return result
            except Exception as e:
                return {
                    'error': f'Failed to create dataset: {str(e)}',
                    'requestId': request_id
                }
        elif request.get('action') == 'import-data':
            data = request.get('data', {})
            file_path = data.get('file_path')
            symbol = data.get('symbol', 'DEFAULT')
            column_mapping = data.get('column_mapping', {})
            incremental = data.get('incremental', True)  # Default to incremental updates
            dataset_name = data.get('dataset_name')  # New: dataset name for metadata
            dataset_description = data.get('dataset_description', '')  # New: dataset description

            if not file_path or not os.path.exists(file_path):
                return {'error': 'Invalid or missing file path', 'requestId': request_id}

            start_time = time.time()
            progress_reporter = None  # Initialize to None
            validator = DataValidationPipeline()

            try:
                print(f"IMPORT: Starting import process for file: {file_path}", file=sys.stderr)
                print(f"IMPORT: File size: {os.path.getsize(file_path) if os.path.exists(file_path) else 'N/A'} bytes", file=sys.stderr)
                print(f"IMPORT: Request ID: {request_id}", file=sys.stderr)
                print(f"IMPORT: Symbol: {symbol}", file=sys.stderr)
                if column_mapping:
                    print(f"IMPORT: Column mapping: {column_mapping}", file=sys.stderr)

                # Read and process the file
                print("IMPORT: Reading file...", file=sys.stderr)
                file_read_start = time.time()
                df = _read_any_ohlcv(file_path)
                file_read_time = time.time() - file_read_start
                print(f"IMPORT: File read, shape: {df.shape}, time: {file_read_time:.2f}s", file=sys.stderr)
                print(f"IMPORT: Original columns: {list(df.columns)}", file=sys.stderr)

                # Initialize progress reporter after we know the row count
                progress_reporter = ProgressReporter(len(df))

                # Apply custom column mapping if provided, otherwise use standardization
                if column_mapping:
                    print(f"IMPORT: Applying custom column mapping", file=sys.stderr)
                    mapping_start = time.time()
                    df = _apply_custom_column_mapping(df, column_mapping)
                    mapping_time = time.time() - mapping_start
                    print(f"IMPORT: Column mapping completed in {mapping_time:.2f}s", file=sys.stderr)
                    print(f"IMPORT: Mapped columns: {list(df.columns)}", file=sys.stderr)
                else:
                    print("IMPORT: Applying standard column mapping", file=sys.stderr)
                    mapping_start = time.time()
                    df = _standardize_ohlcv_columns(df)
                    mapping_time = time.time() - mapping_start
                    print(f"IMPORT: Standard column mapping completed in {mapping_time:.2f}s", file=sys.stderr)
                    print(f"IMPORT: Standardized columns: {list(df.columns)}", file=sys.stderr)

                # Ensure Ticker column exists
                if 'Ticker' not in df.columns:
                    df['Ticker'] = symbol

                # Parse dates and convert to timestamp
                print("IMPORT: Parsing dates...", file=sys.stderr)
                date_parse_start = time.time()
                df['Date'] = _parse_dates(df['Date'])
                date_parse_time = time.time() - date_parse_start
                print(f"IMPORT: Date parsing completed in {date_parse_time:.2f}s", file=sys.stderr)

                if not is_datetime64_any_dtype(df['Date']):
                    return {'error': 'Date column could not be reliably converted to datetime', 'requestId': request_id}

                # Convert dates to timestamps (seconds since epoch)
                print("IMPORT: Converting dates to timestamps...", file=sys.stderr)
                timestamp_start = time.time()
                df['Date'] = df['Date'].astype('int64') // 10**9
                timestamp_time = time.time() - timestamp_start
                print(f"IMPORT: Timestamp conversion completed in {timestamp_time:.2f}s", file=sys.stderr)

                # Numeric coercion
                for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')

                # Run comprehensive validation
                print("IMPORT: Running data validation...", file=sys.stderr)
                validation_start = time.time()
                before_validation = len(df)
                is_valid, errors, warnings = validator.validate_dataframe(df)
                validation_time = time.time() - validation_start
                print(f"IMPORT: Validation completed in {validation_time:.2f}s, valid: {is_valid}", file=sys.stderr)

                if not is_valid:
                    return {
                        'error': f'Validation failed: {"; ".join(errors[:5])}',
                        'validation_errors': errors,
                        'validation_warnings': warnings,
                        'requestId': request_id
                    }

                # Drop rows with missing required data
                before = len(df)
                progress_reporter.report_progress(0, errors + warnings)
                print(f"IMPORT: Initial data validation complete. Rows before cleaning: {before}", file=sys.stderr)

                print("IMPORT: Cleaning data...", file=sys.stderr)
                dropna_start = time.time()
                df.dropna(subset=['Date', 'Close', 'Low', 'Open', 'High'], inplace=True)
                after = len(df)
                dropna_time = time.time() - dropna_start
                print(f"IMPORT: Data cleaned: {after} rows, dropped: {before - after}, time: {dropna_time:.2f}s", file=sys.stderr)
                print(f"IMPORT: Final columns: {list(df.columns)}", file=sys.stderr)
                print(f"IMPORT: Sample data after cleaning:", file=sys.stderr)
                print(df.head(3).to_string(), file=sys.stderr)

                if after == 0:
                    return {'error': f'No valid data rows after cleaning. Before: {before}, After: {after}. Check that Date column is valid and OHLC columns contain numeric data.', 'requestId': request_id}

                # Check if we should do incremental updates
                if incremental:
                    print(f"IMPORT: Checking for incremental updates for symbol '{symbol}'", file=sys.stderr)
                    existing_range = current_db_service.get_symbol_data_range(symbol)
                    print(f"IMPORT: Existing data range: {existing_range}", file=sys.stderr)
                    
                    if existing_range['has_data']:
                        # Filter data to only include new records
                        new_data, existing_data = current_db_service.filter_incremental_data(df, symbol)
                        
                        print(f"IMPORT: Incremental update detected", file=sys.stderr)
                        print(f"IMPORT: New data rows: {len(new_data)}", file=sys.stderr)
                        print(f"IMPORT: Existing data rows: {len(existing_data)}", file=sys.stderr)
                        
                        if len(new_data) == 0:
                            print(f"IMPORT: No new data to import for symbol '{symbol}'", file=sys.stderr)
                            summary = {
                                'success': True,
                                'rowsImported': 0,
                                'rowsSkipped': 0,
                                'symbol': symbol,
                                'totalRows': after,
                                'rowsDropped': before - after,
                                'timeElapsed': round(time.time() - start_time, 2),
                                'validationWarnings': warnings,
                                'incrementalUpdate': True,
                                'existingDataRange': existing_range,
                                'requestId': request_id
                            }
                            progress_reporter.report_summary(summary)
                            return summary
                        
                        # Use only the new data for import
                        df = new_data
                    else:
                        print(f"IMPORT: No existing data found for symbol '{symbol}', doing full import", file=sys.stderr)
                else:
                    print(f"IMPORT: Full import mode (incremental updates disabled)", file=sys.stderr)

                # Insert into database with batched processing for performance
                rows_imported = 0
                rows_skipped = 0
                batch_size = 5000  # Optimal batch size from Implementation Plan benchmarks
                batch_data = []

                print(f"IMPORT: Starting batched database insertion for {len(df)} rows", file=sys.stderr)
                print(f"IMPORT: Market database path: {current_db_service.market_db_path}", file=sys.stderr)
                print(f"IMPORT: Using batch size: {batch_size}", file=sys.stderr)
                print(f"IMPORT: Import mode: {'incremental' if incremental else 'full'}", file=sys.stderr)
                db_start = time.time()
                
                # Create metadata record for this upload
                upload_metadata = {
                    'filename': os.path.basename(file_path),
                    'file_size': os.path.getsize(file_path),
                    'symbol': symbol,
                    'rows_expected': len(df),
                    'import_timestamp': int(time.time())
                }
                
                with sqlite3.connect(current_db_service.market_db_path) as conn:
                    # Create data_uploads record
                    cursor = conn.execute('''
                        INSERT INTO data_uploads
                        (filename, file_size, symbol, status, metadata_json)
                        VALUES (?, ?, ?, 'processing', ?)
                    ''', (
                        upload_metadata['filename'],
                        upload_metadata['file_size'],
                        upload_metadata['symbol'],
                        json.dumps(upload_metadata)
                    ))
                    upload_id = cursor.lastrowid
                    conn.commit()
                    
                    # Update symbols table or create new record
                    cursor = conn.execute('''
                        INSERT OR REPLACE INTO symbols
                        (symbol, name, total_rows, last_updated, metadata_json)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        symbol,
                        f"Imported from {upload_metadata['filename']}",
                        0,  # Will be updated after import
                        int(time.time()),
                        json.dumps({'source_file': upload_metadata['filename']})
                    ))
                    conn.commit()
                    conn.execute('BEGIN TRANSACTION')  # Start transaction for batch insert
                    
                    for index, row in df.iterrows():
                        try:
                            # Log first few rows for debugging
                            if index in [0, 1, 2]:
                                print(f"IMPORT: Processing row {index}: Ticker={row.get('Ticker', 'N/A')}, Date={row.get('Date', 'N/A')}, Open={row.get('Open', 'N/A')}", file=sys.stderr)
                            
                            # Prepare data for batch insert
                            batch_data.append((
                                str(row['Ticker']),
                                int(row['Date']),
                                float(row['Open']),
                                float(row['High']),
                                float(row['Low']),
                                float(row['Close']),
                                int(row['Volume']) if pd.notna(row['Volume']) and row['Volume'] != '' else None
                            ))
                            
                            rows_imported += 1

                            # Execute batch insert when batch size is reached
                            if rows_imported % batch_size == 0 or rows_imported == after:
                                if batch_data:
                                    conn.executemany('''
                                        INSERT OR REPLACE INTO price_data
                                        (symbol, timestamp, open, high, low, close, volume)
                                        VALUES (?, ?, ?, ?, ?, ?, ?)
                                    ''', batch_data)
                                    batch_data = []  # Clear batch after insert
                                
                                # Report progress every batch or at the end
                                elapsed_db = time.time() - db_start
                                print(f"IMPORT: Database progress: {rows_imported}/{after} rows, time: {elapsed_db:.2f}s", file=sys.stderr)
                                progress_reporter.report_progress(rows_imported)

                        except Exception as e:
                            rows_skipped += 1
                            if rows_skipped <= 10:  # Only report first 10 errors
                                progress_reporter.report_progress(rows_imported, [f"Row {index}: {str(e)}"])
                            print(f"IMPORT: Error inserting row {index}: {str(e)}", file=sys.stderr)
                            continue
                    
                    # Insert any remaining rows in the final batch
                    if batch_data:
                        conn.executemany('''
                            INSERT OR REPLACE INTO price_data
                            (symbol, timestamp, open, high, low, close, volume)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', batch_data)
                    
                    conn.commit()  # Commit transaction
                    print(f"IMPORT: Transaction committed successfully", file=sys.stderr)
                    
                    # Update metadata records after successful import
                    try:
                        cursor = conn.execute('''
                            UPDATE data_uploads
                            SET rows_processed = ?, status = 'completed', completed_at = ?
                            WHERE id = ?
                        ''', (rows_imported, int(time.time()), upload_id))
                        
                        # Update symbols table with final row count
                        cursor = conn.execute('''
                            UPDATE symbols
                            SET total_rows = ?, last_updated = ?
                            WHERE symbol = ?
                        ''', (rows_imported, int(time.time()), symbol))
                        
                        conn.commit()
                        print(f"IMPORT: Metadata updated successfully", file=sys.stderr)
                    except Exception as e:
                        print(f"IMPORT: Warning - Failed to update metadata: {e}", file=sys.stderr)
                        # Don't fail the import if metadata update fails

                # Calculate final metrics
                elapsed_time = time.time() - start_time
                print(f"IMPORT: Import process completed in {elapsed_time:.2f} seconds", file=sys.stderr)

                summary = {
                    'success': True,
                    'rowsImported': rows_imported,
                    'rowsSkipped': rows_skipped,
                    'symbol': symbol,
                    'totalRows': after,
                    'rowsDropped': before - after,
                    'timeElapsed': round(elapsed_time, 2),
                    'validationWarnings': warnings,
                    'requestId': request_id
                }

                # Create or update dataset metadata if dataset_name is provided
                if dataset_name:
                    try:
                        print(f"IMPORT: Creating dataset record: {dataset_name}", file=sys.stderr)
                        dataset_result = current_db_service.create_dataset(dataset_name, dataset_description)
                        if dataset_result.get('success'):
                            summary['dataset'] = dataset_result.get('dataset')
                            print(f"IMPORT: Dataset '{dataset_name}' created/updated successfully", file=sys.stderr)
                        else:
                            print(f"IMPORT: Warning - Failed to create dataset: {dataset_result.get('error')}", file=sys.stderr)
                    except Exception as e:
                        print(f"IMPORT: Warning - Failed to create dataset record: {e}", file=sys.stderr)

                # Send final summary
                print(f"IMPORT: About to send final response for requestId: {request_id}", file=sys.stderr)
                progress_reporter.report_summary(summary)
                print(f"IMPORT: Final response sent for requestId: {request_id}", file=sys.stderr)

                return summary

            except Exception as e:
                # Mark upload as failed if there's a critical error and we have a connection
                upload_id = None  # Initialize upload_id to None
                try:
                    if upload_id is not None:
                        with sqlite3.connect(current_db_service.market_db_path) as error_conn:
                            cursor = error_conn.execute('''
                                UPDATE data_uploads
                                SET status = 'failed', error_message = ?, completed_at = ?
                                WHERE id = ?
                            ''', (str(e), int(time.time()), upload_id))
                            error_conn.commit()
                except:
                    pass  # Don't fail the import further if metadata update fails
                
                elapsed_time = time.time() - start_time
                error_summary = {
                    'error': f'Import failed: {str(e)}',
                    'timeElapsed': round(elapsed_time, 2),
                    'requestId': request_id
                }
                if progress_reporter:
                    progress_reporter.report_summary(error_summary)
                return error_summary
        else:
            return {
                'error': 'Unknown action',
                'action': request.get('action'),
                'requestId': request_id
            }
    except Exception as e:
        return {
            'error': str(e),
            'requestId': request_id
        }

def main():
    """Main entry point for the Python backend service"""
    print("Python backend process started", flush=True, file=sys.stderr)

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