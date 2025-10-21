"""
Unit tests for position_sizing module
Tests all 6 position sizing methods and edge cases
"""
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / 'backend'
sys.path.insert(0, str(backend_path))

import pytest
import pandas as pd
import numpy as np
from position_sizing import (
    PositionSizer,
    PositionSizingMethod,
    create_position_sizer
)


class TestPositionSizer:
    """Test PositionSizer class"""
    
    def test_equal_weight_basic(self):
        """Test equal weight sizing returns 2% of portfolio"""
        sizer = PositionSizer(method=PositionSizingMethod.EQUAL_WEIGHT)
        
        shares = sizer.calculate_shares(
            entry_price=100.0,
            portfolio_value=50000.0
        )
        
        # 2% of $50,000 = $1,000 / $100 = 10 shares
        assert shares == 10
    
    def test_equal_weight_with_open_positions(self):
        """Test equal weight respects available capital"""
        sizer = PositionSizer(method=PositionSizingMethod.EQUAL_WEIGHT)
        
        shares = sizer.calculate_shares(
            entry_price=100.0,
            portfolio_value=50000.0,
            open_positions_value=40000.0,
            allow_leverage=False
        )
        
        # Available capital = $10,000
        # 2% of $50,000 = $1,000 / $100 = 10 shares
        # But limited by available capital: $10,000 / $100 = 100 max
        # Should get 10 shares (equal weight)
        assert shares == 10
    
    def test_equal_weight_insufficient_capital(self):
        """Test equal weight returns 0 when insufficient capital"""
        sizer = PositionSizer(method=PositionSizingMethod.EQUAL_WEIGHT)
        
        shares = sizer.calculate_shares(
            entry_price=100.0,
            portfolio_value=50000.0,
            open_positions_value=50000.0,
            allow_leverage=False
        )
        
        # No available capital
        assert shares == 0
    
    def test_fixed_amount_basic(self):
        """Test fixed amount sizing"""
        sizer = PositionSizer(
            method=PositionSizingMethod.FIXED_AMOUNT,
            fixed_amount=10000.0
        )
        
        shares = sizer.calculate_shares(
            entry_price=100.0,
            portfolio_value=100000.0
        )
        
        # $10,000 / $100 = 100 shares
        assert shares == 100
    
    def test_fixed_amount_limited_by_capital(self):
        """Test fixed amount limited by available capital"""
        sizer = PositionSizer(
            method=PositionSizingMethod.FIXED_AMOUNT,
            fixed_amount=10000.0
        )
        
        shares = sizer.calculate_shares(
            entry_price=100.0,
            portfolio_value=15000.0,
            open_positions_value=10000.0,
            allow_leverage=False
        )
        
        # Available capital = $5,000
        # Want $10,000 position but limited to $5,000
        # $5,000 / $100 = 50 shares
        assert shares == 50
    
    def test_percent_risk_with_stop_loss(self):
        """Test percent risk sizing with stop-loss"""
        sizer = PositionSizer(
            method=PositionSizingMethod.PERCENT_RISK,
            risk_per_trade=2.0  # 2% risk
        )
        
        shares = sizer.calculate_shares(
            entry_price=100.0,
            portfolio_value=100000.0,
            stop_loss_pct=5.0  # 5% stop-loss
        )
        
        # Risk amount = $100,000 × 2% = $2,000
        # Position size = $2,000 / 5% = $40,000
        # Shares = $40,000 / $100 = 400
        assert shares == 400
    
    def test_percent_risk_without_stop_loss(self):
        """Test percent risk falls back to equal weight without stop-loss"""
        sizer = PositionSizer(
            method=PositionSizingMethod.PERCENT_RISK,
            risk_per_trade=2.0
        )
        
        shares = sizer.calculate_shares(
            entry_price=100.0,
            portfolio_value=50000.0,
            stop_loss_pct=None  # No stop-loss provided
        )
        
        # Should fallback to equal weight: 2% of $50,000 = $1,000 / $100 = 10
        assert shares == 10
    
    def test_volatility_target_basic(self):
        """Test volatility target sizing"""
        sizer = PositionSizer(
            method=PositionSizingMethod.VOLATILITY_TARGET,
            volatility_target=0.15  # 15% target
        )
        
        shares = sizer.calculate_shares(
            entry_price=100.0,
            portfolio_value=100000.0,
            volatility=0.25  # 25% instrument volatility
        )
        
        # Position size = ($100,000 × 15%) / 25% = $60,000
        # Shares = $60,000 / $100 = 600
        assert shares == 600
    
    def test_volatility_target_without_volatility(self):
        """Test volatility target falls back without volatility data"""
        sizer = PositionSizer(
            method=PositionSizingMethod.VOLATILITY_TARGET,
            volatility_target=0.15
        )
        
        shares = sizer.calculate_shares(
            entry_price=100.0,
            portfolio_value=50000.0,
            volatility=None  # No volatility provided
        )
        
        # Should fallback to equal weight: 2% of $50,000 = $1,000 / $100 = 10
        assert shares == 10
    
    def test_atr_based_basic(self):
        """Test ATR-based sizing"""
        sizer = PositionSizer(
            method=PositionSizingMethod.ATR_BASED,
            risk_per_trade=2.0,  # 2% risk
            atr_multiplier=2.0
        )
        
        shares = sizer.calculate_shares(
            entry_price=250.0,
            portfolio_value=100000.0,
            atr=5.0  # $5 ATR
        )
        
        # Risk amount = $100,000 × 2% = $2,000
        # ATR stop distance = $5 × 2 = $10
        # Shares = $2,000 / $10 = 200
        # Position value = 200 × $250 = $50,000
        assert shares == 200
    
    def test_atr_based_without_atr(self):
        """Test ATR-based falls back without ATR data"""
        sizer = PositionSizer(
            method=PositionSizingMethod.ATR_BASED,
            risk_per_trade=2.0,
            atr_multiplier=2.0
        )
        
        shares = sizer.calculate_shares(
            entry_price=100.0,
            portfolio_value=50000.0,
            atr=None  # No ATR provided
        )
        
        # Should fallback to equal weight: 2% of $50,000 = $1,000 / $100 = 10
        assert shares == 10
    
    def test_kelly_criterion_basic(self):
        """Test Kelly Criterion sizing"""
        sizer = PositionSizer(
            method=PositionSizingMethod.KELLY_CRITERION,
            kelly_win_rate=55.0,  # 55% win rate (passed as percentage, converted inside)
            kelly_avg_win=8.0,    # 8% average win
            kelly_avg_loss=4.0    # 4% average loss (will be converted to positive inside)
        )
        
        shares = sizer.calculate_shares(
            entry_price=100.0,
            portfolio_value=100000.0
        )
        
        # Kelly % = 0.55 - ((1-0.55) / (0.08/0.04)) = 0.55 - 0.225 = 0.325
        # Capped at 20% = 0.20
        # Fractional Kelly (25%) = 0.20 × 0.25 = 0.05
        # Position = $100,000 × 0.05 = $5,000
        # Shares = $5,000 / $100 = 50
        assert shares == 50
    
    def test_kelly_criterion_capped(self):
        """Test Kelly Criterion caps at 20%"""
        sizer = PositionSizer(
            method=PositionSizingMethod.KELLY_CRITERION,
            kelly_win_rate=90.0,  # Very high win rate
            kelly_avg_win=20.0,
            kelly_avg_loss=2.0
        )
        
        shares = sizer.calculate_shares(
            entry_price=100.0,
            portfolio_value=100000.0
        )
        
        # Kelly would be high, but capped at 20%
        # Fractional Kelly (25%) = 0.20 × 0.25 = 0.05
        # Position = $100,000 × 0.05 = $5,000
        # Shares = $5,000 / $100 = 50
        assert shares == 50
    
    def test_leverage_allowed(self):
        """Test sizing when leverage is allowed"""
        sizer = PositionSizer(method=PositionSizingMethod.EQUAL_WEIGHT)
        
        shares = sizer.calculate_shares(
            entry_price=100.0,
            portfolio_value=50000.0,
            open_positions_value=49000.0,
            allow_leverage=True  # Allow leverage
        )
        
        # 2% of $50,000 = $1,000 / $100 = 10 shares
        # Even though only $1,000 cash available
        assert shares == 10
    
    def test_leverage_not_allowed(self):
        """Test sizing limited by available capital when leverage not allowed"""
        sizer = PositionSizer(method=PositionSizingMethod.EQUAL_WEIGHT)
        
        shares = sizer.calculate_shares(
            entry_price=100.0,
            portfolio_value=50000.0,
            open_positions_value=49500.0,
            allow_leverage=False  # No leverage
        )
        
        # Only $500 available, can only buy 5 shares
        assert shares == 5
    
    def test_zero_price(self):
        """Test sizing returns 0 for zero price"""
        sizer = PositionSizer(method=PositionSizingMethod.EQUAL_WEIGHT)
        
        shares = sizer.calculate_shares(
            entry_price=0.0,  # Invalid price
            portfolio_value=50000.0
        )
        
        assert shares == 0
    
    def test_zero_portfolio(self):
        """Test sizing returns 0 for zero portfolio value"""
        sizer = PositionSizer(method=PositionSizingMethod.EQUAL_WEIGHT)
        
        shares = sizer.calculate_shares(
            entry_price=100.0,
            portfolio_value=0.0  # No capital
        )
        
        assert shares == 0
    
    def test_calculate_volatility(self):
        """Test volatility calculation"""
        sizer = PositionSizer(method=PositionSizingMethod.EQUAL_WEIGHT)
        
        # Create sample price series with known volatility
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        prices = pd.Series(100 + np.random.randn(100) * 2, index=dates)
        
        vol = sizer.calculate_volatility(prices, window=20)
        
        # Should return a positive volatility value
        assert vol > 0
        assert vol < 1.0  # Should be reasonable (< 100%)
    
    def test_calculate_atr(self):
        """Test ATR calculation"""
        sizer = PositionSizer(method=PositionSizingMethod.EQUAL_WEIGHT)
        
        # Create sample OHLC data
        dates = pd.date_range('2024-01-01', periods=50, freq='D')
        base = 100
        high = pd.Series([base + np.random.rand() * 5 for _ in range(50)], index=dates)
        low = pd.Series([base - np.random.rand() * 5 for _ in range(50)], index=dates)
        close = pd.Series([base + np.random.randn() * 2 for _ in range(50)], index=dates)
        
        atr = sizer.calculate_atr(high, low, close, period=14)
        
        # Should return a positive ATR value
        assert atr > 0
        assert atr < 20  # Should be reasonable
    
    def test_get_method_description(self):
        """Test method descriptions"""
        sizer = PositionSizer(method=PositionSizingMethod.EQUAL_WEIGHT)
        desc = sizer.get_method_description()
        assert 'Equal Weight' in desc
        
        sizer2 = PositionSizer(method=PositionSizingMethod.KELLY_CRITERION)
        desc2 = sizer2.get_method_description()
        assert 'Kelly' in desc2
    
    def test_get_required_data(self):
        """Test required data checking"""
        sizer = PositionSizer(method=PositionSizingMethod.PERCENT_RISK)
        requirements = sizer.get_required_data()
        
        assert requirements['stop_loss_pct'] == True
        assert requirements['volatility'] == False
        
        sizer2 = PositionSizer(method=PositionSizingMethod.VOLATILITY_TARGET)
        requirements2 = sizer2.get_required_data()
        
        assert requirements2['volatility'] == True
        assert requirements2['stop_loss_pct'] == False


