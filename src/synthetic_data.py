import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SyntheticDataGenerator:
    """Generates synthetic market data for testing"""

    def __init__(self, volatility: float = 0.02, trend: float = 0.0001):
        """Initialize the synthetic data generator"""
        self.volatility = volatility
        self.trend = trend
        self.default_symbols = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'DOGEUSDT'
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

    def generate_ohlcv(self, symbol: str, start_date: datetime, days: int) -> pd.DataFrame:
        """Generate OHLCV data for a symbol"""
        # Set initial price and volatility based on symbol
        if 'BTC' in symbol:
            initial_price = 40000
            volatility = self.volatility
        elif 'ETH' in symbol:
            initial_price = 2200
            volatility = self.volatility * 1.25
        else:
            initial_price = np.random.uniform(1, 100)
            volatility = self.volatility * np.random.uniform(1.0, 2.0)

        # Generate daily timestamps
        dates = pd.date_range(start=start_date, periods=days, freq='D')

        # Generate close prices
        returns = np.random.normal(loc=self.trend, scale=volatility, size=days)
        # Add some cyclical patterns
        trend = np.sin(np.linspace(0, 4*np.pi, days)) * volatility
        returns = returns + trend

        # Calculate price series
        closes = initial_price * np.exp(np.cumsum(returns))

        # Generate other OHLCV data
        data = []
        for i in range(days):
            close = closes[i]
            high = close * (1 + abs(np.random.normal(0, volatility/2)))
            low = close * (1 - abs(np.random.normal(0, volatility/2)))
            open_price = close * (1 + np.random.normal(0, volatility/2))
            volume = np.random.uniform(1000, 10000) * close

            data.append([dates[i], open_price, high, low, close, volume])

        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df.set_index('timestamp', inplace=True)
        return df

    def generate_market_data(self, symbols: list = None, start_date: datetime = None,
                           end_date: datetime = None) -> dict:
        """Generate market data for all symbols"""
        symbols = symbols or self.default_symbols
        start_date = start_date or (datetime.now() - timedelta(days=30))
        end_date = end_date or datetime.now()

        days = (end_date - start_date).days
        market_data = {}

        for symbol in symbols:
            # Generate daily data with enough history for EMA calculation
            historical_start = start_date - timedelta(days=200)  # For EMA169
            total_days = (end_date - historical_start).days

            # Generate daily data
            daily_df = self.generate_ohlcv(symbol, historical_start, total_days)

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
