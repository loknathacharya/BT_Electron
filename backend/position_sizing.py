"""
Position Sizing Module
Implements various position sizing methods for portfolio backtesting.
"""
from enum import Enum
from typing import Optional, Dict, Any
import numpy as np
import pandas as pd


class PositionSizingMethod(Enum):
    """Supported position sizing methods"""
    EQUAL_WEIGHT = "equal_weight"
    FIXED_AMOUNT = "fixed_amount"
    PERCENT_RISK = "percent_risk"
    VOLATILITY_TARGET = "volatility_target"
    ATR_BASED = "atr_based"
    KELLY_CRITERION = "kelly_criterion"


class PositionSizer:
    """
    Calculates position sizes using various methods.
    
    This class implements 6 different position sizing methods:
    1. Equal Weight: Fixed percentage of portfolio per position (default 2%)
    2. Fixed Amount: Same dollar amount per trade
    3. Percent Risk: Size based on risk per trade (using stop-loss)
    4. Volatility Target: Size inversely proportional to volatility
    5. ATR-based: Size based on Average True Range
    6. Kelly Criterion: Optimal size based on win rate and avg win/loss
    """
    
    def __init__(
        self,
        method: PositionSizingMethod,
        risk_per_trade: float = 2.0,
        fixed_amount: float = 10000.0,
        volatility_target: float = 0.15,
        kelly_win_rate: float = 55.0,
        kelly_avg_win: float = 8.0,
        kelly_avg_loss: float = -4.0,
        atr_multiplier: float = 2.0,
        **kwargs
    ):
        """
        Initialize position sizer with method and parameters.
        
        Args:
            method: Position sizing method to use
            risk_per_trade: Risk per trade as % of portfolio (for percent_risk method)
            fixed_amount: Fixed dollar amount per trade (for fixed_amount method)
            volatility_target: Target portfolio volatility (for volatility_target method)
            kelly_win_rate: Expected win rate % (for kelly_criterion method)
            kelly_avg_win: Average win % (for kelly_criterion method)
            kelly_avg_loss: Average loss % (for kelly_criterion method)
            atr_multiplier: ATR multiplier for stop-loss (for atr_based method)
        """
        self.method = method
        self.risk_per_trade = risk_per_trade / 100.0  # Convert to decimal
        self.fixed_amount = fixed_amount
        self.volatility_target = volatility_target
        self.kelly_win_rate = kelly_win_rate / 100.0  # Convert to decimal
        self.kelly_avg_win = abs(kelly_avg_win) / 100.0  # Convert to decimal
        self.kelly_avg_loss = abs(kelly_avg_loss) / 100.0  # Convert to decimal
        self.atr_multiplier = atr_multiplier
    
    def calculate_shares(
        self,
        entry_price: float,
        portfolio_value: float,
        stop_loss_pct: Optional[float] = None,
        volatility: Optional[float] = None,
        atr: Optional[float] = None,
        open_positions_value: float = 0.0,
        allow_leverage: bool = False
    ) -> int:
        """
        Calculate number of shares to trade based on the selected method.
        
        Args:
            entry_price: Price at which to enter the position
            portfolio_value: Current total portfolio value
            stop_loss_pct: Stop-loss percentage (required for percent_risk method)
            volatility: Historical volatility (required for volatility_target method)
            atr: Average True Range value (required for atr_based method)
            open_positions_value: Total value of currently open positions
            allow_leverage: Whether to allow positions exceeding available capital
        
        Returns:
            Number of shares to trade (0 if insufficient capital or invalid inputs)
        """
        if entry_price <= 0 or portfolio_value <= 0:
            return 0
        
        # Calculate available capital
        available_capital = portfolio_value - open_positions_value
        if not allow_leverage and available_capital <= 0:
            return 0
        
        # Calculate position size based on method
        position_value = 0.0
        
        if self.method == PositionSizingMethod.EQUAL_WEIGHT:
            # 2% of portfolio per position
            position_value = portfolio_value * 0.02
        
        elif self.method == PositionSizingMethod.FIXED_AMOUNT:
            # Fixed dollar amount
            position_value = self.fixed_amount
        
        elif self.method == PositionSizingMethod.PERCENT_RISK:
            # Size based on risk per trade
            if stop_loss_pct is None or stop_loss_pct <= 0:
                # Fallback to equal weight if no stop-loss provided
                position_value = portfolio_value * 0.02
            else:
                # Position size = (Portfolio × Risk %) / Stop Loss %
                # Example: ($100,000 × 2%) / 5% = $40,000 position
                risk_amount = portfolio_value * self.risk_per_trade
                stop_loss_decimal = stop_loss_pct / 100.0
                position_value = risk_amount / stop_loss_decimal
        
        elif self.method == PositionSizingMethod.VOLATILITY_TARGET:
            # Size inversely proportional to volatility
            if volatility is None or volatility <= 0:
                # Fallback to equal weight if no volatility provided
                position_value = portfolio_value * 0.02
            else:
                # Position size = (Portfolio × Target Vol) / Instrument Vol
                # Example: ($100,000 × 15%) / 25% = $60,000 position
                position_value = (portfolio_value * self.volatility_target) / volatility
        
        elif self.method == PositionSizingMethod.ATR_BASED:
            # Size based on ATR (volatility-adjusted)
            if atr is None or atr <= 0:
                # Fallback to equal weight if no ATR provided
                position_value = portfolio_value * 0.02
            else:
                # Position size = Risk Amount / (ATR × Multiplier)
                # Example: $2,000 / ($5 ATR × 2) = 200 shares → $50,000 position at $250/share
                risk_amount = portfolio_value * self.risk_per_trade
                atr_stop_distance = atr * self.atr_multiplier
                shares = risk_amount / atr_stop_distance
                position_value = shares * entry_price
        
        elif self.method == PositionSizingMethod.KELLY_CRITERION:
            # Optimal size based on Kelly formula
            # Kelly % = W - [(1-W) / (AvgWin/AvgLoss)]
            # Where W = win rate
            if self.kelly_win_rate <= 0 or self.kelly_avg_win <= 0 or self.kelly_avg_loss <= 0:
                # Fallback to equal weight if invalid parameters
                position_value = portfolio_value * 0.02
            else:
                win_loss_ratio = self.kelly_avg_win / self.kelly_avg_loss
                kelly_pct = self.kelly_win_rate - ((1 - self.kelly_win_rate) / win_loss_ratio)
                
                # Cap Kelly % at 20% to avoid over-aggressive sizing
                kelly_pct = max(0.0, min(kelly_pct, 0.20))
                
                # Apply fractional Kelly (25%) for conservative sizing
                fractional_kelly = kelly_pct * 0.25
                position_value = portfolio_value * fractional_kelly
        
        # Apply leverage constraint if not allowed
        if not allow_leverage:
            position_value = min(position_value, available_capital)
        
        # Convert position value to shares
        shares = int(position_value / entry_price)
        
        return max(0, shares)
    
    def calculate_volatility(
        self,
        price_data: pd.Series,
        window: int = 20
    ) -> float:
        """
        Calculate rolling volatility (annualized standard deviation of returns).
        
        Args:
            price_data: Series of prices (e.g., close prices)
            window: Number of periods for rolling calculation
        
        Returns:
            Annualized volatility as a decimal (e.g., 0.25 = 25%)
        """
        if len(price_data) < window + 1:
            return 0.0
        
        # Calculate returns
        returns = price_data.pct_change().dropna()
        
        if len(returns) < window:
            return 0.0
        
        # Calculate rolling volatility (standard deviation)
        rolling_std = returns.rolling(window=window).std()
        
        # Annualize (assuming 252 trading days per year)
        annualized_vol = rolling_std.iloc[-1] * np.sqrt(252)
        
        return float(annualized_vol) if not np.isnan(annualized_vol) else 0.0
    
    def calculate_atr(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14
    ) -> float:
        """
        Calculate Average True Range (ATR).
        
        Args:
            high: Series of high prices
            low: Series of low prices
            close: Series of close prices
            period: Number of periods for ATR calculation
        
        Returns:
            ATR value
        """
        if len(high) < period + 1 or len(low) < period + 1 or len(close) < period + 1:
            return 0.0
        
        # Calculate True Range components
        tr1 = high - low  # High - Low
        tr2 = abs(high - close.shift(1))  # |High - Previous Close|
        tr3 = abs(low - close.shift(1))   # |Low - Previous Close|
        
        # True Range is the maximum of the three
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Calculate ATR as exponential moving average of True Range
        atr = true_range.ewm(span=period, adjust=False).mean()
        
        return float(atr.iloc[-1]) if not atr.empty and not np.isnan(atr.iloc[-1]) else 0.0
    
    def get_method_description(self) -> str:
        """Get a human-readable description of the current method"""
        descriptions = {
            PositionSizingMethod.EQUAL_WEIGHT: "Equal Weight (2% per position)",
            PositionSizingMethod.FIXED_AMOUNT: f"Fixed Amount (${self.fixed_amount:,.0f} per trade)",
            PositionSizingMethod.PERCENT_RISK: f"Percent Risk ({self.risk_per_trade * 100:.1f}% risk per trade)",
            PositionSizingMethod.VOLATILITY_TARGET: f"Volatility Target ({self.volatility_target * 100:.0f}% target vol)",
            PositionSizingMethod.ATR_BASED: f"ATR-based ({self.atr_multiplier}× ATR stop)",
            PositionSizingMethod.KELLY_CRITERION: f"Kelly Criterion ({self.kelly_win_rate * 100:.0f}% win rate, fractional)"
        }
        return descriptions.get(self.method, "Unknown method")
    
    def get_required_data(self) -> Dict[str, bool]:
        """
        Get which data fields are required for the current method.
        
        Returns:
            Dict mapping field names to whether they're required
        """
        requirements = {
            "stop_loss_pct": False,
            "volatility": False,
            "atr": False,
            "price_history": False
        }
        
        if self.method == PositionSizingMethod.PERCENT_RISK:
            requirements["stop_loss_pct"] = True
        
        elif self.method == PositionSizingMethod.VOLATILITY_TARGET:
            requirements["volatility"] = True
            requirements["price_history"] = True
        
        elif self.method == PositionSizingMethod.ATR_BASED:
            requirements["atr"] = True
            requirements["price_history"] = True  # Need OHLC data
        
        return requirements


