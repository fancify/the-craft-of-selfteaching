import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.vegas_channel import VegasChannel

@pytest.fixture
def sample_data():
    """Create sample daily and weekly data for testing with sufficient history for EMA calculation."""
    # Create daily data with sufficient history for EMA calculation
    daily_dates = pd.date_range(start='2024-01-01', periods=200, freq='D')

    # Create price series with different trends for better testing
    prices = np.concatenate([
        np.ones(50) * 100,                    # Flat period for EMA stabilization
        np.linspace(100, 150, 50),            # Uptrend for long testing
        np.ones(50) * 150,                    # Flat high period
        np.linspace(150, 100, 50)             # Downtrend for short testing
    ])

    # Add some noise to make it more realistic
    noise = np.random.normal(0, 1, 200)
    prices = prices + noise

    daily_data = pd.DataFrame({
        'open': prices + np.random.normal(0, 1, 200),
        'high': prices + np.random.normal(2, 1, 200),
        'low': prices - np.random.normal(2, 1, 200),
        'close': prices,
        'volume': np.random.normal(1000, 100, 200)
    }, index=daily_dates)

    # Create weekly data that matches the daily trends
    weekly_dates = pd.date_range(start='2024-01-01', end=daily_dates[-1], freq='W')
    weekly_prices = np.interp(
        np.linspace(0, len(prices)-1, len(weekly_dates)),
        np.arange(len(prices)),
        prices
    )

    weekly_data = pd.DataFrame({
        'open': weekly_prices + np.random.normal(0, 1, len(weekly_dates)),
        'high': weekly_prices + np.random.normal(2, 1, len(weekly_dates)),
        'low': weekly_prices - np.random.normal(2, 1, len(weekly_dates)),
        'close': weekly_prices,
        'volume': np.random.normal(1000, 100, len(weekly_dates))
    }, index=weekly_dates)

    return daily_data, weekly_data

def test_vegas_channel_calculation():
    """Test Vegas Channel bands calculation using EMAs."""
    vegas = VegasChannel()

    # Create test data with specific trend for EMA verification
    dates = pd.date_range(start='2024-01-01', periods=200, freq='D')
    prices = np.concatenate([
        np.ones(100) * 100,  # Flat period for EMA stabilization
        np.linspace(100, 200, 100)  # Upward trend for lag verification
    ])
    data = pd.DataFrame({'close': prices}, index=dates)

    result = vegas.calculate_bands(data)

    # Verify EMA calculations
    assert 'ema_144' in result.columns
    assert 'ema_169' in result.columns
    assert 'vegas_lower' in result.columns
    assert 'vegas_upper' in result.columns

    # Verify EMA mapping
    assert (result['vegas_lower'] == result['ema_144']).all()
    assert (result['vegas_upper'] == result['ema_169']).all()

    # Verify EMA behavior
    stable_period = result.iloc[90:100]  # Check flat period
    assert abs(stable_period['ema_144'].std()) < 0.1  # EMAs should be stable
    assert abs(stable_period['ema_169'].std()) < 0.1

    trend_period = result.iloc[-20:]  # Check trend period
    assert (trend_period['ema_144'] > trend_period['ema_169']).all()  # Faster EMA leads in uptrend

def test_dual_timeframe_signals(sample_data):
    """Test signal generation with dual timeframe data."""
    daily_data, weekly_data = sample_data
    vegas = VegasChannel()

    signals = vegas.get_signals(daily_data, weekly_data)

    assert len(signals) == len(daily_data)
    assert 'position' in signals.columns
    assert signals['position'].isin([-1, 0, 1]).all()

