import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from src.metrics import MetricsCollector

@pytest.fixture
def mock_influx_client():
    return Mock()

@pytest.fixture
def metrics_collector(mock_influx_client):
    with patch('src.metrics.InfluxDBClient', return_value=mock_influx_client):
        collector = MetricsCollector()
        mock_influx_client.get_list_database.return_value = [{'name': 'vegas_strategy'}]
        return collector

def test_record_position(metrics_collector, mock_influx_client):
    success = metrics_collector.record_position(
        symbol="BTCUSDT",
        position=1.0,
        entry_price=50000.0
    )

    assert success is True
    mock_influx_client.write_points.assert_called_once()
    point = mock_influx_client.write_points.call_args[0][0][0]
    assert point['measurement'] == 'positions'
    assert point['tags']['symbol'] == 'BTCUSDT'
    assert point['fields']['position'] == 1.0
    assert point['fields']['entry_price'] == 50000.0

def test_record_account_metrics(metrics_collector, mock_influx_client):
    account_data = {
        'totalWalletBalance': '1000.0',
        'totalUnrealizedProfit': '100.0',
        'totalMarginBalance': '1100.0'
    }

    success = metrics_collector.record_account_metrics(account_data)

    assert success is True
    mock_influx_client.write_points.assert_called_once()
    point = mock_influx_client.write_points.call_args[0][0][0]
    assert point['measurement'] == 'account'
    assert point['fields']['total_balance'] == 1000.0
    assert point['fields']['unrealized_pnl'] == 100.0
    assert point['fields']['margin_balance'] == 1100.0

def test_record_trade(metrics_collector, mock_influx_client):
    success = metrics_collector.record_trade(
        symbol="BTCUSDT",
        side="BUY",
        quantity=1.0,
        price=50000.0
    )

    assert success is True
    mock_influx_client.write_points.assert_called_once()
    point = mock_influx_client.write_points.call_args[0][0][0]
    assert point['measurement'] == 'trades'
    assert point['tags']['symbol'] == 'BTCUSDT'
    assert point['tags']['side'] == 'BUY'
    assert point['fields']['quantity'] == 1.0
    assert point['fields']['price'] == 50000.0

def test_get_current_positions(metrics_collector, mock_influx_client):
    mock_result = Mock()
    mock_result.items.return_value = [
        ((None, {'symbol': 'BTCUSDT'}), iter([{
            'last_position': 1.0,
            'last_entry_price': 50000.0
        }]))
    ]
    mock_influx_client.query.return_value = mock_result

    positions = metrics_collector.get_current_positions()

    assert 'BTCUSDT' in positions
    assert positions['BTCUSDT']['position'] == 1.0
    assert positions['BTCUSDT']['entry_price'] == 50000.0

def test_record_position_with_error(metrics_collector, mock_influx_client):
    mock_influx_client.write_points.side_effect = Exception("Test error")

    success = metrics_collector.record_position(
        symbol="BTCUSDT",
        position=1.0,
        entry_price=50000.0
    )

    assert success is False
