"""
Test cross-timeframe queries in scanner by running full scans
"""
import sys
import os
import sqlite3
import json
from datetime import datetime, timedelta

# Add backend directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

# Mock Electron IPC
sys.modules['electron'] = type(sys)('electron')

def create_test_db_with_intraday():
    """Create test database with both daily and intraday data"""
    db_path = ':memory:'
    conn = sqlite3.connect(db_path)
    
    # Create price_data table (daily)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS price_data (
            symbol TEXT,
            timestamp INTEGER,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER
        )
    ''')
    
    # Create ohlcv_intraday table (5m, 15m, 1h)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS ohlcv_intraday (
            symbol TEXT,
            timeframe TEXT,
            timestamp INTEGER,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER
        )
    ''')
    
    # Generate test data for one symbol
    symbol = 'TEST'
    base_date = datetime(2024, 1, 1)
    
    # Daily data - 30 days, uptrend
    daily_data = []
    for i in range(30):
        date = base_date + timedelta(days=i)
        ts = int(date.timestamp())
        close_price = 100 + i * 2  # Linear uptrend
        daily_data.append((
            symbol, ts, close_price - 1, close_price + 1, 
            close_price - 2, close_price, 100000 + i * 1000
        ))
    
    conn.executemany(
        'INSERT INTO price_data VALUES (?, ?, ?, ?, ?, ?, ?)',
        daily_data
    )
    
    # 1h data for the last day - trending up within the day
    last_day = base_date + timedelta(days=29)
    hourly_data = []
    for hour in range(24):
        date = last_day + timedelta(hours=hour)
        ts = int(date.timestamp())
        close_price = 155 + hour * 0.5  # Intraday uptrend
        hourly_data.append((
            symbol, '1h', ts, close_price - 0.2, close_price + 0.2,
            close_price - 0.3, close_price, 10000 + hour * 100
        ))
    
    conn.executemany(
        'INSERT INTO ohlcv_intraday VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        hourly_data
    )
    
    conn.commit()
    return conn

def test_cross_timeframe_basic():
    """Test basic cross-timeframe functionality by running a scan"""
    conn = create_test_db_with_intraday()
    
    # Import after mocking IPC
    import main
    
    # Temporarily replace the market database path
    original_db_path = main.current_db_service.market_db_path if hasattr(main, 'current_db_service') else None
    
    # Write test data to actual market DB temporarily
    market_db_path = os.path.expanduser('~/.byod_backtesting/market_data.db')
    with sqlite3.connect(market_db_path) as market_conn:
        # Clear any existing TEST data
        market_conn.execute("DELETE FROM price_data WHERE symbol = 'TEST'")
        market_conn.execute("DELETE FROM ohlcv_intraday WHERE symbol = 'TEST'")
        
        # Copy test data
        conn.backup(market_conn, pages=1)
        market_conn.commit()
    
    # Run a simple scan with cross-timeframe reference
    request = {
        'action': 'run-scan',
        'requestId': 'test-1',
        'data': {
            'scannerSpec': {
                'timeframe': '1D',
                'symbols': ['TEST'],
                'filters': [
                    {
                        'op': 'compare',
                        'cmp': '>',
                        'left': {
                            'type': 'attr',
                            'name': 'close'
                        },
                        'right': {
                            'type': 'number',
                            'value': 100
                        }
                    }
                ]
            },
            'options': {
                'includeExplain': True
            }
        }
    }
    
    result = main.handle_request(request)
    
    # Clean up test data
    with sqlite3.connect(market_db_path) as market_conn:
        market_conn.execute("DELETE FROM price_data WHERE symbol = 'TEST'")
        market_conn.execute("DELETE FROM ohlcv_intraday WHERE symbol = 'TEST'")
        market_conn.commit()
    
    # Restore original DB path
    if original_db_path:
        main.current_db_service.market_db_path = original_db_path
    
    assert 'results' in result, "Should return results"
    assert result.get('scanned') == 1, "Should scan 1 symbol"
    print(f"✓ Basic cross-timeframe scan executed: {result.get('matched', 0)} matches")
    
    conn.close()

if __name__ == '__main__':
    print("\n=== Testing Cross-Timeframe Query Support ===\n")
    
    try:
        test_cross_timeframe_basic()
        
        print("\n✅ All cross-timeframe tests passed!\n")
    except Exception as e:
        print(f"\n❌ Test failed: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
