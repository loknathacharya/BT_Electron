# Enhanced BT.py with Long/Short support and improved UI
#vectorized backtesting and position sizing 
# After removing debugging codes
from pygments import highlight
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import pandas as pd
from numba import jit, prange
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing as mp
from typing import List, Tuple, Dict, Optional
from pandas.api.types import is_datetime64_any_dtype
from itertools import product
import seaborn as sns
import matplotlib.pyplot as plt
from datetime import timedelta, datetime

# --- Enhanced Helper Functions ---

def calculate_position_size(sizing_method, entry_price, portfolio_value, volatility=None, atr=None, risk_per_trade=2.0,
                          fixed_amount=10000, volatility_target=0.15, kelly_win_rate=None, kelly_avg_win=None, kelly_avg_loss=None,
                          allow_leverage=False, open_positions_value=0):
    """
    Calculate position size based on different sizing methods with robust leverage control.
    """
    
    
    # --- Step 1: Calculate initial shares based on the selected sizing method ---
    if sizing_method == 'equal_weight':
        position_value = portfolio_value * 0.02
        shares = position_value / entry_price
        
    elif sizing_method == 'fixed_amount':
        shares = fixed_amount / entry_price
        
    elif sizing_method == 'percent_risk':
        risk_amount = portfolio_value * (risk_per_trade / 100)
        stop_distance = entry_price * 0.05
        shares = risk_amount / stop_distance
        
    elif sizing_method == 'volatility_target':
        if volatility is None or volatility == 0: volatility = 0.20
        target_position_vol = portfolio_value * volatility_target
        position_value = target_position_vol / volatility
        shares = position_value / entry_price
        
    elif sizing_method == 'atr_based':
        if atr is None or atr == 0: atr = entry_price * 0.02
        risk_amount = portfolio_value * (risk_per_trade / 100)
        shares = risk_amount / (2 * atr)
        
    elif sizing_method == 'kelly_criterion':
        if kelly_win_rate and kelly_avg_win and kelly_avg_loss and kelly_avg_loss != 0:
            win_prob = kelly_win_rate / 100
            avg_win_decimal = kelly_avg_win / 100
            avg_loss_decimal = abs(kelly_avg_loss / 100)
            if avg_loss_decimal > 0:
                b = avg_win_decimal / avg_loss_decimal
                kelly_fraction = (b * win_prob - (1 - win_prob)) / b
                kelly_fraction = max(0, min(kelly_fraction, 0.25))
            else:
                kelly_fraction = 0.02
        else:
            kelly_fraction = 0.02
        position_value = portfolio_value * kelly_fraction
        shares = position_value / entry_price
    
    else: # Default to equal weight
        position_value = portfolio_value * 0.02
        shares = position_value / entry_price

    # --- Step 2: Apply leverage and capital constraints ---

    # General sanity check: cap shares to not exceed total portfolio value in a single trade
    shares = min(shares, portfolio_value / entry_price)

    # Apply the no-leverage constraint as the final, overriding rule
    if not allow_leverage:
        available_capital = portfolio_value - open_positions_value
        # If there's no capital available, we can't open a position
        if available_capital <= 0:
            return 0
        
        max_shares_available = available_capital / entry_price
        shares = min(shares, max_shares_available)

    # --- Step 3: Finalize share count ---
    # Return the whole number of shares, ensuring it's not negative.
    # Returning 0 shares is a valid outcome if capital is insufficient for even one share.
    result = max(0, np.floor(shares))
    return result

def calculate_volatility(price_data, window=20):
    """Calculate rolling volatility"""
    returns = price_data.pct_change().dropna()
    volatility = returns.rolling(window=window).std() * np.sqrt(252)  # Annualized
    return volatility.iloc[-1] if not volatility.empty else 0.20

def calculate_atr(high, low, close, window=14):
    """Calculate Average True Range"""
    high_low = high - low
    high_close = np.abs(high - close.shift())
    low_close = np.abs(low - close.shift())
    
    true_range = np.maximum(high_low, np.maximum(high_close, low_close))
    atr = true_range.rolling(window=window).mean()
    
    return atr.iloc[-1] if not atr.empty else close.iloc[-1] * 0.02

@jit(nopython=True)
def calculate_trade_outcomes_vectorized(prices: np.ndarray, entry_idx: int, holding_period: int,
                                      stop_loss_pct: float, take_profit_pct: Optional[float],
                                      signal_type: str) -> Tuple[int, float, str]:
    """
    Vectorized calculation of trade outcomes using Numba for speed
    """
    if entry_idx >= len(prices) - 1:
        return -1, 0.0, "No Data"
    
    entry_price = prices[entry_idx, 3]  # Close price
    
    # Determine stop loss and take profit prices based on signal type
    if signal_type == 'long':
        stop_loss_price = entry_price * (1 - stop_loss_pct / 100)
        take_profit_price = entry_price * (1 + take_profit_pct / 100) if take_profit_pct is not None else np.inf
        position_multiplier = 1.0
    else:  # short
        stop_loss_price = entry_price * (1 + stop_loss_pct / 100)
        take_profit_price = entry_price * (1 - take_profit_pct / 100) if take_profit_pct is not None else -np.inf
        position_multiplier = -1.0
    
    # Check each day for stop loss or take profit
    end_idx = min(entry_idx + holding_period + 1, len(prices))
    

    for i in range(entry_idx + 1, end_idx):
        high = prices[i, 1]
        low = prices[i, 2]
        
        if signal_type == 'long':
            if low <= stop_loss_price:
                return i, stop_loss_price, "Stop Loss"
            elif take_profit_pct and high >= take_profit_price:
                return i, take_profit_price, "Take Profit"
        else:  # short
            if high >= stop_loss_price:
                return i, stop_loss_price, "Stop Loss"
            elif take_profit_pct and low <= take_profit_price:
                return i, take_profit_price, "Take Profit"
    
    # Time exit
    if end_idx > entry_idx + 1:
        final_idx = end_idx - 1
        final_price = prices[final_idx, 3]  # Close price
        return final_idx, final_price, "Time Exit"
    
    return -1, 0.0, "No Data"

@jit(nopython=True)
def calculate_position_size_vectorized(sizing_method_code: int, entry_price: float,
                                     portfolio_value: float, volatility: float,
                                     atr: float, risk_per_trade: float,
                                     fixed_amount: float, volatility_target: float = 0.15,
                                     stop_loss_assumption: float = 0.05, allow_leverage: bool = True,
                                     kelly_win_rate: float = 55, kelly_avg_win: float = 8,
                                     kelly_avg_loss: float = -4, open_positions_value: float = 0.0) -> float:
    """
    Vectorized position sizing calculation
    sizing_method_code: 0=equal_weight, 1=fixed_amount, 2=percent_risk, 3=volatility_target, 4=atr_based, 5=kelly_criterion
    """
    if sizing_method_code == 0:  # equal_weight
        position_value = portfolio_value * 0.02
        shares = position_value / entry_price
    elif sizing_method_code == 1:  # fixed_amount
        shares = fixed_amount / entry_price
    elif sizing_method_code == 2:  # percent_risk
        risk_amount = portfolio_value * (risk_per_trade / 100)
        stop_distance = entry_price * stop_loss_assumption  # Configurable stop assumption
        shares = risk_amount / stop_distance
    elif sizing_method_code == 3:  # volatility_target
        if volatility == 0:
            volatility = 0.20
        target_position_vol = portfolio_value * volatility_target  # Use parameter
        position_value = target_position_vol / volatility
        shares = position_value / entry_price
    elif sizing_method_code == 4:  # atr_based
        if atr == 0:
            atr = entry_price * 0.02
        risk_amount = portfolio_value * (risk_per_trade / 100)
        shares = risk_amount / (2 * atr)
    elif sizing_method_code == 5:  # kelly_criterion
        # Kelly criterion sizing using passed parameters
        win_prob = kelly_win_rate / 100  # Convert percentage to decimal
        avg_win_decimal = abs(kelly_avg_win) / 100  # Convert percentage to decimal
        avg_loss_decimal = abs(kelly_avg_loss) / 100  # Convert percentage to decimal (make positive)
        
        # Kelly formula: f = (bp - q) / b
        # where b = avg_win/avg_loss, p = win_prob, q = 1-win_prob
        if avg_loss_decimal > 0:
            b = avg_win_decimal / avg_loss_decimal
            kelly_fraction = (b * win_prob - (1 - win_prob)) / b
            kelly_fraction = max(0, min(kelly_fraction, 0.25))  # Cap at 25%
        else:
            kelly_fraction = 0.02
        
        position_value = portfolio_value * kelly_fraction
        shares = position_value / entry_price
    else:
        shares = portfolio_value * 0.02 / entry_price
    
    # Ensure reasonable bounds
    max_shares = portfolio_value / entry_price
    shares = min(shares, max_shares)
    
    # Apply leverage constraint if not allowed
    if not allow_leverage:
        available_capital = portfolio_value - open_positions_value
        if available_capital <= 0:
            return 0.0
        max_shares_no_leverage = available_capital / entry_price
        shares = min(shares, max_shares_no_leverage)
    
    # Return the whole number of shares, ensuring it's not negative.
    # Returning 0 shares is a valid outcome if capital is insufficient for even one share.
    result = max(0, np.floor(shares))
    return result

def prepare_vectorized_data(ohlcv_df: pd.DataFrame) -> Dict[str, np.ndarray]:
    """
    Prepare OHLCV data in vectorized format for faster processing
    """
    vectorized_data = {}
    
    for ticker in ohlcv_df['Ticker'].unique():
        ticker_data = ohlcv_df[ohlcv_df['Ticker'] == ticker].sort_values('Date')
        
        # Create numpy array: [Date_ordinal, High, Low, Close, Volume]
        dates = ticker_data['Date'].map(pd.Timestamp.toordinal).values
        prices = ticker_data[['High', 'Low', 'Close']].values
        
        # Combine dates and prices
        combined = np.column_stack([dates, prices])
        vectorized_data[ticker] = combined
    
    return vectorized_data

def run_single_parameter_combo(args: Tuple) -> Dict:
    """
    Run backtest for a single parameter combination - designed for single-threaded processing
    """
    (vectorized_data, signals_data, hp, sl, tp, signal_type,
     initial_capital, sizing_method, sizing_params, one_trade_per_instrument, allow_leverage) = args
    
    
    trades = []
    portfolio_value = initial_capital
    active_trades = {}
    open_positions_value = 0.0 # Initialize for vectorized mode
    
    # Convert sizing method to code for numba
    method_map = {'equal_weight': 0, 'fixed_amount': 1, 'percent_risk': 2,
                  'volatility_target': 3, 'atr_based': 4, 'kelly_criterion': 5}
    sizing_code = method_map.get(sizing_method, 0)
    
    
    # Process each signal
    for _, signal in signals_data.iterrows():
        ticker = signal['Ticker']
        entry_date_ordinal = pd.Timestamp(signal['Date']).toordinal()
        
        # Skip if one trade per instrument and active trade exists
        if one_trade_per_instrument and ticker in active_trades:
            if entry_date_ordinal <= active_trades[ticker]:
                continue
            else:
                del active_trades[ticker]
        
        if ticker not in vectorized_data:
            continue
            
        ticker_prices = vectorized_data[ticker]
        
        # Find entry point
        entry_indices = np.where(ticker_prices[:, 0] >= entry_date_ordinal)[0]
        if len(entry_indices) == 0:
            continue
            
        entry_idx = entry_indices[0]
        # Check if there's enough data for the full holding period
        if entry_idx + hp + 1 > len(ticker_prices):
            continue
            
        entry_price = ticker_prices[entry_idx, 3]
        
        # Calculate position size (pass user Kelly parameters if available)
        kelly_win_rate = sizing_params.get('kelly_win_rate', 55)
        kelly_avg_win = sizing_params.get('kelly_avg_win', 8)
        kelly_avg_loss = sizing_params.get('kelly_avg_loss', -4)
        
        shares = calculate_position_size_vectorized(
            sizing_code, entry_price, portfolio_value,
            0.20, entry_price * 0.02, sizing_params.get('risk_per_trade', 2.0),
            sizing_params.get('fixed_amount', 10000),
            sizing_params.get('volatility_target', 0.15),
            0.05,  # Default stop loss assumption for percent risk calculation
            allow_leverage,  # Use user's leverage setting
            kelly_win_rate, kelly_avg_win, kelly_avg_loss,
            open_positions_value # Pass open_positions_value
        )
        
        position_value = shares * entry_price
        
        # For no leverage mode, check if we have enough capital
        if not allow_leverage and open_positions_value + position_value > portfolio_value:
            continue  # Skip this trade as it would require leverage

        # Update open positions value
        open_positions_value += position_value

        
        # Calculate trade outcome
        exit_idx, exit_price, exit_reason = calculate_trade_outcomes_vectorized(
            ticker_prices, entry_idx, hp, sl, tp, signal_type
        )
        
        if exit_idx > 0 and exit_price > 0:
            # Calculate P&L
            if signal_type == 'long':
                pl_dollar = (exit_price - entry_price) * shares
                pl_pct = ((exit_price - entry_price) / entry_price) * 100
            else:  # short
                pl_dollar = (entry_price - exit_price) * shares
                pl_pct = ((entry_price - exit_price) / entry_price) * 100
            
            portfolio_value += pl_dollar
            
            # Update open positions value when trade exits
            open_positions_value -= position_value

            # Convert ordinal dates back to datetime for consistency with original format
            entry_date = pd.Timestamp.fromordinal(int(ticker_prices[entry_idx, 0]))
            exit_date = pd.Timestamp.fromordinal(int(ticker_prices[exit_idx, 0]))
            

            # Record trade with comprehensive data matching original format
            trades.append({
                'Ticker': ticker,
                'Signal Type': signal_type.title(),
                'Entry Date': entry_date,
                'Entry Price': entry_price,
                'Exit Date': exit_date,
                'Exit Price': exit_price,
                'Shares': shares,
                'Position Value': position_value,
                'P&L ($)': pl_dollar,
                'Profit/Loss (%)': pl_pct,
                'Exit Reason': exit_reason,
                'Days Held': exit_idx - entry_idx,
                'Portfolio Value': portfolio_value,
                'Signal Date': entry_date  # Same as entry date for simplicity
            })
            
            # Update active trades
            if one_trade_per_instrument:
                active_trades[ticker] = ticker_prices[exit_idx, 0]
    
    # Calculate performance metrics (matching original calculation)
    if not trades:
        return {
            'Holding Period': hp, 'Stop Loss (%)': sl, 'Take Profit (%)': tp or 0,
            'Total Return (%)': 0, 'Total P&L ($)': 0, 'Win Rate (%)': 0,
            'Max Drawdown (%)': 0, 'Profit Factor': 0, 'Sharpe Ratio': 0,
            'Calmar Ratio': 0, 'Average Win (%)': 0, 'Average Loss (%)': 0,
            'Average Win ($)': 0, 'Average Loss ($)': 0, 'Total Trades': 0,
            'Avg Position Size ($)': 0, 'Signal Type': signal_type.title()
        }
    
    trades_df = pd.DataFrame(trades)
    total_trades = len(trades_df)
    winners = trades_df[trades_df['Profit/Loss (%)'] > 0]
    losers = trades_df[trades_df['Profit/Loss (%)'] <= 0]
    
    # Basic metrics
    win_rate = (len(winners) / total_trades) * 100 if total_trades > 0 else 0
    avg_win = winners['Profit/Loss (%)'].mean() if not winners.empty else 0
    avg_loss = losers['Profit/Loss (%)'].mean() if not losers.empty else 0
    
    # Dollar-based metrics
    total_pl = trades_df['P&L ($)'].sum()
    avg_win_dollar = winners['P&L ($)'].mean() if not winners.empty else 0
    avg_loss_dollar = losers['P&L ($)'].mean() if not losers.empty else 0
    
    # Risk-adjusted metrics
    profit_factor = abs(winners['P&L ($)'].sum() / losers['P&L ($)'].sum()) if not losers.empty and losers['P&L ($)'].sum() != 0 else np.inf
    
    # Portfolio value progression - use final portfolio value for accurate return calculation
    final_portfolio_value = portfolio_value if trades else initial_capital
    total_return = ((final_portfolio_value - initial_capital) / initial_capital) * 100
    
    # DEBUG: Log vectorized return calculation
    print(f"DEBUG run_single_parameter_combo: Final portfolio value = ${final_portfolio_value:.2f}, Total return = {total_return:.2f}%")
    
    # Drawdown calculation using portfolio values
    cumulative_pl = trades_df['P&L ($)'].cumsum()
    running_max = (initial_capital + cumulative_pl).cummax()
    drawdown = ((initial_capital + cumulative_pl) - running_max) / running_max
    max_drawdown = drawdown.min() * 100 if not drawdown.empty else 0
    
    # Sharpe ratio (annualized) with risk-free rate
    returns = trades_df['P&L ($)'] / initial_capital
    if len(returns) > 1:
        excess_return = returns.mean() - 0.06/252  # Daily risk-free rate (6% annual)
        sharpe_ratio = (excess_return / returns.std()) * np.sqrt(252) if returns.std() != 0 else 0
    else:
        sharpe_ratio = 0
    
    # Calmar ratio
    calmar_ratio = total_return / abs(max_drawdown) if max_drawdown != 0 else 0
    
    return {
        'Holding Period': hp,
        'Stop Loss (%)': sl,
        'Take Profit (%)': tp or 0,
        'Total Return (%)': total_return,
        'Total P&L ($)': total_pl,
        'Win Rate (%)': win_rate,
        'Max Drawdown (%)': max_drawdown,
        'Profit Factor': profit_factor,
        'Sharpe Ratio': sharpe_ratio,
        'Calmar Ratio': calmar_ratio,
        'Average Win (%)': avg_win,
        'Average Loss (%)': avg_loss,
        'Average Win ($)': avg_win_dollar,
        'Average Loss ($)': avg_loss_dollar,
        'Total Trades': total_trades,
        'Avg Position Size ($)': trades_df['Position Value'].mean(),
        'Signal Type': signal_type.title()
    }
    

