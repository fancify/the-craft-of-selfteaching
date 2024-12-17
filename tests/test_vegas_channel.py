import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.vegas_channel import VegasChannel

def create_test_data(start_date: str, periods: int, freq: str) -> pd.DataFrame:
    """Create test data for testing the Vegas Channel strategy"""
    dates = pd.date_range(start=start_date, periods=periods, freq=freq)
    data = pd.DataFrame(index=dates)

    # Generate sample price data
    data['close'] = np.linspace(100, 200, periods) + np.random.normal(0, 5, periods)
    data['open'] = data['close'] + np.random.normal(0, 2, periods)
    data['high'] = np.maximum(data['open'], data['close']) + np.random.normal(0, 1, periods)
    data['low'] = np.minimum(data['open'], data['close']) - np.random.normal(0, 1, periods)

    return data

def test_calculate_bands():
    """Test Vegas Channel bands calculation"""
    vc = VegasChannel()
    data = create_test_data('2023-01-01', 200, 'D')

    result = vc.calculate_bands(data)
    assert 'vegas_lower' in result.columns
    assert 'vegas_upper' in result.columns
    assert len(result) == len(data)

def test_get_signals():
    """Test signal generation"""
    vc = VegasChannel()
    daily_data = create_test_data('2023-01-01', 200, 'D')
    weekly_data = create_test_data('2023-01-01', 30, 'W')

    signals = vc.get_signals(daily_data, weekly_data)
    assert 'position' in signals.columns
    assert len(signals) == len(daily_data)
    assert all(signals['position'].isin([-1, 0, 1]))

def test_backtest():
    """Test backtest functionality with position sizing"""
    vc = VegasChannel(total_margin=100000, max_coins=50)
    daily_data = create_test_data('2023-01-01', 200, 'D')
    weekly_data = create_test_data('2023-01-01', 30, 'W')

    results = vc.backtest(daily_data, weekly_data)

    # Check required columns
    required_columns = ['position', 'position_size', 'strategy_returns',
                       'cumulative_returns', 'close', 'vegas_lower', 'vegas_upper']
    assert all(col in results.columns for col in required_columns)

    # Verify position sizing
    non_zero_positions = results[results['position'] != 0]
    if len(non_zero_positions) > 0:
        position_values = abs(non_zero_positions['position_size'] *
                            non_zero_positions['close'])
        assert all(position_values <= vc.position_manager.margin_per_coin * 1.01)  # Allow 1% margin

    # Check strategy calculations
    assert len(results) == len(daily_data)
    assert all(results['position'].isin([-1, 0, 1]))
    assert all(results['cumulative_returns'].notna())

def test_real_market_data():
    """Test Vegas Channel strategy with real Binance futures data"""
    # Load real market data
    daily_data = pd.read_csv('data/market_data/daily/BTCUSDT_daily_20241217.csv')
    weekly_data = pd.read_csv('data/market_data/weekly/BTCUSDT_weekly_20241217.csv')

    # Convert close_time to datetime index
    daily_data['timestamp'] = pd.to_datetime(daily_data['close_time'], unit='ms')
    weekly_data['timestamp'] = pd.to_datetime(weekly_data['close_time'], unit='ms')
    daily_data.set_index('timestamp', inplace=True)
    weekly_data.set_index('timestamp', inplace=True)

    # Select required columns
    columns = ['open', 'high', 'low', 'close']
    daily_data = daily_data[columns]
    weekly_data = weekly_data[columns]

    # Calculate weekly EMAs before the loop
    weekly_data['ema_169'] = weekly_data['close'].ewm(span=169, adjust=False).mean()
    weekly_data['ema_144'] = weekly_data['close'].ewm(span=144, adjust=False).mean()

    # Initialize strategy
    vc = VegasChannel(total_margin=100000, max_coins=50)

    # Run backtest
    results = vc.backtest(daily_data, weekly_data)

    # Verify required columns
    required_columns = ['position', 'position_size', 'strategy_returns',
                       'cumulative_returns', 'close', 'vegas_lower', 'vegas_upper']
    assert all(col in results.columns for col in required_columns)

    # Test position sizing
    non_zero_positions = results[results['position'] != 0]
    if len(non_zero_positions) > 0:
        position_values = abs(non_zero_positions['position_size'] *
                            non_zero_positions['close'])
        assert all(position_values <= vc.position_manager.margin_per_coin * 1.01)

    # Check that positions align with strategy rules
    for i in range(len(results)):
        if i == 0:  # Skip first row due to NaN returns
            continue

        current_date = results.index[i]
        weekly_mask = weekly_data.index <= current_date
        if not weekly_mask.any():
            continue

        current_weekly = weekly_data[weekly_mask].iloc[-1]

        # Check position changes
        if results['position'].iloc[i] == 1:  # Long position
            if results['position'].iloc[i-1] != 1:  # New long position
                assert (results['close'].iloc[i] > results['vegas_upper'].iloc[i] and
                       current_weekly['close'] > current_weekly['ema_169']), \
                    f"Long entry conditions not met at {current_date}"
            elif results['close'].iloc[i] < results['vegas_lower'].iloc[i]:
                assert results['position'].iloc[i+1] == 0 if i < len(results)-1 else True, \
                    f"Long exit condition not met at {current_date}"

        elif results['position'].iloc[i] == -1:  # Short position
            if results['position'].iloc[i-1] != -1:  # New short position
                assert (results['close'].iloc[i] < results['vegas_lower'].iloc[i] and
                       current_weekly['close'] < current_weekly['ema_144']), \
                    f"Short entry conditions not met at {current_date}"
            elif results['close'].iloc[i] > results['vegas_upper'].iloc[i]:
                assert results['position'].iloc[i+1] == 0 if i < len(results)-1 else True, \
                    f"Short exit condition not met at {current_date}"

    # Verify no NaN values in cumulative returns
    assert all(results['cumulative_returns'].notna())

    # Print strategy performance metrics
    print(f"\nStrategy Performance Metrics:")
    print(f"Total Returns: {(results['cumulative_returns'].iloc[-1] - 1) * 100:.2f}%")
    print(f"Number of Trades: {(results['position'] != results['position'].shift(1)).sum()}")
    print(f"Max Drawdown: {((results['cumulative_returns'] / results['cumulative_returns'].cummax() - 1).min() * 100):.2f}%")
