"""
Unit tests for trade_analytics module
Tests performance metrics, Monte Carlo, and leverage analysis
"""
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / 'backend'
sys.path.insert(0, str(backend_path))

import pytest
import pandas as pd
import numpy as np
from trade_analytics import TradeAnalyzer, analyze_symbol_correlation


class TestTradeAnalyzer:
    """Test TradeAnalyzer class"""
    
    @pytest.fixture
    def sample_trades(self):
        """Create sample trade log for testing"""
        return pd.DataFrame({
            'symbol': ['AAPL', 'GOOGL', 'MSFT', 'AAPL', 'TSLA', 'AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AAPL', 'GOOGL', 'MSFT'],
            'entry_date': ['2024-01-01', '2024-01-05', '2024-01-10', '2024-01-15', '2024-01-20',
                           '2024-02-01', '2024-02-05', '2024-02-10', '2024-02-15', '2024-02-20',
                           '2024-03-01', '2024-03-05'],
            'exit_date': ['2024-01-10', '2024-01-15', '2024-01-20', '2024-01-25', '2024-01-30',
                          '2024-02-10', '2024-02-15', '2024-02-20', '2024-02-25', '2024-03-01',
                          '2024-03-10', '2024-03-15'],
            'entry_price': [150.0, 140.0, 380.0, 155.0, 250.0, 152.0, 138.0, 385.0, 248.0, 158.0, 142.0, 390.0],
            'exit_price': [165.0, 135.0, 400.0, 160.0, 245.0, 160.0, 140.0, 395.0, 250.0, 162.0, 138.0, 395.0],
            'shares': [100, 50, 20, 100, 40, 100, 50, 20, 40, 100, 50, 20],
            'direction': ['long'] * 12,
            'pnl': [1500.0, -250.0, 400.0, 500.0, -200.0, 800.0, 100.0, 200.0, 80.0, 400.0, -200.0, 100.0],
            'pnl_pct': [10.0, -3.57, 5.26, 3.23, -2.0, 5.26, 1.45, 2.60, 0.81, 2.53, -2.82, 1.28],
            'exit_reason': ['take_profit', 'stop_loss', 'time_exit', 'take_profit', 'stop_loss',
                            'take_profit', 'time_exit', 'take_profit', 'time_exit', 'take_profit',
                            'stop_loss', 'time_exit'],
            'holding_period': [9, 10, 10, 10, 10, 9, 10, 10, 10, 9, 9, 10],
            'position_value': [15000.0, 7000.0, 7600.0, 15500.0, 10000.0, 15200.0, 6900.0, 7700.0, 9920.0, 15800.0, 7100.0, 7800.0]
        })
    
    def test_calculate_performance_metrics_basic(self, sample_trades):
        """Test basic performance metrics calculation"""
        analyzer = TradeAnalyzer(sample_trades)
        metrics = analyzer.calculate_performance_metrics(initial_capital=100000.0)
        
        # Check metrics structure
        assert 'totalReturn' in metrics
        assert 'winRate' in metrics
        assert 'profitFactor' in metrics
        assert 'totalTrades' in metrics
        
        # Check values - 12 total trades, 9 winners (pnl > 0), 3 losers (pnl < 0)
        assert metrics['totalTrades'] == 12
        assert metrics['winningTrades'] == 9
        assert metrics['losingTrades'] == 3
    
    def test_win_rate_calculation(self, sample_trades):
        """Test win rate calculation"""
        analyzer = TradeAnalyzer(sample_trades)
        metrics = analyzer.calculate_performance_metrics(initial_capital=100000.0)
        
        # 9 winners out of 12 trades = 75%
        assert metrics['winRate'] == 0.75
    
    def test_profit_factor_calculation(self, sample_trades):
        """Test profit factor calculation"""
        analyzer = TradeAnalyzer(sample_trades)
        metrics = analyzer.calculate_performance_metrics(initial_capital=100000.0)
        
        # Gross profit = 1500 + 400 + 500 + 800 + 100 + 200 + 80 + 400 + 100 = 4080
        # Gross loss = 250 + 200 + 200 = 650
        # Profit factor = 4080 / 650 = 6.28
        assert abs(metrics['profitFactor'] - 6.28) < 0.01
    
    def test_total_return_calculation(self, sample_trades):
        """Test total return calculation"""
        analyzer = TradeAnalyzer(sample_trades)
        metrics = analyzer.calculate_performance_metrics(initial_capital=100000.0)
        
        # Total P&L = 1500 - 250 + 400 + 500 - 200 + 800 + 100 + 200 + 80 + 400 - 200 + 100 = 3430
        # Return = 3430 / 100000 = 0.0343
        assert abs(metrics['totalReturn'] - 0.0343) < 0.0001
    
    def test_max_consecutive_wins(self, sample_trades):
        """Test max consecutive wins calculation"""
        analyzer = TradeAnalyzer(sample_trades)
        metrics = analyzer.calculate_performance_metrics(initial_capital=100000.0)
        
        # Pattern: W, L, W, W, L, W, W, W, W, W, L, W → max consecutive wins = 5
        assert metrics['maxConsecutiveWins'] == 5
    
    def test_max_consecutive_losses(self, sample_trades):
        """Test max consecutive losses calculation"""
        # Create trades with consecutive losses
        trades = pd.DataFrame({
            'pnl': [100, -50, -30, -20, 150, -10],
            'pnl_pct': [5, -2, -1, -0.5, 7, -0.3],
            'entry_date': ['2024-01-01'] * 6,
            'exit_date': ['2024-01-10'] * 6,
            'holding_period': [9] * 6
        })
        
        analyzer = TradeAnalyzer(trades)
        metrics = analyzer.calculate_performance_metrics(initial_capital=100000.0)
        
        # Pattern: W, L, L, L, W, L → max consecutive losses = 3
        assert metrics['maxConsecutiveLosses'] == 3
    
    def test_empty_trades(self):
        """Test metrics with empty trade log"""
        analyzer = TradeAnalyzer(pd.DataFrame())
        metrics = analyzer.calculate_performance_metrics(initial_capital=100000.0)
        
        assert metrics['totalTrades'] == 0
        assert metrics['winRate'] == 0.0
        assert metrics['totalReturn'] == 0.0
    
    def test_analyze_exit_reasons(self, sample_trades):
        """Test exit reason analysis"""
        analyzer = TradeAnalyzer(sample_trades)
        exit_reasons = analyzer.analyze_exit_reasons()
        
        assert exit_reasons['take_profit'] == 5
        assert exit_reasons['stop_loss'] == 3
        assert exit_reasons['time_exit'] == 4
    
    def test_analyze_holding_periods(self, sample_trades):
        """Test holding period analysis"""
        analyzer = TradeAnalyzer(sample_trades)
        holding_periods = analyzer.analyze_holding_periods()
        
        assert len(holding_periods) == 12
        assert all(h >= 9 for h in holding_periods)
    
    def test_analyze_pl_distribution(self, sample_trades):
        """Test P&L distribution analysis"""
        analyzer = TradeAnalyzer(sample_trades)
        pl_dist = analyzer.analyze_pl_distribution()
        
        assert len(pl_dist) == 12
        assert 10.0 in pl_dist  # Largest winner
        assert -3.57 in pl_dist  # Largest loser
    
    def test_get_pl_timeline(self, sample_trades):
        """Test P&L timeline generation"""
        analyzer = TradeAnalyzer(sample_trades)
        timeline = analyzer.get_pl_timeline()
        
        assert len(timeline) == 12
        assert all('date' in t for t in timeline)
        assert all('pl' in t for t in timeline)
        assert all('reason' in t for t in timeline)
    
    def test_run_monte_carlo_basic(self, sample_trades):
        """Test Monte Carlo simulation basic functionality"""
        analyzer = TradeAnalyzer(sample_trades)
        mc_results = analyzer.run_monte_carlo(n_simulations=100, n_trades=10)
        
        assert 'simulations' in mc_results
        assert len(mc_results['simulations']) == 100
        assert 'percentile_5' in mc_results
        assert 'percentile_50' in mc_results
        assert 'percentile_95' in mc_results
        assert 'probability_profit' in mc_results
    
    def test_monte_carlo_percentiles_ordered(self, sample_trades):
        """Test Monte Carlo percentiles are correctly ordered"""
        analyzer = TradeAnalyzer(sample_trades)
        mc_results = analyzer.run_monte_carlo(n_simulations=1000, n_trades=50)
        
        # p5 < p50 < p95
        assert mc_results['percentile_5'] < mc_results['percentile_50']
        assert mc_results['percentile_50'] < mc_results['percentile_95']
    
    def test_monte_carlo_insufficient_trades(self):
        """Test Monte Carlo with insufficient trades returns error"""
        # Only 5 trades (need 10+)
        trades = pd.DataFrame({
            'pnl_pct': [5.0, -2.0, 3.0, -1.0, 4.0]
        })
        
        analyzer = TradeAnalyzer(trades)
        mc_results = analyzer.run_monte_carlo(n_simulations=100, n_trades=50)
        
        assert 'error' in mc_results
    
    def test_monte_carlo_deterministic_seed(self):
        """Test Monte Carlo gives consistent results with same seed"""
        trades = pd.DataFrame({
            'pnl_pct': [float(i % 10 - 5) for i in range(20)]
        })
        
        analyzer = TradeAnalyzer(trades)
        
        # Set numpy seed for reproducibility
        np.random.seed(42)
        mc1 = analyzer.run_monte_carlo(n_simulations=100, n_trades=20)
        
        np.random.seed(42)
        mc2 = analyzer.run_monte_carlo(n_simulations=100, n_trades=20)
        
        # Results should be identical
        assert mc1['percentile_50'] == mc2['percentile_50']
    
    def test_calculate_leverage_metrics_basic(self, sample_trades):
        """Test leverage metrics calculation"""
        analyzer = TradeAnalyzer(sample_trades)
        leverage = analyzer.calculate_leverage_metrics(initial_capital=100000.0)
        
        assert 'average_leverage' in leverage
        assert 'max_leverage' in leverage
        assert 'leverage_distribution' in leverage
        assert 'high_leverage_trades' in leverage
        assert 'leverage_risk_score' in leverage
    
    def test_leverage_metrics_no_leverage(self):
        """Test leverage metrics when positions < capital"""
        # All positions well below capital
        trades = pd.DataFrame({
            'pnl': [100] * 5,
            'pnl_pct': [2.0] * 5,
            'entry_date': ['2024-01-01'] * 5,
            'exit_date': ['2024-01-10'] * 5,
            'holding_period': [9] * 5,
            'position_value': [5000.0] * 5  # Small positions
        })
        
        analyzer = TradeAnalyzer(trades)
        leverage = analyzer.calculate_leverage_metrics(initial_capital=100000.0)
        
        # All trades should be ≤1x leverage
        assert leverage['average_leverage'] < 1.0
        assert leverage['high_leverage_trades'] == 0
    
    def test_leverage_metrics_with_leverage(self):
        """Test leverage metrics with leveraged positions"""
        trades = pd.DataFrame({
            'pnl': [100] * 3,
            'pnl_pct': [2.0] * 3,
            'entry_date': ['2024-01-01'] * 3,
            'exit_date': ['2024-01-10'] * 3,
            'holding_period': [9] * 3,
            'position_value': [200000.0, 150000.0, 250000.0]  # Large positions
        })
        
        analyzer = TradeAnalyzer(trades)
        leverage = analyzer.calculate_leverage_metrics(initial_capital=100000.0)
        
        # Should show high leverage
        assert leverage['average_leverage'] > 1.0
        assert leverage['high_leverage_trades'] > 0
        assert leverage['leverage_risk_score'] > 50  # High risk
    
    def test_calculate_invested_value_timeline(self, sample_trades):
        """Test invested value timeline calculation"""
        analyzer = TradeAnalyzer(sample_trades)
        timeline = analyzer.calculate_invested_value_timeline(initial_capital=100000.0)
        
        assert len(timeline) > 0
        assert all('date' in t for t in timeline)
        assert all('invested_value' in t for t in timeline)
        assert all('available_cash' in t for t in timeline)
        assert all('total_value' in t for t in timeline)
    
    def test_invested_value_timeline_empty(self):
        """Test invested value timeline with no trades"""
        analyzer = TradeAnalyzer(pd.DataFrame())
        timeline = analyzer.calculate_invested_value_timeline(initial_capital=100000.0)
        
        assert timeline == []


