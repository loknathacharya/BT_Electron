"""
Data Quality Analyzer for Trading Data
Analyzes imported data for quality metrics and missing periods
"""
import sqlite3
from typing import Dict, List, Any, Tuple, Optional
import pandas as pd
from datetime import datetime, timedelta
import json

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
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # 1. Get basic date range and record count
                basic_info = self._get_basic_info(conn, symbol)
                if basic_info is None:
                    return {'error': f'No data found for symbol {symbol}'}
                
                # 2. Analyze data quality metrics
                quality_metrics = self._analyze_quality_metrics(conn, symbol, basic_info)
                
                # 3. Find missing periods (gaps > 5 days)
                missing_periods = self._find_missing_periods(conn, symbol, basic_info)
                
                # 4. Find alternative symbols during missing periods
                comparable_symbols = self._find_comparable_symbols(conn, symbol, missing_periods, basic_info)
                
                return {
                    'symbol': symbol,
                    'basic_info': basic_info,
                    'quality_metrics': quality_metrics,
                    'missing_periods': missing_periods,
                    'comparable_symbols': comparable_symbols,
                    'summary': self._generate_summary(basic_info, quality_metrics, missing_periods)
                }
        
        except Exception as e:
            return {'error': f'Analysis failed: {str(e)}'}
    
    def analyze_all_symbols(self) -> List[Dict[str, Any]]:
        """Analyze all symbols in the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.execute(
                    'SELECT DISTINCT symbol FROM price_data ORDER BY symbol'
                )
                symbols = [row[0] for row in cur.fetchall()]
            
            results = []
            for symbol in symbols:
                analysis = self.analyze_symbol(symbol)
                results.append(analysis)
            
            return results
        except Exception as e:
            return [{'error': f'Analysis failed: {str(e)}'}]
    
    def _get_basic_info(self, conn: sqlite3.Connection, symbol: str) -> Optional[Dict[str, Any]]:
        """Get basic data range and count"""
        cur = conn.execute('''
            SELECT 
                MIN(timestamp) as start_timestamp,
                MAX(timestamp) as end_timestamp,
                COUNT(*) as total_records,
                COUNT(DISTINCT DATE(timestamp, 'unixepoch')) as unique_dates
            FROM price_data
            WHERE symbol = ?
        ''', (symbol,))
        
        row = cur.fetchone()
        if not row or row['total_records'] == 0:
            return None
        
        start_date = datetime.fromtimestamp(row['start_timestamp']).date()
        end_date = datetime.fromtimestamp(row['end_timestamp']).date()
        days_span = (end_date - start_date).days + 1
        
        return {
            'symbol': symbol,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'total_records': row['total_records'],
            'unique_dates': row['unique_dates'],
            'days_span': days_span,
            'expected_records': days_span  # Assuming 1 record per day
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
        
        # Get all dates for this symbol
        cur = conn.execute('''
            SELECT DISTINCT DATE(timestamp, 'unixepoch') as date
            FROM price_data
            WHERE symbol = ?
            ORDER BY date
        ''', (symbol,))
        
        dates = [datetime.fromisoformat(row[0]).date() for row in cur.fetchall()]
        
        if len(dates) < 2:
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
        
        return missing_periods
    
    def _find_comparable_symbols(
        self, 
        conn: sqlite3.Connection, 
        symbol: str, 
        missing_periods: List[Dict],
        basic_info: Dict
    ) -> Dict[str, Any]:
        """Find other symbols available during the given symbol's data coverage"""
        
        if not missing_periods:
            return {'status': 'No significant gaps', 'comparable_symbols': []}
        
        comparable = []
        
        for gap in missing_periods:
            gap_start = gap['gap_start_date']
            gap_end = gap['gap_end_date']
            
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
            
            gap_symbols = []
            for row in cur.fetchall():
                gap_symbols.append({
                    'symbol': row[0],
                    'records_available': row[1],
                    'coverage_start': datetime.fromtimestamp(row[2]).date().isoformat(),
                    'coverage_end': datetime.fromtimestamp(row[3]).date().isoformat()
                })
            
            if gap_symbols:
                comparable.append({
                    'gap_period': {
                        'start': gap_start,
                        'end': gap_end,
                        'duration_days': gap['gap_days']
                    },
                    'alternative_symbols': gap_symbols
                })
        
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
            'data_coverage': f"{basic_info['unique_dates']} / {basic_info['days_span']} days",
            'coverage_percentage': round(basic_info['unique_dates'] / max(1, basic_info['days_span']) * 100, 2),
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
        
        if basic_info['unique_dates'] / max(1, basic_info['days_span']) < 0.8:
            issues.append('Data coverage is below 80% of expected dates')
        
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