def run_vectorized_parameter_optimization(ohlcv_df, signals_df, holding_periods, stop_losses,
                                        take_profits=None, one_trade_per_instrument=False,
                                        initial_capital=100000, sizing_method='equal_weight',
                                        sizing_params=None, signal_type='long',
                                        use_multiprocessing=True, max_workers=None, allow_leverage=False):
    """
    Vectorized parameter optimization with multiprocessing support
    """
    if sizing_params is None:
        sizing_params = {}
    
    # Prepare vectorized data
    st.info("Preparing data for vectorized processing...")
    vectorized_data = prepare_vectorized_data(ohlcv_df)
    
    # Prepare parameter combinations
    if take_profits is not None and len(take_profits) > 0:
        param_combinations = [(hp, sl, tp) for hp in holding_periods
                             for sl in stop_losses for tp in take_profits]
    else:
        param_combinations = [(hp, sl, None) for hp in holding_periods for sl in stop_losses]
    
    total_combinations = len(param_combinations)
    
    # Prepare arguments for sequential processing
    args_list = []
    for hp, sl, tp in param_combinations:
        args = (vectorized_data, signals_df, hp, sl, tp, signal_type,
                initial_capital, sizing_method, sizing_params, one_trade_per_instrument, allow_leverage)
        args_list.append(args)
    
    # Progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    results = []
    
    if use_multiprocessing and len(param_combinations) > 4:
        # Use multiprocessing for large parameter spaces
        if max_workers is None:
            max_workers = min(mp.cpu_count() - 1, 8)  # Leave one core free, cap at 8
        
        status_text.text(f"Running vectorized optimization with {max_workers} processes...")
        
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit all jobs
            future_to_params = {executor.submit(run_single_parameter_combo, args): args
                               for args in args_list}
            
            completed = 0
            for future in as_completed(future_to_params):
                try:
                    result = future.result()
                    results.append(result)
                    completed += 1
                    progress_bar.progress(completed / total_combinations)
                    
                    if completed % max(1, total_combinations // 20) == 0:  # Update every 5%
                        status_text.text(f"Completed {completed}/{total_combinations} combinations ({completed/total_combinations*100:.1f}%)")
                        
                except Exception as exc:
                    st.warning(f"Parameter combination generated an exception: {exc}")
                    completed += 1
                    progress_bar.progress(completed / total_combinations)
    
    else:
        # Sequential processing for smaller parameter spaces or when multiprocessing is disabled
        status_text.text("Running sequential optimization...")
        for i, args in enumerate(args_list):
            try:
                result = run_single_parameter_combo(args)
                results.append(result)
                progress_bar.progress((i + 1) / total_combinations)
                
                if (i + 1) % max(1, total_combinations // 10) == 0:
                    status_text.text(f"Completed {i + 1}/{total_combinations} combinations")
                    
            except Exception as exc:
                st.warning(f"Parameter combination {i+1} generated an exception: {exc}")
    
    progress_bar.empty()
    status_text.empty()
    
    if results:
        st.success(f"Vectorized optimization completed! Processed {len(results)} combinations in parallel.")
        return pd.DataFrame(results)
    else:
        st.error("No valid results from vectorized optimization.")
        return pd.DataFrame()

def run_backtest(ohlcv_df, signals_df, holding_period, stop_loss_pct, take_profit_pct=None,
                one_trade_per_instrument=False, initial_capital=100000, sizing_method='equal_weight',
                sizing_params=None, signal_type='long', allow_leverage=False):
    """Enhanced backtest function with position sizing, long/short support and leverage control"""
    
    if sizing_params is None:
        sizing_params = {}
    
    trades = []
    active_trades = {}  # Track active trades per instrument {ticker: exit_date}
    portfolio_value = initial_capital
    open_positions_value = 0  # Track total value of open positions
    leverage_warnings = []  # Track leverage warnings
    
    # DEBUG: Log initial state
    print(f"DEBUG run_backtest: Initial capital={initial_capital}, signal_type={signal_type}, allow_leverage={allow_leverage}")
    
    # Sort signals by date to process chronologically
    signals_df_sorted = signals_df.sort_values('Date').reset_index(drop=True)
    
    # Calculate historical stats for Kelly criterion if needed
    kelly_stats = None
    if sizing_method == 'kelly_criterion':
        # This would ideally use historical performance, but we'll use defaults for now
        kelly_stats = {
            'win_rate': sizing_params.get('kelly_win_rate', 55),
            'avg_win': sizing_params.get('kelly_avg_win', 8),
            'avg_loss': sizing_params.get('kelly_avg_loss', -4)
        }
    
    for _, signal in signals_df_sorted.iterrows():
        ticker = signal['Ticker']
        entry_date = signal['Date']
        
        # Check if we should skip this signal due to active trade
        if one_trade_per_instrument and ticker in active_trades:
            if entry_date <= active_trades[ticker]:
                continue  # Skip this signal, trade still active
            else:
                # Remove expired trade from active trades
                del active_trades[ticker]
        
        # Filter OHLCV data for this ticker
        instrument_data = ohlcv_df[ohlcv_df['Ticker'] == ticker].copy()
        instrument_data.set_index('Date', inplace=True)
        instrument_data.sort_index(inplace=True)
        
        # Find entry point
        entry_row_index = instrument_data.index.asof(entry_date)
        
        if pd.notna(entry_row_index):
            entry_price = instrument_data.loc[entry_row_index]['Close']
            
            # Calculate additional metrics for position sizing
            volatility = None
            atr = None
            
            if sizing_method == 'volatility_target':
                # Calculate volatility using recent price data
                recent_data = instrument_data.loc[:entry_row_index]['Close'].tail(60)
                volatility = calculate_volatility(recent_data)
            
            elif sizing_method == 'atr_based':
                # Calculate ATR using recent OHLC data
                recent_data = instrument_data.loc[:entry_row_index].tail(30)
                if len(recent_data) >= 14:
                    atr = calculate_atr(recent_data['High'], recent_data['Low'], recent_data['Close'])
            
            # Calculate position size with leverage control
            shares = calculate_position_size(
                sizing_method=sizing_method,
                entry_price=entry_price,
                portfolio_value=portfolio_value,
                volatility=volatility,
                atr=atr,
                risk_per_trade=sizing_params.get('risk_per_trade', 2.0),
                fixed_amount=sizing_params.get('fixed_amount', 10000),
                volatility_target=sizing_params.get('volatility_target', 0.15),
                kelly_win_rate=kelly_stats['win_rate'] if kelly_stats else None,
                kelly_avg_win=kelly_stats['avg_win'] if kelly_stats else None,
                kelly_avg_loss=kelly_stats['avg_loss'] if kelly_stats else None,
                allow_leverage=allow_leverage,
                open_positions_value=open_positions_value
            )
            
            # DEBUG: Log position sizing
            print(f"DEBUG run_backtest: Ticker={ticker}, Entry Price={entry_price:.2f}, Shares={shares:.0f}, Portfolio Value={portfolio_value:.2f}, Open Positions Value={open_positions_value:.2f}")
            
            position_value = shares * entry_price
            
            # DEBUG: Log position value calculation
            print(f"DEBUG run_backtest: Position Value={position_value:.2f}, Available Capital={portfolio_value - open_positions_value:.2f}")
            
            # For no leverage mode, check if we have enough capital
            if not allow_leverage and open_positions_value + position_value > portfolio_value:
                leverage_warnings.append(f"Skipped {ticker} on {entry_date}: would require leverage")
                print(f"DEBUG run_backtest: SKIPPED - Would require leverage. Total needed: {open_positions_value + position_value:.2f} > Available: {portfolio_value:.2f}")
                continue  # Skip this trade as it would require leverage
            
            # Update open positions value
            open_positions_value += position_value
            print(f"DEBUG run_backtest: Updated open positions value to {open_positions_value:.2f}")
            
            # Adjust stop loss and take profit for short positions
            if signal_type == 'long':
                stop_loss_price = entry_price * (1 - stop_loss_pct / 100)
                take_profit_price = entry_price * (1 + take_profit_pct / 100) if take_profit_pct is not None else None
                position_multiplier = 1  # Long positions: profit when price goes up
            else:  # short
                stop_loss_price = entry_price * (1 + stop_loss_pct / 100)  # Stop loss above entry for shorts
                take_profit_price = entry_price * (1 - take_profit_pct / 100) if take_profit_pct is not None else None  # Take profit below entry for shorts
                position_multiplier = -1  # Short positions: profit when price goes down
            
            exit_date, exit_price, exit_reason = None, None, 'Time Exit'
            
            # Calculate the index of the entry date in the instrument_data DataFrame
            entry_data_idx = instrument_data.index.get_loc(entry_row_index)

            # Determine the end index for checking, based on holding_period trading days
            # The slice should include 'holding_period' days after the entry day.
            # So, if holding_period is 1, we check the next day (index entry_data_idx + 1).
            # The slice needs to go up to entry_data_idx + holding_period (inclusive).
            # For .iloc, the end index is exclusive, so we add 1.
            end_check_idx_for_slice = min(entry_data_idx + holding_period + 1, len(instrument_data))

            # Check if there's enough data for the holding period
            if entry_data_idx + holding_period + 1 > len(instrument_data):
                # Not enough data for the full holding period, skip this trade
                continue

            # Slice the dataframe based on the calculated index range (trading days)
            # Start from the day *after* entry_data_idx
            trade_data = instrument_data.iloc[entry_data_idx + 1 : end_check_idx_for_slice]

            for date, row in trade_data.iterrows():
                    if signal_type == 'long':
                        if row['Low'] <= stop_loss_price:
                            exit_date, exit_price, exit_reason = date, stop_loss_price, 'Stop Loss'
                            break
                        elif take_profit_price and row['High'] >= take_profit_price:
                            exit_date, exit_price, exit_reason = date, take_profit_price, 'Take Profit'
                            break
                    else:
                        if row['High'] >= stop_loss_price:
                            exit_date, exit_price, exit_reason = date, stop_loss_price, 'Stop Loss'
                            break
                        elif take_profit_price and row['Low'] <= take_profit_price:
                            exit_date, exit_price, exit_reason = date, take_profit_price, 'Take Profit'
                            break
                
                # If no stop/profit hit, exit at the end of the holding period.
                # The exit date will be the last available trading day within the calendar period.
            if exit_date is None and not trade_data.empty:
                    exit_date, exit_price = trade_data.index[-1], trade_data.iloc[-1]['Close']
            
            
            # Record trade if we have valid exit
            if exit_date and exit_price is not None:
                # Calculate P&L based on position type
                if signal_type == 'long':
                    pl_dollar = (exit_price - entry_price) * shares
                    pl_pct = ((exit_price - entry_price) / entry_price) * 100
                else:  # short
                    pl_dollar = (entry_price - exit_price) * shares  # Reversed for short
                    pl_pct = ((entry_price - exit_price) / entry_price) * 100  # Reversed for short
                
                days_held = instrument_data.index.get_loc(exit_date) - instrument_data.index.get_loc(entry_row_index) # Calculate trading days held
                
                # Update portfolio value
                portfolio_value += pl_dollar
                
                # Update open positions value when trade exits
                open_positions_value -= position_value
                
                # DEBUG: Log trade execution
                print(f"DEBUG run_backtest: Trade executed - P&L={pl_dollar:.2f}, New Portfolio Value={portfolio_value:.2f}, New Open Positions Value={open_positions_value:.2f}")
                

                trades.append({
                    'Ticker': ticker,
                    'Signal Type': signal_type.title(),
                    'Entry Date': entry_date, # Use entry_date (datetime object)
                    'Entry Price': entry_price,
                    'Exit Date': exit_date,
                    'Exit Price': exit_price,
                    'Shares': shares,
                    'Position Value': position_value,
                    'P&L ($)': pl_dollar,
                    'Profit/Loss (%)': pl_pct,
                    'Exit Reason': exit_reason,
                    'Days Held': days_held,
                    'Portfolio Value': portfolio_value,
                    'Signal Date': entry_date,
                    'Volatility': volatility,
                    'ATR': atr,
                    'Leverage Used': position_value / (portfolio_value - pl_dollar)  # Leverage at entry
                })
                
                # Track active trade if option is enabled
                if one_trade_per_instrument:
                    active_trades[ticker] = exit_date
    
    
    # Return DataFrame or empty DataFrame
    if not trades:
        return pd.DataFrame(), leverage_warnings
    return pd.DataFrame(trades).sort_values(by='Exit Date').reset_index(drop=True), leverage_warnings

def run_vectorized_single_backtest(ohlcv_df, signals_df, holding_period, stop_loss_pct, take_profit_pct=None,
                                 one_trade_per_instrument=False, initial_capital=100000, sizing_method='equal_weight',
                                 sizing_params=None, signal_type='long', allow_leverage=False):
    """
    Vectorized version of single backtest
    """
    if sizing_params is None:
        sizing_params = {}
    
    trades = []
    portfolio_value = initial_capital
    active_trades = {}
    open_positions_value = 0.0
    
    # DEBUG: Log initial state
    print(f"DEBUG run_vectorized_single_backtest: Initial capital={initial_capital}, signal_type={signal_type}, allow_leverage={allow_leverage}")
    
    # Prepare vectorized data
    st.info("Preparing data for vectorized processing...")
    vectorized_data = prepare_vectorized_data(ohlcv_df)
    
    # Convert sizing method to code for numba
    method_map = {'equal_weight': 0, 'fixed_amount': 1, 'percent_risk': 2,
                  'volatility_target': 3, 'atr_based': 4, 'kelly_criterion': 5}
    sizing_code = method_map.get(sizing_method, 0)
    
    # Process each signal
    for _, signal in signals_df.iterrows():
        ticker = signal['Ticker']
        entry_date_ordinal = pd.Timestamp(signal['Date']).toordinal()
        
        # Skip if one trade per instrument and active trade exists
        if one_trade_per_instrument and ticker in active_trades:
            if entry_date_ordinal <= active_trades[ticker]:
                continue
            else:
                del active_trades[ticker]
        
        if ticker not in vectorized_data:
            continue
            
        ticker_prices = vectorized_data[ticker]
        
        # Find entry point
        entry_indices = np.where(ticker_prices[:, 0] >= entry_date_ordinal)[0]
        if len(entry_indices) == 0:
            continue
            
        entry_idx = entry_indices[0]
        # Check if there's enough data for the full holding period
        if entry_idx + holding_period + 1 > len(ticker_prices):
            continue
            
        entry_price = ticker_prices[entry_idx, 3]
        
        # Calculate position size with actual volatility and ATR (like regular backtest)
        kelly_win_rate = sizing_params.get('kelly_win_rate', 55)
        kelly_avg_win = sizing_params.get('kelly_avg_win', 8)
        kelly_avg_loss = sizing_params.get('kelly_avg_loss', -4)
        
        # Calculate actual volatility and ATR for consistency with regular backtest
        volatility = 0.20  # Default
        atr = entry_price * 0.02  # Default
        
        if sizing_method == 'volatility_target':
            # Calculate volatility using recent price data
            # Get data up to current entry point
            recent_indices = ticker_prices[:entry_idx+1, 0]  # All dates up to entry
            if len(recent_indices) > 0:
                # Convert back to datetime for volatility calculation
                recent_dates = [pd.Timestamp.fromordinal(int(d)) for d in recent_indices]
                recent_prices = ticker_prices[:entry_idx+1, 3]  # Close prices
                if len(recent_prices) >= 60:  # Need enough data for volatility calculation
                    recent_volatility_data = pd.Series(recent_prices)
                    volatility = calculate_volatility(recent_volatility_data.tail(60))
        
        elif sizing_method == 'atr_based':
            # Calculate ATR using recent OHLC data
            if entry_idx >= 14:  # Need enough data for ATR calculation
                recent_high = ticker_prices[max(0, entry_idx-29):entry_idx+1, 1]  # High prices
                recent_low = ticker_prices[max(0, entry_idx-29):entry_idx+1, 2]   # Low prices
                recent_close = ticker_prices[max(0, entry_idx-29):entry_idx+1, 3] # Close prices
                
                # Create DataFrame for ATR calculation
                atr_data = pd.DataFrame({
                    'High': recent_high,
                    'Low': recent_low,
                    'Close': recent_close
                })
                atr = calculate_atr(atr_data['High'], atr_data['Low'], atr_data['Close'])
        
        shares = calculate_position_size_vectorized(
            sizing_code, entry_price, portfolio_value,
            volatility, atr, sizing_params.get('risk_per_trade', 2.0),
            sizing_params.get('fixed_amount', 10000),
            sizing_params.get('volatility_target', 0.15),
            0.05,  # Default stop loss assumption for percent risk calculation
            allow_leverage,  # Use user's leverage setting
            kelly_win_rate, kelly_avg_win, kelly_avg_loss,
            open_positions_value # Pass open_positions_value
        )
        
        # DEBUG: Log position sizing
        print(f"DEBUG run_vectorized_single_backtest: Ticker={ticker}, Entry Price={entry_price:.2f}, Shares={shares:.0f}, Portfolio Value={portfolio_value:.2f}, Open Positions Value={open_positions_value:.2f}")
        
        position_value = shares * entry_price
        
        # DEBUG: Log position value calculation
        print(f"DEBUG run_vectorized_single_backtest: Position Value={position_value:.2f}, Available Capital={portfolio_value - open_positions_value:.2f}")
        
        # For no leverage mode, check if we have enough capital
        if not allow_leverage and open_positions_value + position_value > portfolio_value:
            print(f"DEBUG run_vectorized_single_backtest: SKIPPED - Would require leverage. Total needed: {open_positions_value + position_value:.2f} > Available: {portfolio_value:.2f}")
            continue # Skip this trade as it would require leverage

        # Update open positions value
        open_positions_value += position_value
        print(f"DEBUG run_vectorized_single_backtest: Updated open positions value to {open_positions_value:.2f}")

        
        # Calculate trade outcome
        exit_idx, exit_price, exit_reason = calculate_trade_outcomes_vectorized(
            ticker_prices, entry_idx, holding_period, stop_loss_pct, take_profit_pct, signal_type
        )
        
        if exit_idx > 0 and exit_price > 0:
            # Calculate P&L
            if signal_type == 'long':
                pl_dollar = (exit_price - entry_price) * shares
                pl_pct = ((exit_price - entry_price) / entry_price) * 100
            else:  # short
                pl_dollar = (entry_price - exit_price) * shares
                pl_pct = ((entry_price - exit_price) / entry_price) * 100
            
            portfolio_value += pl_dollar
            
            # Update open positions value when trade exits
            open_positions_value -= position_value
            
            # DEBUG: Log trade execution
            print(f"DEBUG run_vectorized_single_backtest: Trade executed - P&L={pl_dollar:.2f}, New Portfolio Value={portfolio_value:.2f}, New Open Positions Value={open_positions_value:.2f}")

            # Convert ordinal dates back to datetime for consistency with original format
            entry_date = pd.Timestamp.fromordinal(int(ticker_prices[entry_idx, 0]))
            exit_date = pd.Timestamp.fromordinal(int(ticker_prices[exit_idx, 0]))
            

            # Record trade with comprehensive data matching original format
            trades.append({
                'Ticker': ticker,
                'Signal Type': signal_type.title(),
                'Entry Date': entry_date,
                'Entry Price': entry_price,
                'Exit Date': exit_date,
                'Exit Price': exit_price,
                'Shares': shares,
                'Position Value': position_value,
                'P&L ($)': pl_dollar,
                'Profit/Loss (%)': pl_pct,
                'Exit Reason': exit_reason,
                'Days Held': exit_idx - entry_idx,
                'Portfolio Value': portfolio_value,
                'Signal Date': entry_date  # Same as entry date for simplicity
            })
            
            # Update active trades
            if one_trade_per_instrument:
                active_trades[ticker] = ticker_prices[exit_idx, 0]
    
    # Return DataFrame or empty DataFrame
    if not trades:
        return pd.DataFrame(), []
    return pd.DataFrame(trades).sort_values(by='Exit Date').reset_index(drop=True), []
def calculate_invested_value_over_time(trade_log_df_df):
    """
    Calculates the net invested value (total capital in active trades) over time.
    
    Parameters:
    - trade_log_df_df (pd.DataFrame): DataFrame containing trade details with 'Entry Date',
                                   'Exit Date', and 'Position Value'.
    
    Returns:
    - pd.DataFrame: A DataFrame with 'Date' and 'Invested Value' columns, showing
                    the total capital invested on each day.
    """
    if trade_log_df_df.empty:
        return pd.DataFrame({'Date': [], 'Invested Value': []})
    # Ensure dates are normalized for consistent grouping
    trade_log_df_df['Entry Date'] = pd.to_datetime(trade_log_df_df['Entry Date']).dt.normalize()
    trade_log_df_df['Exit Date'] = pd.to_datetime(trade_log_df_df['Exit Date']).dt.normalize()
    # Get the overall date range for the backtest from trade_log_df
    min_date = trade_log_df_df['Entry Date'].min()
    max_date = trade_log_df_df['Exit Date'].max()
    
    # Create a full daily date range covering all trade activity, extending by one day for exit events
    full_date_range = pd.date_range(start=min_date, end=max_date + pd.Timedelta(days=1), freq='D')
    # Create events for position entry and exit
    # A position is invested from Entry Date up to and including Exit Date.
    # So, add value on Entry Date, subtract on Exit Date + 1.
    entry_events = trade_log_df_df[['Entry Date', 'Position Value']].copy()
    entry_events.rename(columns={'Entry Date': 'Date'}, inplace=True)
    
    exit_events = trade_log_df_df[['Exit Date', 'Position Value']].copy()
    exit_events['Date'] = exit_events['Exit Date'] + pd.Timedelta(days=1) # Subtract on the day *after* exit
    exit_events['Position Value'] = -exit_events['Position Value'] # Subtract on exit
    exit_events = exit_events[['Date', 'Position Value']] # Keep only relevant columns
    # Combine events and sum changes per day
    all_events = pd.concat([entry_events, exit_events])
    daily_net_change = all_events.groupby('Date')['Position Value'].sum().sort_index()
    # Reindex to the full date range, filling missing days with 0 change, then calculate cumulative sum
    invested_value_series = daily_net_change.reindex(full_date_range, fill_value=0.0).cumsum()
    invested_value_series[invested_value_series < 0] = 0 # Ensure invested value doesn't go below zero
    invested_df = pd.DataFrame({'Date': invested_value_series.index, 'Invested Value': invested_value_series.values})
    return invested_df

def calculate_leverage_metrics(trade_log_df, initial_capital=100000):
    """Calculate comprehensive leverage metrics for trade analysis"""
    if trade_log_df.empty:
        return {}
    
    # Ensure leverage column exists, calculate if missing
    if 'Leverage Used' not in trade_log_df.columns:
        trade_log_df['Leverage Used'] = trade_log_df.apply(
            lambda row: row['Position Value'] / (row['Portfolio Value'] - row['P&L ($)'])
            if (row['Portfolio Value'] - row['P&L ($)']) != 0 else 1.0, axis=1
        )
    
    leverage_data = trade_log_df['Leverage Used']
    
    # Basic leverage statistics
    avg_leverage = leverage_data.mean()
    max_leverage = leverage_data.max()
    min_leverage = leverage_data.min()
    median_leverage = leverage_data.median()
    
    # Leverage distribution analysis
    leverage_1x = (leverage_data <= 1.0).sum()
    leverage_2x = ((leverage_data > 1.0) & (leverage_data <= 2.0)).sum()
    leverage_3x = ((leverage_data > 2.0) & (leverage_data <= 3.0)).sum()
    leverage_4x_plus = (leverage_data > 3.0).sum()
    
    total_trades = len(leverage_data)
    leverage_distribution = {
        '1x or less': leverage_1x,
        '1x-2x': leverage_2x,
        '2x-3x': leverage_3x,
        '3x or more': leverage_4x_plus
    }
    
    # Leverage risk analysis
    high_leverage_trades = (leverage_data > 2.0).sum()
    very_high_leverage_trades = (leverage_data > 3.0).sum()
    
    # Leverage performance correlation
    if 'Profit/Loss (%)' in trade_log_df.columns:
        # Correlation between leverage and performance
        leverage_performance_corr = trade_log_df['Leverage Used'].corr(trade_log_df['Profit/Loss (%)'])

        # Performance by leverage level
        low_leverage_perf = trade_log_df[trade_log_df['Leverage Used'] <= 1.0]['Profit/Loss (%)'].mean()
        med_leverage_perf = trade_log_df[(trade_log_df['Leverage Used'] > 1.0) & (trade_log_df['Leverage Used'] <= 2.0)]['Profit/Loss (%)'].mean()
        high_leverage_perf = trade_log_df[trade_log_df['Leverage Used'] > 2.0]['Profit/Loss (%)'].mean()
    else:
        leverage_performance_corr = 0
        low_leverage_perf = 0
        med_leverage_perf = 0
        high_leverage_perf = 0
    
    # Leverage volatility analysis
    leverage_volatility = leverage_data.std()
    leverage_range = max_leverage - min_leverage
    
    # Leverage trend over time
    if 'Entry Date' in trade_log_df.columns:
        leverage_trend = trade_log_df.set_index('Entry Date')['Leverage Used'].rolling(window=10).mean()
        avg_leverage_trend = leverage_trend.mean() if not leverage_trend.empty else avg_leverage
    else:
        leverage_trend = None
        avg_leverage_trend = avg_leverage
    
    return {
        "Average Leverage": avg_leverage,
        "Max Leverage": max_leverage,
        "Min Leverage": min_leverage,
        "Median Leverage": median_leverage,
        "Leverage Volatility": leverage_volatility,
        "Leverage Range": leverage_range,
        "High Leverage Trades (>2x)": high_leverage_trades,
        "Very High Leverage Trades (>3x)": very_high_leverage_trades,
        "Leverage Performance Correlation": leverage_performance_corr,
        "Low Leverage Performance (≤1x)": low_leverage_perf,
        "Medium Leverage Performance (1x-2x)": med_leverage_perf,
        "High Leverage Performance (>2x)": high_leverage_perf,
        "Leverage Distribution": leverage_distribution,
        "Average Leverage Trend": avg_leverage_trend,
        "Leverage Risk Score": (high_leverage_trades / total_trades) * 100 if total_trades > 0 else 0
    }

def calculate_performance_metrics(trade_log_df, initial_capital=100000, risk_free_rate=0.06):
    """Enhanced performance metrics calculation with position sizing and leverage analysis"""
    if trade_log_df.empty:
        return {}
    
    # DEBUG: Log performance metrics calculation
    print(f"DEBUG calculate_performance_metrics: Processing {len(trade_log_df)} trades, initial_capital={initial_capital}")
    if not trade_log_df.empty:
        print(f"DEBUG calculate_performance_metrics: Sample portfolio values - min: {trade_log_df['Portfolio Value'].min():.2f}, max: {trade_log_df['Portfolio Value'].max():.2f}")
    
    total_trades = len(trade_log_df)
    winners = trade_log_df[trade_log_df['Profit/Loss (%)'] > 0]
    losers = trade_log_df[trade_log_df['Profit/Loss (%)'] <= 0]
    
    # Basic metrics
    win_rate = (len(winners) / total_trades) * 100 if total_trades > 0 else 0
    avg_win = winners['Profit/Loss (%)'].mean() if not winners.empty else 0
    avg_loss = losers['Profit/Loss (%)'].mean() if not losers.empty else 0
    
    # Dollar-based metrics
    total_pl_dollar = trade_log_df['P&L ($)'].sum()
    avg_win_dollar = winners['P&L ($)'].mean() if not winners.empty else 0
    avg_loss_dollar = losers['P&L ($)'].mean() if not losers.empty else 0
    
    # Risk-adjusted metrics
    profit_factor = abs(winners['P&L ($)'].sum() / losers['P&L ($)'].sum()) if not losers.empty and losers['P&L ($)'].sum() != 0 else np.inf
    
    # DEBUG: Log return calculation methods
    print(f"DEBUG calculate_performance_metrics: Total P&L = ${total_pl_dollar:.2f}")
    
    # Portfolio value progression
    if 'Portfolio Value' in trade_log_df.columns:
        final_value = trade_log_df['Portfolio Value'].iloc[-1]
        total_return = (final_value / initial_capital - 1) * 100
        print(f"DEBUG calculate_performance_metrics: Using portfolio value method - Final: ${final_value:.2f}, Return: {total_return:.2f}%")
    else:
        total_return = (total_pl_dollar / initial_capital) * 100
        print(f"DEBUG calculate_performance_metrics: Using P&L method - Total P&L: ${total_pl_dollar:.2f}, Return: {total_return:.2f}%")
    
    # Portfolio value progression
    if 'Portfolio Value' in trade_log_df.columns:
        final_value = trade_log_df['Portfolio Value'].iloc[-1]
        total_return = (final_value / initial_capital - 1) * 100

        # Calculate returns for each trade based on portfolio value changes
        trade_log_df['Portfolio Return'] = trade_log_df['P&L ($)'] / (trade_log_df['Portfolio Value'] - trade_log_df['P&L ($)'])
    else:
        total_return = (total_pl_dollar / initial_capital) * 100
        trade_log_df['Portfolio Return'] = trade_log_df['P&L ($)'] / initial_capital
    
    # Drawdown calculation using portfolio values
    if 'Portfolio Value' in trade_log_df.columns:
        portfolio_values = trade_log_df['Portfolio Value']
        running_max = portfolio_values.cummax()
        drawdown = (portfolio_values - running_max) / running_max
        max_drawdown = drawdown.min() * 100
        
        # Equity curve for plotting
        equity_curve = trade_log_df[['Exit Date', 'Portfolio Value']].set_index('Exit Date')
    else:
        # Fallback calculation
        cumulative_returns = (1 + trade_log_df['Portfolio Return']).cumprod()
        running_max = cumulative_returns.cummax()
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = drawdown.min() * 100
        
        equity_curve = pd.DataFrame({
            'Portfolio Value': initial_capital * cumulative_returns
        }, index=trade_log_df['Exit Date'])
    
    # Sharpe ratio (annualized)
    returns = trade_log_df['Portfolio Return']
    if len(returns) > 1:
        excess_return = returns.mean() - risk_free_rate/252  # Daily risk-free rate
        sharpe_ratio = (excess_return / returns.std()) * np.sqrt(252) if returns.std() != 0 else 0
    else:
        sharpe_ratio = 0
    
    # Calmar ratio
    calmar_ratio = total_return / abs(max_drawdown) if max_drawdown != 0 else 0
    
    # Position sizing metrics
    avg_position_size = trade_log_df['Position Value'].mean() if 'Position Value' in trade_log_df.columns else 0
    max_position_size = trade_log_df['Position Value'].max() if 'Position Value' in trade_log_df.columns else 0
    min_position_size = trade_log_df['Position Value'].min() if 'Position Value' in trade_log_df.columns else 0

    # Hit ratio and average holding period
    avg_holding_period = trade_log_df['Days Held'].mean() if 'Days Held' in trade_log_df.columns else 0
    
    # Signal type breakdown
    signal_breakdown = {}
    if 'Signal Type' in trade_log_df.columns:
        signal_breakdown = trade_log_df['Signal Type'].value_counts().to_dict()

    # Calculate leverage metrics
    leverage_metrics = calculate_leverage_metrics(trade_log_df, initial_capital)
    
    return {
        "Total Trades": total_trades,
        "Win Rate (%)": win_rate,
        "Average Win (%)": avg_win,
        "Average Loss (%)": avg_loss,
        "Average Win ($)": avg_win_dollar,
        "Average Loss ($)": avg_loss_dollar,
        "Total Return (%)": total_return,
        "Total P&L ($)": total_pl_dollar,
        "Max Drawdown (%)": max_drawdown,
        "Profit Factor": profit_factor,
        "Sharpe Ratio": sharpe_ratio,
        "Calmar Ratio": calmar_ratio,
        "Average Holding Period (days)": avg_holding_period,
        "Average Position Size ($)": avg_position_size,
        "Max Position Size ($)": max_position_size,
        "Min Position Size ($)": min_position_size,
        "Avg Leverage Used": leverage_metrics.get("Average Leverage", 1.0),
        "Max Leverage Used": leverage_metrics.get("Max Leverage", 1.0),
        "Leverage Risk Score": leverage_metrics.get("Leverage Risk Score", 0),
        "Leverage Performance Correlation": leverage_metrics.get("Leverage Performance Correlation", 0),
        "Signal Breakdown": signal_breakdown,
        "Equity Curve": equity_curve,
        "Leverage Metrics": leverage_metrics
    }

def run_parameter_optimization(ohlcv_df, signals_df, holding_periods, stop_losses, take_profits=None, 
                             one_trade_per_instrument=False, initial_capital=100000, 
                             sizing_method='equal_weight', sizing_params=None, signal_type='long'):
    """Run optimization across multiple parameters with position sizing and long/short support"""
    results = []
    
    # Fix: Properly calculate total combinations
    total_combinations = len(holding_periods) * len(stop_losses)
    if take_profits is not None and len(take_profits) > 0:
        total_combinations *= len(take_profits)
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    combination_count = 0
    
    # Fix: Properly handle parameter combinations
    if take_profits is not None and len(take_profits) > 0:
        param_combinations = product(holding_periods, stop_losses, take_profits)
    else:
        param_combinations = product(holding_periods, stop_losses)
    
    for params in param_combinations:
        if take_profits is not None and len(take_profits) > 0:
            if len(params) == 3:
                hp, sl, tp = params
            else:
                hp, sl = params
                tp = None
        else:
            if len(params) == 2:
                hp, sl = params
            else:
                hp, sl, tp = params
            tp = None
        
        combination_count += 1
        status_text.text(f"Testing combination {combination_count}/{total_combinations}: HP={hp}, SL={sl}%, TP={tp if tp else 'None'}% ({signal_type.upper()})")
        
        # Run backtest for optimization with position sizing and signal type
        trade_log_df, _ = run_backtest(ohlcv_df, signals_df, hp, sl, tp, one_trade_per_instrument,
                                initial_capital, sizing_method, sizing_params, signal_type, allow_leverage=False)
        
        if not trade_log_df.empty:
            metrics = calculate_performance_metrics(trade_log_df, initial_capital)
            result = {
                'Signal Type': signal_type.title(),
                'Holding Period': hp,
                'Stop Loss (%)': sl,
                'Take Profit (%)': tp if tp else 0,
                'Total Return (%)': metrics.get('Total Return (%)', 0),
                'Total P&L ($)': metrics.get('Total P&L ($)', 0),
                'Win Rate (%)': metrics.get('Win Rate (%)', 0),
                'Max Drawdown (%)': metrics.get('Max Drawdown (%)', 0),
                'Profit Factor': metrics.get('Profit Factor', 0),
                'Sharpe Ratio': metrics.get('Sharpe Ratio', 0),
                'Total Trades': metrics.get('Total Trades', 0),
                'Avg Position Size ($)': metrics.get('Average Position Size ($)', 0)
            }
        else:
            result = {
                'Signal Type': signal_type.title(),
                'Holding Period': hp,
                'Stop Loss (%)': sl,
                'Take Profit (%)': tp if tp else 0,
                'Total Return (%)': 0,
                'Total P&L ($)': 0,
                'Win Rate (%)': 0,
                'Max Drawdown (%)': 0,
                'Profit Factor': 0,
                'Sharpe Ratio': 0,
                'Total Trades': 0,
                'Avg Position Size ($)': 0
            }
        
        results.append(result)
        progress_bar.progress(combination_count / total_combinations)
    
    progress_bar.empty()
    status_text.empty()
    
    return pd.DataFrame(results)

def create_heatmap(df, x_col, y_col, z_col, title):
    """Create a heatmap for parameter optimization results"""
    pivot_table = df.pivot_table(values=z_col, index=y_col, columns=x_col, aggfunc='mean')
    
    fig = px.imshow(pivot_table,
                    labels=dict(x=x_col, y=y_col, color=z_col),
                    x=pivot_table.columns,
                    y=pivot_table.index,
                    title=title,
                    aspect="auto")
    
    return fig

def create_leverage_distribution_chart(trade_log_df):
    """Create leverage distribution visualization"""
    if 'Leverage Used' not in trade_log_df.columns:
        return None

    leverage_data = trade_log_df['Leverage Used']
    
    # Create bins for leverage distribution
    bins = [0, 1, 2, 3, 5, 10, float('inf')]
    labels = ['≤1x', '1x-2x', '2x-3x', '3x-5x', '5x-10x', '>10x']
    
    leverage_data_binned = pd.cut(leverage_data, bins=bins, labels=labels, right=False)
    leverage_counts = leverage_data_binned.value_counts().sort_index()
    
    fig = px.bar(x=leverage_counts.index, y=leverage_counts.values,
                 title="Leverage Distribution",
                 labels={'x': 'Leverage Range', 'y': 'Number of Trades'},
                 color=leverage_counts.values,
                 color_continuous_scale='Viridis')
    
    fig.update_layout(showlegend=False)
    return fig

def create_leverage_performance_scatter(trade_log_df):
    """Create scatter plot showing leverage vs performance correlation"""
    if 'Leverage Used' not in trade_log_df.columns or 'Profit/Loss (%)' not in trade_log_df.columns:
        return None

    fig = px.scatter(trade_log_df, x='Leverage Used', y='Profit/Loss (%)',
                     title="Leverage vs Performance Correlation",
                     labels={'Leverage Used': 'Leverage Used', 'Profit/Loss (%)': 'Profit/Loss (%)'},
                     color='Profit/Loss (%)',
                     hover_data=['Ticker', 'Exit Date', 'Position Value'],
                     color_continuous_scale='RdYlGn')
    
    # Add trend line
    if len(trade_log_df) > 1:
        z = np.polyfit(trade_log_df['Leverage Used'], trade_log_df['Profit/Loss (%)'], 1)
        p = np.poly1d(z)
        fig.add_trace(go.Scatter(
            x=trade_log_df['Leverage Used'],
            y=p(trade_log_df['Leverage Used']),
            mode='lines',
            name='Trend Line',
            line=dict(color='red', dash='dash')
        ))
    
    return fig

def create_leverage_timeline(trade_log_df):
    """Create timeline showing leverage usage over time"""
    if 'Leverage Used' not in trade_log_df.columns or 'Entry Date' not in trade_log_df.columns:
        return None

    # Sort by entry date
    timeline_data = trade_log_df.sort_values('Entry Date')
    
    # Calculate rolling average for smoother visualization
    timeline_data['Rolling Avg Leverage'] = timeline_data['Leverage Used'].rolling(window=10, min_periods=1).mean()
    
    fig = px.line(timeline_data, x='Entry Date', y='Leverage Used',
                  title="Leverage Usage Over Time",
                  labels={'Entry Date': 'Date', 'Leverage Used': 'Leverage Used'},
                  hover_data=['Ticker', 'Profit/Loss (%)', 'Position Value'])
    
    # Add rolling average line
    fig.add_trace(go.Scatter(
        x=timeline_data['Entry Date'],
        y=timeline_data['Rolling Avg Leverage'],
        mode='lines',
        name='10-Day Rolling Average',
        line=dict(color='orange', width=2)
    ))
    
    # Add reference lines
    fig.add_hline(y=1.0, line_dash="dash", line_color="green",
                  annotation_text="1x Leverage (No Leverage)")
    fig.add_hline(y=2.0, line_dash="dash", line_color="orange",
                  annotation_text="2x Leverage")
    fig.add_hline(y=3.0, line_dash="dash", line_color="red",
                  annotation_text="3x Leverage")
    
    return fig

def create_leverage_risk_dashboard(trade_log_df):
    """Create comprehensive leverage risk dashboard"""
    if 'Leverage Used' not in trade_log_df.columns:
        return None

    leverage_data = trade_log_df['Leverage Used']
    
    # Calculate risk metrics
    high_risk_threshold = 2.0
    extreme_risk_threshold = 3.0
    
    high_risk_trades = (leverage_data > high_risk_threshold).sum()
    extreme_risk_trades = (leverage_data > extreme_risk_threshold).sum()
    total_trades = len(leverage_data)
    
    # Create subplots
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Leverage Distribution', 'Leverage vs Performance',
                       'Leverage Risk Levels', 'Leverage Statistics'),
        specs=[[{"type": "bar"}, {"type": "scatter"}],
               [{"type": "pie"}, {"type": "indicator"}]]
    )
    
    # 1. Leverage Distribution (simplified)
    bins = [0, 1, 2, 3, 5, float('inf')]
    labels = ['≤1x', '1x-2x', '2x-3x', '3x-5x', '>5x']
    leverage_counts = pd.cut(leverage_data, bins=bins, labels=labels, right=False).value_counts().sort_index()
    
    fig.add_trace(
        go.Bar(x=leverage_counts.index, y=leverage_counts.values, name='Leverage Distribution'),
        row=1, col=1
    )
    
    # 2. Leverage vs Performance (if available)
    if 'Profit/Loss (%)' in trade_log_df.columns:
        fig.add_trace(
            go.Scatter(x=leverage_data, y=trade_log_df['Profit/Loss (%)'],
                      mode='markers', name='Leverage vs P&L',
                      marker=dict(size=5, opacity=0.7)),
            row=1, col=2
        )
    
    # 3. Risk Level Distribution
    risk_levels = ['Low Risk (≤2x)', 'Medium Risk (2x-3x)', 'High Risk (>3x)']
    risk_counts = [
        (leverage_data <= high_risk_threshold).sum(),
        ((leverage_data > high_risk_threshold) & (leverage_data <= extreme_risk_threshold)).sum(),
        (leverage_data > extreme_risk_threshold).sum()
    ]
    
    fig.add_trace(
        go.Pie(labels=risk_levels, values=risk_counts, name='Risk Distribution'),
        row=2, col=1
    )
    
    # 4. Key Statistics
    avg_leverage = leverage_data.mean()
    max_leverage = leverage_data.max()
    
    fig.add_trace(
        go.Indicator(
            mode="gauge+number+delta",
            value=avg_leverage,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Avg Leverage"},
            delta={'reference': 1.0},
            gauge={
                'axis': {'range': [None, 5]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 1], 'color': "lightgray"},
                    {'range': [1, 2], 'color': "gray"},
                    {'range': [2, 3], 'color': "orange"},
                    {'range': [3, 5], 'color': "red"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 2.0
                }
            }
        ),
        row=2, col=2
    )
    
    fig.update_layout(height=800, showlegend=False, title_text="Leverage Risk Dashboard")
    return fig

