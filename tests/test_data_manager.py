import pytest
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from binance.client import Client
from src.data_manager import DataManager

@pytest.fixture
def mock_client():
    return Mock(spec=Client)

@pytest.fixture
def data_manager(mock_client):
    return DataManager(mock_client)

@pytest.fixture
def sample_klines():
    base_time = int(datetime(2024, 1, 1).timestamp() * 1000)
    return [
        [
            base_time + i * 86400000,  # timestamp
            "100",  # open
            "101",  # high
            "99",   # low
            "100.5",# close
            "1000", # volume
            base_time + (i + 1) * 86400000 - 1,  # close_time
            "100000",  # quote_volume
            100,    # trades
            "500",  # taker_buy_volume
            "50000",# taker_buy_quote_volume
            "0"     # ignore
        ]
        for i in range(10)
    ]

def test_get_klines_success(data_manager, mock_client, sample_klines):
    mock_client.futures_klines.return_value = sample_klines

    df = data_manager.get_klines("BTCUSDT", "1d", 10)

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 10
    assert all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume'])
    assert isinstance(df.index, pd.DatetimeIndex)
    assert df['close'].dtype == float

def test_get_klines_error(data_manager, mock_client):
    mock_client.futures_klines.side_effect = Exception("API Error")

    df = data_manager.get_klines("BTCUSDT", "1d", 10)

    assert df is None

def test_get_synchronized_data_success(data_manager, mock_client, sample_klines):
    mock_client.futures_klines.return_value = sample_klines

    daily_data, weekly_data = data_manager.get_synchronized_data("BTCUSDT")

    assert isinstance(daily_data, pd.DataFrame)
    assert isinstance(weekly_data, pd.DataFrame)
    assert len(daily_data) > 0
    assert len(weekly_data) > 0

def test_validate_data(data_manager):
    # Create sample valid data
    dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
    valid_daily = pd.DataFrame({
        'open': 100,
        'high': 101,
        'low': 99,
        'close': 100,
        'volume': 1000
    }, index=dates)

    dates_weekly = pd.date_range(start='2024-01-01', periods=5, freq='W')
    valid_weekly = pd.DataFrame({
        'open': 100,
        'high': 101,
        'low': 99,
        'close': 100,
        'volume': 1000
    }, index=dates_weekly)

    assert data_manager.validate_data(valid_daily, valid_weekly) is True

    # Test with insufficient data
    insufficient_daily = valid_daily.iloc[:10]
    assert data_manager.validate_data(insufficient_daily, valid_weekly) is False

    # Test with missing values
    invalid_daily = valid_daily.copy()
    invalid_daily.loc[dates[0], 'close'] = None
    assert data_manager.validate_data(invalid_daily, valid_weekly) is False
