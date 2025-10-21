"""
Data Quality Analyzer for Trading Data
Analyzes imported data for quality metrics and missing periods
"""
import sqlite3
from typing import Dict, List, Any, Tuple, Optional
import pandas as pd
from datetime import datetime, timedelta
import json
import time
import sys

class DataQualityAnalyzer:
    """Analyzes data quality for trading symbols"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def analyze_symbol(self, symbol: str) -> Dict[str, Any]:
        """
        Comprehensive analysis of a symbol's data quality

        Returns:
            Dictionary containing:
            - basic_info: Start date, end date, total records
            - quality_metrics: Completeness, data integrity
            - missing_periods: Gaps in data (> 5 days)
            - comparison: Other symbols available during same period
            - data_gaps: Detailed list of gaps
        """
        import sys
        print(f"DATA-QUALITY: Starting analysis for symbol '{symbol}'", file=sys.stderr)
        start_time = time.time()

        try:
            print(f"DATA-QUALITY: Connecting to database: {self.db_path}", file=sys.stderr)
            conn_start = time.time()
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                conn_time = time.time() - conn_start
                print(f"DATA-QUALITY: Database connection established in {conn_time:.3f}s", file=sys.stderr)

                # 1. Get basic date range and record count
                print(f"DATA-QUALITY: Step 1 - Getting basic info for {symbol}", file=sys.stderr)
                basic_start = time.time()
                basic_info = self._get_basic_info(conn, symbol)
                basic_time = time.time() - basic_start
                print(f"DATA-QUALITY: Basic info retrieved in {basic_time:.3f}s", file=sys.stderr)

                if basic_info is None:
                    print(f"DATA-QUALITY: No data found for symbol {symbol}", file=sys.stderr)
                    return {'error': f'No data found for symbol {symbol}'}

                print(f"DATA-QUALITY: Basic info: {basic_info['total_records']} records, {basic_info['unique_dates']} unique dates", file=sys.stderr)

                # 2. Analyze data quality metrics
                print(f"DATA-QUALITY: Step 2 - Analyzing quality metrics for {symbol}", file=sys.stderr)
                quality_start = time.time()
                quality_metrics = self._analyze_quality_metrics(conn, symbol, basic_info)
                quality_time = time.time() - quality_start
                print(f"DATA-QUALITY: Quality metrics calculated in {quality_time:.3f}s", file=sys.stderr)

                # 3. Find missing periods (gaps > 5 days)
                print(f"DATA-QUALITY: Step 3 - Finding missing periods for {symbol}", file=sys.stderr)
                missing_start = time.time()
                missing_periods = self._find_missing_periods(conn, symbol, basic_info)
                missing_time = time.time() - missing_start
                print(f"DATA-QUALITY: Missing periods found in {missing_time:.3f}s ({len(missing_periods)} gaps)", file=sys.stderr)

                # 4. Find alternative symbols during missing periods
                print(f"DATA-QUALITY: Step 4 - Finding comparable symbols for {symbol}", file=sys.stderr)
                comparable_start = time.time()
                comparable_symbols = self._find_comparable_symbols(conn, symbol, missing_periods, basic_info)
                comparable_time = time.time() - comparable_start
                print(f"DATA-QUALITY: Comparable symbols found in {comparable_time:.3f}s", file=sys.stderr)

                total_time = time.time() - start_time
                print(f"DATA-QUALITY: Analysis complete for {symbol} in {total_time:.3f}s", file=sys.stderr)

                return {
                    'symbol': symbol,
                    'basic_info': basic_info,
                    'quality_metrics': quality_metrics,
                    'missing_periods': missing_periods,
                    'comparable_symbols': comparable_symbols,
                    'summary': self._generate_summary(basic_info, quality_metrics, missing_periods)
                }

        except Exception as e:
            total_time = time.time() - start_time
            print(f"DATA-QUALITY: Analysis failed for {symbol} after {total_time:.3f}s: {str(e)}", file=sys.stderr)
            import traceback
            print(f"DATA-QUALITY: Traceback: {traceback.format_exc()}", file=sys.stderr)
            return {'error': f'Analysis failed: {str(e)}'}
    
    def analyze_all_symbols(self) -> List[Dict[str, Any]]:
        """Analyze all symbols in the database"""
        import sys
        print(f"DATA-QUALITY: Starting analysis of all symbols", file=sys.stderr)
        start_time = time.time()

        try:
            print(f"DATA-QUALITY: Connecting to database to fetch symbol list", file=sys.stderr)
            conn_start = time.time()
            with sqlite3.connect(self.db_path) as conn:
                conn_time = time.time() - conn_start
                print(f"DATA-QUALITY: Database connection established in {conn_time:.3f}s", file=sys.stderr)

                cur = conn.execute(
                    'SELECT DISTINCT symbol FROM price_data ORDER BY symbol'
                )
                symbols = [row[0] for row in cur.fetchall()]

            print(f"DATA-QUALITY: Found {len(symbols)} symbols to analyze: {symbols[:10]}{'...' if len(symbols) > 10 else ''}", file=sys.stderr)

            # Send initial progress
            self._send_progress(0, len(symbols), "Starting analysis...")

            results = []
            for i, symbol in enumerate(symbols):
                print(f"DATA-QUALITY: Processing symbol {i+1}/{len(symbols)}: {symbol}", file=sys.stderr)
                sym_start = time.time()
                analysis = self.analyze_symbol(symbol)
                sym_time = time.time() - sym_start
                print(f"DATA-QUALITY: Symbol {symbol} completed in {sym_time:.3f}s", file=sys.stderr)
                results.append(analysis)

                # Progress update every 5 symbols or at key milestones
                if (i + 1) % 5 == 0 or (i + 1) == len(symbols):
                    elapsed = time.time() - start_time
                    progress = int(((i + 1) / len(symbols)) * 100)
                    avg_time = elapsed / (i + 1)
                    remaining = avg_time * (len(symbols) - i - 1)
                    status = f"Processed {i+1}/{len(symbols)} symbols ({progress}%)"
                    print(f"DATA-QUALITY: Progress: {status}, elapsed: {elapsed:.1f}s, remaining: {remaining:.1f}s", file=sys.stderr)
                    self._send_progress(progress, len(symbols), status)

            total_time = time.time() - start_time
            print(f"DATA-QUALITY: All symbols analysis completed in {total_time:.3f}s", file=sys.stderr)

            # Send final progress
            self._send_progress(100, len(symbols), "Analysis complete!")
            return results
        except Exception as e:
            total_time = time.time() - start_time
            print(f"DATA-QUALITY: All symbols analysis failed after {total_time:.3f}s: {str(e)}", file=sys.stderr)
            import traceback
            print(f"DATA-QUALITY: Traceback: {traceback.format_exc()}", file=sys.stderr)
            return [{'error': f'Analysis failed: {str(e)}'}]

    def _send_progress(self, progress: int, total: int, status: str):
        """Send progress update to stdout for Electron to capture"""
        try:
            progress_data = {
                'type': 'import-progress',
                'progress': progress,
                'current': progress,
                'total': total,
                'status': status,
                'timestamp': time.time()
            }
            print(json.dumps(progress_data), flush=True)
        except Exception as e:
            print(f"DATA-QUALITY: Failed to send progress: {e}", file=sys.stderr)

    def _calculate_trading_days(self, start_date, end_date) -> int:
        """Calculate number of trading days (Monday-Friday) between two dates"""
        trading_days = 0
        current_date = start_date

        while current_date <= end_date:
            # Monday = 0, Friday = 4, Saturday = 5, Sunday = 6
            if current_date.weekday() < 5:  # Monday through Friday
                trading_days += 1
            current_date += timedelta(days=1)

        return trading_days
    
    def _get_basic_info(self, conn: sqlite3.Connection, symbol: str) -> Optional[Dict[str, Any]]:
        """Get basic data range and count"""
        import sys
        print(f"DATA-QUALITY: Getting basic info for {symbol}", file=sys.stderr)
        query_start = time.time()

        cur = conn.execute('''
            SELECT
                MIN(timestamp) as start_timestamp,
                MAX(timestamp) as end_timestamp,
                COUNT(*) as total_records,
                COUNT(DISTINCT DATE(timestamp, 'unixepoch')) as unique_dates
            FROM price_data
            WHERE symbol = ?
        ''', (symbol,))

        query_time = time.time() - query_start
        print(f"DATA-QUALITY: Basic info query completed in {query_time:.3f}s", file=sys.stderr)

        row = cur.fetchone()
        if not row or row['total_records'] == 0:
            print(f"DATA-QUALITY: No data found for {symbol}", file=sys.stderr)
            return None

        start_date = datetime.fromtimestamp(row['start_timestamp']).date()
        end_date = datetime.fromtimestamp(row['end_timestamp']).date()

        # Calculate calendar days (original method)
        calendar_days = (end_date - start_date).days + 1

        # Calculate trading days only (Monday-Friday, excludes weekends)
        trading_days = self._calculate_trading_days(start_date, end_date)

        print(f"DATA-QUALITY: Basic info for {symbol}: {row['total_records']} records, {row['unique_dates']} unique dates", file=sys.stderr)
        print(f"DATA-QUALITY: Date range: {start_date} to {end_date}", file=sys.stderr)
        print(f"DATA-QUALITY: Calendar days: {calendar_days}, Trading days: {trading_days}", file=sys.stderr)

        return {
            'symbol': symbol,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'total_records': row['total_records'],
            'unique_dates': row['unique_dates'],
            'calendar_days': calendar_days,
            'trading_days': trading_days,
            'calendar_coverage': round((row['unique_dates'] / max(1, calendar_days)) * 100, 2),
            'trading_coverage': round((row['unique_dates'] / max(1, trading_days)) * 100, 2)
        }
    
    def _analyze_quality_metrics(self, conn: sqlite3.Connection, symbol: str, basic_info: Dict) -> Dict[str, Any]:
        """Analyze data quality metrics"""
        cur = conn.execute('''
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN open IS NULL OR open = 0 THEN 1 END) as null_open,
                COUNT(CASE WHEN high IS NULL OR high = 0 THEN 1 END) as null_high,
                COUNT(CASE WHEN low IS NULL OR low = 0 THEN 1 END) as null_low,
                COUNT(CASE WHEN close IS NULL OR close = 0 THEN 1 END) as null_close,
                COUNT(CASE WHEN volume IS NULL OR volume = 0 THEN 1 END) as null_volume,
                COUNT(CASE WHEN high < low THEN 1 END) as high_low_errors,
                COUNT(CASE WHEN close < low OR close > high THEN 1 END) as close_range_errors
            FROM price_data
            WHERE symbol = ?
        ''', (symbol,))
        
        row = cur.fetchone()
        total = row['total']
        
        completeness_score = (
            (1 - row['null_open'] / max(1, total)) +
            (1 - row['null_high'] / max(1, total)) +
            (1 - row['null_low'] / max(1, total)) +
            (1 - row['null_close'] / max(1, total)) +
            (1 - row['null_volume'] / max(1, total))
        ) / 5 * 100
        
        integrity_score = (
            (1 - row['high_low_errors'] / max(1, total)) +
            (1 - row['close_range_errors'] / max(1, total))
        ) / 2 * 100
        
        return {
            'completeness_score': round(completeness_score, 2),
            'integrity_score': round(integrity_score, 2),
            'null_fields': {
                'open': row['null_open'],
                'high': row['null_high'],
                'low': row['null_low'],
                'close': row['null_close'],
                'volume': row['null_volume']
            },
            'data_errors': {
                'high_low_reversed': row['high_low_errors'],
                'close_outside_range': row['close_range_errors']
            }
        }
    
    def _find_missing_periods(self, conn: sqlite3.Connection, symbol: str, basic_info: Dict) -> List[Dict[str, Any]]:
        """Find periods with missing data (> 5 days)"""
        import sys
        print(f"DATA-QUALITY: Finding missing periods for {symbol}", file=sys.stderr)
        query_start = time.time()

        # Get all dates for this symbol
        cur = conn.execute('''
            SELECT DISTINCT DATE(timestamp, 'unixepoch') as date
            FROM price_data
            WHERE symbol = ?
            ORDER BY date
        ''', (symbol,))

        query_time = time.time() - query_start
        print(f"DATA-QUALITY: Missing periods query completed in {query_time:.3f}s", file=sys.stderr)

        dates = [datetime.fromisoformat(row[0]).date() for row in cur.fetchall()]
        print(f"DATA-QUALITY: Found {len(dates)} unique dates for {symbol}", file=sys.stderr)

        if len(dates) < 2:
            print(f"DATA-QUALITY: Not enough dates for gap analysis", file=sys.stderr)
            return []

        missing_periods = []
        current_date = dates[0]

        for date in dates[1:]:
            gap_days = (date - current_date).days

            # Report gaps > 5 days
            if gap_days > 5:
                gap_start = current_date + timedelta(days=1)
                gap_end = date - timedelta(days=1)

                missing_periods.append({
                    'gap_start_date': gap_start.isoformat(),
                    'gap_end_date': gap_end.isoformat(),
                    'gap_days': gap_days - 1,
                    'date_before': current_date.isoformat(),
                    'date_after': date.isoformat()
                })

            current_date = date

        print(f"DATA-QUALITY: Found {len(missing_periods)} missing periods for {symbol}", file=sys.stderr)
        return missing_periods
    
    def _find_comparable_symbols(
        self,
        conn: sqlite3.Connection,
        symbol: str,
        missing_periods: List[Dict],
        basic_info: Dict
    ) -> Dict[str, Any]:
        """Find other symbols available during the given symbol's data coverage"""
        import sys
        print(f"DATA-QUALITY: Finding comparable symbols for {symbol}", file=sys.stderr)

        if not missing_periods:
            print(f"DATA-QUALITY: No missing periods for {symbol}", file=sys.stderr)
            return {'status': 'No significant gaps', 'comparable_symbols': []}

        print(f"DATA-QUALITY: Processing {len(missing_periods)} missing periods for {symbol}", file=sys.stderr)
        comparable = []

        for i, gap in enumerate(missing_periods):
            print(f"DATA-QUALITY: Processing gap {i+1}/{len(missing_periods)} for {symbol}", file=sys.stderr)
            gap_start = gap['gap_start_date']
            gap_end = gap['gap_end_date']

            query_start = time.time()
            # Find symbols that have data during this gap
            cur = conn.execute('''
                SELECT DISTINCT symbol,
                    COUNT(*) as records_in_gap,
                    MIN(timestamp) as first_in_gap,
                    MAX(timestamp) as last_in_gap
                FROM price_data
                WHERE symbol != ?
                    AND timestamp >= ? AND timestamp <= ?
                    AND symbol NOT IN (
                        SELECT symbol FROM price_data
                        WHERE symbol = ?
                            AND timestamp >= ? AND timestamp <= ?
                    )
                GROUP BY symbol
                ORDER BY records_in_gap DESC
                LIMIT 5
            ''', (
                symbol,
                int(datetime.fromisoformat(gap_start).timestamp()),
                int(datetime.fromisoformat(gap_end).timestamp()),
                symbol,
                int(datetime.fromisoformat(gap_start).timestamp()),
                int(datetime.fromisoformat(gap_end).timestamp())
            ))

            query_time = time.time() - query_start
            print(f"DATA-QUALITY: Comparable symbols query {i+1} completed in {query_time:.3f}s", file=sys.stderr)

            gap_symbols = []
            for row in cur.fetchall():
                gap_symbols.append({
                    'symbol': row[0],
                    'records_available': row[1],
                    'coverage_start': datetime.fromtimestamp(row[2]).date().isoformat(),
                    'coverage_end': datetime.fromtimestamp(row[3]).date().isoformat()
                })

            print(f"DATA-QUALITY: Found {len(gap_symbols)} comparable symbols for gap {i+1}", file=sys.stderr)

            if gap_symbols:
                comparable.append({
                    'gap_period': {
                        'start': gap_start,
                        'end': gap_end,
                        'duration_days': gap['gap_days']
                    },
                    'alternative_symbols': gap_symbols
                })

        print(f"DATA-QUALITY: Comparable symbols analysis complete for {symbol}", file=sys.stderr)
        return {
            'status': f'Found alternatives for {len(comparable)}/{len(missing_periods)} gaps',
            'comparable_gaps': comparable
        }
    
    def _generate_summary(
        self,
        basic_info: Dict,
        quality_metrics: Dict,
        missing_periods: List[Dict]
    ) -> Dict[str, Any]:
        """Generate overall data quality summary"""
        
        avg_score = (quality_metrics['completeness_score'] + quality_metrics['integrity_score']) / 2
        
        if avg_score >= 95:
            quality_rating = 'Excellent'
            status = '✓'
        elif avg_score >= 85:
            quality_rating = 'Good'
            status = '⚠'
        elif avg_score >= 70:
            quality_rating = 'Fair'
            status = '⚠⚠'
        else:
            quality_rating = 'Poor'
            status = '✗'
        
        return {
            'overall_score': round(avg_score, 2),
            'quality_rating': quality_rating,
            'status': status,
            'data_coverage': f"{basic_info['unique_dates']} / {basic_info['trading_days']} trading days",
            'coverage_percentage': basic_info['trading_coverage'],
            'missing_gaps_count': len(missing_periods),
            'recommendation': self._get_recommendation(avg_score, len(missing_periods), basic_info)
        }
    
    def _get_recommendation(self, avg_score: float, gap_count: int, basic_info: Dict) -> str:
        """Generate recommendation based on analysis"""
        
        issues = []
        
        if avg_score < 90:
            issues.append('Data quality score is below 90%')
        
        if gap_count > 2:
            issues.append(f'{gap_count} significant data gaps detected')
        
        if basic_info['trading_coverage'] < 80:
            issues.append('Trading day coverage is below 80%')
        
        if not issues:
            return '✓ Data quality is acceptable for backtesting'
        else:
            return f'⚠ {"; ".join(issues)}. Review missing periods and consider data augmentation.'
    
    def get_dataset_summary(self, conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
        """Get summary statistics for all data"""
        
        should_close = False
        if conn is None:
            conn = sqlite3.connect(self.db_path)
            should_close = True
        
        try:
            cur = conn.execute('''
                SELECT 
                    COUNT(DISTINCT symbol) as total_symbols,
                    COUNT(*) as total_records,
                    MIN(timestamp) as earliest,
                    MAX(timestamp) as latest
                FROM price_data
            ''')
            
            row = cur.fetchone()
            
            return {
                'total_symbols': row[0],
                'total_records': row[1],
                'date_range_start': datetime.fromtimestamp(row[2]).date().isoformat() if row[2] else None,
                'date_range_end': datetime.fromtimestamp(row[3]).date().isoformat() if row[3] else None,
                'days_span': (datetime.fromtimestamp(row[3]) - datetime.fromtimestamp(row[2])).days if row[2] and row[3] else 0
            }
        
        finally:
            if should_close:
                conn.close()