def create_position_sizer(config: Dict[str, Any]) -> PositionSizer:
    """
    Factory function to create a PositionSizer from configuration dict.
    
    Args:
        config: Configuration dict with keys:
            - method: Position sizing method name (string)
            - risk_per_trade: Risk per trade % (optional)
            - fixed_amount: Fixed dollar amount (optional)
            - volatility_target: Target volatility % (optional)
            - kelly_win_rate: Expected win rate % (optional)
            - kelly_avg_win: Average win % (optional)
            - kelly_avg_loss: Average loss % (optional)
            - atr_multiplier: ATR multiplier (optional)
    
    Returns:
        Configured PositionSizer instance
    
    Raises:
        ValueError: If method is invalid or missing
    """
    method_str = config.get('method', 'equal_weight').upper()
    
    try:
        method = PositionSizingMethod[method_str]
    except KeyError:
        raise ValueError(f"Invalid position sizing method: {method_str}")
    
    return PositionSizer(
        method=method,
        risk_per_trade=config.get('risk_per_trade', 2.0),
        fixed_amount=config.get('fixed_amount', 10000.0),
        volatility_target=config.get('volatility_target', 15.0) / 100.0,  # Convert to decimal
        kelly_win_rate=config.get('kelly_win_rate', 55.0),
        kelly_avg_win=config.get('kelly_avg_win', 8.0),
        kelly_avg_loss=config.get('kelly_avg_loss', 4.0),  # Note: will be converted to positive
        atr_multiplier=config.get('atr_multiplier', 2.0)
    )
