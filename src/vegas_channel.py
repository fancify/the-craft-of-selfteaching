import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
from .position_manager import PositionManager

class VegasChannel:
    """
    Vegas Channel strategy implementation using EMA144 and EMA169 as channel boundaries.
    """

    def __init__(self, total_margin: float = 100000, max_coins: int = 50):
        self.ema_short = 144  # Lower band EMA period
        self.ema_long = 169   # Upper band EMA period
        self.position_manager = PositionManager(total_margin, max_coins)

    def calculate_ema(self, data: pd.Series, periods: int) -> pd.Series:
        """Calculate Exponential Moving Average for given periods"""
        multiplier = 2 / (periods + 1)
        ema = data.ewm(span=periods, adjust=False).mean()
        return ema

    def calculate_bands(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate Vegas Channel bands using EMA144 and EMA169"""
        df = data.copy()

        # Calculate EMAs
        df['vegas_lower'] = self.calculate_ema(df['close'], self.ema_short)  # EMA144
        df['vegas_upper'] = self.calculate_ema(df['close'], self.ema_long)   # EMA169

        return df

    def get_signals(self, daily_data: pd.DataFrame, weekly_data: pd.DataFrame) -> pd.DataFrame:
        """Generate trading signals based on dual timeframe EMA channel"""
        daily = self.calculate_bands(daily_data)
        weekly = self.calculate_bands(weekly_data)

        signals = pd.DataFrame(index=daily.index)
        signals['position'] = 0

        position = 0
        for i in range(len(daily)):
            current_daily = daily.iloc[i]
            current_date = daily.index[i]

            # Find the most recent weekly data point
            weekly_mask = weekly.index <= current_date
            if not weekly_mask.any():
                continue
            current_weekly = weekly[weekly_mask].iloc[-1]

            # Position management logic
            if position == 1:  # Long position
                # Exit long if daily close below EMA144 (vegas_lower)
                if current_daily['close'] < current_daily['vegas_lower']:
                    position = 0
                signals.iloc[i, signals.columns.get_loc('position')] = position

            elif position == -1:  # Short position
                # Exit short if daily close above EMA169 (vegas_upper)
                if current_daily['close'] > current_daily['vegas_upper']:
                    position = 0
                signals.iloc[i, signals.columns.get_loc('position')] = position

            else:  # No position
                # Long entry: both weekly and daily close above EMA169 (vegas_upper)
                if (current_weekly['close'] > current_weekly['vegas_upper'] and
                    current_daily['close'] > current_daily['vegas_upper']):
                    position = 1
                # Short entry: both weekly and daily close below EMA144 (vegas_lower)
                elif (current_weekly['close'] < current_weekly['vegas_lower'] and
                      current_daily['close'] < current_daily['vegas_lower']):
                    position = -1
                signals.iloc[i, signals.columns.get_loc('position')] = position

        return signals

    def backtest(self, daily_data: pd.DataFrame, weekly_data: pd.DataFrame) -> pd.DataFrame:
        """Run backtest using the Vegas Channel strategy with real Binance futures data"""
        # Ensure data has required columns
        required_columns = ['open', 'high', 'low', 'close']
        if not all(col in daily_data.columns for col in required_columns):
            raise ValueError(f"Daily data missing required columns: {required_columns}")
        if not all(col in weekly_data.columns for col in required_columns):
            raise ValueError(f"Weekly data missing required columns: {required_columns}")

        # Generate trading signals
        signals = self.get_signals(daily_data, weekly_data)

        # Calculate returns and positions
        results = pd.DataFrame(index=daily_data.index)
        results['position'] = signals['position']

        # Calculate position sizes (1/50 of margin per coin)
        position_sizes = []
        for i, pos in enumerate(signals['position']):
            if pos != 0:
                # Calculate position size based on closing price
                close_price = daily_data['close'].iloc[i]
                size = self.position_manager.margin_per_coin / close_price
                position_sizes.append(size if pos == 1 else -size)
            else:
                position_sizes.append(0)
        results['position_size'] = position_sizes

        # Calculate strategy returns
        daily_returns = daily_data['close'].pct_change()
        strategy_returns = results['position'].shift(1) * daily_returns
        results['strategy_returns'] = strategy_returns

        # Handle cumulative returns calculation
        results['cumulative_returns'] = 1.0  # Initialize with 1.0
        mask = ~strategy_returns.isna()  # Create mask for non-NaN values
        results.loc[mask, 'cumulative_returns'] = (1 + strategy_returns[mask]).cumprod()

        # Add price data for analysis
        results['close'] = daily_data['close']
        results['vegas_lower'] = self.calculate_ema(daily_data['close'], self.ema_short)
        results['vegas_upper'] = self.calculate_ema(daily_data['close'], self.ema_long)

        return results