class TestSymbolCorrelation:
    """Test symbol correlation analysis"""
    
    def test_analyze_symbol_correlation_basic(self):
        """Test basic correlation analysis"""
        # Create sample trades for two symbols
        trades_aapl = pd.DataFrame({
            'exit_date': ['2024-01-10', '2024-01-20', '2024-01-30'],
            'pnl_pct': [5.0, -2.0, 3.0]
        })
        
        trades_googl = pd.DataFrame({
            'exit_date': ['2024-01-10', '2024-01-20', '2024-01-30'],
            'pnl_pct': [4.5, -1.8, 2.9]
        })
        
        symbol_trades = {
            'AAPL': trades_aapl,
            'GOOGL': trades_googl
        }
        
        corr_matrix = analyze_symbol_correlation(symbol_trades)
        
        assert not corr_matrix.empty
        assert 'AAPL' in corr_matrix.index
        assert 'GOOGL' in corr_matrix.columns
        assert corr_matrix.loc['AAPL', 'AAPL'] == 1.0  # Self correlation
    
    def test_analyze_symbol_correlation_empty(self):
        """Test correlation with empty trades"""
        corr_matrix = analyze_symbol_correlation({})
        assert corr_matrix.empty
    
    def test_analyze_symbol_correlation_positive(self):
        """Test symbols with positive correlation"""
        # Create perfectly correlated returns
        dates = ['2024-01-10', '2024-01-20', '2024-01-30']
        returns = [5.0, -2.0, 3.0]
        
        symbol_trades = {
            'AAPL': pd.DataFrame({'exit_date': dates, 'pnl_pct': returns}),
            'MSFT': pd.DataFrame({'exit_date': dates, 'pnl_pct': returns})
        }
        
        corr_matrix = analyze_symbol_correlation(symbol_trades)
        
        # Should be perfectly correlated
        assert abs(corr_matrix.loc['AAPL', 'MSFT'] - 1.0) < 0.01
    
    def test_analyze_symbol_correlation_negative(self):
        """Test symbols with negative correlation"""
        dates = ['2024-01-10', '2024-01-20', '2024-01-30']
        
        symbol_trades = {
            'AAPL': pd.DataFrame({'exit_date': dates, 'pnl_pct': [5.0, -2.0, 3.0]}),
            'GOOGL': pd.DataFrame({'exit_date': dates, 'pnl_pct': [-5.0, 2.0, -3.0]})
        }
        
        corr_matrix = analyze_symbol_correlation(symbol_trades)
        
        # Should be negatively correlated
        assert corr_matrix.loc['AAPL', 'GOOGL'] < 0


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_single_trade(self):
        """Test analyzer with single trade"""
        trades = pd.DataFrame({
            'pnl': [100],
            'pnl_pct': [5.0],
            'entry_date': ['2024-01-01'],
            'exit_date': ['2024-01-10'],
            'holding_period': [9]
        })
        
        analyzer = TradeAnalyzer(trades)
        metrics = analyzer.calculate_performance_metrics(initial_capital=10000.0)
        
        assert metrics['totalTrades'] == 1
        assert metrics['winRate'] == 1.0
    
    def test_all_winning_trades(self):
        """Test analyzer with all winners"""
        trades = pd.DataFrame({
            'pnl': [100, 200, 150],
            'pnl_pct': [5.0, 10.0, 7.5],
            'entry_date': ['2024-01-01'] * 3,
            'exit_date': ['2024-01-10'] * 3,
            'holding_period': [9] * 3
        })
        
        analyzer = TradeAnalyzer(trades)
        metrics = analyzer.calculate_performance_metrics(initial_capital=10000.0)
        
        assert metrics['winRate'] == 1.0
        assert metrics['losingTrades'] == 0
        assert metrics['profitFactor'] == 0.0  # No losses to divide by
    
    def test_all_losing_trades(self):
        """Test analyzer with all losers"""
        trades = pd.DataFrame({
            'pnl': [-100, -200, -150],
            'pnl_pct': [-5.0, -10.0, -7.5],
            'entry_date': ['2024-01-01'] * 3,
            'exit_date': ['2024-01-10'] * 3,
            'holding_period': [9] * 3
        })
        
        analyzer = TradeAnalyzer(trades)
        metrics = analyzer.calculate_performance_metrics(initial_capital=10000.0)
        
        assert metrics['winRate'] == 0.0
        assert metrics['winningTrades'] == 0
        assert metrics['profitFactor'] == 0.0  # No profits
    
    def test_zero_volatility_trades(self):
        """Test with trades that have zero variance"""
        trades = pd.DataFrame({
            'pnl': [100] * 10,
            'pnl_pct': [5.0] * 10,
            'entry_date': ['2024-01-01'] * 10,
            'exit_date': ['2024-01-10'] * 10,
            'holding_period': [9] * 10
        })
        
        analyzer = TradeAnalyzer(trades)
        metrics = analyzer.calculate_performance_metrics(initial_capital=10000.0)
        
        # Should handle zero variance without error
        assert metrics['sharpeRatio'] == 0.0  # Can't calculate with no variance


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