class TestCreatePositionSizer:
    """Test factory function"""
    
    def test_create_equal_weight(self):
        """Test creating equal weight sizer from config"""
        config = {'method': 'equal_weight'}
        sizer = create_position_sizer(config)
        
        assert sizer.method == PositionSizingMethod.EQUAL_WEIGHT
    
    def test_create_kelly_with_params(self):
        """Test creating Kelly sizer with parameters"""
        config = {
            'method': 'kelly_criterion',
            'kelly_win_rate': 60.0,
            'kelly_avg_win': 10.0,
            'kelly_avg_loss': 5.0
        }
        sizer = create_position_sizer(config)
        
        assert sizer.method == PositionSizingMethod.KELLY_CRITERION
        assert sizer.kelly_win_rate == 0.60  # Converted to decimal
        assert sizer.kelly_avg_win == 0.10
    
    def test_create_invalid_method(self):
        """Test creating sizer with invalid method raises error"""
        config = {'method': 'invalid_method'}
        
        with pytest.raises(ValueError):
            create_position_sizer(config)
    
    def test_create_with_defaults(self):
        """Test creating sizer uses defaults for missing parameters"""
        config = {'method': 'percent_risk'}
        sizer = create_position_sizer(config)
        
        assert sizer.method == PositionSizingMethod.PERCENT_RISK
        assert sizer.risk_per_trade == 0.02  # Default 2%


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
