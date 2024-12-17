import pandas as pd
from binance.client import Client
from typing import Tuple, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataManager:
    """Manages data fetching and processing for the Vegas Channel strategy."""

    def __init__(self, client: Client):
        """Initialize DataManager with Binance client.

        Args:
            client: Authenticated Binance Client instance
        """
        self.client = client
        self.required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']

    def get_klines(self, symbol: str, interval: str, limit: int = 500) -> Optional[pd.DataFrame]:
        """Fetch kline data from Binance futures API.

        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            interval: Kline interval ('1d' for daily, '1w' for weekly)
            limit: Number of klines to fetch

        Returns:
            DataFrame with OHLCV data or None if fetch fails
        """
        try:
            klines = self.client.futures_klines(
                symbol=symbol,
                interval=interval,
                limit=limit
            )

            df = pd.DataFrame(
                klines,
                columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'quote_volume', 'trades', 'taker_buy_volume',
                    'taker_buy_quote_volume', 'ignore'
                ]
            )

            # Convert string values to float for price and volume
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            # Convert timestamp to datetime and set as index
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)

            # Keep only required columns
            df = df[self.required_columns]

            return df

        except Exception as e:
            logger.error(f"Error fetching klines for {symbol} {interval}: {str(e)}")
            return None

    def get_synchronized_data(self, symbol: str, daily_limit: int = 500, weekly_limit: int = 200) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
        """Get synchronized daily and weekly data for a symbol.

        Args:
            symbol: Trading pair symbol
            daily_limit: Number of daily candles to fetch
            weekly_limit: Number of weekly candles to fetch

        Returns:
            Tuple of (daily_data, weekly_data) DataFrames
        """
        daily_data = self.get_klines(symbol, '1d', daily_limit)
        weekly_data = self.get_klines(symbol, '1w', weekly_limit)

        if daily_data is None or weekly_data is None:
            logger.error(f"Failed to fetch data for {symbol}")
            return None, None

        # Ensure data alignment
        start_date = max(daily_data.index.min(), weekly_data.index.min())
        end_date = min(daily_data.index.max(), weekly_data.index.max())

        daily_data = daily_data[start_date:end_date]
        weekly_data = weekly_data[start_date:end_date]

        return daily_data, weekly_data

    def validate_data(self, daily_data: pd.DataFrame, weekly_data: pd.DataFrame) -> bool:
        """Validate that the data meets strategy requirements.

        Args:
            daily_data: Daily OHLCV DataFrame
            weekly_data: Weekly OHLCV DataFrame

        Returns:
            bool: True if data is valid
        """
        if daily_data is None or weekly_data is None:
            return False

        # Check for minimum required data points
        if len(daily_data) < 20 or len(weekly_data) < 4:
            logger.warning("Insufficient data points for strategy calculation")
            return False

        # Check for missing values
        if daily_data.isnull().any().any() or weekly_data.isnull().any().any():
            logger.warning("Data contains missing values")
            return False

        return True
