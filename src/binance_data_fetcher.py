import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from pathlib import Path
import pandas as pd
import requests

logger = logging.getLogger(__name__)

class BinanceDataFetcher:
    """Class to fetch market data from Binance API"""

    BASE_URL = "https://fapi.binance.com/fapi/v1"
    KLINES_ENDPOINT = "klines"  # Using futures klines endpoint
    INTERVALS = {
        'daily': '1d',
        'weekly': '1w'
    }

    def __init__(self, data_dir: str = "data/market_data"):
        """Initialize the data fetcher"""
        self.headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json',
            'X-MBX-APIKEY': 'P66OGjwThOb5eDdlkhPLROhZ2dRo52mpjLaTRfut2LE3s5Kmf3CBJ6t7HKVFzwLD'
        }
        self.rate_limit_wait = 1  # seconds between requests
        self.data_dir = Path(data_dir)
        self.default_pairs = ["BTCUSDT"]  # Start with just BTCUSDT for testing

    def _make_request(self, url: str, params: Dict[str, Any] = None) -> Dict:
        """Make a request to the Binance API with proper error handling"""
        try:
            response = requests.get(url, params=params, headers=self.headers)
            if response.status_code == 451:
                logger.warning("Region restriction detected. You may need to use a VPN or different endpoint.")
                return {'error': 'region_restricted'}
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request error: {e}")
            return {'error': str(e)}

    def download_and_process_data(self, symbol: str, interval: str,
                                start_ts: int, end_ts: int) -> Optional[pd.DataFrame]:
        """Download and process market data for a symbol and interval"""
        url = f"{self.BASE_URL}/{self.KLINES_ENDPOINT}"
        params = {
            'symbol': symbol,
            'interval': interval,
            'startTime': start_ts,
            'endTime': end_ts,
            'limit': 1000
        }

        response_data = self._make_request(url, params)
        if response_data.get('error') == 'region_restricted':
            logger.warning(f"Region restricted for {symbol} {interval}")
            return None
        elif 'error' in response_data:
            logger.error(f"Error fetching data for {symbol} {interval}: {response_data['error']}")
            return None

        try:
            df = pd.DataFrame(response_data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_volume',
                'taker_buy_quote_volume', 'ignore'
            ])

            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)

            # Convert numeric columns
            numeric_columns = ['open', 'high', 'low', 'close', 'volume']
            df[numeric_columns] = df[numeric_columns].astype(float)

            return df

        except Exception as e:
            logger.error(f"Error processing data for {symbol} {interval}: {str(e)}")
            return None

    def save_data(self, df: pd.DataFrame, symbol: str, timeframe: str) -> bool:
        """Save market data to CSV file"""
        try:
            save_dir = self.data_dir / timeframe
            save_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d")
            filename = f"{symbol}_{timeframe}_{timestamp}.csv"
            filepath = save_dir / filename

            df.to_csv(filepath)
            logger.info(f"Saved {symbol} {timeframe} data to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error saving data for {symbol}: {str(e)}")
            return False

    def fetch_market_data(self, start_date: datetime = None, end_date: datetime = None) -> Dict[str, Dict[str, pd.DataFrame]]:
        """
        Fetch historical market data for the specified date range
        Returns a dictionary with format: {symbol: {'daily': df_daily, 'weekly': df_weekly}}
        """
        if start_date is None or end_date is None:
            # Calculate date range to ensure enough historical data for EMA calculations
            end_date = datetime(2024, 3, 1)  # Reference date
            # Get 200 days of historical data to ensure enough for EMA169
            start_date = end_date - timedelta(days=200)

        start_ts = int(start_date.timestamp() * 1000)
        end_ts = int((end_date + timedelta(days=1)).timestamp() * 1000)

        market_data = {}
        for symbol in self.default_pairs:
            market_data[symbol] = {}

            # Fetch daily and weekly data
            for timeframe, interval in self.INTERVALS.items():
                logger.info(f"Fetching {timeframe} data for {symbol}")
                df = self.download_and_process_data(symbol, interval, start_ts, end_ts)
                if df is not None:
                    market_data[symbol][timeframe] = df
                    self.save_data(df, symbol, timeframe)
                else:
                    logger.error(f"Failed to fetch {timeframe} data for {symbol}")
                    return None

        return market_data

        return market_data
