import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
import requests
import time
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CryptoDataFetcher:
    """Fetches market data from CryptoCompare"""

    def __init__(self):
        self.base_url = "https://min-api.cryptocompare.com/data"
        self.rate_limit_wait = 0.25  # 250ms between requests

    def _handle_rate_limit(self):
        """Simple rate limiting"""
        time.sleep(self.rate_limit_wait)

    def get_top_symbols(self, limit: int = 50) -> List[str]:
        """Get list of top trading pairs by volume"""
        try:
            response = requests.get(f"{self.base_url}/top/totalvolfull",
                                  params={'limit': limit, 'tsym': 'USDT'})
            if response.status_code != 200:
                logger.error(f"Error fetching symbols: {response.text}")
                return []

            data = response.json()
            if not data.get('Data'):
                return []

            symbols = [f"{coin['CoinInfo']['Name']}USDT"
                      for coin in data['Data']
                      if coin.get('CoinInfo', {}).get('Name')]
            return symbols[:limit]

        except Exception as e:
            logger.error(f"Error fetching symbols: {e}")
            return []

    def fetch_historical_data(self, symbol: str, timeframe: str,
                            days: int = 30) -> Optional[pd.DataFrame]:
        """
        Fetch historical data for a symbol
        timeframe: 'day' or 'hour' for daily/hourly data
        """
        try:
            # Remove USDT suffix for CryptoCompare API
            base_symbol = symbol.replace('USDT', '')

            endpoint = 'histoday' if timeframe == 'day' else 'histohour'
            limit = days if timeframe == 'day' else days * 24

            params = {
                'fsym': base_symbol,
                'tsym': 'USDT',
                'limit': limit,
                'e': 'binance'  # Prefer Binance as data source
            }

            response = requests.get(f"{self.base_url}/v2/{endpoint}", params=params)
            if response.status_code != 200:
                logger.error(f"Error fetching data for {symbol}: {response.text}")
                return None

            data = response.json()
            if not data.get('Data', {}).get('Data'):
                return None

            df = pd.DataFrame(data['Data']['Data'])
            df['timestamp'] = pd.to_datetime(df['time'], unit='s')
            df.set_index('timestamp', inplace=True)
            df = df.rename(columns={
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volumefrom': 'volume'
            })

            return df[['open', 'high', 'low', 'close', 'volume']]

        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return None

    def fetch_recent_data(self, symbols: Optional[List[str]] = None,
                         lookback_days: int = 30) -> Dict[str, Dict[str, pd.DataFrame]]:
        """
        Fetch both daily and hourly data for weekly aggregation
        Returns: {symbol: {'daily': df_daily, 'weekly': df_weekly}}
        """
        if symbols is None:
            symbols = self.get_top_symbols()

        data = {}
        for symbol in symbols:
            # Fetch daily data
            daily_df = self.fetch_historical_data(symbol, 'day', lookback_days)
            self._handle_rate_limit()

            # Fetch hourly data and resample to weekly
            hourly_df = self.fetch_historical_data(symbol, 'hour', lookback_days)
            self._handle_rate_limit()

            if daily_df is not None and hourly_df is not None:
                # Resample hourly data to weekly
                weekly_df = hourly_df.resample('W').agg({
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum'
                })

                data[symbol] = {
                    'daily': daily_df,
                    'weekly': weekly_df
                }
                logger.info(f"Fetched data for {symbol}")

        return data
