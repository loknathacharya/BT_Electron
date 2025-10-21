"""
Trade Analytics Module
Comprehensive analysis of backtest trades including Monte Carlo simulation,
leverage metrics, and advanced performance analysis.
"""
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from datetime import datetime


class TradeAnalyzer:
    """
    Analyzes backtest trade results and provides comprehensive metrics.
    
    Features:
    - Enhanced performance metrics (win rate, profit factor, Sharpe ratio, etc.)
    - Trade exit reason analysis (stop-loss, take-profit, time exit)
    - Holding period distribution
    - P&L distribution and analysis
    - Monte Carlo simulation for forward-looking analysis
    - Leverage metrics and risk analysis
    - Invested capital tracking over time
    """
    
    def __init__(self, trade_log: pd.DataFrame):
        """
        Initialize analyzer with trade log.
        
        Args:
            trade_log: DataFrame with columns:
                - symbol: Trading symbol
                - entry_date: Entry date (string YYYY-MM-DD)
                - exit_date: Exit date (string YYYY-MM-DD)
                - entry_price: Entry price
                - exit_price: Exit price
                - shares: Number of shares
                - direction: 'long' or 'short'
                - pnl: Profit/Loss in dollars
                - pnl_pct: Profit/Loss as percentage
                - exit_reason: 'stop_loss', 'take_profit', or 'time_exit'
                - holding_period: Days held
                - position_value: Position value at entry
        """
        self.trades = trade_log.copy() if not trade_log.empty else pd.DataFrame()
    
    def calculate_performance_metrics(self, initial_capital: float) -> Dict[str, Any]:
        """
        Calculate comprehensive performance metrics.
        
        Args:
            initial_capital: Starting capital for the backtest
        
        Returns:
            Dict with performance metrics including:
            - totalReturn, annualizedReturn, winRate, profitFactor
            - averageWin, averageLoss, maxDrawdown, sharpeRatio
            - totalTrades, winningTrades, losingTrades
            - averageHoldingPeriod, maxConsecutiveWins, maxConsecutiveLosses
        """
        if self.trades.empty:
            return self._empty_metrics()
        
        total_trades = len(self.trades)
        winning_trades = len(self.trades[self.trades['pnl'] > 0])
        losing_trades = len(self.trades[self.trades['pnl'] < 0])
        
        # Win rate
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
        
        # Profit factor
        gross_profit = self.trades[self.trades['pnl'] > 0]['pnl'].sum()
        gross_loss = abs(self.trades[self.trades['pnl'] < 0]['pnl'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0
        
        # Average win/loss
        avg_win = self.trades[self.trades['pnl'] > 0]['pnl_pct'].mean() if winning_trades > 0 else 0.0
        avg_loss = self.trades[self.trades['pnl'] < 0]['pnl_pct'].mean() if losing_trades > 0 else 0.0
        
        # Total and annualized return
        total_pnl = self.trades['pnl'].sum()
        total_return = total_pnl / initial_capital if initial_capital > 0 else 0.0
        
        # Calculate annualized return
        if not self.trades.empty:
            start_date = pd.to_datetime(self.trades['entry_date'].min())
            end_date = pd.to_datetime(self.trades['exit_date'].max())
            days = (end_date - start_date).days
            years = days / 365.25 if days > 0 else 1.0
            
            if years > 0 and total_return > -1:
                annualized_return = (1 + total_return) ** (1 / years) - 1
            else:
                annualized_return = 0.0
        else:
            annualized_return = 0.0
        
        # Sharpe ratio (simplified: using trade returns)
        if len(self.trades) >= 2:
            returns = self.trades['pnl_pct'] / 100.0
            mean_return = returns.mean()
            std_return = returns.std()
            sharpe_ratio = (mean_return / std_return) * np.sqrt(252) if std_return > 0 else 0.0
        else:
            sharpe_ratio = 0.0
        
        # Max drawdown
        cumulative_pnl = self.trades['pnl'].cumsum()
        running_max = cumulative_pnl.cummax()
        drawdown = cumulative_pnl - running_max
        max_drawdown = drawdown.min() / initial_capital if initial_capital > 0 else 0.0
        
        # Holding period
        avg_holding_period = self.trades['holding_period'].mean() if 'holding_period' in self.trades.columns else 0.0
        
        # Consecutive wins/losses
        wins = (self.trades['pnl'] > 0).astype(int)
        max_consecutive_wins = self._max_consecutive(wins)
        losses = (self.trades['pnl'] < 0).astype(int)
        max_consecutive_losses = self._max_consecutive(losses)
        
        return {
            'totalReturn': round(total_return, 6),
            'annualizedReturn': round(annualized_return, 6),
            'winRate': round(win_rate, 4),
            'profitFactor': round(profit_factor, 4),
            'averageWin': round(avg_win, 4),
            'averageLoss': round(avg_loss, 4),
            'maxDrawdown': round(max_drawdown, 6),
            'sharpeRatio': round(sharpe_ratio, 4),
            'totalTrades': int(total_trades),
            'winningTrades': int(winning_trades),
            'losingTrades': int(losing_trades),
            'averageHoldingPeriod': round(avg_holding_period, 2),
            'maxConsecutiveWins': int(max_consecutive_wins),
            'maxConsecutiveLosses': int(max_consecutive_losses),
            'grossProfit': round(gross_profit, 2),
            'grossLoss': round(gross_loss, 2),
            'totalPnL': round(total_pnl, 2)
        }
    
    def analyze_exit_reasons(self) -> Dict[str, int]:
        """
        Analyze distribution of exit reasons.
        
        Returns:
            Dict mapping exit reason to count
        """
        if self.trades.empty or 'exit_reason' not in self.trades.columns:
            return {}
        
        exit_counts = self.trades['exit_reason'].value_counts().to_dict()
        return exit_counts
    
    def analyze_holding_periods(self) -> List[int]:
        """
        Get distribution of holding periods.
        
        Returns:
            List of holding periods in days
        """
        if self.trades.empty or 'holding_period' not in self.trades.columns:
            return []
        
        return self.trades['holding_period'].tolist()
    
    def analyze_pl_distribution(self) -> List[float]:
        """
        Get distribution of profit/loss percentages.
        
        Returns:
            List of P&L percentages
        """
        if self.trades.empty:
            return []
        
        return self.trades['pnl_pct'].tolist()
    
    def get_pl_timeline(self) -> List[Dict[str, Any]]:
        """
        Get P&L values over time for visualization.
        
        Returns:
            List of dicts with date, pl, and exit_reason
        """
        if self.trades.empty:
            return []
        
        timeline = []
        for _, trade in self.trades.iterrows():
            timeline.append({
                'date': trade.get('exit_date', ''),
                'pl': trade.get('pnl_pct', 0.0),
                'reason': trade.get('exit_reason', 'unknown')
            })
        
        return timeline
    
    def run_monte_carlo(
        self,
        n_simulations: int = 1000,
        n_trades: int = 50
    ) -> Dict[str, Any]:
        """
        Run Monte Carlo simulation for forward-looking performance analysis.
        
        Uses historical trade returns to simulate future performance by randomly
        sampling from the historical distribution.
        
        Args:
            n_simulations: Number of simulation runs
            n_trades: Number of future trades to simulate in each run
        
        Returns:
            Dict with:
            - simulations: List of final return % for each simulation
            - percentile_5: 5th percentile (worst case)
            - percentile_50: 50th percentile (median)
            - percentile_95: 95th percentile (best case)
            - mean: Average outcome
            - std: Standard deviation
            - probability_profit: Probability of positive return
            - probability_loss_10: Probability of losing >10%
        """
        if self.trades.empty or len(self.trades) < 10:
            return {
                'simulations': [],
                'percentile_5': 0.0,
                'percentile_50': 0.0,
                'percentile_95': 0.0,
                'mean': 0.0,
                'std': 0.0,
                'probability_profit': 0.0,
                'probability_loss_10': 0.0,
                'error': 'Insufficient trades for Monte Carlo (need at least 10)'
            }
        
        # Get historical returns
        returns_array = (self.trades['pnl_pct'] / 100.0).to_numpy()
        
        # Run simulations
        simulations = []
        for _ in range(n_simulations):
            # Randomly sample returns with replacement
            sampled_returns = np.random.choice(returns_array, size=n_trades, replace=True)
            
            # Calculate cumulative return
            cumulative_return = np.prod(1 + sampled_returns) - 1
            simulations.append(cumulative_return * 100)  # Convert to percentage
        
        simulations = np.array(simulations)
        
        # Calculate statistics
        percentile_5 = np.percentile(simulations, 5)
        percentile_50 = np.percentile(simulations, 50)
        percentile_95 = np.percentile(simulations, 95)
        mean = np.mean(simulations)
        std = np.std(simulations)
        
        # Calculate probabilities
        probability_profit = (simulations > 0).sum() / len(simulations)
        probability_loss_10 = (simulations < -10).sum() / len(simulations)
        
        return {
            'simulations': simulations.tolist(),
            'percentile_5': round(float(percentile_5), 2),
            'percentile_50': round(float(percentile_50), 2),
            'percentile_95': round(float(percentile_95), 2),
            'mean': round(float(mean), 2),
            'std': round(float(std), 2),
            'probability_profit': round(float(probability_profit), 4),
            'probability_loss_10': round(float(probability_loss_10), 4),
            'n_simulations': n_simulations,
            'n_trades': n_trades
        }
    
    def calculate_leverage_metrics(self, initial_capital: float) -> Dict[str, Any]:
        """
        Calculate leverage-related metrics.
        
        Args:
            initial_capital: Starting capital
        
        Returns:
            Dict with leverage analysis:
            - average_leverage: Average leverage across all trades
            - max_leverage: Maximum leverage reached
            - leverage_distribution: Count of trades by leverage bucket
            - high_leverage_trades: Count of trades with leverage > 2x
            - leverage_risk_score: Risk score based on leverage usage (0-100)
        """
        if self.trades.empty or 'position_value' not in self.trades.columns:
            return {
                'average_leverage': 0.0,
                'max_leverage': 0.0,
                'leverage_distribution': {},
                'high_leverage_trades': 0,
                'leverage_risk_score': 0.0
            }
        
        # Calculate leverage for each trade (position value / capital at that time)
        # Simplified: assume capital grows/shrinks with cumulative P&L
        cumulative_capital = initial_capital + self.trades['pnl'].cumsum().shift(1).fillna(0)
        leverage = self.trades['position_value'] / cumulative_capital
        
        # Replace inf and nan with 0
        leverage = leverage.replace([np.inf, -np.inf], 0).fillna(0)
        
        # Calculate metrics
        avg_leverage = leverage.mean()
        max_leverage = leverage.max()
        
        # Distribution by buckets
        leverage_buckets = pd.cut(
            leverage,
            bins=[0, 1, 2, 3, float('inf')],
            labels=['≤1x', '1-2x', '2-3x', '>3x']
        )
        leverage_distribution = leverage_buckets.value_counts().to_dict()
        
        # Convert keys to strings for JSON serialization
        leverage_distribution = {str(k): int(v) for k, v in leverage_distribution.items()}
        
        # High leverage trades (>2x)
        high_leverage_trades = (leverage > 2.0).sum()
        
        # Risk score (0-100, higher = more risky)
        # Based on: average leverage, max leverage, and % of high leverage trades
        if len(leverage) > 0:
            high_leverage_pct = high_leverage_trades / len(leverage)
            risk_score = min(100, (
                (avg_leverage / 3.0) * 40 +  # 40 points for avg leverage
                (max_leverage / 5.0) * 30 +   # 30 points for max leverage
                high_leverage_pct * 30        # 30 points for high leverage %
            ))
        else:
            risk_score = 0.0
        
        return {
            'average_leverage': round(float(avg_leverage), 4),
            'max_leverage': round(float(max_leverage), 4),
            'leverage_distribution': leverage_distribution,
            'high_leverage_trades': int(high_leverage_trades),
            'leverage_risk_score': round(float(risk_score), 2)
        }
    
    def calculate_invested_value_timeline(
        self,
        initial_capital: float
    ) -> List[Dict[str, Any]]:
        """
        Calculate invested capital over time.
        
        Tracks how much capital is actively deployed in trades vs available cash.
        
        Args:
            initial_capital: Starting capital
        
        Returns:
            List of dicts with:
            - date: Date string
            - invested_value: Value invested in open positions
            - available_cash: Available cash
            - total_value: Total portfolio value
        """
        if self.trades.empty:
            return []
        
        # Create timeline of events (entries and exits)
        events = []
        
        for _, trade in self.trades.iterrows():
            # Entry event
            events.append({
                'date': trade['entry_date'],
                'type': 'entry',
                'value': trade.get('position_value', 0),
                'pnl': 0
            })
            
            # Exit event
            events.append({
                'date': trade['exit_date'],
                'type': 'exit',
                'value': -trade.get('position_value', 0),
                'pnl': trade.get('pnl', 0)
            })
        
        # Sort by date
        events_df = pd.DataFrame(events)
        events_df['date'] = pd.to_datetime(events_df['date'])
        events_df = events_df.sort_values('date')
        
        # Track invested value and cash over time
        timeline = []
        current_invested = 0.0
        current_cash = initial_capital
        current_total = initial_capital
        
        for _, event in events_df.iterrows():
            if event['type'] == 'entry':
                current_invested += event['value']
                current_cash -= event['value']
            else:  # exit
                current_invested += event['value']  # Negative, reduces invested
                current_cash -= event['value']  # Adds back value + pnl
                current_cash += event['pnl']
                current_total += event['pnl']
            
            timeline.append({
                'date': event['date'].strftime('%Y-%m-%d'),
                'invested_value': round(max(0, current_invested), 2),
                'available_cash': round(current_cash, 2),
                'total_value': round(current_total, 2),
                'invested_pct': round((max(0, current_invested) / current_total * 100) if current_total > 0 else 0, 2)
            })
        
        return timeline
    
    def _empty_metrics(self) -> Dict[str, Any]:
        """Return empty metrics structure"""
        return {
            'totalReturn': 0.0,
            'annualizedReturn': 0.0,
            'winRate': 0.0,
            'profitFactor': 0.0,
            'averageWin': 0.0,
            'averageLoss': 0.0,
            'maxDrawdown': 0.0,
            'sharpeRatio': 0.0,
            'totalTrades': 0,
            'winningTrades': 0,
            'losingTrades': 0,
            'averageHoldingPeriod': 0.0,
            'maxConsecutiveWins': 0,
            'maxConsecutiveLosses': 0,
            'grossProfit': 0.0,
            'grossLoss': 0.0,
            'totalPnL': 0.0
        }
    
    def _max_consecutive(self, binary_series: pd.Series) -> int:
        """Calculate maximum consecutive 1s in a binary series"""
        if binary_series.empty:
            return 0
        
        max_count = 0
        current_count = 0
        
        for value in binary_series:
            if value == 1:
                current_count += 1
                max_count = max(max_count, current_count)
            else:
                current_count = 0
        
        return max_count


def analyze_symbol_correlation(
    symbol_trades: Dict[str, pd.DataFrame]
) -> pd.DataFrame:
    """
    Analyze correlation between returns of different symbols.
    
    Args:
        symbol_trades: Dict mapping symbol to DataFrame of trades
    
    Returns:
        Correlation matrix as DataFrame
    """
    if not symbol_trades:
        return pd.DataFrame()
    
    # Build returns series for each symbol
    returns_dict = {}
    
    for symbol, trades in symbol_trades.items():
        if trades.empty:
            continue
        
        # Use trade returns indexed by exit date
        trades_sorted = trades.sort_values('exit_date')
        returns_dict[symbol] = pd.Series(
            trades_sorted['pnl_pct'].values,
            index=pd.to_datetime(trades_sorted['exit_date'])
        )
    
    if not returns_dict:
        return pd.DataFrame()
    
    # Create DataFrame and calculate correlation
    returns_df = pd.DataFrame(returns_dict)
    
    # Fill missing values with 0 (days with no trades)
    returns_df = returns_df.fillna(0)
    
    # Calculate correlation
    correlation_matrix = returns_df.corr()
    
    return correlation_matrix
