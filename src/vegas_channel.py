import numpy as np
import pandas as pd

class VegasChannel:
    def __init__(self):
        pass

    def calculate_bands(self, data: pd.DataFrame) -> pd.DataFrame:
        if 'close' not in data.columns:
            raise ValueError("DataFrame must contain 'close' column")

        df = data.copy()

        # Calculate EMAs
        df['ema_144'] = df['close'].ewm(span=144, adjust=False).mean()
        df['ema_169'] = df['close'].ewm(span=169, adjust=False).mean()

        # Set channel boundaries
        df['vegas_lower'] = df['ema_144']
        df['vegas_upper'] = df['ema_169']

        return df

    def get_signals(self, daily_data: pd.DataFrame, weekly_data: pd.DataFrame) -> pd.DataFrame:
        daily = self.calculate_bands(daily_data)
        weekly = self.calculate_bands(weekly_data)

        signals = pd.DataFrame(index=daily.index)
        signals['position'] = 0
        signals['daily_close'] = daily['close']
        signals['daily_upper'] = daily['vegas_upper']
        signals['daily_lower'] = daily['vegas_lower']
        signals['weekly_close'] = np.nan
        signals['weekly_upper'] = np.nan
        signals['weekly_lower'] = np.nan

        position = 0
        for i in range(len(daily)):
            current_daily = daily.iloc[i]
            weekly_mask = weekly.index <= daily.index[i]
            if not weekly_mask.any():
                continue

            current_weekly = weekly[weekly_mask].iloc[-1]

            signals.iloc[i, signals.columns.get_loc('weekly_close')] = current_weekly['close']
            signals.iloc[i, signals.columns.get_loc('weekly_upper')] = current_weekly['vegas_upper']
            signals.iloc[i, signals.columns.get_loc('weekly_lower')] = current_weekly['vegas_lower']

            if position == 0:  # No position
                if (current_weekly['close'] > current_weekly['vegas_upper'] and
                    current_daily['close'] > current_daily['vegas_upper']):
                    position = 1
                elif (current_weekly['close'] < current_weekly['vegas_lower'] and
                      current_daily['close'] < current_daily['vegas_lower']):
                    position = -1
            elif position == 1:  # Long position
                if current_daily['close'] < current_daily['vegas_lower']:
                    position = 0
            elif position == -1:  # Short position
                if current_daily['close'] > current_daily['vegas_upper']:
                    position = 0

            signals.iloc[i, signals.columns.get_loc('position')] = position

        return signals
