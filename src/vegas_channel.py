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
            weekly_mask = weekly.index <= daily.index[i]
            if not weekly_mask.any():
                continue

            current_weekly = weekly[weekly_mask].iloc[-1]

            # Position management logic
            if position == 0:  # No position
                # Long entry: both weekly and daily close above EMA169
                if (current_weekly['close'] > current_weekly['vegas_upper'] and
                    current_daily['close'] > current_daily['vegas_upper']):
                    signals.iloc[i, signals.columns.get_loc('position')] = 1
                    position = 1
                # Short entry: both weekly and daily close below EMA144
                elif (current_weekly['close'] < current_weekly['vegas_lower'] and
                      current_daily['close'] < current_daily['vegas_lower']):
                    signals.iloc[i, signals.columns.get_loc('position')] = -1
                    position = -1

            elif position == 1:  # Long position
                # Exit long if daily close below EMA144
                if current_daily['close'] < current_daily['vegas_lower']:
                    signals.iloc[i, signals.columns.get_loc('position')] = 0
                    position = 0
                else:
                    signals.iloc[i, signals.columns.get_loc('position')] = 1

            elif position == -1:  # Short position
                # Exit short if daily close above EMA169
                if current_daily['close'] > current_daily['vegas_upper']:
                    signals.iloc[i, signals.columns.get_loc('position')] = 0
                    position = 0
                else:
                    signals.iloc[i, signals.columns.get_loc('position')] = -1

        return signals
