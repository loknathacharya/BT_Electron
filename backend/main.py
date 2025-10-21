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
from typing import Any
from pathlib import Path
import pandas as pd
from pandas.api.types import is_datetime64_any_dtype, is_numeric_dtype
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import re

# Import backup and recovery managers
try:
    from backend.backup_manager import BackupManager, RecoveryManager
    from backend.data_quality_analyzer import DataQualityAnalyzer
except ImportError:
    from backup_manager import BackupManager, RecoveryManager
    from data_quality_analyzer import DataQualityAnalyzer

# Ensure repository root is on sys.path so 'backend.*' absolute imports work when running this file directly
try:
    _this_file = Path(__file__).resolve()
    _repo_root = _this_file.parent.parent  # .../BT_Electron
    if str(_repo_root) not in sys.path:
        sys.path.insert(0, str(_repo_root))
except Exception:
    # Non-fatal; fallback imports may still work when tests run from repo root
    pass

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

    # Saved scans CRUD
    def save_scan(self, name: str, spec: dict, description: str = '') -> dict:
        try:
            with sqlite3.connect(self.user_db_path) as conn:
                now = int(time.time())
                conn.execute('''
                    INSERT INTO saved_scans (name, description, spec_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(name) DO UPDATE SET description=excluded.description, spec_json=excluded.spec_json, updated_at=excluded.updated_at
                ''', (name, description, json.dumps(spec), now, now))
                conn.commit()
            return {'success': True, 'name': name}
        except Exception as e:
            return {'error': str(e)}

    # Utility: list available symbols in market DB
    def list_symbols(self) -> list[str]:
        try:
            with sqlite3.connect(self.market_db_path) as conn:
                cur = conn.execute('SELECT DISTINCT symbol FROM price_data ORDER BY symbol')
                return [r[0] for r in cur.fetchall()]
        except Exception:
            return []

    def get_scans(self) -> dict:
        try:
            with sqlite3.connect(self.user_db_path) as conn:
                cur = conn.execute('SELECT name, description, spec_json, created_at, updated_at FROM saved_scans ORDER BY updated_at DESC')
                scans = []
                for row in cur.fetchall():
                    scans.append({
                        'name': row[0],
                        'description': row[1],
                        'spec': json.loads(row[2]) if row[2] else {},
                        'created_at': row[3],
                        'updated_at': row[4]
                    })
            return {'success': True, 'scans': scans}
        except Exception as e:
            return {'error': str(e), 'scans': []}

    def get_scan(self, name: str) -> dict:
        try:
            with sqlite3.connect(self.user_db_path) as conn:
                cur = conn.execute('SELECT name, description, spec_json, created_at, updated_at FROM saved_scans WHERE name = ?', (name,))
                row = cur.fetchone()
                if not row:
                    return {'error': f'scan "{name}" not found'}
                return {
                    'success': True,
                    'scan': {
                        'name': row[0], 'description': row[1], 'spec': json.loads(row[2]) if row[2] else {}, 'created_at': row[3], 'updated_at': row[4]
                    }
                }
        except Exception as e:
            return {'error': str(e)}

    def delete_scan(self, name: str) -> dict:
        try:
            with sqlite3.connect(self.user_db_path) as conn:
                conn.execute('DELETE FROM saved_scans WHERE name = ?', (name,))
                conn.commit()
            return {'success': True}
        except Exception as e:
            return {'error': str(e)}

    # Watchlists CRUD
    def save_watchlist(self, name: str, symbols: list[str], description: str = '') -> dict:
        try:
            with sqlite3.connect(self.user_db_path) as conn:
                now = int(time.time())
                conn.execute('''
                    INSERT INTO watchlists (name, description, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(name) DO UPDATE SET description=excluded.description, updated_at=excluded.updated_at
                ''', (name, description, now, now))
                cur = conn.execute('SELECT id FROM watchlists WHERE name = ?', (name,))
                row = cur.fetchone()
                if not row:
                    return {'error': 'failed to upsert watchlist'}
                wid = row[0]
                conn.execute('DELETE FROM watchlist_symbols WHERE watchlist_id = ?', (wid,))
                conn.executemany('INSERT INTO watchlist_symbols (watchlist_id, symbol) VALUES (?, ?)', [(wid, s) for s in symbols])
                conn.commit()
            return {'success': True, 'name': name, 'count': len(symbols)}
        except Exception as e:
            return {'error': str(e)}

    def get_watchlists(self) -> dict:
        try:
            with sqlite3.connect(self.user_db_path) as conn:
                cur = conn.execute('SELECT id, name, description, created_at, updated_at FROM watchlists ORDER BY updated_at DESC')
                lists = []
                for row in cur.fetchall():
                    wid = row[0]
                    c2 = conn.execute('SELECT COUNT(*) FROM watchlist_symbols WHERE watchlist_id = ?', (wid,))
                    cnt = c2.fetchone()[0]
                    lists.append({'name': row[1], 'description': row[2], 'symbolCount': cnt, 'created_at': row[3], 'updated_at': row[4]})
            return {'success': True, 'watchlists': lists}
        except Exception as e:
            return {'error': str(e), 'watchlists': []}

    def get_watchlist_symbols(self, name: str) -> list[str]:
        try:
            with sqlite3.connect(self.user_db_path) as conn:
                cur = conn.execute('SELECT id FROM watchlists WHERE name = ?', (name,))
                row = cur.fetchone()
                if not row:
                    return []
                wid = row[0]
                cur2 = conn.execute('SELECT symbol FROM watchlist_symbols WHERE watchlist_id = ? ORDER BY symbol', (wid,))
                return [r[0] for r in cur2.fetchall()]
        except Exception:
            return []

    def delete_watchlist(self, name: str) -> dict:
        try:
            with sqlite3.connect(self.user_db_path) as conn:
                cur = conn.execute('SELECT id FROM watchlists WHERE name = ?', (name,))
                row = cur.fetchone()
                if not row:
                    return {'success': True}
                wid = row[0]
                conn.execute('DELETE FROM watchlist_symbols WHERE watchlist_id = ?', (wid,))
                conn.execute('DELETE FROM watchlists WHERE id = ?', (wid,))
                conn.commit()
            return {'success': True}
        except Exception as e:
            return {'error': str(e)}

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

                # Saved scans
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS saved_scans (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        description TEXT,
                        spec_json TEXT NOT NULL,
                        created_at INTEGER DEFAULT (strftime('%s', 'now')),
                        updated_at INTEGER DEFAULT (strftime('%s', 'now'))
                    )
                ''')

                # Watchlists and symbols
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS watchlists (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        description TEXT,
                        created_at INTEGER DEFAULT (strftime('%s', 'now')),
                        updated_at INTEGER DEFAULT (strftime('%s', 'now'))
                    )
                ''')
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS watchlist_symbols (
                        watchlist_id INTEGER NOT NULL,
                        symbol TEXT NOT NULL,
                        PRIMARY KEY (watchlist_id, symbol),
                        FOREIGN KEY (watchlist_id) REFERENCES watchlists (id)
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
            # Test user database (quiet)
            with sqlite3.connect(self.user_db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                user_table_count = cursor.fetchone()[0]

            # Test market database (quiet)
            with sqlite3.connect(self.market_db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                market_table_count = cursor.fetchone()[0]

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

    def delete_dataset(self, name: str) -> dict:
        """Delete a dataset by name (removes metadata and all associated price data)"""
        try:
            with sqlite3.connect(self.market_db_path) as conn:
                # First, get the dataset to verify it exists
                cursor = conn.execute('SELECT id, name FROM datasets WHERE name = ?', (name,))
                row = cursor.fetchone()
                
                if not row:
                    return {'error': f'Dataset "{name}" not found', 'success': False}
                
                dataset_id = row[0]
                dataset_name = row[1]
                
                # Delete all price data associated with this dataset
                # Note: We're assuming price_data table has a reference to datasets
                # If not, we delete all rows for symbols that were in this dataset
                cursor = conn.execute('SELECT symbols_json FROM datasets WHERE id = ?', (dataset_id,))
                symbols_row = cursor.fetchone()
                
                if symbols_row and symbols_row[0]:
                    try:
                        symbols = json.loads(symbols_row[0])
                        # Delete price data for each symbol in this dataset
                        for symbol in symbols:
                            conn.execute('DELETE FROM price_data WHERE symbol = ?', (symbol,))
                    except json.JSONDecodeError:
                        pass
                
                # Delete the dataset metadata entry
                conn.execute('DELETE FROM datasets WHERE id = ?', (dataset_id,))
                conn.commit()
                
                print(f"Successfully deleted dataset '{dataset_name}' (ID: {dataset_id})", file=sys.stderr)
                return {
                    'success': True,
                    'message': f'Dataset "{dataset_name}" and all associated data have been deleted.',
                    'dataset_name': dataset_name
                }
        except Exception as e:
            print(f"Error deleting dataset '{name}': {e}", file=sys.stderr)
            import traceback
            print(traceback.format_exc(), file=sys.stderr)
            return {'error': f'Failed to delete dataset: {str(e)}', 'success': False}

# Global database service instance
db_service = DatabaseService()
_parse_dsl_timestamps: list[float] = []

def _rate_limit_parse(now: float | None = None, max_per_window: int = 30, window_sec: int = 10) -> bool:
    """Simple global rate limiter: allow up to max_per_window parse-dsl calls per window_sec."""
    global _parse_dsl_timestamps
    now = now or time.time()
    # Drop old timestamps
    _parse_dsl_timestamps = [t for t in _parse_dsl_timestamps if now - t <= window_sec]
    if len(_parse_dsl_timestamps) >= max_per_window:
        return False
    _parse_dsl_timestamps.append(now)
    return True

def _validate_universe(universe: Any) -> Any:
    """Validate/normalize universe; raise ValueError on invalid."""
    if isinstance(universe, str):
        s = universe.strip()
        if len(s) > 200:
            raise ValueError('universe string too long')
        if s.upper() == 'ALL':
            return 'ALL'
        if s.upper().startswith('WATCHLIST:'):
            name = s.split(':', 1)[1]
            if not name or len(name) > 100:
                raise ValueError('invalid watchlist name')
            if not re.match(r'^[A-Za-z0-9 _\-]+$', name):
                raise ValueError('invalid watchlist name')
            return f'WATCHLIST:{name}'
        # Allow comma-separated list? For strings we limit to ALL or WATCHLIST
        raise ValueError('invalid universe string')
    if isinstance(universe, list):
        # Ensure reasonable size and safe symbols
        if len(universe) > 2000:
            raise ValueError('too many symbols in universe list')
        cleaned = []
        for sym in universe:
            if not isinstance(sym, str) or len(sym) > 32 or not re.match(r'^[A-Za-z0-9_.\-]+$', sym):
                raise ValueError('invalid symbol in universe list')
            cleaned.append(sym)
        return cleaned
    if universe is None:
        return 'ALL'
    raise ValueError('invalid universe type')

#########################
# DSL Parser (minimal v1)
#########################

Token = tuple[str, str]

class DSLTokenizer:
    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.len = len(text)
        self.current: Token | None = None

    def _peek(self) -> str:
        return self.text[self.pos] if self.pos < self.len else ''

    def _advance(self) -> str:
        ch = self._peek()
        self.pos += 1
        return ch

    def _skip_ws(self):
        while self._peek() and self._peek().isspace():
            self._advance()

    def _match(self, s: str) -> bool:
        if self.text[self.pos:self.pos+len(s)].lower() == s.lower():
            self.pos += len(s)
            return True
        return False

    def next(self) -> Token:
        self._skip_ws()
        if self.pos >= self.len:
            self.current = ('EOF', '')
            return self.current
        ch = self._peek()

        # Symbols and basic operators
        if ch in '(),[]+*/':
            self._advance()
            self.current = (ch, ch)
            return self.current
        # Standalone '-' and '=' should be OP tokens (used in offsets like [-1] or [=3])
        if ch in '-=':
            self._advance()
            self.current = ('OP', ch)
            return self.current

        # Comparators and brackets
        if ch in '<>!=':
            s = ch
            self._advance()
            if self._peek() == '=':
                s += self._advance()
            self.current = ('OP', s)
            return self.current

        # Numbers (int/float)
        if ch.isdigit() or (ch == '.' and self.pos+1 < self.len and self.text[self.pos+1].isdigit()):
            start = self.pos
            has_dot = ch == '.'
            self._advance()
            while self._peek() and (self._peek().isdigit() or (self._peek() == '.' and not has_dot)):
                if self._peek() == '.':
                    has_dot = True
                self._advance()
            val = self.text[start:self.pos]
            self.current = ('NUMBER', val)
            return self.current

        # Identifiers/keywords
        if ch.isalpha() or ch == '_':
            start = self.pos
            while self._peek() and (self._peek().isalnum() or self._peek() in ['_', '.']):
                self._advance()
            ident = self.text[start:self.pos]
            self.current = ('IDENT', ident)
            return self.current

        # Fallback single char
        self._advance()
        self.current = (ch, ch)
        return self.current

class DSLParseError(Exception):
    def __init__(self, message: str, pos: int | None = None, token: Token | None = None):
        super().__init__(message)
        self.pos = pos
        self.token = token

class DSLParser:
    def __init__(self, text: str):
        self.tok = DSLTokenizer(text)
        self.cur = self.tok.next()
        self.depth = 0
        self.max_depth = 200

    def _eat(self, kind: str, value: str | None = None):
        if self.cur[0] != kind or (value is not None and self.cur[1].lower() != value.lower()):
            raise DSLParseError(f"Expected {kind} {value or ''}, found {self.cur}", pos=self.tok.pos, token=self.cur)
        self.cur = self.tok.next()

    def _check(self, kind: str, value: str | None = None) -> bool:
        if self.cur[0] != kind:
            return False
        if value is not None and self.cur[1].lower() != value.lower():
            return False
        return True

    # Grammar (simplified):
    # expr := or_expr
    # or_expr := and_expr (IDENT 'OR' and_expr)*
    # and_expr := not_expr (IDENT 'AND' not_expr)*
    # not_expr := (IDENT 'NOT')* comp_expr
    # comp_expr := crossover_call | arith (OP comp arith)?
    # crossover_call := IDENT 'CROSSES_ABOVE' '(' arith ',' arith ')' | idem for CROSSES_BELOW
    # arith := term ((+|-) term)*
    # term := factor ((*|/) factor)*
    # factor := primary | offset primary | '(' expr ')'
    # offset := '[' ('-' NUMBER | '=' NUMBER) ']'
    # primary := attribute | number | func_call | indicator_call

    def _guard_depth(self):
        self.depth += 1
        if self.depth > self.max_depth:
            raise DSLParseError('Expression too deep', pos=self.tok.pos, token=self.cur)

    def _leave_depth(self):
        self.depth = max(0, self.depth - 1)

    def parse(self):
        self._guard_depth()
        try:
            node = self.parse_or()
        finally:
            self._leave_depth()
        if not self._check('EOF'):
            raise DSLParseError(f"Unexpected token {self.cur}", pos=self.tok.pos, token=self.cur)
        return node

    def parse_or(self):
        self._guard_depth()
        try:
            nodes = [self.parse_and()]
            while self._check('IDENT') and self.cur[1].upper() == 'OR':
                self._eat('IDENT')
                nodes.append(self.parse_and())
            if len(nodes) == 1:
                return nodes[0]
            return {'op': 'group', 'logic': 'OR', 'children': nodes}
        finally:
            self._leave_depth()

    def parse_and(self):
        self._guard_depth()
        try:
            nodes = [self.parse_not()]
            while self._check('IDENT') and self.cur[1].upper() == 'AND':
                self._eat('IDENT')
                nodes.append(self.parse_not())
            if len(nodes) == 1:
                return nodes[0]
            return {'op': 'group', 'logic': 'AND', 'children': nodes}
        finally:
            self._leave_depth()

    def parse_not(self):
        self._guard_depth()
        try:
            not_count = 0
            while self._check('IDENT') and self.cur[1].upper() == 'NOT':
                self._eat('IDENT')
                not_count += 1
            node = self.parse_comp()
            if not_count % 2 == 1:
                return {'op': 'not', 'child': node}
            return node
        finally:
            self._leave_depth()

    def parse_comp(self):
        # CROSSES_ABOVE/BELOW function form: CROSSES_ABOVE(a, b)
        if self._check('IDENT') and self.cur[1].upper() in ('CROSSES_ABOVE', 'CROSSES_BELOW'):
            cross_type = self.cur[1].upper()
            self._eat('IDENT')
            self._eat('(')
            left = self.parse_arith()
            self._eat(',')
            right = self.parse_arith()
            self._eat(')')
            return {'op': 'crossover', 'type': cross_type, 'left': left, 'right': right}
        # Infix crossover: <arith> CROSSES_ABOVE <arith>
        left = self.parse_arith()
        if self._check('IDENT') and self.cur[1].upper() in ('CROSSES_ABOVE', 'CROSSES_BELOW'):
            cross_type = self.cur[1].upper()
            self._eat('IDENT')
            right = self.parse_arith()
            return {'op': 'crossover', 'type': cross_type, 'left': left, 'right': right}
        if self._check('OP') and self.cur[1] in ('<', '<=', '>', '>=', '==', '!='):
            op = self.cur[1]
            self._eat('OP')
            right = self.parse_arith()
            return {'op': 'compare', 'cmp': op, 'left': left, 'right': right}
        # standalone arith truthiness is allowed but we'll wrap as 'arith' filter
        # Here, convert to boolean-arith filter to match engine, if it's an expr chain
        if isinstance(left, dict) and left.get('type') == 'expr':
            return {'op': 'arith', 'expr': left.get('expr', [])}
        # Otherwise, compare to non-zero by default (rare)
        return {'op': 'arith', 'expr': [left]}

    def parse_arith(self):
        self._guard_depth()
        try:
            node = self.parse_term()
            parts: list[Any] = [node]
            while self._check('+') or self._check('-'):
                op = self.cur[1]
                self._eat(op)
                right = self.parse_term()
                parts.append(op)
                parts.append(right)
            if len(parts) == 1:
                return node
            return {'type': 'expr', 'expr': parts}
        finally:
            self._leave_depth()

    def parse_term(self):
        self._guard_depth()
        try:
            node = self.parse_factor()
            parts: list[Any] = [node]
            while self._check('*') or self._check('/'):
                op = self.cur[1]
                self._eat(op)
                right = self.parse_factor()
                parts.append(op)
                parts.append(right)
            if len(parts) == 1:
                return node
            return {'type': 'expr', 'expr': parts}
        finally:
            self._leave_depth()

    def parse_factor(self):
        # Parentheses
        if self._check('('):
            self._eat('(')
            node = self.parse_or()
            self._eat(')')
            return node
        # Offset + primary
        offset = None
        if self._check('['):
            self._eat('[')
            if self._check('OP') and self.cur[1] == '-':
                self._eat('OP')
                if not self._check('NUMBER'):
                    raise DSLParseError('Expected number after - in lookback')
                bars = int(float(self.cur[1]))
                self._eat('NUMBER')
                offset = {'kind': 'lookback', 'bars': bars}
            elif self._check('OP') and self.cur[1] == '=':
                self._eat('OP')
                if not self._check('NUMBER'):
                    raise DSLParseError('Expected number after = in ordinal')
                n = int(float(self.cur[1]))
                self._eat('NUMBER')
                offset = {'kind': 'ordinal', 'n': n}
            else:
                # Allow shorthand like [-1] where '-' may be a literal char, handle NUMBER next
                sign = ''
                if self._check('-'):
                    sign = '-'
                    self._eat('-')
                if not self._check('NUMBER'):
                    raise DSLParseError('Expected number inside offset []')
                val = int(float(self.cur[1]))
                self._eat('NUMBER')
                if sign == '-':
                    offset = {'kind': 'lookback', 'bars': val}
                else:
                    offset = {'kind': 'ordinal', 'n': val}
            self._eat(']')
        node = self.parse_primary()
        if offset and isinstance(node, dict):
            # Attach offset to measure/indicator/func
            # For expr, wrap it
            if node.get('type') in ('attr', 'indicator', 'func', 'const'):
                node = {**node, 'offset': offset}
            elif node.get('type') == 'expr':
                node = {'type': 'expr', 'expr': node['expr'], 'offset': offset}
        return node

    def parse_primary(self):
        # Number constant
        if self._check('NUMBER'):
            val = float(self.cur[1])
            self._eat('NUMBER')
            return {'type': 'const', 'value': val}
        # Identifier-based
        if self._check('IDENT'):
            name = self.cur[1]
            upper = name.upper()
            lower = name.lower()
            self._eat('IDENT')
            # Function/indicator call
            if self._check('('):
                self._eat('(')
                args = []
                if not self._check(')'):
                    args.append(self.parse_arith())
                    while self._check(','):
                        self._eat(',')
                        args.append(self.parse_arith())
                self._eat(')')
                return self._build_call(upper, args)
            # Attribute
            if lower in ('open','high','low','close','volume'):
                return {'type': 'attr', 'name': lower}
            # Unknown identifier as attribute (fallback)
            return {'type': 'attr', 'name': lower}
        raise DSLParseError(f"Unexpected token {self.cur}", pos=self.tok.pos, token=self.cur)

    def _build_call(self, upper: str, args: list[Any]):
        # Cross handled in parse_comp
        if upper in ('SMA','EMA','RSI'):
            # SMA(src, period)
            src = args[0] if args else {'type': 'attr', 'name': 'close'}
            period = int(float(args[1]['value'])) if len(args) > 1 and isinstance(args[1], dict) and args[1].get('type') == 'const' else 20
            return {'type': 'indicator', 'name': upper, 'params': {'src': src, 'period': period}}
        if upper == 'MACD':
            src = args[0] if args else {'type': 'attr', 'name': 'close'}
            fast = int(float(args[1]['value'])) if len(args) > 1 and args[1].get('type') == 'const' else 12
            slow = int(float(args[2]['value'])) if len(args) > 2 and args[2].get('type') == 'const' else 26
            signal = int(float(args[3]['value'])) if len(args) > 3 and args[3].get('type') == 'const' else 9
            return {'type': 'indicator', 'name': 'MACD', 'params': {'src': src, 'fast': fast, 'slow': slow, 'signal': signal}}
        if upper == 'ADX':
            period = int(float(args[0]['value'])) if args and args[0].get('type') == 'const' else 14
            return {'type': 'indicator', 'name': 'ADX', 'params': {'period': period}}
        if upper == 'ATR':
            period = int(float(args[0]['value'])) if args and args[0].get('type') == 'const' else 14
            return {'type': 'indicator', 'name': 'ATR', 'params': {'period': period}}
        if upper == 'VWAP':
            return {'type': 'indicator', 'name': 'VWAP', 'params': {}}
        if upper in ('BOLLINGERMIDDLE','BOLLINGERMID','BBMIDDLE','BBMID'):
            src = args[0] if args else {'type': 'attr', 'name': 'close'}
            period = int(float(args[1]['value'])) if len(args) > 1 and args[1].get('type') == 'const' else 20
            std = float(args[2]['value']) if len(args) > 2 and args[2].get('type') == 'const' else 2.0
            return {'type': 'indicator', 'name': 'BB_MIDDLE', 'params': {'src': src, 'period': period, 'std': std}}
        if upper in ('BOLLINGERUPPER','BBUPPER'):
            src = args[0] if args else {'type': 'attr', 'name': 'close'}
            period = int(float(args[1]['value'])) if len(args) > 1 and args[1].get('type') == 'const' else 20
            std = float(args[2]['value']) if len(args) > 2 and args[2].get('type') == 'const' else 2.0
            return {'type': 'indicator', 'name': 'BB_UPPER', 'params': {'src': src, 'period': period, 'std': std}}
        if upper in ('BOLLINGERLOWER','BBLOWER'):
            src = args[0] if args else {'type': 'attr', 'name': 'close'}
            period = int(float(args[1]['value'])) if len(args) > 1 and args[1].get('type') == 'const' else 20
            std = float(args[2]['value']) if len(args) > 2 and args[2].get('type') == 'const' else 2.0
            return {'type': 'indicator', 'name': 'BB_LOWER', 'params': {'src': src, 'period': period, 'std': std}}
        if upper in ('MAX','MIN'):
            # MAX(n, measure)
            if not args:
                raise DSLParseError(f"{upper} requires at least 1 argument")
            if len(args) == 1:
                period = int(float(args[0]['value'])) if args[0].get('type') == 'const' else 14
                meas = {'type': 'attr', 'name': 'close'}
            else:
                period = int(float(args[0]['value'])) if args[0].get('type') == 'const' else 14
                meas = args[1]
            return {'type': 'func', 'name': upper, 'period': period, 'measure': meas}
        # Default: treat as attribute
        return {'type': 'attr', 'name': upper.lower()}

def parse_dsl_to_filter_node(text: str) -> dict:
    parser = DSLParser(text)
    node = parser.parse()
    # normalize 'logical' alias for group
    if isinstance(node, dict) and node.get('op') == 'group' and 'logic' in node:
        return node
    return node

def dsl_to_scanner_spec(text: str, timeframe: str | None = None, universe: Any | None = None) -> dict:
    filters_node = parse_dsl_to_filter_node(text)
    filters = [filters_node] if filters_node else []
    return {
        'timeframe': (timeframe or '1D').upper(),
        'universe': universe if universe is not None else 'ALL',
        'filters': filters
    }

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
        elif request.get('action') == 'parse-dsl':
            try:
                data = request.get('data', {}) or {}
                dsl = data.get('dsl') or data.get('text')
                timeframe = data.get('timeframe')
                universe = data.get('universe')
                if not dsl or not isinstance(dsl, str):
                    return {'error': 'dsl string is required', 'requestId': request_id}
                if len(dsl) > 5000:
                    return {'error': 'DSL too long', 'requestId': request_id}
                if not _rate_limit_parse():
                    return {'error': 'rate_limited', 'retryAfterMs': 1000, 'requestId': request_id}
                try:
                    universe = _validate_universe(universe)
                except Exception as ve:
                    return {'error': f'invalid_universe: {ve}', 'requestId': request_id}
                spec = dsl_to_scanner_spec(dsl, timeframe=timeframe, universe=universe)
                return {'success': True, 'scannerSpec': spec, 'requestId': request_id}
            except DSLParseError as pe:
                payload = {'error': 'ParseError', 'message': str(pe), 'requestId': request_id}
                if hasattr(pe, 'pos') and pe.pos is not None:
                    payload['pos'] = pe.pos
                if hasattr(pe, 'token') and pe.token is not None:
                    payload['token'] = pe.token
                return payload
            except Exception as e:
                return {'error': f'Failed to parse DSL: {e}', 'requestId': request_id}
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
        elif request.get('action') == 'delete-dataset':
            """Delete a dataset by name"""
            try:
                data = request.get('data', {}) or {}
                name = data.get('name')
                if not name:
                    return {'error': 'name is required', 'requestId': request_id}
                result = current_db_service.delete_dataset(name)
                result['requestId'] = request_id
                return result
            except Exception as e:
                return {
                    'error': f'Failed to delete dataset: {str(e)}',
                    'requestId': request_id
                }
        elif request.get('action') == 'save-scan':
            try:
                data = request.get('data', {}) or {}
                name = data.get('name')
                spec = data.get('spec') or data.get('scannerSpec') or {}
                description = data.get('description', '')
                if not name or not isinstance(spec, dict):
                    return {'error': 'name and spec are required', 'requestId': request_id}
                result = current_db_service.save_scan(name, spec, description)
                result['requestId'] = request_id
                return result
            except Exception as e:
                return {'error': f'Failed to save scan: {e}', 'requestId': request_id}
        elif request.get('action') == 'get-scans':
            try:
                result = current_db_service.get_scans()
                result['requestId'] = request_id
                return result
            except Exception as e:
                return {'error': f'Failed to get scans: {e}', 'requestId': request_id}
        elif request.get('action') == 'get-scan':
            try:
                data = request.get('data', {}) or {}
                name = data.get('name')
                if not name:
                    return {'error': 'name is required', 'requestId': request_id}
                result = current_db_service.get_scan(name)
                result['requestId'] = request_id
                return result
            except Exception as e:
                return {'error': f'Failed to get scan: {e}', 'requestId': request_id}
        elif request.get('action') == 'delete-scan':
            try:
                data = request.get('data', {}) or {}
                name = data.get('name')
                if not name:
                    return {'error': 'name is required', 'requestId': request_id}
                result = current_db_service.delete_scan(name)
                result['requestId'] = request_id
                return result
            except Exception as e:
                return {'error': f'Failed to delete scan: {e}', 'requestId': request_id}
        elif request.get('action') == 'save-watchlist':
            try:
                data = request.get('data', {}) or {}
                name = data.get('name')
                symbols = data.get('symbols') or []
                description = data.get('description', '')
                if not name or not isinstance(symbols, list):
                    return {'error': 'name and symbols(list) are required', 'requestId': request_id}
                result = current_db_service.save_watchlist(name, symbols, description)
                result['requestId'] = request_id
                return result
            except Exception as e:
                return {'error': f'Failed to save watchlist: {e}', 'requestId': request_id}
        elif request.get('action') == 'get-watchlists':
            try:
                result = current_db_service.get_watchlists()
                result['requestId'] = request_id
                return result
            except Exception as e:
                return {'error': f'Failed to get watchlists: {e}', 'requestId': request_id}
        elif request.get('action') == 'get-watchlist-symbols':
            try:
                data = request.get('data', {}) or {}
                name = data.get('name')
                if not name:
                    return {'error': 'name is required', 'requestId': request_id}
                syms = current_db_service.get_watchlist_symbols(name)
                return {'success': True, 'name': name, 'symbols': syms, 'requestId': request_id}
            except Exception as e:
                return {'error': f'Failed to get watchlist symbols: {e}', 'requestId': request_id}
        elif request.get('action') == 'delete-watchlist':
            try:
                data = request.get('data', {}) or {}
                name = data.get('name')
                if not name:
                    return {'error': 'name is required', 'requestId': request_id}
                result = current_db_service.delete_watchlist(name)
                result['requestId'] = request_id
                return result
            except Exception as e:
                return {'error': f'Failed to delete watchlist: {e}', 'requestId': request_id}
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
        elif request.get('action') == 'list-symbols':
            try:
                syms = current_db_service.list_symbols()
                return {'success': True, 'symbols': syms, 'count': len(syms), 'requestId': request_id}
            except Exception as e:
                return {'error': f'Failed to list symbols: {e}', 'requestId': request_id}
        elif request.get('action') == 'validate-symbols':
            try:
                data = request.get('data', {}) or {}
                symbols = data.get('symbols') or []
                if isinstance(symbols, str):
                    symbols = [symbols]
                if not isinstance(symbols, list):
                    return {'error': 'symbols must be a list or string', 'requestId': request_id}
                all_syms = set(current_db_service.list_symbols())
                valid = [s for s in symbols if s in all_syms]
                invalid = [s for s in symbols if s not in all_syms]
                return {'success': True, 'valid': valid, 'invalid': invalid, 'requestId': request_id}
            except Exception as e:
                return {'error': f'Failed to validate symbols: {e}', 'requestId': request_id}
        elif request.get('action') == 'analyze-data-quality':
            try:
                print(f"DATA-QUALITY: Starting comprehensive data quality analysis", file=sys.stderr)
                analyzer = DataQualityAnalyzer(current_db_service.market_db_path)
                
                # Check if specific symbols are requested
                data = request.get('data', {}) or {}
                symbols = data.get('symbols')
                
                if symbols:
                    # Analyze specific symbols
                    if isinstance(symbols, str):
                        symbols = [symbols]
                    results = [analyzer.analyze_symbol(sym) for sym in symbols]
                else:
                    # Analyze all symbols
                    results = analyzer.analyze_all_symbols()
                
                print(f"DATA-QUALITY: Analysis complete for {len(results)} symbols", file=sys.stderr)
                return {'success': True, 'results': results, 'requestId': request_id}
            except Exception as e:
                print(f"DATA-QUALITY: Analysis failed: {e}", file=sys.stderr)
                return {'error': f'Data quality analysis failed: {e}', 'requestId': request_id}
        elif request.get('action') == 'parse-symbol-csv':
            try:
                data = request.get('data', {}) or {}
                file_path = data.get('file_path') or data.get('path')
                if not file_path or not os.path.exists(file_path):
                    return {'error': 'invalid file path', 'requestId': request_id}
                # Read via pandas but cheap: only first column or a "symbol" column
                df = _read_any_ohlcv(file_path)
                cols = [c.lower() for c in df.columns]
                sym_col = None
                for cand in ['symbol', 'ticker', 'sym', 'code']:
                    if cand in cols:
                        sym_col = df.columns[cols.index(cand)]
                        break
                if sym_col is None:
                    # Fallback: first column
                    sym_col = df.columns[0]
                syms = [str(s).strip() for s in df[sym_col].dropna().astype(str).tolist()]
                # Basic normalization and dedupe
                syms = [s for s in syms if s]
                syms = list(dict.fromkeys(syms))
                return {'success': True, 'symbols': syms, 'count': len(syms), 'requestId': request_id}
            except Exception as e:
                return {'error': f'Failed to parse symbol CSV: {e}', 'requestId': request_id}
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
                                int(row['Volume']) if row['Volume'] is not None and row['Volume'] != '' else None
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

                # Run data quality analysis
                if rows_imported > 0:
                    try:
                        print(f"IMPORT: Running data quality analysis for symbol '{symbol}'", file=sys.stderr)
                        analyzer = DataQualityAnalyzer(current_db_service.market_db_path)
                        quality_analysis = analyzer.analyze_symbol(symbol)
                        if 'error' not in quality_analysis:
                            summary['dataQuality'] = quality_analysis
                            print(f"IMPORT: Data quality analysis completed successfully", file=sys.stderr)
                        else:
                            print(f"IMPORT: Warning - Data quality analysis failed: {quality_analysis.get('error')}", file=sys.stderr)
                    except Exception as e:
                        print(f"IMPORT: Warning - Failed to run data quality analysis: {e}", file=sys.stderr)

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
        elif request.get('action') == 'run-scan':
            # Phase 1-4: Scanner execution with multi-timeframe support, memoization, and explain values
            t0 = time.time()
            try:
                data = request.get('data', {}) or {}
                print(f"SCAN: Received data keys: {list(data.keys())}", file=sys.stderr)
                
                # If a raw DSL string is provided, parse into scannerSpec
                raw_dsl = data.get('dsl')
                if isinstance(raw_dsl, str):
                    print(f"SCAN: DSL mode detected, parsing DSL", file=sys.stderr)
                    try:
                        dsl_spec = dsl_to_scanner_spec(raw_dsl, timeframe=data.get('timeframe'), universe=data.get('universe'))
                        scanner_spec = dsl_spec
                        print(f"SCAN: DSL parsed successfully, universe in spec: {scanner_spec.get('universe')}", file=sys.stderr)
                    except DSLParseError as pe:
                        return {'error': f'DSL parse error: {str(pe)}', 'requestId': request_id}
                else:
                    scanner_spec = data.get('scannerSpec') or data.get('spec') or {}
                    print(f"SCAN: JSON spec mode, universe in spec: {scanner_spec.get('universe')}", file=sys.stderr)
                options = data.get('options') or {}
                print(f"SCAN: start requestId={request_id}, timeframe={scanner_spec.get('timeframe')}, universe={scanner_spec.get('universe')}, includeExplain={options.get('includeExplain', False)}", file=sys.stderr)

                if not isinstance(scanner_spec, dict):
                    return {
                        'error': 'Invalid scannerSpec: expected object',
                        'requestId': request_id
                    }

                timeframe = str(scanner_spec.get('timeframe', '1D')).upper()
                # Phase 3: Support multiple timeframes (1D, 5M, 15M, 1H)
                supported_timeframes = ['1D', '5M', '15M', '1H', '1HOUR']
                if timeframe not in supported_timeframes:
                    return {
                        'error': f"Unsupported timeframe '{timeframe}'. Supported: {', '.join(supported_timeframes)}",
                        'requestId': request_id
                    }
                
                # Normalize 1HOUR to 1H
                if timeframe == '1HOUR':
                    timeframe = '1H'

                universe = scanner_spec.get('universe', 'ALL')
                print(f"SCAN: Universe extracted from spec: {universe}, type: {type(universe)}", file=sys.stderr)
                
                # Determine symbols
                symbols_list = []
                
                # Phase 4: Helper function to fetch OHLCV data for a symbol and timeframe
                def fetch_ohlcv_data(symbol: str, tf: str, conn_override=None) -> pd.DataFrame:
                    """Fetch OHLCV data from database for the specified symbol and timeframe
                     
                    Args:
                        symbol: Symbol to fetch
                        tf: Timeframe (1D, 1h, 15m, 5m)
                        conn_override: Optional sqlite3 connection (for parallel execution)
                    """
                    start_time = time.time()
                    print(f"DEBUG: fetch_ohlcv_data called for {symbol}, timeframe: {tf}", file=sys.stderr)
                    
                    def _fetch_with_conn(conn):
                        query_start = time.time()
                        try:
                            if tf == '1D':
                                # Daily data from price_data table
                                where = "symbol = ?"
                                params: list = [symbol]
                                if options.get('dateFrom'):
                                    where += " AND timestamp >= ?"
                                    # assume dateFrom is YYYY-MM-DD
                                    dt = int(time.mktime(datetime.datetime.strptime(options['dateFrom'], '%Y-%m-%d').timetuple()))
                                    params.append(dt)
                                if options.get('dateTo'):
                                    where += " AND timestamp <= ?"
                                    dt = int(time.mktime(datetime.datetime.strptime(options['dateTo'], '%Y-%m-%d').timetuple())) + 86399
                                    params.append(dt)
                                # Hard cap rows to avoid pathological very long series stalling scans
                                cap = int(options.get('rowCapPerSymbol', 20000) or 20000)
                                print(f"DEBUG: Executing daily query for {symbol}: WHERE {where}, LIMIT {cap}", file=sys.stderr)
                                
                                # Set timeout for the query
                                conn.execute("PRAGMA busy_timeout = 10000")  # 10 second timeout
                                cursor = conn.execute(
                                    f"SELECT timestamp, open, high, low, close, volume FROM price_data WHERE {where} ORDER BY timestamp ASC LIMIT ?",
                                    tuple(params + [cap])
                                )
                                rows = cursor.fetchall()
                                query_time = time.time() - query_start
                                print(f"DEBUG: Daily query for {symbol} returned {len(rows)} rows in {query_time:.3f}s", file=sys.stderr)
                                if not rows:
                                    return pd.DataFrame()
                                df = pd.DataFrame(rows, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                                df = df.set_index(pd.to_datetime(df['timestamp'], unit='s'))
                                return df
                            else:
                                # Intraday data from ohlcv_intraday table
                                where = "symbol = ? AND timeframe = ?"
                                params: list = [symbol, tf]
                                if options.get('dateFrom'):
                                    where += " AND timestamp >= ?"
                                    dt = int(time.mktime(datetime.datetime.strptime(options['dateFrom'], '%Y-%m-%d').timetuple()))
                                    params.append(dt)
                                if options.get('dateTo'):
                                    where += " AND timestamp <= ?"
                                    dt = int(time.mktime(datetime.datetime.strptime(options['dateTo'], '%Y-%m-%d').timetuple())) + 86399
                                    params.append(dt)
                                cap = int(options.get('rowCapPerSymbol', 50000) or 50000)
                                print(f"DEBUG: Executing intraday query for {symbol}: WHERE {where}, LIMIT {cap}", file=sys.stderr)
                                
                                # Set timeout for the query
                                conn.execute("PRAGMA busy_timeout = 10000")  # 10 second timeout
                                cursor = conn.execute(
                                    f"SELECT timestamp, open, high, low, close, volume FROM ohlcv_intraday WHERE {where} ORDER BY timestamp ASC LIMIT ?",
                                    tuple(params + [cap])
                                )
                                rows = cursor.fetchall()
                                query_time = time.time() - query_start
                                print(f"DEBUG: Intraday query for {symbol} returned {len(rows)} rows in {query_time:.3f}s", file=sys.stderr)
                                if not rows:
                                    # No intraday data available - could resample from daily if needed
                                    return pd.DataFrame()
                                df = pd.DataFrame(rows, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                                df = df.set_index(pd.to_datetime(df['timestamp'], unit='s'))
                                return df
                        except sqlite3.OperationalError as e:
                            print(f"ERROR: Database query failed for {symbol}: {e}", file=sys.stderr)
                            return pd.DataFrame()
                        except Exception as e:
                            print(f"ERROR: Unexpected error fetching data for {symbol}: {e}", file=sys.stderr)
                            return pd.DataFrame()
                    
                    try:
                        if conn_override:
                            result = _fetch_with_conn(conn_override)
                        else:
                            with sqlite3.connect(current_db_service.market_db_path) as conn:
                                result = _fetch_with_conn(conn)
                        
                        total_time = time.time() - start_time
                        print(f"DEBUG: fetch_ohlcv_data for {symbol} completed in {total_time:.3f}s, shape: {result.shape}", file=sys.stderr)
                        return result
                    except Exception as e:
                        total_time = time.time() - start_time
                        print(f"ERROR: fetch_ohlcv_data for {symbol} failed after {total_time:.3f}s: {e}", file=sys.stderr)
                        return pd.DataFrame()
                
                with sqlite3.connect(current_db_service.market_db_path) as conn:
                    if isinstance(universe, str) and universe.upper().startswith('WATCHLIST:'):
                        wl_name = universe.split(':', 1)[1]
                        print(f"SCAN: Resolving WATCHLIST: {wl_name}", file=sys.stderr)
                        # Resolve watchlist symbols from user DB
                        wl_syms = current_db_service.get_watchlist_symbols(wl_name)
                        print(f"SCAN: WATCHLIST {wl_name} resolved to {len(wl_syms)} symbols", file=sys.stderr)
                        if wl_syms:
                            placeholders = ','.join('?' for _ in wl_syms)
                            cursor = conn.execute(f"SELECT DISTINCT symbol FROM price_data WHERE symbol IN ({placeholders}) ORDER BY symbol", tuple(wl_syms))
                        else:
                            cursor = conn.execute("SELECT DISTINCT symbol FROM price_data WHERE 1=0")
                    elif isinstance(universe, list) and len(universe) > 0:
                        print(f"SCAN: Universe is LIST with {len(universe)} symbols: {universe[:5]}...", file=sys.stderr)
                        # Validate existence
                        placeholders = ','.join('?' for _ in universe)
                        cursor = conn.execute(f"SELECT DISTINCT symbol FROM price_data WHERE symbol IN ({placeholders}) ORDER BY symbol", tuple(universe))
                    else:
                        print(f"SCAN: Universe is ALL - scanning entire database", file=sys.stderr)
                        cursor = conn.execute("SELECT DISTINCT symbol FROM price_data ORDER BY symbol")
                    symbols_list = [row[0] for row in cursor.fetchall()]
                print(f"SCAN: symbols to scan={len(symbols_list)}, first 5: {symbols_list[:5]}", file=sys.stderr)

                filters = scanner_spec.get('filters', []) or []
                # If this is a skeleton scan request (no filters) and caller requested latestOnly,
                # don't scan the entire database — return an empty skeleton result. Tests expect
                # scannedSymbols == 0 in this case.
                if not filters and options.get('latestOnly'):
                    return {
                        'results': [],
                        'stats': {
                            'scannedSymbols': 0,
                            'timeMs': int((time.time() - t0) * 1000)
                        },
                        'requestId': request_id
                    }
                # If there are no symbols to scan, return early
                if not symbols_list:
                    return {
                        'results': [],
                        'stats': {
                            'scannedSymbols': 0,
                            'timeMs': int((time.time() - t0) * 1000)
                        },
                        'requestId': request_id
                    }
                if not isinstance(filters, list):
                    return { 'error': 'filters must be an array', 'requestId': request_id }

                # Apply maxSymbols cap if provided in options (development convenience)
                max_symbols = 0
                try:
                    max_symbols = int(options.get('maxSymbols', 0) or 0)
                except Exception:
                    max_symbols = 0
                if max_symbols > 0 and len(symbols_list) > max_symbols:
                    symbols_list = symbols_list[:max_symbols]

                # Emit initial scan-progress event
                try:
                    print(json.dumps({
                        'type': 'scan-progress',
                        'requestId': request_id,
                        'phase': 'start',
                        'totalSymbols': len(symbols_list)
                    }), flush=True)
                except Exception:
                    pass

                # Phase 4: Memoization cache for computed indicators per symbol
                # Key: (symbol, indicator_signature) -> pd.Series
                indicator_cache = {}
                
                def get_cache_key(sym: str, indicator_sig: str) -> str:
                    return f"{sym}:{indicator_sig}"
                
                def describe_measure(node) -> str:
                    """Generate a human-readable description of a measure node for explain values"""
                    if not isinstance(node, dict):
                        return "unknown"
                    ntype = node.get('type')
                    if ntype == 'const':
                        return str(node.get('value', 0))
                    if ntype == 'expr':
                        parts = []
                        for token in node.get('expr', []):
                            if isinstance(token, str):
                                parts.append(token)
                            else:
                                parts.append(describe_measure(token))
                        inner = ' '.join(parts).strip()
                        return f"({inner})" if inner else "(expr)"
                    if ntype == 'attr':
                        name = node.get('name', '')
                        offset = node.get('offset')
                        if offset and offset.get('kind') == 'lookback':
                            return f"{name}[-{offset.get('bars')}]"
                        elif offset and offset.get('kind') == 'ordinal':
                            return f"{name}[={offset.get('n')}]"
                        return name
                    if ntype == 'indicator':
                        iname = node.get('name', '')
                        params = node.get('params', {})
                        if iname == 'SMA':
                            return f"SMA({params.get('period', 20)})"
                        if iname == 'EMA':
                            return f"EMA({params.get('period', 20)})"
                        if iname == 'RSI':
                            return f"RSI({params.get('period', 14)})"
                        if iname == 'MACD':
                            return f"MACD({params.get('fast', 12)},{params.get('slow', 26)},{params.get('signal', 9)})"
                        if iname == 'ATR':
                            return f"ATR({params.get('period', 14)})"
                        if iname in ('BB_UPPER', 'BB_MIDDLE', 'BB_LOWER'):
                            return f"{iname}({params.get('period', 20)})"
                        if iname == 'ADX':
                            return f"ADX({params.get('period', 14)})"
                        if iname == 'VWAP':
                            return "VWAP"
                        return iname
                    if ntype == 'func':
                        fname = node.get('name', '')
                        period = node.get('period', 0)
                        return f"{fname}({period})"
                    return "measure"

                # Helper: evaluate filters for one symbol using pandas Series
                def rsi(series: pd.Series, period: int = 14) -> pd.Series:
                    delta = series.diff()
                    gain = (delta.clip(lower=0)).ewm(alpha=1/period, adjust=False).mean()
                    loss = (-delta.clip(upper=0)).ewm(alpha=1/period, adjust=False).mean()
                    rs = np.where(loss == 0, np.nan, gain / loss)
                    rsi_val = 100 - (100 / (1 + rs))
                    return pd.Series(rsi_val, index=series.index)

                def ema(series: pd.Series, period: int) -> pd.Series:
                    return series.ewm(span=period, adjust=False).mean()

                def sma(series: pd.Series, period: int) -> pd.Series:
                    return series.rolling(window=period, min_periods=period).mean()

                def macd_line(series: pd.Series, fast: int = 12, slow: int = 26):
                    return ema(series, fast) - ema(series, slow)

                def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
                    line = macd_line(series, fast, slow)
                    sig = line.ewm(span=signal, adjust=False).mean()
                    hist = line - sig
                    return line, sig, hist

                def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
                    prev_close = close.shift(1)
                    tr = pd.concat([
                        (high - low),
                        (high - prev_close).abs(),
                        (low - prev_close).abs()
                    ], axis=1).max(axis=1)
                    # Wilder smoothing (RMA)
                    return tr.ewm(alpha=1/period, adjust=False).mean()

                def bollinger(series: pd.Series, period: int = 20, std_mult: float = 2.0):
                    mid = sma(series, period)
                    std = series.rolling(window=period, min_periods=period).std()
                    upper = mid + std_mult * std
                    lower = mid - std_mult * std
                    return mid, upper, lower

                def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
                    # Wilder's ADX using pandas operations
                    up_move = high.diff().astype(float)
                    down_move = (-low.diff()).astype(float)
                    plus_dm = up_move.where((up_move > down_move) & (up_move > 0.0), 0.0)
                    minus_dm = down_move.where((down_move > up_move) & (down_move > 0.0), 0.0)
                    prev_close = close.shift(1)
                    tr = pd.concat([
                        (high - low),
                        (high - prev_close).abs(),
                        (low - prev_close).abs()
                    ], axis=1).max(axis=1)
                    tr_rma = tr.ewm(alpha=1/period, adjust=False).mean()
                    plus_dm_rma = plus_dm.ewm(alpha=1/period, adjust=False).mean()
                    minus_dm_rma = minus_dm.ewm(alpha=1/period, adjust=False).mean()
                    plus_di = 100 * (plus_dm_rma / tr_rma.replace(0, np.nan))
                    minus_di = 100 * (minus_dm_rma / tr_rma.replace(0, np.nan))
                    dx = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)).replace([np.inf, -np.inf], np.nan)
                    adx_val = dx.ewm(alpha=1/period, adjust=False).mean()
                    return adx_val

                def vwap_cumulative(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
                    # Cumulative VWAP over the series (approx for daily data)
                    tp = (high + low + close) / 3.0
                    vol = volume.fillna(0)
                    cum_vol = vol.cumsum().replace(0, np.nan)
                    return (tp * vol).cumsum() / cum_vol

                def eval_measure(node, df: pd.DataFrame, symbol: str = '', current_timeframe: str = '') -> pd.Series:
                    """Evaluate a measure node and return a pandas Series. Uses indicator_cache for memoization.
                     
                    Phase 3: Supports cross-timeframe queries - if node has 'timeframe' property different
                    from main_timeframe, fetches data for that timeframe and aligns it.
                    """
                    start_time = time.time()
                    node_desc = str(node).replace('\n', ' ')[:80] if isinstance(node, dict) else str(node)[:80]
                    print(f"DEBUG: eval_measure START for {symbol}: {node_desc}", file=sys.stderr)
                    
                    if node is None:
                        print(f"DEBUG: eval_measure END (node is None) for {symbol} in {time.time()-start_time:.3f}s", file=sys.stderr)
                        return pd.Series(dtype=float, index=df.index)
                    if not isinstance(node, dict):
                        print(f"DEBUG: eval_measure END (not dict) for {symbol} in {time.time()-start_time:.3f}s", file=sys.stderr)
                        return pd.Series(np.nan, index=df.index)
                    
                    ntype = node.get('type')
                    offset = node.get('offset')
                    node_timeframe = node.get('timeframe', current_timeframe)
                    active_df = df
                    active_tf = current_timeframe
                    
                    # Phase 3: If this node specifies a different timeframe, fetch that data
                    if symbol and node_timeframe and node_timeframe != current_timeframe:
                        print(f"DEBUG: Cross-timeframe fetch for {symbol}: {current_timeframe} -> {node_timeframe}", file=sys.stderr)
                        cross_tf_df = fetch_ohlcv_data(symbol, node_timeframe)
                        if not cross_tf_df.empty:
                            active_df = cross_tf_df
                            active_tf = node_timeframe
                        else:
                            active_tf = node_timeframe or current_timeframe
                    else:
                        active_tf = node_timeframe or current_timeframe
                    
                    index_ref = active_df.index if not active_df.empty else df.index
                    def apply_offset(series: pd.Series) -> pd.Series:
                        if isinstance(offset, dict):
                            kind = offset.get('kind')
                            if kind == 'lookback':
                                bars = int(offset.get('bars', 0))
                                if bars > 0:
                                    return series.shift(bars)
                            elif kind == 'ordinal':
                                # Phase 3: ordinal offset [=k] - access k-th bar from series start
                                n = int(offset.get('n', 0))
                                if 0 <= n < len(series):
                                    # Return a series with the value at position n for all indices
                                    return pd.Series(series.iloc[n], index=series.index)
                                else:
                                    # Out of bounds - return NaN
                                    return pd.Series(np.nan, index=series.index)
                        return series

                    if ntype == 'const':
                        val = float(node.get('value', 0))
                        if index_ref.empty:
                            return pd.Series(dtype=float, index=index_ref)
                        return pd.Series(val, index=index_ref)
                    if ntype == 'attr':
                        name = node.get('name', '').lower()
                        mapping = {
                            'open': 'open', 'high': 'high', 'low': 'low', 'close': 'close', 'volume': 'volume'
                        }
                        if name not in mapping:
                            return pd.Series(np.nan, index=index_ref)
                        column_name = mapping[name]
                        if column_name not in active_df.columns:
                            return pd.Series(np.nan, index=index_ref)
                        result = apply_offset(active_df[column_name].astype(float))
                        elapsed = time.time() - start_time
                        print(f"DEBUG: eval_measure attr '{name}' for {symbol} took {elapsed:.3f}s", file=sys.stderr)
                        return result
                    if ntype == 'func':
                        fname = node.get('name', '').upper()
                        period = int(node.get('period', 14))
                        inner = eval_measure(node.get('measure'), active_df, symbol, active_tf)
                        if fname == 'MAX':
                            result = inner.rolling(window=period, min_periods=period).max()
                        elif fname == 'MIN':
                            result = inner.rolling(window=period, min_periods=period).min()
                        else:
                            result = pd.Series(np.nan, index=index_ref)
                        elapsed = time.time() - start_time
                        print(f"DEBUG: eval_measure func '{fname}' for {symbol} took {elapsed:.3f}s", file=sys.stderr)
                        return result
                    if ntype == 'expr':
                        tokens = node.get('expr', []) or []
                        if not tokens:
                            return pd.Series(np.nan, index=index_ref)
                        resolved: list[Any] = []
                        for token in tokens:
                            if isinstance(token, str):
                                resolved.append(token)
                            else:
                                resolved.append(eval_measure(token, active_df, symbol, active_tf))
                        if not resolved or isinstance(resolved[0], str):
                            return pd.Series(np.nan, index=index_ref)
                        result_series = resolved[0]
                        if isinstance(result_series, pd.Series):
                            result_series = result_series.reindex(index_ref)
                        else:
                            result_series = pd.Series(result_series, index=index_ref)
                        idx = 1
                        while idx < len(resolved):
                            op_token = resolved[idx]
                            rhs_token = resolved[idx + 1] if idx + 1 < len(resolved) else None
                            if isinstance(rhs_token, pd.Series):
                                rhs_series = rhs_token.reindex(result_series.index)
                            else:
                                rhs_series = pd.Series(rhs_token, index=result_series.index)
                            if op_token == '+':
                                result_series = result_series + rhs_series
                            elif op_token == '-':
                                result_series = result_series - rhs_series
                            elif op_token == '*':
                                result_series = result_series * rhs_series
                            elif op_token == '/':
                                rhs_safe = rhs_series.replace(0, np.nan)
                                result_series = result_series / rhs_safe
                            idx += 2
                        result = apply_offset(result_series)
                        elapsed = time.time() - start_time
                        print(f"DEBUG: eval_measure expr for {symbol} took {elapsed:.3f}s", file=sys.stderr)
                        return result
                    if ntype == 'indicator':
                        iname = node.get('name', '').upper()
                        params = node.get('params', {}) or {}
                        cache_scope = (node_timeframe or active_tf or current_timeframe or 'default')
                        # Phase 4: Check cache before computing
                        cache_sig = f"{cache_scope}:{iname}:{json.dumps(params, sort_keys=True)}"
                        cache_key = get_cache_key(symbol, cache_sig)
                        if cache_key in indicator_cache:
                            print(f"DEBUG: Cache hit for {iname} on {symbol}", file=sys.stderr)
                            return apply_offset(indicator_cache[cache_key])
                        
                        print(f"DEBUG: Computing {iname} for {symbol} with params: {params}", file=sys.stderr)
                        result_series = None
                        if iname == 'SMA':
                            src = eval_measure(params.get('src') or {'type': 'attr', 'name': 'close'}, active_df, symbol, active_tf)
                            per = int(params.get('period', 20))
                            result_series = sma(src, per)
                        elif iname == 'EMA':
                            src = eval_measure(params.get('src') or {'type': 'attr', 'name': 'close'}, active_df, symbol, active_tf)
                            per = int(params.get('period', 20))
                            result_series = ema(src, per)
                        elif iname == 'RSI':
                            src = eval_measure(params.get('src') or {'type': 'attr', 'name': 'close'}, active_df, symbol, active_tf)
                            per = int(params.get('period', 14))
                            result_series = rsi(src, per)
                        elif iname == 'MACD':
                            src = eval_measure(params.get('src') or {'type': 'attr', 'name': 'close'}, active_df, symbol, active_tf)
                            fast = int(params.get('fast', 12))
                            slow = int(params.get('slow', 26))
                            signal_p = int(params.get('signal', 9))
                            out = str(params.get('output', 'line')).lower()
                            line, sig, hist = macd(src, fast, slow, signal_p)
                            out_map = {'line': line, 'signal': sig, 'hist': hist}
                            result_series = out_map.get(out, line)
                        elif iname == 'ATR':
                            per = int(params.get('period', 14))
                            result_series = atr(active_df['high'], active_df['low'], active_df['close'], per)
                        elif iname in ('BB', 'BOLLINGER', 'BBANDS', 'BB_MIDDLE', 'BB_UPPER', 'BB_LOWER'):
                            src = eval_measure(params.get('src') or {'type': 'attr', 'name': 'close'}, active_df, symbol, active_tf)
                            per = int(params.get('period', 20))
                            mult = float(params.get('std', 2))
                            mid, up, low_b = bollinger(src, per, mult)
                            if iname == 'BB_MIDDLE':
                                result_series = mid
                            elif iname == 'BB_UPPER':
                                result_series = up
                            elif iname == 'BB_LOWER':
                                result_series = low_b
                            else:
                                result_series = mid  # default
                        elif iname == 'ADX':
                            per = int(params.get('period', 14))
                            result_series = adx(active_df['high'], active_df['low'], active_df['close'], per)
                        elif iname == 'VWAP':
                            # Approximate cumulative VWAP in daily data
                            volume_series = active_df['volume'] if 'volume' in active_df.columns else pd.Series(0, index=index_ref)
                            result_series = vwap_cumulative(active_df['high'], active_df['low'], active_df['close'], volume_series)
                        
                        if result_series is not None:
                            # Cache the computed indicator
                            indicator_cache[cache_key] = result_series
                            elapsed = time.time() - start_time
                            print(f"DEBUG: eval_measure {iname} for {symbol} took {elapsed:.3f}s, cached", file=sys.stderr)
                            return apply_offset(result_series)
                        
                        # Unknown indicator
                        elapsed = time.time() - start_time
                        print(f"DEBUG: eval_measure unknown indicator for {symbol} took {elapsed:.3f}s", file=sys.stderr)
                        return pd.Series(np.nan, index=index_ref)
                    # Unknown node type
                    elapsed = time.time() - start_time
                    print(f"DEBUG: eval_measure unknown node type for {symbol} took {elapsed:.3f}s", file=sys.stderr)
                    return pd.Series(np.nan, index=index_ref)

                def eval_filter(node, df: pd.DataFrame, symbol: str = '', explain_values: dict | None = None, main_timeframe: str = '1D') -> bool:
                    """Evaluate a filter node and optionally collect explain values for debugging/UI tooltips"""
                    start_time = time.time()
                    print(f"DEBUG: eval_filter ENTER for {symbol}, op={node.get('op') if isinstance(node, dict) else 'unknown'}", file=sys.stderr)
                    if not isinstance(node, dict):
                        print(f"DEBUG: eval_filter EXIT (not dict) for {symbol} in {time.time()-start_time:.3f}s", file=sys.stderr)
                        return False
                    op = node.get('op')
                    if op in ('group', 'logical'):
                        logic = node.get('logic', 'AND').upper()
                        children = node.get('children', []) or []
                        vals = [eval_filter(ch, df, symbol, explain_values, main_timeframe) for ch in children]
                        result = all(vals) if logic == 'AND' else any(vals)
                        elapsed = time.time() - start_time
                        print(f"DEBUG: eval_filter logical {logic} for {symbol} took {elapsed:.3f}s, result: {result}", file=sys.stderr)
                        return result
                    if op == 'not':
                        result = not eval_filter(node.get('child'), df, symbol, explain_values, main_timeframe)
                        elapsed = time.time() - start_time
                        print(f"DEBUG: eval_filter NOT for {symbol} took {elapsed:.3f}s, result: {result}", file=sys.stderr)
                        return result
                    if op == 'compare':
                        cmp_op = node.get('cmp')
                        print(f"DEBUG: eval_filter compare {cmp_op} for {symbol} - calling eval_measure for left", file=sys.stderr)
                        left_start = time.time()
                        left = eval_measure(node.get('left'), df, symbol, main_timeframe)
                        left_elapsed = time.time() - left_start
                        print(f"DEBUG: eval_filter compare left took {left_elapsed:.3f}s, now calling eval_measure for right", file=sys.stderr)
                        right_start = time.time()
                        right = eval_measure(node.get('right'), df, symbol, main_timeframe)
                        right_elapsed = time.time() - right_start
                        print(f"DEBUG: eval_filter compare right took {right_elapsed:.3f}s", file=sys.stderr)
                        lv = float(left.iloc[-1]) if len(left) else np.nan
                        rv = float(right.iloc[-1]) if len(right) else np.nan
                        
                        # Phase 4: Collect explain values
                        if explain_values is not None and not np.isnan(lv) and not np.isnan(rv):
                            left_desc = describe_measure(node.get('left'))
                            right_desc = describe_measure(node.get('right'))
                            explain_values[f"{left_desc}_{cmp_op}_{right_desc}"] = {
                                'left': round(lv, 4),
                                'right': round(rv, 4),
                                'operator': cmp_op,
                                'result': None  # Will be set below
                            }
                        
                        if np.isnan(lv) or np.isnan(rv):
                            if explain_values is not None:
                                left_desc = describe_measure(node.get('left'))
                                right_desc = describe_measure(node.get('right'))
                                key = f"{left_desc}_{cmp_op}_{right_desc}"
                                if key in explain_values:
                                    explain_values[key]['result'] = False
                            elapsed = time.time() - start_time
                            print(f"DEBUG: eval_filter compare {cmp_op} for {symbol} took {elapsed:.3f}s, result: False (NaN)", file=sys.stderr)
                            return False
                        
                        result = False
                        if cmp_op == '>':
                            result = lv > rv
                        elif cmp_op == '>=':
                            result = lv >= rv
                        elif cmp_op == '<':
                            result = lv < rv
                        elif cmp_op == '<=':
                            result = lv <= rv
                        elif cmp_op == '==':
                            result = abs(lv - rv) <= 1e-8
                        elif cmp_op == '!=':
                            result = abs(lv - rv) > 1e-8
                        
                        # Update result in explain values
                        if explain_values is not None:
                            left_desc = describe_measure(node.get('left'))
                            right_desc = describe_measure(node.get('right'))
                            key = f"{left_desc}_{cmp_op}_{right_desc}"
                            if key in explain_values:
                                explain_values[key]['result'] = result
                        
                        elapsed = time.time() - start_time
                        print(f"DEBUG: eval_filter compare {cmp_op} for {symbol} took {elapsed:.3f}s, result: {result} ({lv} vs {rv})", file=sys.stderr)
                        return result
                    if op == 'crossover':
                        # Phase1: relaxed crossover detection — consider a match when
                        # the left measure is currently above the right (CROSSES_ABOVE)
                        # or currently below (CROSSES_BELOW). This avoids missing
                        # cases where the previous value may be NaN due to indicator warmup.
                        cross_type = node.get('type', 'CROSSES_ABOVE').upper()
                        print(f"DEBUG: eval_filter crossover {cross_type} for {symbol} - calling eval_measure for left", file=sys.stderr)
                        left_start = time.time()
                        left = eval_measure(node.get('left'), df, symbol, main_timeframe)
                        left_elapsed = time.time() - left_start
                        print(f"DEBUG: eval_filter crossover left took {left_elapsed:.3f}s, now calling eval_measure for right", file=sys.stderr)
                        right_start = time.time()
                        right = eval_measure(node.get('right'), df, symbol, main_timeframe)
                        right_elapsed = time.time() - right_start
                        print(f"DEBUG: eval_filter crossover right took {right_elapsed:.3f}s", file=sys.stderr)
                        if len(left) < 1 or len(right) < 1:
                            elapsed = time.time() - start_time
                            print(f"DEBUG: eval_filter crossover {cross_type} for {symbol} took {elapsed:.3f}s, result: False (insufficient data)", file=sys.stderr)
                            return False
                        l_curr = left.iloc[-1]
                        r_curr = right.iloc[-1]
                        if np.isnan(l_curr) or np.isnan(r_curr):
                            elapsed = time.time() - start_time
                            print(f"DEBUG: eval_filter crossover {cross_type} for {symbol} took {elapsed:.3f}s, result: False (NaN values)", file=sys.stderr)
                            return False
                        
                        result = False
                        if cross_type == 'CROSSES_ABOVE':
                            result = l_curr > r_curr
                        elif cross_type == 'CROSSES_BELOW':
                            result = l_curr < r_curr
                        
                        # Phase 4: Collect explain values for crossovers
                        if explain_values is not None:
                            left_desc = describe_measure(node.get('left'))
                            right_desc = describe_measure(node.get('right'))
                            explain_values[f"{left_desc}_{cross_type}_{right_desc}"] = {
                                'left': round(l_curr, 4),
                                'right': round(r_curr, 4),
                                'type': cross_type,
                                'result': result
                            }
                        
                        elapsed = time.time() - start_time
                        print(f"DEBUG: eval_filter crossover {cross_type} for {symbol} took {elapsed:.3f}s, result: {result} ({l_curr} vs {r_curr})", file=sys.stderr)
                        return result
                    if op == 'arith':
                        # Optional basic arithmetic chain; evaluate last value
                        expr = node.get('expr', [])
                        if not expr:
                            return False
                        # Evaluate into a stack of numbers / operators, then compute left-to-right
                        vals = []
                        for token in expr:
                            if isinstance(token, dict):
                                series = eval_measure(token, df, symbol, main_timeframe)
                                vals.append(float(series.iloc[-1]) if len(series) else np.nan)
                            else:
                                vals.append(token)
                        # Compute
                        try:
                            acc = vals[0]
                            i = 1
                            while i < len(vals):
                                op2 = vals[i]
                                rhs = vals[i+1]
                                if op2 == '+': acc = acc + rhs
                                elif op2 == '-': acc = acc - rhs
                                elif op2 == '*': acc = acc * rhs
                                elif op2 == '/': acc = acc / rhs if rhs != 0 else np.nan
                                i += 2
                            # Non-zero truthiness
                            result = bool(acc) and not np.isnan(acc)
                            elapsed = time.time() - start_time
                            print(f"DEBUG: eval_filter arith for {symbol} took {elapsed:.3f}s, result: {result}", file=sys.stderr)
                            return result
                        except Exception:
                            elapsed = time.time() - start_time
                            print(f"DEBUG: eval_filter arith for {symbol} took {elapsed:.3f}s, result: False (exception)", file=sys.stderr)
                            return False
                    # Unknown op
                    elapsed = time.time() - start_time
                    print(f"DEBUG: eval_filter unknown op {op} for {symbol} took {elapsed:.3f}s, result: False", file=sys.stderr)
                    return False

                def eval_expr_series(expr_tokens: list[Any], df: pd.DataFrame, symbol: str, main_timeframe: str, df_index: pd.Index) -> pd.Series:
                    # Helper for vector arithmetic into a numeric series
                    if not expr_tokens:
                        return pd.Series(np.nan, index=df_index)
                    # Resolve tokens into series/numbers/operators
                    resolved: list[Any] = []
                    for token in expr_tokens:
                        if isinstance(token, dict):
                            s = eval_measure(token, df, symbol, main_timeframe)
                            resolved.append(s.reindex(df_index))
                        else:
                            resolved.append(token)
                    result_series = resolved[0]
                    if not isinstance(result_series, pd.Series):
                        result_series = pd.Series(result_series, index=df_index)
                    i = 1
                    while i < len(resolved):
                        op2 = resolved[i]
                        rhs = resolved[i+1] if i+1 < len(resolved) else np.nan
                        rhs_series = rhs.reindex(df_index) if isinstance(rhs, pd.Series) else pd.Series(rhs, index=df_index)
                        if op2 == '+':
                            result_series = result_series + rhs_series
                        elif op2 == '-':
                            result_series = result_series - rhs_series
                        elif op2 == '*':
                            result_series = result_series * rhs_series
                        elif op2 == '/':
                            rhs_safe = rhs_series.replace(0, np.nan)
                            result_series = result_series / rhs_safe
                        i += 2
                    return result_series

                def eval_filter_series(node, df: pd.DataFrame, symbol: str = '', main_timeframe: str = '1D') -> pd.Series:
                    """Vectorized evaluation of a filter, returning a boolean Series over time."""
                    index_ref = df.index
                    if not isinstance(node, dict):
                        return pd.Series(False, index=index_ref)
                    op = node.get('op')
                    if op in ('group', 'logical'):
                        logic = node.get('logic', 'AND').upper()
                        children = node.get('children', []) or []
                        if not children:
                            return pd.Series(True, index=index_ref) if logic == 'AND' else pd.Series(False, index=index_ref)
                        series_list = [eval_filter_series(ch, df, symbol, main_timeframe) for ch in children]
                        res = series_list[0]
                        for s in series_list[1:]:
                            res = (res & s) if logic == 'AND' else (res | s)
                        return res.fillna(False)
                    if op == 'not':
                        child = eval_filter_series(node.get('child'), df, symbol, main_timeframe)
                        return (~child).fillna(False)
                    if op == 'compare':
                        cmp_op = node.get('cmp')
                        left = eval_measure(node.get('left'), df, symbol, main_timeframe).reindex(index_ref)
                        right = eval_measure(node.get('right'), df, symbol, main_timeframe).reindex(index_ref)
                        mask_valid = left.notna() & right.notna()
                        result = pd.Series(False, index=index_ref)
                        if cmp_op == '>':
                            result = left > right
                        elif cmp_op == '>=':
                            result = left >= right
                        elif cmp_op == '<':
                            result = left < right
                        elif cmp_op == '<=':
                            result = left <= right
                        elif cmp_op == '==':
                            result = (left - right).abs() <= 1e-8
                        elif cmp_op == '!=':
                            result = (left - right).abs() > 1e-8
                        result = result & mask_valid
                        return result.fillna(False)
                    if op == 'crossover':
                        cross_type = node.get('type', 'CROSSES_ABOVE').upper()
                        left = eval_measure(node.get('left'), df, symbol, main_timeframe).reindex(index_ref)
                        right = eval_measure(node.get('right'), df, symbol, main_timeframe).reindex(index_ref)
                        l_prev = left.shift(1)
                        r_prev = right.shift(1)
                        mask_valid = left.notna() & right.notna() & l_prev.notna() & r_prev.notna()
                        if cross_type == 'CROSSES_ABOVE':
                            result = (l_prev <= r_prev) & (left > right)
                        else:
                            result = (l_prev >= r_prev) & (left < right)
                        result = result & mask_valid
                        return result.fillna(False)
                    if op == 'arith':
                        expr = node.get('expr', []) or []
                        series_val = eval_expr_series(expr, df, symbol, main_timeframe, index_ref)
                        return series_val.notna() & (series_val != 0)
                    return pd.Series(False, index=index_ref)

                # Phase 4: Helper function to process a single symbol (for parallel execution)
                def process_symbol(sym: str, db_path: str, include_explain: bool):
                    """Process a single symbol and return result if matched, else None"""
                    start_time = time.time()
                    try:
                        # Create a new connection for this thread
                        with sqlite3.connect(db_path) as conn:
                            # Fetch OHLCV data for the symbol
                            df = fetch_ohlcv_data(sym, timeframe, conn_override=conn)
                            if df.empty:
                                print(f"DEBUG: process_symbol {sym} - no data", file=sys.stderr)
                                return None
                            
                            # Collect explain values for this symbol
                            explain_vals = {} if include_explain else None
                            
                            # Evaluate all filters; top-level 'filters' is AND of entries
                            match_all = True
                            for f_idx, fnode in enumerate(filters):
                                print(f"DEBUG: process_symbol {sym} evaluating filter {f_idx+1}/{len(filters)}", file=sys.stderr)
                                if not eval_filter(fnode, df, sym, explain_vals, timeframe):
                                    match_all = False
                                    break
                            
                            elapsed = time.time() - start_time
                            print(f"DEBUG: process_symbol {sym} completed in {elapsed:.3f}s, match: {match_all}", file=sys.stderr)
                            
                            if match_all:
                                result_entry = {
                                    'symbol': sym,
                                    'timestamp': int(pd.Timestamp(df.index[-1]).timestamp())
                                }
                                if explain_vals:
                                    result_entry['values'] = explain_vals
                                return result_entry
                            return None
                    except Exception as e:
                        elapsed = time.time() - start_time
                        print(f"DEBUG: process_symbol {sym} failed after {elapsed:.3f}s: {e}", file=sys.stderr)
                        return None

                results = []
                scanned = 0
                symbol_timings: list[tuple[str, int]] = []
                last_progress_ts = time.time()
                scan_start_time = time.time()
                
                # Phase 4: Parallel processing with ThreadPoolExecutor
                # Determine optimal number of workers (max 8 to avoid overwhelming the database)
                max_workers = min(6, max(2, (os.cpu_count() or 4)))
                use_parallel = len(symbols_list) > 10  # Only parallelize for >10 symbols
                
                # Backtest mode evaluates across time; use sequential for clarity/perf predictability initially
                is_backtest = (str(options.get('mode', 'latest')).lower() == 'backtest') or bool(options.get('backtest', False))
                if use_parallel and not is_backtest:
                    # Parallel execution
                    with ThreadPoolExecutor(max_workers=max_workers) as executor:
                        # Submit all tasks
                        db_path_str = str(current_db_service.market_db_path)
                        print(f"SCAN: Submitting {len(symbols_list)} tasks to thread pool", file=sys.stderr)
                        def _task(sym):
                            print(f"SCAN: Starting task for symbol: {sym}", file=sys.stderr)
                            t_sym = time.time()
                            res = process_symbol(sym, db_path_str, options.get('includeExplain', False))
                            elapsed_ms = int((time.time() - t_sym) * 1000)
                            print(f"SCAN: Completed task for symbol: {sym}, took {elapsed_ms}ms", file=sys.stderr)
                            return sym, res, elapsed_ms

                        future_to_symbol = {
                            executor.submit(_task, sym): sym
                            for sym in symbols_list
                        }
                        print(f"SCAN: All tasks submitted, waiting for completion", file=sys.stderr)
                        
                        # Collect results as they complete
                        for future in as_completed(future_to_symbol, timeout=None):
                            scanned += 1
                            try:
                                sym, result, elapsed_ms = future.result(timeout=5)
                            except Exception as fe:
                                # Timeout or worker error; mark symbol as failed but continue
                                sym = future_to_symbol.get(future, 'UNKNOWN')
                                result, elapsed_ms = None, 0
                            symbol_timings.append((sym, elapsed_ms))
                            if result:
                                # attach per-symbol timing when includeExplain is on
                                if options.get('includeExplain', False):
                                    result['timingMs'] = elapsed_ms
                                # add alias for UI
                                if 'values' in result and 'explain' not in result:
                                    result['explain'] = result['values']
                                results.append(result)
                            # Throttle progress events
                            now = time.time()
                            if (now - last_progress_ts) >= 0.5 or (scanned % 50 == 0):
                                try:
                                    print(json.dumps({
                                        'type': 'scan-progress',
                                        'requestId': request_id,
                                        'phase': 'running',
                                        'scanned': scanned,
                                        'totalSymbols': len(symbols_list)
                                    }), flush=True)
                                except Exception:
                                    pass
                                last_progress_ts = now
                else:
                    # Sequential execution for small lists
                    print(f"SCAN: Starting sequential processing of {len(symbols_list)} symbols", file=sys.stderr)
                    for i, sym in enumerate(symbols_list):
                        symbol_start_time = time.time()
                        scanned += 1
                        print(f"SCAN: Processing symbol {i+1}/{len(symbols_list)}: {sym}", file=sys.stderr)
                        
                        # Clear cache for new symbol to avoid memory issues with many symbols
                        if scanned % 100 == 0:
                            print(f"SCAN: Clearing indicator cache at symbol {scanned}", file=sys.stderr)
                            indicator_cache.clear()
                        
                        # Fetch OHLCV data for the symbol using the new helper function
                        fetch_start = time.time()
                        print(f"SCAN: Fetching OHLCV data for {sym}", file=sys.stderr)
                        df = fetch_ohlcv_data(sym, timeframe)
                        fetch_time = time.time() - fetch_start
                        print(f"SCAN: OHLCV fetch completed for {sym} in {fetch_time:.3f}s", file=sys.stderr)
                        
                        if df.empty:
                            print(f"SCAN: No data for symbol {sym}, skipping", file=sys.stderr)
                            # Record timing even if no data
                            elapsed_ms = int((time.time() - symbol_start_time) * 1000)
                            symbol_timings.append((sym, elapsed_ms))
                            # Emit progress periodically
                            now = time.time()
                            if (now - last_progress_ts) >= 0.5 or (scanned % 50 == 0):
                                try:
                                    print(json.dumps({
                                        'type': 'scan-progress',
                                        'requestId': request_id,
                                        'phase': 'running',
                                        'scanned': scanned,
                                        'totalSymbols': len(symbols_list)
                                    }), flush=True)
                                except Exception:
                                    pass
                            last_progress_ts = now
                            continue
                            
                        if is_backtest:
                            # Evaluate vectorized match series across time
                            eval_start = time.time()
                            combined = None
                            for fnode in filters:
                                series_bool = eval_filter_series(fnode, df, sym, timeframe)
                                combined = series_bool if combined is None else (combined & series_bool)
                            combined = (combined.fillna(False)) if combined is not None else pd.Series(False, index=df.index)
                            eval_time = time.time() - eval_start
                            print(f"SCAN: Backtest evaluation for {sym} took {eval_time:.3f}s", file=sys.stderr)
                            
                            # Extract match timestamps; apply per-symbol cap (newest first)
                            match_idx = combined[combined].index
                            per_cap = 0
                            try:
                                per_cap = int(options.get('backtestLimitPerSymbol', 1000))
                            except Exception:
                                per_cap = 1000
                            if per_cap > 0 and len(match_idx) > per_cap:
                                match_idx = match_idx[-per_cap:]
                            if len(match_idx) > 0:
                                match_list = [{'timestamp': int(pd.Timestamp(ts).timestamp())} for ts in match_idx]
                                results.append({'symbol': sym, 'matches': match_list, 'matchCount': len(match_list)})
                        else:
                            # Phase 4: Collect explain values for this symbol
                            explain_vals = {} if options.get('includeExplain', False) else None
                            # Evaluate all filters; top-level 'filters' is AND of entries
                            eval_start = time.time()
                            print(f"SCAN: Evaluating filters for {sym}, data shape: {df.shape}", file=sys.stderr)
                            match_all = True
                            for f_idx, fnode in enumerate(filters):
                                print(f"SCAN: Evaluating filter {f_idx+1}/{len(filters)} for {sym}", file=sys.stderr)
                                if not eval_filter(fnode, df, sym, explain_vals, timeframe):
                                    print(f"SCAN: Filter {f_idx+1} failed for {sym}", file=sys.stderr)
                                    match_all = False
                                    break
                            eval_time = time.time() - eval_start
                            elapsed_ms = int((time.time() - symbol_start_time) * 1000)
                            symbol_timings.append((sym, elapsed_ms))
                            print(f"SCAN: Symbol {sym} evaluation completed in {elapsed_ms}ms (fetch: {fetch_time:.3f}s, eval: {eval_time:.3f}s), match: {match_all}", file=sys.stderr)
                            if match_all:
                                result_entry = {
                                    'symbol': sym,
                                    'timestamp': int(pd.Timestamp(df.index[-1]).timestamp())
                                }
                                if explain_vals:
                                    result_entry['values'] = explain_vals
                                    result_entry['explain'] = explain_vals
                                if options.get('includeExplain', False):
                                    result_entry['timingMs'] = elapsed_ms
                                results.append(result_entry)
                        # Emit progress periodically
                        now = time.time()
                        if (now - last_progress_ts) >= 0.5 or (scanned % 50 == 0):
                            try:
                                print(json.dumps({
                                    'type': 'scan-progress',
                                    'requestId': request_id,
                                    'phase': 'running',
                                    'scanned': scanned,
                                    'totalSymbols': len(symbols_list)
                                }), flush=True)
                            except Exception:
                                pass
                            last_progress_ts = now
                
                # Print scan summary
                total_scan_time = time.time() - scan_start_time
                avg_time_per_symbol = total_scan_time / scanned if scanned > 0 else 0
                print(f"SCAN: Summary - Total time: {total_scan_time:.2f}s, Symbols processed: {scanned}, Results: {len(results)}, Avg time per symbol: {avg_time_per_symbol:.3f}s", file=sys.stderr)
                
                # Print timing statistics for slowest symbols
                if symbol_timings:
                    symbol_timings.sort(key=lambda x: x[1], reverse=True)
                    print(f"SCAN: Slowest symbols: {symbol_timings[:5]}", file=sys.stderr)
                
                # Phase 4: Add sorting and pagination support
                # Support both nested and flat formats: {'sort': {'by': 'x', 'order': 'y'}} or {'sortBy': 'x', 'sortOrder': 'y'}
                sort_config = options.get('sort', {})
                sort_by = sort_config.get('by') if sort_config else options.get('sortBy', 'symbol')  # 'symbol' | 'timestamp'
                sort_order = sort_config.get('order') if sort_config else options.get('sortOrder', 'asc')  # 'asc' | 'desc'
                
                if sort_by == 'symbol':
                    results.sort(key=lambda r: r['symbol'], reverse=(sort_order == 'desc'))
                elif sort_by == 'timestamp':
                    results.sort(key=lambda r: r['timestamp'], reverse=(sort_order == 'desc'))
                
                # Apply pagination
                offset = options.get('offset', 0)
                limit = options.get('limit', 5000)
                if is_backtest:
                    total_matches = sum((len(r.get('matches', [])) for r in results))
                else:
                    total_matches = len(results)
                results = results[offset:offset + limit] if limit > 0 else results[offset:]

                # Prepare optional slowest symbols stats when includeExplain is enabled
                extra_stats = {}
                if options.get('includeExplain', False) and symbol_timings:
                    try:
                        sorted_timings = sorted(symbol_timings, key=lambda x: x[1], reverse=True)
                        extra_stats['slowestSymbols'] = [
                            {'symbol': s, 'timingMs': ms} for s, ms in sorted_timings[:10]
                        ]
                    except Exception:
                        pass

                stats_base = {
                    'scannedSymbols': scanned,
                    'timeMs': int((time.time() - t0) * 1000),
                    **extra_stats
                }
                if is_backtest:
                    resp = {
                        'results': results,
                        'stats': {
                            **stats_base,
                            'mode': 'backtest',
                            'totalMatchBars': total_matches,
                            'returnedSymbols': len(results)
                        },
                        'requestId': request_id
                    }
                else:
                    resp = {
                        'results': results,
                        'stats': {
                            **stats_base,
                            'totalMatches': total_matches,
                            'returnedMatches': len(results)
                        },
                        'requestId': request_id
                    }
                # Emit done event
                try:
                    done_msg = {
                        'type': 'scan-progress',
                        'requestId': request_id,
                        'phase': 'done',
                        'scanned': scanned,
                        'totalSymbols': len(symbols_list),
                        'matches': total_matches
                    }
                    done_json = json.dumps(done_msg)
                    print(done_json, flush=True)
                    print(f"SCAN: Done event emitted, {len(done_json)} bytes", file=sys.stderr)
                except Exception as e:
                    print(f"SCAN: Failed to emit done event: {type(e).__name__}: {e}", file=sys.stderr)
                    import traceback
                    print(f"SCAN: Traceback: {traceback.format_exc()}", file=sys.stderr)
                
                print(f"SCAN: done requestId={request_id}, scanned={scanned}, matches={total_matches}, timeMs={resp['stats']['timeMs']}", file=sys.stderr)
                print(f"SCAN: About to serialize response for return", file=sys.stderr)
                try:
                    resp_json = json.dumps(resp)
                    print(f"SCAN: Response serialization successful, {len(resp_json)} bytes", file=sys.stderr)
                except Exception as e:
                    print(f"SCAN: CRITICAL - Failed to serialize response: {type(e).__name__}: {e}", file=sys.stderr)
                    print(f"SCAN: resp type={type(resp)}, keys={list(resp.keys()) if isinstance(resp, dict) else 'N/A'}", file=sys.stderr)
                    import traceback
                    print(f"SCAN: Traceback: {traceback.format_exc()}", file=sys.stderr)
                    # Return error response instead
                    resp = {'error': f'Failed to serialize response: {e}', 'requestId': request_id}
                return resp
            except Exception as e:
                return {
                    'error': f'run-scan failed: {str(e)}',
                    'requestId': request_id
                }
        elif request.get('action') == 'run-backtest':
            # Phase 5A: Signal generation via existing evaluator (reuse run-scan in backtest mode)
            t0 = time.time()
            try:
                data = request.get('data', {}) or {}
                print(f"BACKTEST: Received data keys: {list(data.keys())}", file=sys.stderr)

                # Extract inputs (single symbol for Phase 5A)
                symbol = (data.get('symbol') or '').strip()
                if not symbol:
                    return {'error': 'symbol is required', 'requestId': request_id}

                # Allow timeframe override in payload, else derive from scanner_spec
                scanner_spec_in = data.get('scanner_spec') or data.get('scannerSpec') or data.get('spec') or {}
                if not isinstance(scanner_spec_in, dict):
                    return {'error': 'scanner_spec must be an object', 'requestId': request_id}

                timeframe = str(data.get('timeframe') or scanner_spec_in.get('timeframe') or '1D').upper()
                supported_timeframes = ['1D', '5M', '15M', '1H', '1HOUR']
                if timeframe not in supported_timeframes:
                    return {
                        'error': f"Unsupported timeframe '{timeframe}'. Supported: {', '.join(supported_timeframes)}",
                        'requestId': request_id
                    }
                if timeframe == '1HOUR':
                    timeframe = '1H'

                # Date filters (optional)
                start_date = data.get('start_date') or data.get('dateFrom')
                end_date = data.get('end_date') or data.get('dateTo')

                # Build a nested run-scan request in backtest mode, limited to the single symbol
                nested_spec = dict(scanner_spec_in)
                nested_spec['timeframe'] = timeframe
                nested_spec['universe'] = [symbol]
                nested_options = {
                    'latestOnly': False,
                    'mode': 'backtest',
                }
                if start_date:
                    nested_options['dateFrom'] = start_date
                if end_date:
                    nested_options['dateTo'] = end_date

                nested_req = {
                    'action': 'run-scan',
                    'data': {
                        'scannerSpec': nested_spec,
                        'options': nested_options
                    },
                    'requestId': f"{request_id}-scan"
                }
                print(f"BACKTEST: Invoking nested run-scan for symbol={symbol}, timeframe={timeframe}", file=sys.stderr)
                scan_res = handle_request(nested_req, db_service_override=current_db_service)
                if scan_res.get('error'):
                    return {'error': f"run-scan failed inside run-backtest: {scan_res.get('error')}", 'requestId': request_id}

                # Extract match timestamps for our symbol
                raw_results = scan_res.get('results') or []
                match_entry = None
                for r in raw_results:
                    if r.get('symbol') == symbol:
                        match_entry = r
                        break
                match_ts = []
                if match_entry:
                    # backtest mode returns either {symbol, matches:[{timestamp}]} or similar
                    if isinstance(match_entry.get('matches'), list):
                        match_ts = [m.get('timestamp') for m in match_entry.get('matches') if isinstance(m, dict) and 'timestamp' in m]
                    elif 'timestamp' in match_entry:
                        match_ts = [match_entry.get('timestamp')]

                # Fetch OHLCV for the symbol to annotate prices for the signals
                def fetch_prices_for_symbol(sym: str, tf: str) -> pd.DataFrame:
                    try:
                        with sqlite3.connect(current_db_service.market_db_path) as conn:
                            where = "symbol = ?"
                            params: list = [sym]
                            if tf == '1D':
                                if start_date:
                                    where += " AND timestamp >= ?"
                                    dt = int(time.mktime(datetime.datetime.strptime(start_date, '%Y-%m-%d').timetuple()))
                                    params.append(dt)
                                if end_date:
                                    where += " AND timestamp <= ?"
                                    dt = int(time.mktime(datetime.datetime.strptime(end_date, '%Y-%m-%d').timetuple())) + 86399
                                    params.append(dt)
                                cap = 20000
                                cursor = conn.execute(
                                    f"SELECT timestamp, open, high, low, close, volume FROM price_data WHERE {where} ORDER BY timestamp ASC LIMIT ?",
                                    tuple(params + [cap])
                                )
                                rows = cursor.fetchall()
                            else:
                                where = "symbol = ? AND timeframe = ?"
                                params2: list = [sym, tf]
                                if start_date:
                                    where += " AND timestamp >= ?"
                                    dt = int(time.mktime(datetime.datetime.strptime(start_date, '%Y-%m-%d').timetuple()))
                                    params2.append(dt)
                                if end_date:
                                    where += " AND timestamp <= ?"
                                    dt = int(time.mktime(datetime.datetime.strptime(end_date, '%Y-%m-%d').timetuple())) + 86399
                                    params2.append(dt)
                                cap = 50000
                                cursor = conn.execute(
                                    f"SELECT timestamp, open, high, low, close, volume FROM ohlcv_intraday WHERE {where} ORDER BY timestamp ASC LIMIT ?",
                                    tuple(params2 + [cap])
                                )
                                rows = cursor.fetchall()
                        if not rows:
                            return pd.DataFrame()
                        dfp = pd.DataFrame(rows, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                        dfp = dfp.set_index(pd.to_datetime(dfp['timestamp'], unit='s'))
                        return dfp
                    except Exception as e:
                        print(f"BACKTEST: fetch_prices_for_symbol failed for {sym}: {e}", file=sys.stderr)
                        return pd.DataFrame()

                df_prices = fetch_prices_for_symbol(symbol, timeframe)
                entries = []
                if not df_prices.empty and match_ts:
                    # Build a map from timestamp to close price
                    ts_set = set(int(ts) for ts in match_ts if isinstance(ts, (int, float)))
                    if len(ts_set) > 0:
                        # Align by converting index to epoch seconds
                        idx_seconds = df_prices.index.view('int64') // 10**9
                        ts_to_close = dict(zip(idx_seconds.tolist(), df_prices['close'].astype(float).tolist()))
                        for ts in sorted(ts_set):
                            price = ts_to_close.get(int(ts))
                            if price is not None:
                                entries.append({'timestamp': int(ts), 'price': float(price)})

                # Mode control: 'signals' (default) or 'simulate' to produce trades using trade_simulator
                mode = str(data.get('mode') or 'signals').lower()
                backtest_config = data.get('backtest_config') or {}

                if mode == 'simulate':
                    try:
                        from backend.trade_simulator import derive_rising_entries, simulate_long_only  # type: ignore
                    except Exception as e:
                        return {'error': f'Failed to import trade_simulator: {e}', 'requestId': request_id}
                    # Derive rising-edge entries and simulate
                    rising_entries = []
                    if not df_prices.empty and match_ts:
                        try:
                            rising_entries = derive_rising_entries(df_prices.index, match_ts)
                        except Exception as e:
                            print(f"BACKTEST: derive_rising_entries failed: {e}", file=sys.stderr)
                            rising_entries = [int(x) for x in match_ts]
                    trades = []
                    try:
                        trades = simulate_long_only(df_prices, symbol, rising_entries, backtest_config)
                    except Exception as e:
                        print(f"BACKTEST: simulate_long_only failed: {e}", file=sys.stderr)
                        trades = []
                    # Analytics: metrics + equity curve
                    metrics = {}
                    equity_curve = {'timestamps': [], 'equity': []}
                    try:
                        from backend.backtest_analytics import calculate_metrics, build_equity_curve  # type: ignore
                        metrics = calculate_metrics(trades, float(backtest_config.get('initial_capital', 10000.0)), df_prices.index, timeframe)
                        ts_list, eq = build_equity_curve(trades, float(backtest_config.get('initial_capital', 10000.0)), df_prices.index)
                        equity_curve = {'timestamps': ts_list, 'equity': eq}
                    except Exception as e:
                        print(f"BACKTEST: analytics failed: {e}", file=sys.stderr)
                        metrics = {}

                    resp = {
                        'signals': {
                            'symbol': symbol,
                            'timeframe': timeframe,
                            'priceField': 'close',
                            'entries': entries,
                            'count': len(entries),
                            'seriesLength': int(len(df_prices)) if isinstance(df_prices, pd.DataFrame) else 0
                        },
                        'trades': trades,
                        'metrics': metrics,
                        'equity_curve': equity_curve,
                        'tradeCount': len(trades),
                        'stats': {
                            'timeMs': int((time.time() - t0) * 1000),
                            'requestType': 'simulate'
                        },
                        'requestId': request_id
                    }
                    print(f"BACKTEST: Completed simulate mode for {symbol}, entries={len(entries)}, trades={len(trades)}, timeMs={resp['stats']['timeMs']}", file=sys.stderr)
                    return resp
                else:
                    resp = {
                        'signals': {
                            'symbol': symbol,
                            'timeframe': timeframe,
                            'priceField': 'close',
                            'entries': entries,
                            'count': len(entries),
                            'seriesLength': int(len(df_prices)) if isinstance(df_prices, pd.DataFrame) else 0
                        },
                        'stats': {
                            'timeMs': int((time.time() - t0) * 1000),
                            'requestType': 'signals-only'
                        },
                        'requestId': request_id
                    }
                    print(f"BACKTEST: Completed Phase 5A for {symbol}, entries={len(entries)}, timeMs={resp['stats']['timeMs']}", file=sys.stderr)
                    return resp
            except Exception as e:
                return {'error': f'run-backtest failed: {e}', 'requestId': request_id}
        
        elif request.get('action') == 'optimize-backtest':
            # Phase 6: Parameter Optimization - Grid search over parameter ranges
            t0 = time.time()
            try:
                from backend.parameter_optimizer import (  # type: ignore
                    generate_parameter_grid,
                    generate_random_parameters,
                    apply_parameters_to_spec,
                    rank_results,
                    extract_best_parameters,
                    calculate_optimization_stats,
                    validate_parameter_ranges
                )
                
                data = request.get('data', {}) or {}
                scanner_spec = data.get('scannerSpec') or {}
                param_ranges = data.get('parameterRanges') or {}
                symbol = data.get('symbol') or 'AAPL'
                timeframe = str(scanner_spec.get('timeframe', '1D')).upper()
                backtest_config = data.get('backtestConfig') or {}
                optimization_config = data.get('optimizationConfig') or {}
                
                # Validate parameter ranges
                is_valid, error_msg = validate_parameter_ranges(param_ranges)
                if not is_valid:
                    return {'error': error_msg, 'requestId': request_id}
                
                # Generate parameter combinations
                search_mode = optimization_config.get('searchMode', 'grid')
                if search_mode == 'random':
                    n_samples = int(optimization_config.get('randomSamples', 100))
                    seed = optimization_config.get('randomSeed')
                    param_combinations = generate_random_parameters(param_ranges, n_samples, seed)
                else:
                    param_combinations = generate_parameter_grid(param_ranges)
                
                print(f"OPTIMIZE: Starting optimization with {len(param_combinations)} parameter combinations", file=sys.stderr)
                
                # Run backtest for each parameter combination
                results = []
                for idx, params in enumerate(param_combinations):
                    try:
                        # Apply parameters to spec
                        parameterized_spec = apply_parameters_to_spec(scanner_spec, params)
                        
                        # Create a mini backtest request
                        backtest_request = {
                            'action': 'run-backtest',
                            'requestId': f"{request_id}_opt_{idx}",
                            'data': {
                                'scannerSpec': parameterized_spec,
                                'symbol': symbol,
                                'backtestConfig': backtest_config,
                                'mode': 'simulate'
                            }
                        }
                        
                        # Run backtest
                        backtest_response = handle_request(backtest_request, db_service_override=current_db_service)
                        
                        if 'error' not in backtest_response:
                            results.append({
                                'parameters': params,
                                'metrics': backtest_response.get('metrics', {}),
                                'tradeCount': backtest_response.get('tradeCount', 0),
                                'stats': backtest_response.get('stats', {})
                            })
                        
                        # Progress reporting (every 10%)
                        if (idx + 1) % max(1, len(param_combinations) // 10) == 0:
                            progress = int(((idx + 1) / len(param_combinations)) * 100)
                            print(f"OPTIMIZE: Progress {progress}% ({idx + 1}/{len(param_combinations)})", file=sys.stderr)
                    
                    except Exception as e:
                        print(f"OPTIMIZE: Failed for params {params}: {e}", file=sys.stderr)
                        continue
                
                # Rank results
                rank_metric = optimization_config.get('rankMetric', 'sharpe_ratio')
                ranked_results = rank_results(results, metric=rank_metric, ascending=False)
                
                # Extract best parameters
                top_n = int(optimization_config.get('topN', 10))
                best_params = extract_best_parameters(ranked_results, metric=rank_metric, top_n=top_n)
                
                # Calculate stats
                stats = calculate_optimization_stats(results, metric=rank_metric)
                
                elapsed_ms = int((time.time() - t0) * 1000)
                print(f"OPTIMIZE: Completed {len(results)} backtests in {elapsed_ms}ms", file=sys.stderr)
                
                return {
                    'results': ranked_results,
                    'bestParameters': best_params,
                    'statistics': stats,
                    'totalCombinations': len(param_combinations),
                    'successfulRuns': len(results),
                    'stats': {
                        'timeMs': elapsed_ms,
                        'searchMode': search_mode,
                        'rankMetric': rank_metric
                    },
                    'requestId': request_id
                }
            
            except Exception as e:
                import traceback
                print(f"OPTIMIZE: Error: {e}\n{traceback.format_exc()}", file=sys.stderr)
                return {'error': f'optimize-backtest failed: {e}', 'requestId': request_id}
        
        elif request.get('action') == 'run-portfolio-backtest':
            # Phase 8: Portfolio Management - Multi-symbol backtests with correlation analysis
            t0 = time.time()
            try:
                from backend.portfolio_manager import (  # type: ignore
                    calculate_portfolio_weights,
                    build_portfolio_equity_curve,
                    calculate_portfolio_metrics,
                    build_correlation_matrix_from_trades,
                    aggregate_trades_by_symbol,
                    calculate_diversification_ratio
                )
                
                data = request.get('data', {}) or {}
                scanner_spec = data.get('scannerSpec') or {}
                symbols = data.get('symbols') or []
                timeframe = str(scanner_spec.get('timeframe', '1D')).upper()
                backtest_config = data.get('backtestConfig') or {}
                portfolio_config = data.get('portfolioConfig') or {}
                
                if not symbols:
                    return {'error': 'At least one symbol required', 'requestId': request_id}
                
                print(f"PORTFOLIO: Running backtest for {len(symbols)} symbols: {symbols}", file=sys.stderr)
                
                # Calculate portfolio weights
                allocation_mode = portfolio_config.get('allocationMode', 'equal')
                custom_weights = portfolio_config.get('customWeights', {})
                weights = calculate_portfolio_weights(allocation_mode, symbols, custom_weights)
                
                # Run backtest for each symbol
                symbol_trades = {}
                symbol_metrics = {}
                all_indices = None
                errors_by_symbol = {}
                
                for symbol in symbols:
                    try:
                        print(f"PORTFOLIO: Running backtest for {symbol}", file=sys.stderr)
                        # Create backtest request for this symbol
                        backtest_request = {
                            'action': 'run-backtest',
                            'requestId': f"{request_id}_portfolio_{symbol}",
                            'data': {
                                'scannerSpec': scanner_spec,
                                'symbol': symbol,
                                'backtestConfig': backtest_config,
                                'mode': 'simulate'
                            }
                        }
                        
                        # Run backtest
                        backtest_response = handle_request(backtest_request, db_service_override=current_db_service)
                        
                        if 'error' not in backtest_response:
                            symbol_trades[symbol] = backtest_response.get('trades', [])
                            symbol_metrics[symbol] = backtest_response.get('metrics', {})
                            print(f"PORTFOLIO: Success for {symbol}: {len(symbol_trades[symbol])} trades", file=sys.stderr)
                            
                            # Store index from first successful backtest
                            if all_indices is None:
                                # Reconstruct index from signals or use a default range
                                signals = backtest_response.get('signals', {})
                                series_length = signals.get('seriesLength', 252)
                                all_indices = pd.date_range('2023-01-01', periods=series_length, freq='D')
                        else:
                            err_msg = backtest_response.get('error', 'Unknown error')
                            errors_by_symbol[symbol] = err_msg
                            print(f"PORTFOLIO: Skipping {symbol}: {err_msg}", file=sys.stderr)
                    
                    except Exception as e:
                        errors_by_symbol[symbol] = str(e)
                        print(f"PORTFOLIO: Error for {symbol}: {e}", file=sys.stderr)
                        continue
                
                if not symbol_trades:
                    error_details = '\n'.join([f"{s}: {e}" for s, e in errors_by_symbol.items()])
                    error_msg = f'No successful backtests for any symbol. Details:\n{error_details}'
                    print(f"PORTFOLIO: {error_msg}", file=sys.stderr)
                    return {'error': error_msg, 'requestId': request_id}
                
                if all_indices is None:
                    all_indices = pd.date_range('2023-01-01', periods=252, freq='D')
                
                # Build portfolio equity curve
                initial_capital = float(backtest_config.get('initial_capital', 10000.0))
                ts_list, portfolio_equity, symbol_equities = build_portfolio_equity_curve(
                    symbol_trades,
                    weights,
                    initial_capital,
                    all_indices
                )
                
                # Calculate portfolio metrics
                portfolio_metrics = calculate_portfolio_metrics(
                    portfolio_equity,
                    symbol_trades,
                    initial_capital,
                    all_indices,
                    timeframe
                )
                
                # Build correlation matrix
                correlation_matrix = build_correlation_matrix_from_trades(symbol_trades, all_indices)
                
                # Calculate diversification ratio
                # Build returns DataFrame for diversification calc
                returns_data = {}
                for symbol, equity in symbol_equities.items():
                    returns = [(equity[i] - equity[i-1]) / equity[i-1] if equity[i-1] else 0 
                              for i in range(1, len(equity))]
                    returns_data[symbol] = returns
                
                if returns_data:
                    returns_df = pd.DataFrame(returns_data)
                    div_ratio = calculate_diversification_ratio(weights, returns_df)
                else:
                    div_ratio = 1.0
                
                elapsed_ms = int((time.time() - t0) * 1000)
                print(f"PORTFOLIO: Completed in {elapsed_ms}ms", file=sys.stderr)
                
                return {
                    'portfolioMetrics': portfolio_metrics,
                    'symbolMetrics': symbol_metrics,
                    'weights': weights,
                    'portfolioEquityCurve': {
                        'timestamps': ts_list,
                        'equity': portfolio_equity
                    },
                    'symbolEquityCurves': {
                        symbol: {'timestamps': ts_list, 'equity': equity}
                        for symbol, equity in symbol_equities.items()
                    },
                    'symbolTrades': symbol_trades,
                    'correlationMatrix': correlation_matrix.to_dict() if not correlation_matrix.empty else {},
                    'diversificationRatio': round(div_ratio, 4),
                    'stats': {
                        'timeMs': elapsed_ms,
                        'symbolsCount': len(symbol_trades),
                        'totalTrades': sum(len(trades) for trades in symbol_trades.values())
                    },
                    'requestId': request_id
                }
            
            except Exception as e:
                import traceback
                print(f"PORTFOLIO: Error: {e}\n{traceback.format_exc()}", file=sys.stderr)
                return {'error': f'run-portfolio-backtest failed: {e}', 'requestId': request_id}
        
        elif request.get('action') == 'run-walk-forward':
            # Walk-Forward Analysis: Run backtests on multiple time windows
            t0 = time.time()
            try:
                from backend.parameter_optimizer import split_data_for_walk_forward  # type: ignore
                
                data = request.get('data', {}) or {}
                scanner_spec = data.get('scannerSpec') or {}
                symbol = data.get('symbol')
                backtest_config = data.get('backtestConfig') or {}
                walk_forward_config = data.get('walkForwardConfig') or {}
                
                if not symbol:
                    return {'error': 'Symbol required for walk-forward analysis', 'requestId': request_id}
                
                # Get walk-forward parameters
                start_date = walk_forward_config.get('startDate', '2020-01-01')
                end_date = walk_forward_config.get('endDate', '2023-12-31')
                in_sample_days = walk_forward_config.get('inSampleDays', 180)
                out_sample_days = walk_forward_config.get('outSampleDays', 60)
                step_days = walk_forward_config.get('stepDays', 30)
                
                # Generate date windows
                windows = split_data_for_walk_forward(
                    start_date,
                    end_date,
                    in_sample_days,
                    out_sample_days,
                    step_days
                )
                
                print(f"WALK-FORWARD: Generated {len(windows)} windows for {symbol}", file=sys.stderr)
                
                # Run backtest for each window
                window_results = []
                for idx, (in_start, in_end, out_start, out_end) in enumerate(windows):
                    print(f"WALK-FORWARD: Processing window {idx + 1}/{len(windows)}", file=sys.stderr)
                    
                    # In-sample backtest (training)
                    in_sample_request = {
                        'action': 'run-backtest',
                        'requestId': f"{request_id}_wf_{idx}_in",
                        'data': {
                            'scannerSpec': scanner_spec,
                            'symbol': symbol,
                            'backtestConfig': {
                                **backtest_config,
                                'start_date': in_start,
                                'end_date': in_end
                            },
                            'mode': 'simulate'
                        }
                    }
                    in_sample_result = handle_request(in_sample_request, db_service_override=current_db_service)
                    
                    # Out-of-sample backtest (testing)
                    out_sample_request = {
                        'action': 'run-backtest',
                        'requestId': f"{request_id}_wf_{idx}_out",
                        'data': {
                            'scannerSpec': scanner_spec,
                            'symbol': symbol,
                            'backtestConfig': {
                                **backtest_config,
                                'start_date': out_start,
                                'end_date': out_end
                            },
                            'mode': 'simulate'
                        }
                    }
                    out_sample_result = handle_request(out_sample_request, db_service_override=current_db_service)
                    
                    # Collect results
                    window_results.append({
                        'windowIndex': idx,
                        'inSample': {
                            'startDate': in_start,
                            'endDate': in_end,
                            'metrics': in_sample_result.get('metrics', {}),
                            'trades': len(in_sample_result.get('trades', []))
                        },
                        'outSample': {
                            'startDate': out_start,
                            'endDate': out_end,
                            'metrics': out_sample_result.get('metrics', {}),
                            'trades': len(out_sample_result.get('trades', []))
                        }
                    })
                
                elapsed_ms = int((time.time() - t0) * 1000)
                
                # Calculate aggregate statistics
                in_sample_returns = [w['inSample']['metrics'].get('totalReturn', 0) for w in window_results]
                out_sample_returns = [w['outSample']['metrics'].get('totalReturn', 0) for w in window_results]
                
                return {
                    'symbol': symbol,
                    'windows': window_results,
                    'summary': {
                        'totalWindows': len(windows),
                        'inSample': {
                            'avgReturn': sum(in_sample_returns) / len(in_sample_returns) if in_sample_returns else 0,
                            'avgSharpe': sum(w['inSample']['metrics'].get('sharpeRatio', 0) for w in window_results) / len(window_results) if window_results else 0,
                            'winRate': sum(1 for r in in_sample_returns if r > 0) / len(in_sample_returns) if in_sample_returns else 0
                        },
                        'outSample': {
                            'avgReturn': sum(out_sample_returns) / len(out_sample_returns) if out_sample_returns else 0,
                            'avgSharpe': sum(w['outSample']['metrics'].get('sharpeRatio', 0) for w in window_results) / len(window_results) if window_results else 0,
                            'winRate': sum(1 for r in out_sample_returns if r > 0) / len(out_sample_returns) if out_sample_returns else 0
                        }
                    },
                    'stats': {
                        'timeMs': elapsed_ms
                    },
                    'requestId': request_id
                }
            
            except Exception as e:
                import traceback
                print(f"WALK-FORWARD: Error: {e}\n{traceback.format_exc()}", file=sys.stderr)
                return {'error': f'run-walk-forward failed: {e}', 'requestId': request_id}
        
        # Backup & Recovery Actions
        elif action == 'create-backup':
            try:
                data = request.get('data', {})
                backup_type = data.get('backupType', 'manual')
                
                backup_mgr = BackupManager()
                result = backup_mgr.create_backup(backup_type=backup_type)
                result['requestId'] = request_id
                
                return result
            
            except Exception as e:
                import traceback
                print(f"BACKUP: Error creating backup: {e}\n{traceback.format_exc()}", file=sys.stderr)
                return {'error': f'create-backup failed: {e}', 'requestId': request_id}
        
        elif action == 'list-backups':
            try:
                backup_mgr = BackupManager()
                backups = backup_mgr.list_backups()
                
                return {
                    'backups': backups,
                    'requestId': request_id
                }
            
            except Exception as e:
                import traceback
                print(f"BACKUP: Error listing backups: {e}\n{traceback.format_exc()}", file=sys.stderr)
                return {'error': f'list-backups failed: {e}', 'requestId': request_id}
        
        elif action == 'verify-backup':
            try:
                data = request.get('data', {})
                backup_name = data.get('backupName')
                
                if not backup_name:
                    return {'error': 'backupName required', 'requestId': request_id}
                
                backup_mgr = BackupManager()
                result = backup_mgr.verify_backup(backup_name)
                result['requestId'] = request_id
                
                return result
            
            except Exception as e:
                import traceback
                print(f"BACKUP: Error verifying backup: {e}\n{traceback.format_exc()}", file=sys.stderr)
                return {'error': f'verify-backup failed: {e}', 'requestId': request_id}
        
        elif action == 'restore-backup':
            try:
                data = request.get('data', {})
                backup_name = data.get('backupName')
                
                if not backup_name:
                    return {'error': 'backupName required', 'requestId': request_id}
                
                backup_mgr = BackupManager()
                result = backup_mgr.restore_backup(backup_name)
                result['requestId'] = request_id
                
                return result
            
            except Exception as e:
                import traceback
                print(f"BACKUP: Error restoring backup: {e}\n{traceback.format_exc()}", file=sys.stderr)
                return {'error': f'restore-backup failed: {e}', 'requestId': request_id}
        
        elif action == 'delete-backup':
            try:
                data = request.get('data', {})
                backup_name = data.get('backupName')
                
                if not backup_name:
                    return {'error': 'backupName required', 'requestId': request_id}
                
                backup_mgr = BackupManager()
                result = backup_mgr.delete_backup(backup_name)
                result['requestId'] = request_id
                
                return result
            
            except Exception as e:
                import traceback
                print(f"BACKUP: Error deleting backup: {e}\n{traceback.format_exc()}", file=sys.stderr)
                return {'error': f'delete-backup failed: {e}', 'requestId': request_id}
        
        elif action == 'get-backup-stats':
            try:
                backup_mgr = BackupManager()
                stats = backup_mgr.get_backup_statistics()
                stats['requestId'] = request_id
                
                return stats
            
            except Exception as e:
                import traceback
                print(f"BACKUP: Error getting backup stats: {e}\n{traceback.format_exc()}", file=sys.stderr)
                return {'error': f'get-backup-stats failed: {e}', 'requestId': request_id}
        
        elif action == 'check-database-integrity':
            try:
                data = request.get('data', {})
                db_name = data.get('dbName', 'market_data.db')
                
                recovery_mgr = RecoveryManager()
                result = recovery_mgr.check_database_integrity(db_name)
                result['requestId'] = request_id
                
                return result
            
            except Exception as e:
                import traceback
                print(f"RECOVERY: Error checking integrity: {e}\n{traceback.format_exc()}", file=sys.stderr)
                return {'error': f'check-database-integrity failed: {e}', 'requestId': request_id}
        
        elif action == 'check-all-databases':
            try:
                recovery_mgr = RecoveryManager()
                result = recovery_mgr.check_all_databases()
                result['requestId'] = request_id
                
                return result
            
            except Exception as e:
                import traceback
                print(f"RECOVERY: Error checking all databases: {e}\n{traceback.format_exc()}", file=sys.stderr)
                return {'error': f'check-all-databases failed: {e}', 'requestId': request_id}
        
        elif action == 'recover-from-wal':
            try:
                data = request.get('data', {})
                db_name = data.get('dbName', 'market_data.db')
                
                recovery_mgr = RecoveryManager()
                result = recovery_mgr.recover_from_wal(db_name)
                result['requestId'] = request_id
                
                return result
            
            except Exception as e:
                import traceback
                print(f"RECOVERY: Error recovering from WAL: {e}\n{traceback.format_exc()}", file=sys.stderr)
                return {'error': f'recover-from-wal failed: {e}', 'requestId': request_id}
        
        elif action == 'export-database':
            try:
                data = request.get('data', {})
                db_name = data.get('dbName', 'market_data.db')
                export_format = data.get('format', 'sql')
                
                recovery_mgr = RecoveryManager()
                result = recovery_mgr.export_database(db_name, export_format)
                result['requestId'] = request_id
                
                return result
            
            except Exception as e:
                import traceback
                print(f"RECOVERY: Error exporting database: {e}\n{traceback.format_exc()}", file=sys.stderr)
                return {'error': f'export-database failed: {e}', 'requestId': request_id}
        
        elif action == 'get-backup-config':
            try:
                backup_mgr = BackupManager()
                config = backup_mgr.config.copy()
                config['requestId'] = request_id
                
                return config
            
            except Exception as e:
                import traceback
                print(f"BACKUP: Error getting config: {e}\n{traceback.format_exc()}", file=sys.stderr)
                return {'error': f'get-backup-config failed: {e}', 'requestId': request_id}
        
        elif action == 'update-backup-config':
            try:
                data = request.get('data', {})
                
                backup_mgr = BackupManager()
                
                # Update config
                if 'retentionDays' in data:
                    backup_mgr.config['retention_days'] = data['retentionDays']
                if 'maxBackups' in data:
                    backup_mgr.config['max_backups'] = data['maxBackups']
                if 'autoBackupEnabled' in data:
                    backup_mgr.config['auto_backup_enabled'] = data['autoBackupEnabled']
                if 'backupOnStartup' in data:
                    backup_mgr.config['backup_on_startup'] = data['backupOnStartup']
                if 'verifyIntegrity' in data:
                    backup_mgr.config['verify_integrity'] = data['verifyIntegrity']
                
                # Save config
                backup_mgr.save_config()
                
                result = {
                    'success': True,
                    'config': backup_mgr.config,
                    'requestId': request_id
                }
                
                return result
            
            except Exception as e:
                import traceback
                print(f"BACKUP: Error updating config: {e}\n{traceback.format_exc()}", file=sys.stderr)
                return {'error': f'update-backup-config failed: {e}', 'requestId': request_id}
        
        # Phase 1: Enhanced Portfolio Backtest with Position Sizing and Signal Type
        elif action == 'run-enhanced-portfolio-backtest':
            try:
                print(f"PORTFOLIO: Running enhanced portfolio backtest, requestId={request_id}", file=sys.stderr)
                data = request.get('data', {})
                
                # Import required modules
                from backend import portfolio_manager
                
                # Extract configuration
                symbols = data.get('symbols', [])
                if not symbols:
                    return {'error': 'symbols list is required', 'requestId': request_id}
                
                initial_capital = float(data.get('initial_capital', 100000.0))
                
                # Position sizing configuration
                position_sizing_config = data.get('position_sizing_config', {'method': 'equal_weight'})
                
                # Signal type (long or short)
                signal_type = data.get('signal_type', 'long')
                
                # Risk management
                stop_loss_pct = data.get('stop_loss_pct')
                take_profit_pct = data.get('take_profit_pct')
                holding_period_days = data.get('holding_period_days')
                allow_leverage = data.get('allow_leverage', False)
                one_trade_per_instrument = data.get('one_trade_per_instrument', False)
                
                # Get price data and signals from database
                # For now, this is a placeholder - frontend will need to provide signals
                # In a full implementation, signals would come from scanner results
                price_data = {}
                signals = {}
                
                # TODO: Fetch price data from database for each symbol
                # TODO: Generate or retrieve signals for each symbol
                
                print(f"PORTFOLIO: symbols={len(symbols)}, signal_type={signal_type}, method={position_sizing_config.get('method')}", file=sys.stderr)
                
                # Run enhanced backtest
                result = portfolio_manager.run_enhanced_portfolio_backtest(
                    symbols=symbols,
                    price_data=price_data,
                    signals=signals,
                    initial_capital=initial_capital,
                    position_sizing_config=position_sizing_config,
                    signal_type=signal_type,
                    stop_loss_pct=stop_loss_pct,
                    take_profit_pct=take_profit_pct,
                    holding_period_days=holding_period_days,
                    allow_leverage=allow_leverage,
                    one_trade_per_instrument=one_trade_per_instrument
                )
                
                result['requestId'] = request_id
                return result
                
            except Exception as e:
                import traceback
                print(f"PORTFOLIO: Error in enhanced backtest: {e}\n{traceback.format_exc()}", file=sys.stderr)
                return {'error': f'run-enhanced-portfolio-backtest failed: {e}', 'requestId': request_id}
        
        # Phase 1: Monte Carlo Simulation
        elif action == 'run-monte-carlo':
            try:
                print(f"MONTE_CARLO: Running simulation, requestId={request_id}", file=sys.stderr)
                data = request.get('data', {})
                
                from backend.trade_analytics import TradeAnalyzer
                
                # Extract trade returns
                trade_returns = data.get('trade_returns', [])
                if not trade_returns or len(trade_returns) < 10:
                    return {
                        'error': 'Insufficient trades for Monte Carlo (need at least 10)',
                        'requestId': request_id
                    }
                
                # Simulation parameters
                n_simulations = int(data.get('n_simulations', 1000))
                n_trades = int(data.get('n_trades', 50))
                
                # Validate parameters
                if n_simulations < 100 or n_simulations > 10000:
                    return {'error': 'n_simulations must be between 100 and 10000', 'requestId': request_id}
                if n_trades < 10 or n_trades > 500:
                    return {'error': 'n_trades must be between 10 and 500', 'requestId': request_id}
                
                print(f"MONTE_CARLO: n_simulations={n_simulations}, n_trades={n_trades}, trade_returns={len(trade_returns)}", file=sys.stderr)
                
                # Create minimal trade log for analyzer
                trade_log = pd.DataFrame({
                    'pnl_pct': trade_returns
                })
                
                analyzer = TradeAnalyzer(trade_log)
                mc_results = analyzer.run_monte_carlo(
                    n_simulations=n_simulations,
                    n_trades=n_trades
                )
                
                mc_results['requestId'] = request_id
                return mc_results
                
            except Exception as e:
                import traceback
                print(f"MONTE_CARLO: Error in simulation: {e}\n{traceback.format_exc()}", file=sys.stderr)
                return {'error': f'run-monte-carlo failed: {e}', 'requestId': request_id}
        
        # Phase 4: Parameter Optimization
        elif action == 'run-parameter-optimization':
            try:
                print(f"OPTIMIZATION: Starting parameter optimization, requestId={request_id}", file=sys.stderr)
                data = request.get('data', {})
                
                from backend.parameter_optimizer import (
                    generate_parameter_grid,
                    apply_parameters_to_spec,
                    rank_results,
                    extract_best_parameters,
                    calculate_optimization_stats
                )
                from backend.backtest_analytics import run_backtest
                
                # Extract configuration
                scanner_spec = data.get('scannerSpec')
                symbols = data.get('symbols', [])
                base_config = data.get('baseConfig', {})
                param_ranges = data.get('parameterRanges', {})
                optimization_metric = data.get('metric', 'sharpe_ratio')
                top_n = int(data.get('topN', 20))
                
                if not scanner_spec:
                    return {'error': 'Scanner spec is required', 'requestId': request_id}
                if not symbols:
                    return {'error': 'At least one symbol is required', 'requestId': request_id}
                if not param_ranges:
                    return {'error': 'Parameter ranges are required', 'requestId': request_id}
                
                # Generate parameter grid
                print(f"OPTIMIZATION: Generating parameter combinations...", file=sys.stderr)
                parameter_combinations = generate_parameter_grid(param_ranges)
                total_combinations = len(parameter_combinations)
                
                print(f"OPTIMIZATION: Running {total_combinations} backtests...", file=sys.stderr)
                
                # Run backtests for each parameter combination
                all_results = []
                successful_runs = 0
                
                for idx, params in enumerate(parameter_combinations):
                    try:
                        # Apply parameters to scanner spec
                        parameterized_spec = apply_parameters_to_spec(scanner_spec, params)
                        
                        # Merge with base config
                        backtest_config = {**base_config, **params}
                        
                        # Run backtest (simplified - single symbol for now)
                        symbol = symbols[0] if len(symbols) == 1 else None
                        if not symbol:
                            # For multi-symbol, we'd need portfolio backtest integration
                            print(f"OPTIMIZATION: Multi-symbol optimization not yet implemented", file=sys.stderr)
                            continue
                        
                        # Run single backtest
                        result = run_backtest(
                            scanner_spec=parameterized_spec,
                            symbol=symbol,
                            initial_capital=backtest_config.get('initial_capital', 100000),
                            position_size_pct=backtest_config.get('position_size_pct', 10),
                            commission=backtest_config.get('commission', 0.001),
                            slippage=backtest_config.get('slippage', 0.001)
                        )
                        
                        if not result.get('error'):
                            metrics = result.get('metrics', {})
                            all_results.append({
                                'parameters': params,
                                'metrics': metrics,
                                'trades': result.get('trades', [])
                            })
                            successful_runs += 1
                        
                        # Progress update (every 10 runs or at milestones)
                        if (idx + 1) % 10 == 0 or (idx + 1) == total_combinations:
                            progress_pct = ((idx + 1) / total_combinations) * 100
                            print(f"OPTIMIZATION: Progress {idx + 1}/{total_combinations} ({progress_pct:.1f}%)", file=sys.stderr)
                    
                    except Exception as e:
                        print(f"OPTIMIZATION: Error in combination {idx + 1}: {e}", file=sys.stderr)
                        continue
                
                if not all_results:
                    return {
                        'error': 'No successful backtest runs',
                        'requestId': request_id
                    }
                
                # Rank results by optimization metric
                ranked_results = rank_results(all_results, metric=optimization_metric, ascending=False)
                
                # Get top N results
                top_results = extract_best_parameters(ranked_results, metric=optimization_metric, top_n=top_n)
                
                # Calculate statistics
                stats = calculate_optimization_stats(ranked_results, metric=optimization_metric)
                
                print(f"OPTIMIZATION: Complete. {successful_runs}/{total_combinations} successful runs", file=sys.stderr)
                
                return {
                    'topResults': top_results,
                    'allResults': ranked_results[:50],  # Limit to 50 for performance
                    'stats': stats,
                    'totalCombinations': total_combinations,
                    'successfulRuns': successful_runs,
                    'requestId': request_id
                }
                
            except Exception as e:
                import traceback
                print(f"OPTIMIZATION: Error: {e}\n{traceback.format_exc()}", file=sys.stderr)
                return {'error': f'run-parameter-optimization failed: {e}', 'requestId': request_id}
        
        # Phase 1: Get Trade Analytics
        elif action == 'get-trade-analytics':
            try:
                print(f"ANALYTICS: Getting trade analytics, requestId={request_id}", file=sys.stderr)
                data = request.get('data', {})
                
                from backend.trade_analytics import TradeAnalyzer
                
                # Extract trade log
                trades = data.get('trades', [])
                if not trades:
                    return {
                        'error': 'No trades provided',
                        'requestId': request_id
                    }
                
                initial_capital = float(data.get('initial_capital', 100000.0))
                
                # Convert to DataFrame
                trade_log = pd.DataFrame(trades)
                
                # Ensure required columns exist
                required_columns = ['pnl', 'pnl_pct']
                missing_columns = [col for col in required_columns if col not in trade_log.columns]
                if missing_columns:
                    return {
                        'error': f'Missing required columns in trade log: {missing_columns}',
                        'requestId': request_id
                    }
                
                print(f"ANALYTICS: Analyzing {len(trades)} trades", file=sys.stderr)
                
                # Run analytics
                analyzer = TradeAnalyzer(trade_log)
                
                result = {
                    'metrics': analyzer.calculate_performance_metrics(initial_capital),
                    'exit_reasons': analyzer.analyze_exit_reasons(),
                    'holding_periods': analyzer.analyze_holding_periods(),
                    'pl_distribution': analyzer.analyze_pl_distribution(),
                    'pl_timeline': analyzer.get_pl_timeline(),
                    'leverage_metrics': analyzer.calculate_leverage_metrics(initial_capital),
                    'invested_capital_timeline': analyzer.calculate_invested_value_timeline(initial_capital),
                    'requestId': request_id
                }
                
                return result
                
            except Exception as e:
                import traceback
                print(f"ANALYTICS: Error in analysis: {e}\n{traceback.format_exc()}", file=sys.stderr)
                return {'error': f'get-trade-analytics failed: {e}', 'requestId': request_id}
        
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
                    print(f"MAIN: Raw input line received: {len(line)} bytes", file=sys.stderr)
                    request = json.loads(line.strip())
                    print(f"MAIN: Processing request with action={request.get('action')}, requestId={request.get('requestId')}", file=sys.stderr)
                    response = handle_request(request)
                    print(f"MAIN: Got response type={type(response)}, hasKeys={isinstance(response, dict)}", file=sys.stderr)
                    if isinstance(response, dict):
                        print(f"MAIN: Response keys={list(response.keys())}, requestId={response.get('requestId')}", file=sys.stderr)
                    response_json = json.dumps(response)
                    print(f"MAIN: JSON serialization successful, length={len(response_json)} bytes", file=sys.stderr)
                    print(response_json, flush=True)
                    print(f"MAIN: Response printed successfully to stdout", file=sys.stderr)
                except json.JSONDecodeError as e:
                    print(f"MAIN: JSONDecodeError: {e}", file=sys.stderr)
                    print(json.dumps({'error': f'Invalid JSON: {e}'}), flush=True)
                except Exception as e:
                    print(f"MAIN: Exception in request handling: {type(e).__name__}: {e}", file=sys.stderr)
                    import traceback
                    print(f"MAIN: Traceback: {traceback.format_exc()}", file=sys.stderr)
                    print(json.dumps({'error': f'Processing error: {e}'}), flush=True)
    except KeyboardInterrupt:
        print("Python backend shutting down", flush=True)
    except Exception as e:
        print(f"MAIN: Fatal error: {type(e).__name__}: {e}", file=sys.stderr)
        print(json.dumps({'error': f'Fatal error: {e}'}), flush=True)

if __name__ == '__main__':
    main()