import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.vegas_channel import VegasChannel

@pytest.fixture
def sample_data():
    """Create sample daily and weekly data for testing."""
    # Create daily data
    daily_dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
    daily_data = pd.DataFrame({
        'open': np.random.normal(100, 10, 30),
        'high': np.random.normal(105, 10, 30),
        'low': np.random.normal(95, 10, 30),
        'close': np.random.normal(100, 10, 30),
        'volume': np.random.normal(1000, 100, 30)
    }, index=daily_dates)

    # Create weekly data that fully covers the daily date range
    weekly_dates = pd.date_range(start='2024-01-01', end=daily_dates[-1], freq='W')
    weekly_data = pd.DataFrame({
        'open': np.random.normal(100, 10, len(weekly_dates)),
        'high': np.random.normal(105, 10, len(weekly_dates)),
        'low': np.random.normal(95, 10, len(weekly_dates)),
        'close': np.random.normal(100, 10, len(weekly_dates)),
        'volume': np.random.normal(1000, 100, len(weekly_dates))
    }, index=weekly_dates)

    return daily_data, weekly_data

def test_vegas_channel_calculation():
    """Test Vegas Channel bands calculation."""
    vegas = VegasChannel()

    dates = pd.date_range(start='2024-01-01', periods=50, freq='D')
    data = pd.DataFrame({
        'close': np.linspace(100, 200, 50)  # Upward trend
    }, index=dates)

    result = vegas.calculate_bands(data, vegas.daily_period)

    assert 'vegas_middle' in result.columns
    assert 'vegas_upper' in result.columns
    assert 'vegas_lower' in result.columns
    assert len(result) == len(data)

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

    # Calculate bands first
    daily_data = vegas.calculate_bands(daily_data, vegas.daily_period)
    weekly_data = vegas.calculate_bands(weekly_data, vegas.weekly_period)

    # Set prices above upper bands at a point where we have both daily and weekly data
    test_date = daily_data.index[25]  # Use a later date to ensure we have weekly data
    weekly_date = weekly_data.index[weekly_data.index <= test_date][-1]

    daily_data.loc[test_date, 'close'] = daily_data.loc[test_date, 'vegas_upper'] * 1.1
    weekly_data.loc[weekly_date, 'close'] = weekly_data.loc[weekly_date, 'vegas_upper'] * 1.1

    signals = vegas.get_signals(daily_data, weekly_data)
    assert signals['position'].loc[test_date] == 1  # Should enter long position

def test_short_entry_conditions(sample_data):
    """Test short entry conditions."""
    daily_data, weekly_data = sample_data
    vegas = VegasChannel()

    # Calculate bands first
    daily_data = vegas.calculate_bands(daily_data, vegas.daily_period)
    weekly_data = vegas.calculate_bands(weekly_data, vegas.weekly_period)

    # Set prices below lower bands at a point where we have both daily and weekly data
    test_date = daily_data.index[25]  # Use a later date to ensure we have weekly data
    weekly_date = weekly_data.index[weekly_data.index <= test_date][-1]

    daily_data.loc[test_date, 'close'] = daily_data.loc[test_date, 'vegas_lower'] * 0.9
    weekly_data.loc[weekly_date, 'close'] = weekly_data.loc[weekly_date, 'vegas_lower'] * 0.9

    signals = vegas.get_signals(daily_data, weekly_data)
    assert signals['position'].loc[test_date] == -1  # Should enter short position

def test_long_exit_conditions(sample_data):
    """Test long exit conditions."""
    daily_data, weekly_data = sample_data
    vegas = VegasChannel()

    # Calculate bands first
    daily_data = vegas.calculate_bands(daily_data, vegas.daily_period)
    weekly_data = vegas.calculate_bands(weekly_data, vegas.weekly_period)

    # Create initial long position
    entry_date = daily_data.index[20]
    weekly_entry_date = weekly_data.index[weekly_data.index <= entry_date][-1]

    daily_data.loc[entry_date, 'close'] = daily_data.loc[entry_date, 'vegas_upper'] * 1.1
    weekly_data.loc[weekly_entry_date, 'close'] = weekly_data.loc[weekly_entry_date, 'vegas_upper'] * 1.1

    # Create exit condition
    exit_date = daily_data.index[25]
    daily_data.loc[exit_date, 'close'] = daily_data.loc[exit_date, 'vegas_lower'] * 0.9

    signals = vegas.get_signals(daily_data, weekly_data)
    assert signals['position'].loc[exit_date] == 0  # Should exit long position

def test_short_exit_conditions(sample_data):
    """Test short exit conditions."""
    daily_data, weekly_data = sample_data
    vegas = VegasChannel()

    # Calculate bands first
    daily_data = vegas.calculate_bands(daily_data, vegas.daily_period)
    weekly_data = vegas.calculate_bands(weekly_data, vegas.weekly_period)

    # Create initial short position
    entry_date = daily_data.index[20]
    weekly_entry_date = weekly_data.index[weekly_data.index <= entry_date][-1]

    daily_data.loc[entry_date, 'close'] = daily_data.loc[entry_date, 'vegas_lower'] * 0.9
    weekly_data.loc[weekly_entry_date, 'close'] = weekly_data.loc[weekly_entry_date, 'vegas_lower'] * 0.9

    # Create exit condition
    exit_date = daily_data.index[25]
    daily_data.loc[exit_date, 'close'] = daily_data.loc[exit_date, 'vegas_upper'] * 1.1

    signals = vegas.get_signals(daily_data, weekly_data)
    assert signals['position'].loc[exit_date] == 0  # Should exit short position

def test_position_state_maintenance():
    """Test that position state is maintained correctly."""
    vegas = VegasChannel()

    # Create test data with proper weekly coverage
    daily_dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
    weekly_dates = pd.date_range(start='2024-01-01', end=daily_dates[-1], freq='W')

    daily_data = pd.DataFrame({
        'close': [100] * len(daily_dates)
    }, index=daily_dates)

    weekly_data = pd.DataFrame({
        'close': [100] * len(weekly_dates)
    }, index=weekly_dates)

    # Calculate bands
    daily_data = vegas.calculate_bands(daily_data, vegas.daily_period)
    weekly_data = vegas.calculate_bands(weekly_data, vegas.weekly_period)

    # Set up entry condition
    entry_date = daily_data.index[20]
    weekly_entry_date = weekly_data.index[weekly_data.index <= entry_date][-1]

    daily_data.loc[entry_date, 'close'] = daily_data.loc[entry_date, 'vegas_upper'] * 1.1
    weekly_data.loc[weekly_entry_date, 'close'] = weekly_data.loc[weekly_entry_date, 'vegas_upper'] * 1.1

    signals = vegas.get_signals(daily_data, weekly_data)

    # Position should be maintained until exit conditions are met
    assert len(signals['position'].unique()) <= 3  # Only -1, 0, 1 allowed
    assert not signals['position'].isna().any()  # No NaN values allowed