def test_long_entry_conditions(sample_data):
    """Test long entry conditions."""
    daily_data, weekly_data = sample_data
    vegas = VegasChannel()

    # Calculate bands
    daily_data = vegas.calculate_bands(daily_data)
    weekly_data = vegas.calculate_bands(weekly_data)

    # Use a point during the uptrend period for long entry test
    test_date = daily_data.index[80]  # During uptrend period
    weekly_date = weekly_data.index[weekly_data.index <= test_date][-1]

    # Force prices above upper bands
    daily_data.loc[test_date, 'close'] = daily_data.loc[test_date, 'vegas_upper'] * 1.1
    weekly_data.loc[weekly_date, 'close'] = weekly_data.loc[weekly_date, 'vegas_upper'] * 1.1

    signals = vegas.get_signals(daily_data, weekly_data)

    # Print debug information
    print("\nLong Entry Test Debug:")
    print(f"Test Date: {test_date}")
    print(f"Weekly Date: {weekly_date}")
    print("\nDaily Data:")
    print(f"Close: {signals.loc[test_date, 'daily_close']:.2f}")
    print(f"Lower Band: {signals.loc[test_date, 'daily_lower']:.2f}")
    print(f"Upper Band: {signals.loc[test_date, 'daily_upper']:.2f}")
    print("\nWeekly Data:")
    print(f"Close: {signals.loc[test_date, 'weekly_close']:.2f}")
    print(f"Lower Band: {signals.loc[test_date, 'weekly_lower']:.2f}")
    print(f"Upper Band: {signals.loc[test_date, 'weekly_upper']:.2f}")
    print(f"\nPosition: {signals.loc[test_date, 'position']}")

    assert signals['position'].loc[test_date] == 1  # Should enter long position

def test_short_entry_conditions(sample_data):
    """Test short entry conditions."""
    daily_data, weekly_data = sample_data
    vegas = VegasChannel()

    # Calculate bands
    daily_data = vegas.calculate_bands(daily_data)
    weekly_data = vegas.calculate_bands(weekly_data)

    # Set prices below lower bands at a point where we have both daily and weekly data
    test_date = daily_data.index[180]  # Use a later date to ensure EMAs are warmed up
    weekly_date = weekly_data.index[weekly_data.index <= test_date][-1]

    daily_data.loc[test_date, 'close'] = daily_data.loc[test_date, 'vegas_lower'] * 0.9
    weekly_data.loc[weekly_date, 'close'] = weekly_data.loc[weekly_date, 'vegas_lower'] * 0.9

    signals = vegas.get_signals(daily_data, weekly_data)

    # Print debug information
    print("\nShort Entry Test Debug:")
    print(f"Test Date: {test_date}")
    print(f"Weekly Date: {weekly_date}")
    print("\nDaily Data:")
    print(f"Close: {signals.loc[test_date, 'daily_close']:.2f}")
    print(f"Lower Band: {signals.loc[test_date, 'daily_lower']:.2f}")
    print(f"Upper Band: {signals.loc[test_date, 'daily_upper']:.2f}")
    print("\nWeekly Data:")
    print(f"Close: {signals.loc[test_date, 'weekly_close']:.2f}")
    print(f"Lower Band: {signals.loc[test_date, 'weekly_lower']:.2f}")
    print(f"Upper Band: {signals.loc[test_date, 'weekly_upper']:.2f}")
    print(f"\nPosition: {signals.loc[test_date, 'position']}")

    assert signals['position'].loc[test_date] == -1  # Should enter short position

def test_long_exit_conditions(sample_data):
    """Test long exit conditions."""
    daily_data, weekly_data = sample_data
    vegas = VegasChannel()

    # Calculate bands
    daily_data = vegas.calculate_bands(daily_data)
    weekly_data = vegas.calculate_bands(weekly_data)

    # Create initial long position during uptrend
    entry_date = daily_data.index[80]  # During uptrend period
    weekly_entry_date = weekly_data.index[weekly_data.index <= entry_date][-1]

    # Force prices above upper bands for entry
    daily_data.loc[entry_date, 'close'] = daily_data.loc[entry_date, 'vegas_upper'] * 1.1
    weekly_data.loc[weekly_entry_date, 'close'] = weekly_data.loc[weekly_entry_date, 'vegas_upper'] * 1.1

    # Create exit condition during downtrend
    exit_date = daily_data.index[160]  # During downtrend period
    daily_data.loc[exit_date, 'close'] = daily_data.loc[exit_date, 'vegas_lower'] * 0.9

    signals = vegas.get_signals(daily_data, weekly_data)

    # Print debug information
    print("\nLong Exit Test Debug:")
    print(f"Entry Date: {entry_date}")
    print(f"Exit Date: {exit_date}")
    print("\nAt Entry:")
    print(f"Daily Close: {signals.loc[entry_date, 'daily_close']:.2f}")
    print(f"Daily Upper: {signals.loc[entry_date, 'daily_upper']:.2f}")
    print("\nAt Exit:")
    print(f"Daily Close: {signals.loc[exit_date, 'daily_close']:.2f}")
    print(f"Daily Lower: {signals.loc[exit_date, 'daily_lower']:.2f}")
    print(f"Position at Exit: {signals.loc[exit_date, 'position']}")

    assert signals['position'].loc[exit_date] == 0  # Should exit long position