def create_enhanced_ui_header():
    """Create an enhanced UI header with better styling"""
    st.markdown("""
    <style>
    .main-header {
        background: linear-gradient(90deg, #1f77b4, #ff7f0e);
        padding: 2rem 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .signal-badge {
        display: inline-block;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-weight: bold;
        margin: 0.2rem;
    }
    .long-badge {
        background-color: #28a745;
        color: white;
    }
    .short-badge {
        background-color: #dc3545;
        color: white;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #1f77b4;
        margin: 0.5rem 0;
    }
    </style>
    """, unsafe_allow_html=True)

# --- Streamlit App ---

st.set_page_config(layout="wide", page_title="NIFTY 100 Backtesting Engine", page_icon="🚀")

# Enhanced UI Header
create_enhanced_ui_header()

st.markdown("""
<div class="main-header">
    <h1>🚀 Advanced Backtesting Engine for NIFTY 100</h1>
    <p style="font-size: 1.1em; margin-top: 1rem;">
        Professional-grade backtesting with Long/Short support, advanced position sizing, and comprehensive analytics
    </p>
</div>
""", unsafe_allow_html=True)

# Sidebar configuration with enhanced styling
st.sidebar.markdown("### 📁 Data Upload")
ohlcv_file = st.sidebar.file_uploader("Upload OHLCV Data (CSV/Parquet/Excel)", type=["csv", "parquet", "xlsx", "xls"], help="Upload your OHLCV price data")
signals_file = st.sidebar.file_uploader("Upload Signals Data (CSV/Parquet/Excel)", type=["csv", "parquet", "xlsx", "xls"], help="Upload your trading signals")

