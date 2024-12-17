import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SyntheticDataGenerator:
    """Generates synthetic market data for testing"""

    def __init__(self, start_date: datetime = None, days: int = 30):
        self.start_date = start_date or (datetime.now() - timedelta(days=days))
        self.days = days
        self.symbols = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'DOGEUSDT',
            'XRPUSDT', 'DOTUSDT', 'UNIUSDT', 'LINKUSDT', 'SOLUSDT'
        ]

    def generate_price_series(self, initial_price: float, volatility: float) -> pd.Series:
        """Generate a realistic price series using GBM"""
        # Daily returns
        returns = np.random.normal(loc=0.0001, scale=volatility, size=self.days)
        # Ensure some trend in the data
        trend = np.linspace(-0.001, 0.001, self.days)
        returns = returns + trend

        # Calculate price series
        price_series = initial_price * np.exp(np.cumsum(returns))
        return price_series

    def generate_ohlcv(self, symbol: str) -> pd.DataFrame:
        """Generate OHLCV data for a symbol"""
        # Set initial price and volatility based on symbol
        if 'BTC' in symbol:
            initial_price = 40000
            volatility = 0.02
        elif 'ETH' in symbol:
            initial_price = 2200
            volatility = 0.025
        else:
            initial_price = np.random.uniform(1, 100)
            volatility = np.random.uniform(0.02, 0.04)

        # Generate daily timestamps
        dates = pd.date_range(start=self.start_date, periods=self.days, freq='D')

        # Generate close prices
        closes = self.generate_price_series(initial_price, volatility)

        # Generate other OHLCV data
        data = []
        for i in range(self.days):
            close = closes[i]
            high = close * (1 + abs(np.random.normal(0, volatility/2)))
            low = close * (1 - abs(np.random.normal(0, volatility/2)))
            open_price = close * (1 + np.random.normal(0, volatility/2))
            volume = np.random.uniform(1000, 10000) * close

            data.append([dates[i], open_price, high, low, close, volume])

        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df.set_index('timestamp', inplace=True)
        return df

    def generate_market_data(self) -> dict:
        """Generate market data for all symbols"""
        market_data = {}

        for symbol in self.symbols:
            # Generate daily data
            daily_df = self.generate_ohlcv(symbol)

            # Resample to weekly
            weekly_df = daily_df.resample('W').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            })

            market_data[symbol] = {
                'daily': daily_df,
                'weekly': weekly_df
            }
            logger.info(f"Generated data for {symbol}")

        return market_data
