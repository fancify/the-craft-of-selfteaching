import numpy as np
import pandas as pd

class VegasChannel:
    def __init__(self, daily_period=20, weekly_period=20, std_multiplier=2.0):
        self.daily_period = daily_period
        self.weekly_period = weekly_period
        self.std_multiplier = std_multiplier

    def calculate_bands(self, data: pd.DataFrame, period: int) -> pd.DataFrame:
        if 'close' not in data.columns:
            raise ValueError("DataFrame must contain 'close' column")

        df = data.copy()
        df['vegas_middle'] = df['close'].rolling(window=period).mean()
        df['std'] = df['close'].rolling(window=period).std()
        df['vegas_upper'] = df['vegas_middle'] + (df['std'] * self.std_multiplier)
        df['vegas_lower'] = df['vegas_middle'] - (df['std'] * self.std_multiplier)

        return df

    def get_signals(self, daily_data: pd.DataFrame, weekly_data: pd.DataFrame) -> pd.DataFrame:
        daily = self.calculate_bands(daily_data, self.daily_period)
        weekly = self.calculate_bands(weekly_data, self.weekly_period)

        signals = pd.DataFrame(index=daily.index)
        signals['position'] = 0

        position = 0
        for i in range(len(daily)):
            current_daily = daily.iloc[i]
            weekly_mask = weekly.index <= daily.index[i]
            if not weekly_mask.any():
                continue

            current_weekly = weekly[weekly_mask].iloc[-1]

            if position == 0:
                if (current_weekly['close'] > current_weekly['vegas_upper'] and
                    current_daily['close'] > current_daily['vegas_upper']):
                    signals.iloc[i, signals.columns.get_loc('position')] = 1
                    position = 1
                elif (current_weekly['close'] < current_weekly['vegas_lower'] and
                      current_daily['close'] < current_daily['vegas_lower']):
                    signals.iloc[i, signals.columns.get_loc('position')] = -1
                    position = -1
            elif position == 1:
                if current_daily['close'] < current_daily['vegas_lower']:
                    signals.iloc[i, signals.columns.get_loc('position')] = 0
                    position = 0
                else:
                    signals.iloc[i, signals.columns.get_loc('position')] = 1
            elif position == -1:
                if current_daily['close'] > current_daily['vegas_upper']:
                    signals.iloc[i, signals.columns.get_loc('position')] = 0
                    position = 0
                else:
                    signals.iloc[i, signals.columns.get_loc('position')] = -1

        return signals
