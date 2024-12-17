import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import pandas as pd
import requests

logger = logging.getLogger(__name__)

class BinanceDataFetcher:
    """Fetches market data from Binance API"""

    def __init__(self, data_dir: str = "data/market_data", use_testnet: bool = True):
        """Initialize the data fetcher"""
        self.base_url = "https://testnet.binancefuture.com" if use_testnet else "https://fapi.binance.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.data_dir = Path(data_dir)
        self.default_pairs = ["BTCUSDT"]
        self.max_retries = 3
        self.retry_delay = 1

    def _make_request(self, url: str, params: Dict[str, Any] = None) -> Optional[List]:
        """Make a request to the Binance API with retry logic"""
        for attempt in range(self.max_retries):
            try:
                response = requests.get(url, params=params, headers=self.headers, timeout=10)

                if response.status_code == 451:
                    logger.warning("Region restriction detected. Trying alternative endpoint...")
                    return None

                if response.status_code == 429:  # Rate limit
                    wait_time = int(response.headers.get('Retry-After', self.retry_delay))
                    logger.warning(f"Rate limit hit. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue

                response.raise_for_status()
                return response.json()

            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (attempt + 1)
                    logger.warning(f"Request failed. Retrying in {wait_time} seconds... Error: {e}")
                    time.sleep(wait_time)
                else:
                    logger.error(f"API request error after {self.max_retries} attempts: {e}")
                    return None

    def download_and_process_data(self, symbol: str, interval: str,
                                start_ts: int, end_ts: int) -> Optional[pd.DataFrame]:
        """Download and process market data for a symbol"""
        url = f"{self.base_url}/fapi/v1/klines"
        params = {
            'symbol': symbol,
            'interval': interval,
            'startTime': start_ts * 1000,  # Convert to milliseconds
            'endTime': end_ts * 1000,
            'limit': 1500  # Maximum allowed
        }

        response_data = self._make_request(url, params)
        if response_data is None:
            logger.error(f"Failed to fetch data for {symbol} {interval}")
            return None

        if not isinstance(response_data, list):
            logger.error(f"Unexpected response format for {symbol} {interval}")
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

            # Convert string values to float
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)

            return df

        except Exception as e:
            logger.error(f"Error processing data for {symbol} {interval}: {str(e)}")
            return None

    def save_data(self, df: pd.DataFrame, symbol: str, interval: str) -> bool:
        """Save market data to CSV file"""
        try:
            # Create directory if it doesn't exist
            save_dir = self.data_dir / interval
            save_dir.mkdir(parents=True, exist_ok=True)

            # Save to CSV
            filename = f"{symbol}_{interval}_{datetime.now().strftime('%Y%m%d')}.csv"
            filepath = save_dir / filename
            df.to_csv(filepath)
            logger.info(f"Saved {symbol} {interval} data to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error saving data for {symbol} {interval}: {str(e)}")
            return False

    def fetch_market_data(self, start_date: datetime, end_date: datetime,
                         symbols: List[str] = None) -> Dict[str, Dict[str, pd.DataFrame]]:
        """Fetch market data for specified symbols and time range"""
        if symbols is None:
            symbols = self.default_pairs

        market_data = {}
        start_ts = int(start_date.timestamp())
        end_ts = int(end_date.timestamp())

        for symbol in symbols:
            market_data[symbol] = {}

            # Try both testnet and mainnet endpoints
            endpoints = [True, False]  # [use_testnet, use_mainnet]

            for use_testnet in endpoints:
                self.base_url = "https://testnet.binancefuture.com" if use_testnet else "https://fapi.binance.com"
                logger.info(f"Trying {'testnet' if use_testnet else 'mainnet'} endpoint for {symbol}")

                # Fetch daily data
                daily_data = self.download_and_process_data(symbol, '1d', start_ts, end_ts)
                if daily_data is not None:
                    market_data[symbol]['daily'] = daily_data
                    self.save_data(daily_data, symbol, 'daily')

                    # Fetch weekly data only if daily data was successful
                    weekly_data = self.download_and_process_data(symbol, '1w', start_ts, end_ts)
                    if weekly_data is not None:
                        market_data[symbol]['weekly'] = weekly_data
                        self.save_data(weekly_data, symbol, 'weekly')
                        break  # Successfully got both daily and weekly data

                if 'daily' in market_data[symbol] and 'weekly' in market_data[symbol]:
                    break  # Skip trying other endpoints if we have all the data

            if 'daily' not in market_data[symbol] or 'weekly' not in market_data[symbol]:
                logger.error(f"Failed to fetch complete data for {symbol}")
                continue

        return market_data