def test_short_exit_conditions(sample_data):
    """Test short exit conditions."""
    daily_data, weekly_data = sample_data
    vegas = VegasChannel()

    # Calculate bands
    daily_data = vegas.calculate_bands(daily_data)
    weekly_data = vegas.calculate_bands(weekly_data)

    # Create initial short position
    entry_date = daily_data.index[170]  # Use later dates to ensure EMAs are warmed up
    weekly_entry_date = weekly_data.index[weekly_data.index <= entry_date][-1]

    daily_data.loc[entry_date, 'close'] = daily_data.loc[entry_date, 'vegas_lower'] * 0.9
    weekly_data.loc[weekly_entry_date, 'close'] = weekly_data.loc[weekly_entry_date, 'vegas_lower'] * 0.9

    # Create exit condition
    exit_date = daily_data.index[180]
    daily_data.loc[exit_date, 'close'] = daily_data.loc[exit_date, 'vegas_upper'] * 1.1

    signals = vegas.get_signals(daily_data, weekly_data)

    # Print debug information
    print("\nShort Exit Test Debug:")
    print(f"Entry Date: {entry_date}")
    print(f"Exit Date: {exit_date}")
    print("\nAt Entry:")
    print(f"Daily Close: {signals.loc[entry_date, 'daily_close']:.2f}")
    print(f"Daily Lower: {signals.loc[entry_date, 'daily_lower']:.2f}")
    print("\nAt Exit:")
    print(f"Daily Close: {signals.loc[exit_date, 'daily_close']:.2f}")
    print(f"Daily Upper: {signals.loc[exit_date, 'daily_upper']:.2f}")
    print(f"Position at Exit: {signals.loc[exit_date, 'position']}")

    assert signals['position'].loc[exit_date] == 0  # Should exit short position

def test_position_state_maintenance():
    """Test that position state is maintained correctly."""
    vegas = VegasChannel()

    # Create test data with sufficient history
    daily_dates = pd.date_range(start='2024-01-01', periods=200, freq='D')
    weekly_dates = pd.date_range(start='2024-01-01', end=daily_dates[-1], freq='W')

    daily_data = pd.DataFrame({
        'close': np.linspace(100, 200, 200)  # Linear trend
    }, index=daily_dates)

    weekly_data = pd.DataFrame({
        'close': np.linspace(100, 200, len(weekly_dates))  # Matching trend
    }, index=weekly_dates)

    # Calculate bands
    daily_data = vegas.calculate_bands(daily_data)
    weekly_data = vegas.calculate_bands(weekly_data)

    # Set up entry condition
    entry_date = daily_data.index[170]  # Use later date to ensure EMAs are warmed up
    weekly_entry_date = weekly_data.index[weekly_data.index <= entry_date][-1]

    daily_data.loc[entry_date, 'close'] = daily_data.loc[entry_date, 'vegas_upper'] * 1.1
    weekly_data.loc[weekly_entry_date, 'close'] = weekly_data.loc[weekly_entry_date, 'vegas_upper'] * 1.1

    signals = vegas.get_signals(daily_data, weekly_data)

    # Position should be maintained until exit conditions are met
    assert len(signals['position'].unique()) <= 3  # Only -1, 0, 1 allowed
    assert not signals['position'].isna().any()  # No NaN values allowed