if ohlcv_file and signals_file:
    try:
        # Data loading and preprocessing
        # Handle different file formats for OHLCV data
        ohlcv_file_name = ohlcv_file.name.lower()
        if ohlcv_file_name.endswith('.parquet'):
            ohlcv_df = pd.read_parquet(ohlcv_file)
        elif ohlcv_file_name.endswith(('.xlsx', '.xls')):
            ohlcv_df = pd.read_excel(ohlcv_file)
        else:  # Default to CSV
            ohlcv_df = pd.read_csv(ohlcv_file)
        
        # Handle different file formats for Signals data
        signals_file_name = signals_file.name.lower()
        if signals_file_name.endswith('.parquet'):
            signals_df = pd.read_parquet(signals_file)
        elif signals_file_name.endswith(('.xlsx', '.xls')):
            signals_df = pd.read_excel(signals_file)
        else:  # Default to CSV
            signals_df = pd.read_csv(signals_file)

        with st.expander("🔍 Show raw column names from uploaded files"):
            col1, col2 = st.columns(2)
            with col1:
                st.write("**OHLCV file columns:**", ohlcv_df.columns.tolist())
            with col2:
                st.write("**Signals file columns:**", signals_df.columns.tolist())

        # Data preprocessing
        ohlcv_df.columns = ohlcv_df.columns.str.lower().str.strip()
        signals_df.columns = signals_df.columns.str.lower().str.strip()
        ohlcv_df.rename(columns={'ticker': 'Ticker', 'date': 'Date', 'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
        signals_df.rename(columns={'symbol': 'Ticker', 'ticker': 'Ticker', 'date': 'Date'}, inplace=True)

        # Validation
        required_ohlcv_cols = ['Ticker', 'Date', 'Open', 'High', 'Low', 'Close']
        if not all(col in ohlcv_df.columns for col in required_ohlcv_cols):
            missing = [col for col in required_ohlcv_cols if col not in ohlcv_df.columns]
            st.error(f"OHLCV file is missing required columns: {missing}. Found: {ohlcv_df.columns.tolist()}")
            st.stop()
        
        required_signals_cols = ['Ticker', 'Date']
        if not all(col in signals_df.columns for col in required_signals_cols):
            missing = [col for col in required_signals_cols if col not in signals_df.columns]
            st.error(f"Signals file is missing required columns: {missing}. Found: {signals_df.columns.tolist()}")
            st.stop()
        
        # Date parsing
        st.info("📅 Parsing date columns...")
        ohlcv_df['Date'] = ohlcv_df['Date'].apply(lambda x: str(x).split(' ')[0])
        ohlcv_df['Date'] = pd.to_datetime(ohlcv_df['Date'], format='%Y-%m-%d', errors='coerce')
        signals_df['Date'] = pd.to_datetime(signals_df['Date'], dayfirst=True, errors='coerce')
        
        # Validation
        if not is_datetime64_any_dtype(ohlcv_df['Date']):
            st.error("Date column in OHLCV file could not be reliably converted to datetime after parsing.")
            st.stop()
        if not is_datetime64_any_dtype(signals_df['Date']):
            st.error("Date column in Signals file could not be converted. Please ensure format is DD-MM-YYYY.")
            st.stop()
        
        ohlcv_df.dropna(subset=['Date', 'Close', 'Low'], inplace=True)
        signals_df.dropna(subset=['Date', 'Ticker'], inplace=True)
        
        st.success("✅ Data validation and normalization successful!")

        # Signal Type Selection - Prominent UI element
        st.markdown("### 📊 Signal Configuration")
        col1, col2, col3 = st.columns([2, 2, 3])
        
        with col1:
            signal_type = st.radio(
                "**Select Signal Type:**",
                options=['long', 'short'],
                index=0,  # Default to long
                help="Choose whether your signals are for long positions (buy) or short positions (sell)"
            )
        
        with col2:
            st.markdown("**Signal Type Explanation:**")
            if signal_type == 'long':
                st.markdown('<span class="signal-badge long-badge">📈 LONG SIGNALS</span>', unsafe_allow_html=True)
                st.write("• Buy at signal, profit when price goes up")
                st.write("• Stop loss below entry price")
                st.write("• Take profit above entry price")
            else:
                st.markdown('<span class="signal-badge short-badge">📉 SHORT SIGNALS</span>', unsafe_allow_html=True)
                st.write("• Sell at signal, profit when price goes down")
                st.write("• Stop loss above entry price")
                st.write("• Take profit below entry price")
        
        with col3:
            # Show signal statistics
            st.markdown("**Signal Statistics:**")
            st.info(f"📊 Total Signals: {len(signals_df):,}")
            st.info(f"🏢 Unique Instruments: {signals_df['Ticker'].nunique()}")
            date_range = f"{signals_df['Date'].min().strftime('%d-%m-%Y')} to {signals_df['Date'].max().strftime('%d-%m-%Y')}"
            st.info(f"📅 Date Range: {date_range}")

        # Add data summary for debugging
        with st.expander("📊 Data Summary for Debugging"):
            col1, col2 = st.columns(2)
            with col1:
                st.write("**OHLCV Data Summary:**")
                st.write(f"- Total records: {len(ohlcv_df):,}")
                st.write(f"- Unique tickers: {ohlcv_df['Ticker'].nunique()}")
                st.write(f"- Date range: {ohlcv_df['Date'].min().date()} to {ohlcv_df['Date'].max().date()}")
                st.write("**Top 10 Tickers:**")
                st.write(ohlcv_df['Ticker'].value_counts().head(10).to_dict())
            
            with col2:
                st.write("**Signals Data Summary:**")
                st.write(f"- Total signals: {len(signals_df):,}")
                st.write(f"- Unique tickers: {signals_df['Ticker'].nunique()}")
                st.write(f"- Date range: {signals_df['Date'].min().date()} to {signals_df['Date'].max().date()}")
                st.write("**Signals by Ticker:**")
                st.write(signals_df['Ticker'].value_counts().head(10).to_dict())
            
            # Check for ticker mismatches
            ohlcv_tickers = set(ohlcv_df['Ticker'].unique())
            signals_tickers = set(signals_df['Ticker'].unique())
            common_tickers = ohlcv_tickers.intersection(signals_tickers)
            missing_in_ohlcv = signals_tickers - ohlcv_tickers
            missing_in_signals = ohlcv_tickers - signals_tickers
            
            st.write("**Ticker Matching Analysis:**")
            st.write(f"- Common tickers: {len(common_tickers)}")
            if missing_in_ohlcv:
                st.warning(f"- Tickers in signals but NOT in OHLCV: {sorted(list(missing_in_ohlcv))}")
            if missing_in_signals:
                st.info(f"- Tickers in OHLCV but NOT in signals: {len(missing_in_signals)} tickers")

        # Enhanced sidebar with mode selection
        st.sidebar.markdown("### 🎯 Analysis Mode")
        analysis_mode = st.sidebar.radio(
            "Choose analysis mode:",
            ["Single Backtest", "Parameter Optimization"],
            help="Single Backtest: Test specific parameters | Parameter Optimization: Find best parameter combinations"
        )

        # Portfolio Configuration with enhanced styling
        st.sidebar.markdown("### 💰 Portfolio Settings")
        initial_capital = st.sidebar.number_input(
            "Initial Capital ($)", 
            min_value=1000, 
            max_value=10000000, 
            value=100000, 
            step=1000,
            help="Starting portfolio value in dollars"
        )
        # Add leverage control
        allow_leverage = st.sidebar.checkbox(
            "Allow Leverage",
            value=False,
            help="When disabled, ensures total position values never exceed portfolio value")

        # Position Sizing Configuration with better UI
        st.sidebar.markdown("### 📏 Position Sizing")
        sizing_method = st.sidebar.selectbox(
            "Position Sizing Method:",
            [
                "equal_weight",
                "fixed_amount", 
                "percent_risk",
                "volatility_target",
                "atr_based",
                "kelly_criterion"
            ],
            format_func=lambda x: {
                "equal_weight": "💰 Equal Weight (2% per position)",
                "fixed_amount": "💵 Fixed Dollar Amount",
                "percent_risk": "⚠️ Percent Risk (Risk-based)",
                "volatility_target": "📊 Volatility Targeting",
                "atr_based": "📈 ATR-based Sizing",
                "kelly_criterion": "🎯 Kelly Criterion"
            }[x],
            help="Choose how to size each position"
        )

        # Position sizing parameters with enhanced UI
        sizing_params = {}
        
        if sizing_method == "fixed_amount":
            sizing_params['fixed_amount'] = st.sidebar.number_input(
                "Fixed Amount per Trade ($)", 
                min_value=100, max_value=100000, value=10000, step=100,
                help="Same dollar amount for every trade"
            )
            
        elif sizing_method == "percent_risk":
            sizing_params['risk_per_trade'] = st.sidebar.slider(
                "Risk per Trade (%)", 
                min_value=0.1, max_value=10.0, value=2.0, step=0.1,
                help="Percentage of portfolio to risk on each trade"
            )
            
        elif sizing_method == "volatility_target":
            sizing_params['volatility_target'] = st.sidebar.slider(
                "Target Portfolio Volatility", 
                min_value=0.05, max_value=0.50, value=0.15, step=0.01,
                help="Target annual volatility for the portfolio"
            )
            
        elif sizing_method == "atr_based":
            sizing_params['risk_per_trade'] = st.sidebar.slider(
                "Risk per Trade (% of portfolio)", 
                min_value=0.1, max_value=10.0, value=2.0, step=0.1,
                help="Risk based on Average True Range"
            )
            
        elif sizing_method == "kelly_criterion":
            st.sidebar.markdown("**Kelly Criterion Parameters:**")
            sizing_params['kelly_win_rate'] = st.sidebar.slider(
                "Expected Win Rate (%)", 
                min_value=30, max_value=80, value=55,
                help="Expected percentage of winning trades"
            )
            sizing_params['kelly_avg_win'] = st.sidebar.slider(
                "Average Win (%)", 
                min_value=1, max_value=50, value=8,
                help="Average percentage gain on winning trades"
            )
            sizing_params['kelly_avg_loss'] = st.sidebar.slider(
                "Average Loss (%)", 
                min_value=-50, max_value=-1, value=-4,
                help="Average percentage loss on losing trades"
            )

        # Show position sizing explanation with better formatting
        with st.sidebar.expander("ℹ️ Position Sizing Methods"):
            st.markdown("""
            **💰 Equal Weight**: Fixed 2% of portfolio per position
            
            **💵 Fixed Amount**: Same dollar amount for each trade
            
            **⚠️ Percent Risk**: Risk fixed % of portfolio per trade based on stop loss
            
            **📊 Volatility Target**: Size positions to achieve target portfolio volatility
            
            **📈 ATR-based**: Size based on Average True Range (volatility measure)
            
            **🎯 Kelly Criterion**: Optimal sizing based on win rate and avg win/loss
            """)

        # Enhanced Filters UI
        st.sidebar.markdown("### 🔍 Filters & Selection")
        
        # Date filters with better styling
        min_date = signals_df['Date'].min().to_pydatetime()
        max_date = signals_df['Date'].max().to_pydatetime()
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            start_date = st.date_input("Start Date", min_date, min_value=min_date, max_value=max_date)
        with col2:
            end_date = st.date_input("End Date", max_date, min_value=min_date, max_value=max_date)

        # Enhanced instrument selection
        instrument_list = sorted(signals_df['Ticker'].unique())
        total_instruments = len(instrument_list)
        
        # Instrument selection mode
        selection_mode = st.sidebar.radio(
            "Instrument Selection:",
            ["All Instruments", "Select Specific", "Top N by Signals", "Search & Select"],
            help="Choose how to select instruments for backtesting"
        )
        
        if selection_mode == "All Instruments":
            selected_instruments = instrument_list
            st.sidebar.success(f"✅ Using all {total_instruments} instruments")
            
        elif selection_mode == "Select Specific":
            selected_instruments = st.sidebar.multiselect(
                "Choose Instruments:", 
                instrument_list, 
                default=[],
                help="Select specific tickers to backtest"
            )
            if selected_instruments:
                st.sidebar.info(f"📊 Selected: {len(selected_instruments)} instruments")
            else:
                st.sidebar.warning("⚠️ No instruments selected")
                
        elif selection_mode == "Top N by Signals":
            # Get top N instruments by signal count
            signal_counts = signals_df['Ticker'].value_counts()
            top_n = st.sidebar.slider("Number of top instruments:", 1, min(50, total_instruments), 10)
            top_instruments = signal_counts.head(top_n).index.tolist()
            selected_instruments = top_instruments
            
            with st.sidebar.expander("📈 Preview top instruments"):
                preview_df = pd.DataFrame({
                    'Ticker': signal_counts.head(top_n).index,
                    'Signals': signal_counts.head(top_n).values
                })
                st.dataframe(preview_df, use_container_width=True)
            
        else:  # Search & Select
            search_term = st.sidebar.text_input("🔍 Search tickers:", placeholder="e.g., RELIANCE, TCS")
            
            if search_term:
                # Filter instruments based on search
                filtered_list = [ticker for ticker in instrument_list 
                               if search_term.upper() in ticker.upper()]
                
                if filtered_list:
                    selected_instruments = st.sidebar.multiselect(
                        f"Found {len(filtered_list)} matches:", 
                        filtered_list, 
                        default=filtered_list[:10] if len(filtered_list) > 10 else filtered_list
                    )
                    st.sidebar.info(f"📊 Selected: {len(selected_instruments)} instruments")
                else:
                    st.sidebar.warning("No matches found")
                    selected_instruments = []
            else:
                selected_instruments = []
                st.sidebar.info("👆 Enter search term to find instruments")

        if analysis_mode == "Single Backtest":
            # Single backtest parameters with enhanced UI
            st.sidebar.markdown("### ⚙️ Backtesting Parameters")
            
            col1, col2 = st.sidebar.columns(2)
            with col1:
                holding_period = st.number_input("Holding Period (days)", min_value=1, max_value=100, value=10)
                stop_loss_pct = st.number_input("Stop Loss (%)", min_value=0.1, max_value=50.0, value=5.0, step=0.5)
            with col2:
                use_take_profit = st.checkbox("Enable Take Profit")
                take_profit_pct = st.number_input("Take Profit (%)", min_value=0.1, max_value=100.0, value=10.0, step=0.5) if use_take_profit else None
            
            # New option for one trade per instrument
            one_trade_per_instrument = st.sidebar.checkbox(
                "📍 One Trade Per Instrument", 
                value=False,
                help="Only allow one active trade per instrument at a time. New signals for the same instrument will be ignored until the current trade exits."
            )

            # Vectorization options for single backtest
            st.sidebar.markdown("### ⚡ Performance Options")
            use_vectorized = st.sidebar.checkbox("Enable Vectorized Processing", value=False,
                                                 help="Use vectorized processing for faster backtesting")
            
            use_multiprocessing = False
            max_workers = 1
            if use_vectorized:
                max_cores = mp.cpu_count()


            # Enhanced run button
            run_backtest_button = st.sidebar.button(
                f"🚀 Run {signal_type.upper()} Backtest",
                type="primary",
                help=f"Execute backtest with {signal_type} signals on selected instruments"
            )

            if run_backtest_button:
                # Validate instrument selection
                if not selected_instruments:
                    st.error("⚠️ Please select at least one instrument to backtest")
                    st.stop()
                
                # Filter data
                signals_df['Date'] = signals_df['Date'].dt.normalize()
                ohlcv_df['Date'] = ohlcv_df['Date'].dt.normalize()
                
                filtered_signals = signals_df[
                    (signals_df['Date'].dt.date >= start_date) & 
                    (signals_df['Date'].dt.date <= end_date) & 
                    (signals_df['Ticker'].isin(selected_instruments))
                ]
                
                if filtered_signals.empty:
                    st.warning("⚠️ No signals found for the selected date range and instruments.")
                else:
                    # Show configuration summary
                    st.markdown("### 📋 Backtest Configuration Summary")
                    config_col1, config_col2, config_col3 = st.columns(3)
                    
                    with config_col1:
                        st.markdown(f"""
                        <div class="metric-card">
                            <strong>Signal Configuration</strong><br>
                            Type: <span class="signal-badge {'long-badge' if signal_type == 'long' else 'short-badge'}">{signal_type.upper()}</span><br>
                            Signals: {len(filtered_signals):,}<br>
                            Instruments: {filtered_signals['Ticker'].nunique()}
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with config_col2:
                        st.markdown(f"""
                        <div class="metric-card">
                            <strong>Risk Parameters</strong><br>
                            Holding Period: {holding_period} days<br>
                            Stop Loss: {stop_loss_pct}%<br>
                            Take Profit: {take_profit_pct if take_profit_pct else 'Disabled'}
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with config_col3:
                        st.markdown(f"""
                        <div class="metric-card">
                            <strong>Portfolio Setup</strong><br>
                            Capital: ${initial_capital:,}<br>
                            Sizing: {sizing_method.replace('_', ' ').title()}<br>
                            One Trade/Instrument: {'Yes' if one_trade_per_instrument else 'No'}
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Show signal summary before backtesting
                    with st.expander("📋 Signals to be tested"):
                        signal_summary = filtered_signals.groupby('Ticker').agg({
                            'Date': ['count', 'min', 'max']
                        }).round(2)
                        signal_summary.columns = ['Count', 'First Signal', 'Last Signal']
                        st.dataframe(signal_summary, use_container_width=True)
                    
                    with st.spinner(f"Running {signal_type.upper()} backtest..."):
                        # Simple debug check before running backtest
                        with st.expander("🔍 Quick Debug Check"):
                            # Check data availability for each ticker
                            debug_results = []
                            for ticker in selected_instruments:
                                signals_for_ticker = filtered_signals[filtered_signals['Ticker'] == ticker]
                                ohlcv_for_ticker = ohlcv_df[ohlcv_df['Ticker'] == ticker]
                                
                                debug_results.append({
                                    'Ticker': ticker,
                                    'Signals': len(signals_for_ticker),
                                    'OHLCV_Records': len(ohlcv_for_ticker),
                                    'Has_OHLCV_Data': len(ohlcv_for_ticker) > 0
                                })
                            
                            st.dataframe(pd.DataFrame(debug_results), use_container_width=True)
                        
                        # Run the backtest with position sizing and signal type
                        if use_vectorized:
                            trade_log_df, _ = run_vectorized_single_backtest(ohlcv_df, filtered_signals, holding_period, stop_loss_pct,
                                                                   take_profit_pct, one_trade_per_instrument, initial_capital,
                                                                   sizing_method, sizing_params, signal_type, allow_leverage)
                        else:
                            trade_log_df, _ = run_backtest(ohlcv_df, filtered_signals, holding_period, stop_loss_pct,
                                                   take_profit_pct, one_trade_per_instrument, initial_capital,
                                                   sizing_method, sizing_params, signal_type, allow_leverage)
                        
                        # Store backtest results in session state to prevent recalculation on filter changes
                        st.write("DEBUG: trade_log_df shape:", trade_log_df.shape)
                        if not trade_log_df.empty:
                            st.session_state['backtest_results'] = trade_log_df
                            st.session_state['backtest_params'] = {
                                'holding_period': holding_period,
                                'stop_loss_pct': stop_loss_pct,
                                'take_profit_pct': take_profit_pct,
                                'one_trade_per_instrument': one_trade_per_instrument,
                                'initial_capital': initial_capital,
                                'sizing_method': sizing_method,
                                'sizing_params': sizing_params,
                                'signal_type': signal_type,
                                'allow_leverage': allow_leverage
                            }
                            st.success("✅ Backtest results cached in session state")
                            st.write("DEBUG: backtest_results in session_state:", 'backtest_results' in st.session_state)
                        else:
                            # Clear session state if no results
                            if 'backtest_results' in st.session_state:
                                del st.session_state['backtest_results']
                            if 'backtest_params' in st.session_state:
                                del st.session_state['backtest_params']
                            st.warning("⚠️ No trades were executed for the selected parameters.")


        else:  # Parameter Optimization Mode
            st.sidebar.markdown("### 🔧 Optimization Parameters")
            
            # Enhanced parameter input with better organization
            param_col1, param_col2 = st.sidebar.columns(2)
            
            with param_col1:
                st.write("**Holding Periods (days):**")
                hp_min = st.number_input("Min", min_value=1, max_value=50, value=5, key="hp_min")
                hp_max = st.number_input("Max", min_value=hp_min, max_value=100, value=20, key="hp_max")
                hp_step = st.number_input("Step", min_value=1, max_value=10, value=5, key="hp_step")
            
            with param_col2:
                st.write("**Stop Loss (%):**")
                sl_min = st.number_input("Min", min_value=0.5, max_value=20.0, value=2.0, step=0.5, key="sl_min")
                sl_max = st.number_input("Max", min_value=sl_min, max_value=50.0, value=10.0, step=0.5, key="sl_max")
                sl_step = st.number_input("Step", min_value=0.5, max_value=5.0, value=1.0, step=0.5, key="sl_step")
            
            holding_periods = list(range(hp_min, hp_max + 1, hp_step))
            stop_losses = [round(x, 1) for x in np.arange(sl_min, sl_max + sl_step, sl_step)]
            
            # Take profits (optional)
            use_tp_optimization = st.sidebar.checkbox("Include Take Profit Optimization")
            take_profits = None
            if use_tp_optimization:
                tp_col1, tp_col2 = st.sidebar.columns(2)
                with tp_col1:
                    tp_min = st.number_input("Min TP", min_value=1.0, max_value=50.0, value=5.0, step=1.0)
                    tp_max = st.number_input("Max TP", min_value=tp_min, max_value=100.0, value=20.0, step=1.0)
                with tp_col2:
                    tp_step = st.number_input("TP Step", min_value=1.0, max_value=10.0, value=5.0, step=1.0)
                take_profits = list(range(int(tp_min), int(tp_max) + 1, int(tp_step)))
            
            # One trade per instrument option for optimization
            one_trade_per_instrument = st.sidebar.checkbox(
                "📍 One Trade Per Instrument",
                value=False,
                help="Only allow one active trade per instrument at a time during optimization."
            )
            
            # Show parameter summary with enhanced display
            total_combinations = len(holding_periods) * len(stop_losses)
            if take_profits is not None:
                total_combinations *= len(take_profits)
            
            st.sidebar.markdown("**Parameter Summary:**")
            st.sidebar.info(f"""
            • Holding Periods: {len(holding_periods)} values ({hp_min}-{hp_max})
            • Stop Losses: {len(stop_losses)} values ({sl_min}%-{sl_max}%)
            • Take Profits: {len(take_profits) if take_profits else 0} values
            • **Total Combinations: {total_combinations}**
            """)
            
            # Vectorization options
            st.sidebar.markdown("### ⚡ Performance Options")
            
            # Auto-detect if vectorization should be recommended
            if total_combinations > 50:
                st.sidebar.success(f"🚀 Vectorization recommended for {total_combinations} combinations")
                use_vectorized = st.sidebar.checkbox("Enable Vectorized Processing", value=True)
            else:
                use_vectorized = st.sidebar.checkbox("Enable Vectorized Processing", value=False,
                                                   help="May not provide benefits for small parameter spaces")
            
            if use_vectorized:
                max_cores = mp.cpu_count()
                use_multiprocessing = st.sidebar.checkbox("Use Multiprocessing for Parameter Optimization", value=True)
                max_workers = st.sidebar.slider("Worker Processes", 1, max_cores,
                                               min(max_cores - 1, 4))
                st.sidebar.info(f"Will use {max_workers} of {max_cores} available cores for parameter optimization")
            else:
                use_multiprocessing = False
                max_workers = 1
            
            # Estimated time
            est_time_seconds = total_combinations * 0.1  # Rough estimate
            if est_time_seconds > 60:
                est_time_str = f"~{est_time_seconds/60:.1f} minutes"
            else:
                est_time_str = f"~{est_time_seconds:.0f} seconds"
            st.sidebar.write(f"**Estimated Time:** {est_time_str}")
            
            if st.sidebar.button(f"🔍 Run {signal_type.upper()} Optimization", type="primary"):
                # Validate instrument selection
                if not selected_instruments:
                    st.error("⚠️ Please select at least one instrument to optimize")
                    st.stop()
                
                # Filter data
                signals_df['Date'] = signals_df['Date'].dt.normalize()
                ohlcv_df['Date'] = ohlcv_df['Date'].dt.normalize()
                
                filtered_signals = signals_df[
                    (signals_df['Date'].dt.date >= start_date) & 
                    (signals_df['Date'].dt.date <= end_date) & 
                    (signals_df['Ticker'].isin(selected_instruments))
                ]
                
                if filtered_signals.empty:
                    st.warning("⚠️ No signals found for the selected date range and instruments.")
                else:
                    st.markdown(f"## 🔍 Parameter Optimization Results ({signal_type.upper()} Signals)")
                    
                    # Show optimization setup
                    st.markdown(f"""
                    <div style="background: linear-gradient(90deg, #6f42c1, #e83e8c); padding: 1rem; border-radius: 10px; color: white; text-align: center; margin-bottom: 2rem;">
                        <h3>🚀 Starting Optimization Process</h3>
                        <p>Testing <strong>{total_combinations}</strong> parameter combinations on <strong>{len(filtered_signals)}</strong> {signal_type.upper()} signals</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    with st.spinner(f"Running {signal_type} parameter optimization..."):
                        # Try vectorized optimization first if enabled
                        if use_vectorized:
                            try:
                                optimization_results = run_vectorized_parameter_optimization(
                                    ohlcv_df, filtered_signals, holding_periods, stop_losses, take_profits,
                                    one_trade_per_instrument, initial_capital, sizing_method, sizing_params,
                                    signal_type, use_multiprocessing, max_workers, allow_leverage
                                )
                            except Exception as e:
                                st.warning(f"Vectorized optimization failed: {e}. Falling back to standard optimization.")
                                optimization_results = run_parameter_optimization(
                                    ohlcv_df, filtered_signals, holding_periods, stop_losses, take_profits,
                                    one_trade_per_instrument, initial_capital, sizing_method, sizing_params, signal_type
                                )
                        else:
                            optimization_results = run_parameter_optimization(
                                ohlcv_df, filtered_signals, holding_periods, stop_losses, take_profits,
                                one_trade_per_instrument, initial_capital, sizing_method, sizing_params, signal_type
                            )
                        
                        # Store optimization results in session state to prevent recalculation
                        if not optimization_results.empty:
                            st.session_state['optimization_results'] = optimization_results
                            st.session_state['optimization_params'] = {
                                'holding_periods': holding_periods,
                                'stop_losses': stop_losses,
                                'take_profits': take_profits,
                                'one_trade_per_instrument': one_trade_per_instrument,
                                'initial_capital': initial_capital,
                                'sizing_method': sizing_method,
                                'sizing_params': sizing_params,
                                'signal_type': signal_type,
                                'use_multiprocessing': use_multiprocessing,
                                'max_workers': max_workers,
                                'allow_leverage': allow_leverage
                            }
                            st.success("✅ Optimization results cached in session state")
                        else:
                            # Clear session state if no results
                            if 'optimization_results' in st.session_state:
                                del st.session_state['optimization_results']
                            if 'optimization_params' in st.session_state:
                                del st.session_state['optimization_params']
                            st.warning("⚠️ No valid results from optimization.")
                    
                    if not optimization_results.empty:
                        st.success(f"✅ Optimization completed! Found {len(optimization_results)} valid parameter combinations.")
                        
                        # Display top results with enhanced formatting
                        st.markdown("### 🏆 Top 20 Parameter Combinations")
                        top_results = optimization_results.nlargest(20, 'Total Return (%)')
                        
                        # Add ranking column
                        top_results = top_results.reset_index(drop=True)
                        top_results.index = top_results.index + 1
                        top_results.index.name = 'Rank'
                        
                        st.dataframe(
                            top_results.style.format({
                                'Total Return (%)': '{:.2f}%',
                                'Total P&L ($)': '${:,.0f}',
                                'Win Rate (%)': '{:.2f}%',
                                'Max Drawdown (%)': '{:.2f}%',
                                'Profit Factor': '{:.2f}',
                                'Sharpe Ratio': '{:.3f}',
                                'Avg Position Size ($)': '${:,.0f}'
                            }).background_gradient(subset=['Total Return (%)'], cmap='RdYlGn')
                            .background_gradient(subset=['Sharpe Ratio'], cmap='viridis'),
                            use_container_width=True,
                            height=600
                        )
                        
                        # Enhanced analysis tabs
                        opt_tab1, opt_tab2, opt_tab3, opt_tab4 = st.tabs([
                            "🔥 Heatmaps", 
                            "📊 3D Analysis", 
                            "📈 Performance Metrics", 
                            "🎯 Best Strategies"
                        ])
                        
                        with opt_tab1:
                            st.markdown("### Parameter Heatmaps")
                            
                            heatmap_col1, heatmap_col2 = st.columns(2)
                            with heatmap_col1:
                                fig1 = create_heatmap(optimization_results, 'Holding Period', 'Stop Loss (%)', 
                                                    'Total Return (%)', 'Total Return % by Parameters')
                                st.plotly_chart(fig1, use_container_width=True)
                                
                                fig3 = create_heatmap(optimization_results, 'Holding Period', 'Stop Loss (%)', 
                                                    'Total P&L ($)', 'Total P&L ($) by Parameters')
                                st.plotly_chart(fig3, use_container_width=True)
                            
                            with heatmap_col2:
                                fig2 = create_heatmap(optimization_results, 'Holding Period', 'Stop Loss (%)', 
                                                    'Sharpe Ratio', 'Sharpe Ratio by Parameters')
                                st.plotly_chart(fig2, use_container_width=True)
                                
                                fig4 = create_heatmap(optimization_results, 'Holding Period', 'Stop Loss (%)', 
                                                    'Win Rate (%)', 'Win Rate % by Parameters')
                                st.plotly_chart(fig4, use_container_width=True)
                        
                        with opt_tab2:
                            # 3D visualization if take profits are included
                            if use_tp_optimization and take_profits:
                                st.markdown("### 3D Parameter Analysis")
                                metric_choice = st.selectbox("Choose metric for 3D analysis:", 
                                                           ['Total Return (%)', 'Total P&L ($)', 'Sharpe Ratio', 'Win Rate (%)'])
                                
                                fig = px.scatter_3d(optimization_results,
                                                  x='Holding Period',
                                                  y='Stop Loss (%)',
                                                  z='Take Profit (%)',
                                                  color=metric_choice,
                                                  size='Total Trades',
                                                  hover_data=['Win Rate (%)', 'Max Drawdown (%)', 'Total P&L ($)'],
                                                  title=f"3D Parameter Space: {metric_choice}")
                                fig.update_layout(height=600)
                                st.plotly_chart(fig, use_container_width=True)
                            else:
                                st.info("📊 Enable Take Profit Optimization to see 3D analysis")
                                
                                # Show 2D scatter plots instead
                                scatter_col1, scatter_col2 = st.columns(2)
                                with scatter_col1:
                                    fig = px.scatter(optimization_results, x='Holding Period', y='Total Return (%)',
                                                   color='Stop Loss (%)', size='Total Trades',
                                                   title="Holding Period vs Total Return")
                                    st.plotly_chart(fig, use_container_width=True)
                                
                                with scatter_col2:
                                    fig = px.scatter(optimization_results, x='Stop Loss (%)', y='Sharpe Ratio',
                                                   color='Holding Period', size='Total Trades',
                                                   title="Stop Loss vs Sharpe Ratio")
                                    st.plotly_chart(fig, use_container_width=True)
                        
                        with opt_tab3:
                            st.markdown("### Performance Metrics Analysis")
                            
                            # Correlation matrix of metrics
                            metrics_cols = ['Total Return (%)', 'Win Rate (%)', 'Max Drawdown (%)', 
                                          'Profit Factor', 'Sharpe Ratio', 'Total Trades']
                            if all(col in optimization_results.columns for col in metrics_cols):
                                corr_matrix = optimization_results[metrics_cols].corr()
                                
                                fig = px.imshow(corr_matrix, 
                                              title="Correlation Matrix of Performance Metrics",
                                              color_continuous_scale='RdBu',
                                              aspect="auto")
                                st.plotly_chart(fig, use_container_width=True)
                            
                            # Performance distribution
                            metric_dist_col1, metric_dist_col2 = st.columns(2)
                            with metric_dist_col1:
                                fig = px.histogram(optimization_results, x='Total Return (%)', 
                                                 title="Distribution of Total Returns")
                                st.plotly_chart(fig, use_container_width=True)
                            
                            with metric_dist_col2:
                                fig = px.histogram(optimization_results, x='Sharpe Ratio', 
                                                 title="Distribution of Sharpe Ratios")
                                st.plotly_chart(fig, use_container_width=True)
                        
                        with opt_tab4:
                            st.markdown("### Best Strategy Analysis")
                            
                            # Find best strategies by different criteria
                            criteria = {
                                'Highest Return': optimization_results.loc[optimization_results['Total Return (%)'].idxmax()],
                                'Best Sharpe': optimization_results.loc[optimization_results['Sharpe Ratio'].idxmax()],
                                'Lowest Drawdown': optimization_results.loc[optimization_results['Max Drawdown (%)'].idxmin()],
                                'Highest Win Rate': optimization_results.loc[optimization_results['Win Rate (%)'].idxmax()]
                            }
                            
                            for criterion, best_strategy in criteria.items():
                                with st.expander(f"🎯 {criterion} Strategy"):
                                    strategy_col1, strategy_col2, strategy_col3 = st.columns(3)
                                    
                                    with strategy_col1:
                                        st.markdown("**Parameters:**")
                                        st.write(f"• Holding Period: {best_strategy['Holding Period']} days")
                                        st.write(f"• Stop Loss: {best_strategy['Stop Loss (%)']}%")
                                        if 'Take Profit (%)' in best_strategy and float(best_strategy['Take Profit (%)'].values[0]) > 0:
                                            st.write(f"• Take Profit: {best_strategy['Take Profit (%)']}%")
                                    
                                    with strategy_col2:
                                        st.markdown("**Performance:**")
                                        st.write(f"• Total Return: {best_strategy['Total Return (%)']:.2f}%")
                                        st.write(f"• Win Rate: {best_strategy['Win Rate (%)']:.2f}%")
                                        st.write(f"• Sharpe Ratio: {best_strategy['Sharpe Ratio']:.3f}")
                                    
                                    with strategy_col3:
                                        st.markdown("**Risk Metrics:**")
                                        st.write(f"• Max Drawdown: {best_strategy['Max Drawdown (%)']:.2f}%")
                                        st.write(f"• Profit Factor: {best_strategy['Profit Factor']:.2f}")
                                        st.write(f"• Total Trades: {int(float(best_strategy['Total Trades'].values[0]))}")
                        
                        # Download optimization results with enhanced filename
                        csv = optimization_results.to_csv(index=False)
                        filename = f"optimization_results_{signal_type}_{len(optimization_results)}combinations.csv"
                        st.download_button("📥 Download Optimization Results", csv, filename, "text/csv")
                        
                    else:
                        st.warning("⚠️ No valid results from optimization.")

    except Exception as e:
        st.error(f"❌ An unexpected error occurred: {e}")
        st.info("Please check the format and content of your CSV files.")
        # Add more detailed error information for debugging
        import traceback
        with st.expander("🔧 Detailed Error Information"):
            st.code(traceback.format_exc())
    
    # Clear session state on file change
    if ohlcv_file is not None and signals_file is not None:
        if 'ohlcv_file_name' not in st.session_state or st.session_state.ohlcv_file_name != ohlcv_file.name:
            st.session_state.clear()
            st.session_state['ohlcv_file_name'] = ohlcv_file.name
        if 'signals_file_name' not in st.session_state or st.session_state.signals_file_name != signals_file.name:
            st.session_state.clear()
            st.session_state['signals_file_name'] = signals_file.name

else:
    # Enhanced welcome screen
    st.markdown("""
    <div style="text-align: center; padding: 2rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 15px; color: white; margin: 2rem 0;">
        <h2>🚀 Welcome to the Advanced Backtesting Engine</h2>
        <p style="font-size: 1.1em;">Upload your OHLCV and Signals data to get started with professional-grade backtesting</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.info("👆 Please upload both the OHLCV and Signals CSV files to begin.")
    
    # Enhanced example data format section
    st.markdown("## 📝 Expected Data Format")
    
    format_col1, format_col2 = st.columns(2)
    with format_col1:
        st.markdown("### 📊 OHLCV Data Format")
        st.write("Your price data should contain these columns:")
        ohlcv_example = pd.DataFrame({
            'Ticker': ['RELIANCE', 'TCS', 'INFY'],
            'Date': ['2023-01-01 00:00:00', '2023-01-01 00:00:00', '2023-01-01 00:00:00'],
            'Open': [2500.0, 3200.0, 1400.0],
            'High': [2550.0, 3250.0, 1450.0],
            'Low': [2480.0, 3180.0, 1380.0],
            'Close': [2520.0, 3220.0, 1420.0],
            'Volume': [1000000, 800000, 1200000]
        })
        st.dataframe(ohlcv_example, use_container_width=True)
        
        st.markdown("**Requirements:**")
        st.write("• Date format: YYYY-MM-DD or YYYY-MM-DD HH:MM:SS")
        st.write("• Ticker names must match signals file")
        st.write("• Price columns: Open, High, Low, Close")
    
    with format_col2:
        st.markdown("### 📡 Signals Data Format")
        st.write("Your trading signals should contain these columns:")
        signals_example = pd.DataFrame({
            'Ticker': ['RELIANCE', 'TCS', 'INFY'],
            'Date': ['01-01-2023', '02-01-2023', '03-01-2023']
        })
        st.dataframe(signals_example, use_container_width=True)
        
        st.markdown("**Requirements:**")
        st.write("• Date format: DD-MM-YYYY")
        st.write("• Ticker names must match OHLCV file")
        st.write("• Each row represents one trading signal")
        st.write("• Choose Long/Short after uploading")

# Enhanced footer
st.markdown("---")
st.markdown("### 🎓 Features & Capabilities")

feature_col1, feature_col2, feature_col3 = st.columns(3)

with feature_col1:
    st.markdown("""
    **📊 Signal Types**
    - 📈 Long Signals (Buy & Hold)
    - 📉 Short Signals (Sell & Cover)
    - Mixed signal analysis
    - Signal type comparison
    """)

with feature_col2:
    st.markdown("""
    **💰 Position Sizing**
    - Equal Weight allocation
    - Fixed dollar amounts
    - Risk-based sizing
    - Volatility targeting
    - ATR-based sizing
    - Kelly Criterion optimization
    """)

with feature_col3:
    st.markdown("""
    **🔍 Analysis Tools**
    - Parameter optimization
    - Monte Carlo simulation
    - Risk-adjusted metrics
    - Interactive visualizations
    - Performance attribution
    - Export capabilities
    """)

# Position sizing guide with enhanced content
with st.expander("📚 Complete Position Sizing Guide"):
    st.markdown("""
    ## Position Sizing Methods Explained
    
    ### 💰 Equal Weight (2% per position)
    - **How it works:** Allocates exactly 2% of current portfolio value to each trade
    - **Pros:** Simple, ensures diversification, good for consistent strategies
    - **Cons:** Doesn't account for volatility differences between instruments
    - **Best for:** Beginners, strategies with consistent win rates across instruments
    
    ### 💵 Fixed Dollar Amount
    - **How it works:** Uses the same dollar amount for every trade
    - **Pros:** Easy to understand, predictable position sizes
    - **Cons:** Doesn't scale with portfolio growth, ignores volatility
    - **Best for:** Testing strategies with limited capital, stable portfolio sizes
    
    ### ⚠️ Percent Risk (Risk-based)
    - **How it works:** Risks a fixed percentage of portfolio on each trade based on stop-loss distance
    - **Pros:** Controls maximum loss per trade, adapts to stop-loss levels
    - **Cons:** Requires stop-loss for every trade, can lead to very small positions
    - **Best for:** Risk-conscious traders, strategies with variable stop-losses
    
    ### 📊 Volatility Targeting
    - **How it works:** Adjusts position size based on instrument volatility to maintain target portfolio volatility
    - **Pros:** Risk-adjusted sizing, accounts for instrument characteristics
    - **Cons:** Complex calculation, requires volatility estimation
    - **Best for:** Professional traders, diversified portfolios, institutional strategies
    
    ### 📈 ATR-based Sizing
    - **How it works:** Uses Average True Range to measure volatility and size positions inversely
    - **Pros:** Adapts to market conditions, good for trend-following
    - **Cons:** Lagging indicator, may not capture sudden volatility changes
    - **Best for:** Trend-following strategies, momentum trading, technical analysis
    
    ### 🎯 Kelly Criterion
    - **How it works:** Mathematically optimal sizing based on win rate and average win/loss ratio
    - **Pros:** Theoretically optimal, maximizes long-term growth
    - **Cons:** Can be aggressive, sensitive to input parameters, requires accurate estimates
    - **Best for:** Experienced traders with good historical data, long-term growth focus
    
    ## Tips for Choosing Position Sizing:
    
    1. **Start Conservative:** Begin with 1-2% risk per trade until you understand your strategy
    2. **Consider Correlation:** If trading correlated instruments, reduce position sizes
    3. **Monitor Portfolio Concentration:** Avoid putting too much capital in similar trades
    4. **Backtest Different Methods:** Compare performance across sizing methods
    5. **Account for Market Conditions:** Consider reducing sizes during volatile periods
    6. **Regular Review:** Adjust sizing parameters based on changing market conditions
    
    ## Risk Management Guidelines:
    
    - **Maximum Single Position:** Generally 5-10% of portfolio
    - **Sector Concentration:** Limit exposure to single sectors
    - **Correlation Limits:** Account for correlated positions
    - **Drawdown Controls:** Reduce sizing after significant losses
    - **Volatility Adjustments:** Scale down during high volatility periods
    """)

st.markdown("---")
st.markdown(
    '<div style="text-align: center; color: #666; font-size: 0.9em; padding: 1rem;">'
    '🚀 Enhanced Backtesting Engine with Long/Short Support • Built with Streamlit • '
    'Professional-grade trading analytics'
    '</div>', 
    unsafe_allow_html=True
)
# --- Presentation Block (runs independently) ---
if 'backtest_results' in st.session_state and not st.session_state['backtest_results'].empty:
    trade_log_df = st.session_state['backtest_results']
    params = st.session_state['backtest_params']
    
    initial_capital = params.get('initial_capital', 100000)
    signal_type = params.get('signal_type', 'long')
    
    performance_metrics = calculate_performance_metrics(trade_log_df, initial_capital)
    
    st.markdown("## 📊 Backtest Results")
    st.markdown(f"""
    <div style="background: linear-gradient(90deg, #28a745, #20c997); padding: 1rem; border-radius: 10px; color: white; text-align: center; margin-bottom: 2rem;">
        <h3>✅ Backtest Completed Successfully!</h3>
        <p>Analyzed <strong>{performance_metrics.get('Total Trades', 0)}</strong> {signal_type.upper()} trades across <strong>{trade_log_df['Ticker'].nunique()}</strong> instruments</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Enhanced KPI display
    st.markdown("### 🎯 Key Performance Indicators")
    kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5 = st.columns(5)
    with kpi_col1:
        st.metric("Total Return", f"{performance_metrics.get('Total Return (%)', 0):.2f}%", 
                 help=f"Total portfolio return from {signal_type} signals")
        st.metric("Total P&L", f"${performance_metrics.get('Total P&L ($)', 0):,.0f}")
    with kpi_col2:
        st.metric("Win Rate", f"{performance_metrics.get('Win Rate (%)', 0):.2f}%")
        st.metric("Profit Factor", f"{performance_metrics.get('Profit Factor', 0):.2f}")
    with kpi_col3:
        st.metric("Max Drawdown", f"{performance_metrics.get('Max Drawdown (%)', 0):.2f}%")
        st.metric("Sharpe Ratio", f"{performance_metrics.get('Sharpe Ratio', 0):.3f}")
    with kpi_col4:
        st.metric("Total Trades", f"{performance_metrics.get('Total Trades', 0)}")
        st.metric("Avg Win", f"{performance_metrics.get('Average Win (%)', 0):.2f}%")
    with kpi_col5:
        st.metric("Avg Position", f"${performance_metrics.get('Average Position Size ($)', 0):,.0f}")
        st.metric("Max Position", f"${performance_metrics.get('Max Position Size ($)', 0):,.0f}")

    # Tabs for detailed analysis
    tab1, tab_invested, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📈 Equity Curve", "📊 Invested Capital", "📋 Trade Log", "🏢 Per-Instrument",
        "📊 Trade Analysis", "📏 Position Sizing", "🎲 Monte Carlo", "⚖️ Leverage Metrics"
    ])
    
    with tab1:
        st.markdown("### Portfolio Performance Over Time")
        equity_curve = performance_metrics.get("Equity Curve")
        if equity_curve is not None:
            fig = px.line(equity_curve, x=equity_curve.index, y='Portfolio Value', 
                        title=f"Portfolio Value Over Time ({signal_type.upper()} Signals)",
                        labels={'Portfolio Value': 'Portfolio Value ($)', 'Exit Date': 'Date'})
            fig.add_hline(y=initial_capital, line_dash="dash", 
                        annotation_text=f"Starting Capital: ${initial_capital:,}")
            fig.update_layout(hovermode='x', height=500)
            st.plotly_chart(fig, use_container_width=True)
            final_value = equity_curve['Portfolio Value'].iloc[-1]
            total_return = ((final_value / initial_capital) - 1) * 100
            st.info(f"📊 Final Portfolio Value: ${final_value:,.0f} | Total Return: {total_return:.2f}%")

    with tab_invested:
        st.markdown("### Net Invested Value Over Time")
        invested_value_df = calculate_invested_value_over_time(trade_log_df)
        if not invested_value_df.empty:
            fig = px.line(invested_value_df, x='Date', y='Invested Value',
                        title="Net Invested Value Over Time",
                        labels={'Invested Value': 'Invested Value ($)', 'Date': 'Date'})
            fig.update_layout(hovermode='x', height=500)
            st.plotly_chart(fig, use_container_width=True)
            st.markdown("#### Invested Value Data")
            st.dataframe(invested_value_df.style.format({'Invested Value': '${:,.0f}'}), use_container_width=True)
        else:
            st.info("No invested value data to display.")

    with tab2:
        st.markdown("### Detailed Trade Log")
        
        # Add filtering options for trade log
        st.markdown("#### 🔍 Filter Options")
        filter_col1, filter_col2, filter_col3 = st.columns(3)
        
        with filter_col1:
            all_tickers = ['All'] + sorted(trade_log_df['Ticker'].unique())
            ticker_filter = st.selectbox("Filter by Ticker:", all_tickers, key="ticker_filter_2")
        
        with filter_col2:
            outcome_filter = st.selectbox("Filter by Outcome:", ['All', 'Winners', 'Losers'], key="outcome_filter_2")
            
        with filter_col3:
            all_exit_reasons = ['All'] + sorted(trade_log_df['Exit Reason'].unique())
            exit_reason_filter = st.selectbox("Filter by Exit Reason:", all_exit_reasons, key="exit_reason_filter_2")
            
        # Apply filters
        filtered_df = trade_log_df.copy()
        if ticker_filter != 'All':
            filtered_df = filtered_df[filtered_df['Ticker'] == ticker_filter]
        if outcome_filter == 'Winners':
            filtered_df = filtered_df[filtered_df['Profit/Loss (%)'] > 0]
        elif outcome_filter == 'Losers':
            filtered_df = filtered_df[filtered_df['Profit/Loss (%)'] <= 0]
        if exit_reason_filter != 'All':
            filtered_df = filtered_df[filtered_df['Exit Reason'] == exit_reason_filter]
            
        st.dataframe(filtered_df)

    with tab3:
        st.markdown("### Performance by Instrument")
        instrument_performance = trade_log_df.groupby('Ticker').agg({
            'Profit/Loss (%)': ['mean', 'sum', 'count', 'std'],
            'P&L ($)': ['mean', 'sum'],
            'Position Value': 'mean'
        })
        instrument_performance.columns = [
            'Avg P/L (%)', 'Total P/L (%)', 'Trades', 'Volatility (%)',
            'Avg P/L ($)', 'Total P/L ($)', 'Avg Position ($)'
        ]
        instrument_performance = instrument_performance.sort_values(by='Total P/L ($)', ascending=False)
        win_rates = trade_log_df.groupby('Ticker').apply(
            lambda x: (x['Profit/Loss (%)'] > 0).sum() / len(x) * 100
        ).rename('Win Rate (%)')
        instrument_performance = instrument_performance.join(win_rates)
        st.dataframe(
            instrument_performance.style.format({
                'Avg P/L (%)': '{:.2f}%', 'Total P/L (%)': '{:.2f}%',
                'Volatility (%)': '{:.2f}%', 'Win Rate (%)': '{:.1f}%',
                'Avg P/L ($)': '${:,.0f}', 'Total P/L ($)': '${:,.0f}',
                'Avg Position ($)': '${:,.0f}'
            }).background_gradient(subset=['Total P/L ($)'], cmap='RdYlGn'),
            use_container_width=True
        )

    with tab4:
        st.markdown("### Trade Analysis Dashboard")
        
        analysis_col1, analysis_col2 = st.columns(2)
        
        with analysis_col1:
            # Exit reason distribution
            exit_reasons = trade_log_df['Exit Reason'].value_counts()
            fig = px.pie(values=exit_reasons.values, names=exit_reasons.index,
                       title="Trade Exit Reasons",
                       color_discrete_sequence=px.colors.qualitative.Set3)
            st.plotly_chart(fig, use_container_width=True)
            
            # Holding period distribution
            fig = px.histogram(trade_log_df, x='Days Held', nbins=20,
                             title="Holding Period Distribution",
                             labels={'Days Held': 'Days Held'})
            st.plotly_chart(fig, use_container_width=True)
        
        with analysis_col2:
            # P&L distribution (percentage)
            fig = px.histogram(trade_log_df, x='Profit/Loss (%)', nbins=25,
                             title="P&L Distribution (%)",
                             color_discrete_sequence=['#1f77b4'])
            fig.add_vline(x=0, line_dash="dash", line_color="red",
                        annotation_text="Break-even")
            st.plotly_chart(fig, use_container_width=True)
            
            # P&L over time
            fig = px.scatter(trade_log_df, x='Exit Date', y='Profit/Loss (%)',
                           color='Exit Reason', size='Position Value',
                           title="P&L Over Time",
                           hover_data=['Ticker', 'Days Held'])
            fig.add_hline(y=0, line_dash="dash", line_color="red")
            st.plotly_chart(fig, use_container_width=True)

    with tab5:
        st.markdown("### Position Sizing Analysis")
        
        pos_col1, pos_col2 = st.columns(2)
        
        with pos_col1:
            # Position size distribution
            fig = px.histogram(trade_log_df, x='Position Value', nbins=20,
                             title="Position Size Distribution",
                             labels={'Position Value': 'Position Value ($)'},
                             color_discrete_sequence=['#ff7f0e'])
            st.plotly_chart(fig, use_container_width=True)
        
        with pos_col2:
            # Position size over time
            fig = px.scatter(trade_log_df, x='Entry Date', y='Position Value',
                           color='Profit/Loss (%)',
                           title="Position Size Over Time",
                           labels={'Position Value': 'Position Value ($)'},
                           hover_data=['Ticker', 'P&L ($)'],
                           color_continuous_scale='RdYlGn')
            st.plotly_chart(fig, use_container_width=True)

    with tab6:
        st.markdown("### Monte Carlo Analysis")
        
        if len(trade_log_df) > 10:
            returns = trade_log_df['Profit/Loss (%)'] / 100
            
            n_simulations = st.slider("Number of Simulations", 100, 2000, 1000, key="mc_sims_2")
            n_trades = st.slider("Future Trades to Simulate", 10, 200, 50, key="mc_trades_2")
            
            if st.button("🎲 Run Monte Carlo Simulation", key="mc_run_2"):
                with st.spinner("Running Monte Carlo simulation..."):
                    simulations = []
                    for _ in range(n_simulations):
                        sim_returns = np.random.choice(returns, n_trades, replace=True)
                        final_return = np.prod(1 + sim_returns) - 1
                        simulations.append(final_return * 100)
                    
                    fig = px.histogram(simulations, nbins=50,
                                     title=f"Monte Carlo Simulation: {n_trades} Future Trades ({n_simulations} simulations)")
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("⚠️ Need at least 10 trades to run Monte Carlo simulation")

    with tab7:
        st.markdown("### ⚖️ Leverage Metrics Analysis")
        
        leverage_metrics = performance_metrics.get('Leverage Metrics', {})
        
        if leverage_metrics:
            st.markdown("#### 📊 Key Leverage Metrics")
            leverage_col1, leverage_col2, leverage_col3, leverage_col4 = st.columns(4)
            
            with leverage_col1:
                st.metric("Average Leverage", f"{leverage_metrics.get('Average Leverage', 0):.2f}x")
            with leverage_col2:
                st.metric("Maximum Leverage", f"{leverage_metrics.get('Max Leverage', 0):.2f}x")
            with leverage_col3:
                st.metric("Leverage Risk Score", f"{leverage_metrics.get('Leverage Risk Score', 0):.2f}")
            with leverage_col4:
                st.metric("Leverage-Performance Correlation", f"{leverage_metrics.get('Leverage Performance Correlation', 0):.3f}")

            # Leverage distribution chart
            leverage_dist_fig = create_leverage_distribution_chart(trade_log_df)
            if leverage_dist_fig:
                st.plotly_chart(leverage_dist_fig, use_container_width=True)
        else:
            st.warning("⚠️ No leverage data available.")