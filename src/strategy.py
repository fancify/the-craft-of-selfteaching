import pandas as pd
import numpy as np
from typing import Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VegasChannelStrategy:
    """
    Implementation of Vegas Channel trading strategy using EMA144 and EMA169
    """
    def __init__(self):
        self.ema_short = 144  # EMA144 (lower band)
        self.ema_long = 169   # EMA169 (upper band)
        self.positions = {}   # Current positions for each symbol
        self.max_positions = 50  # Maximum number of concurrent positions

    def calculate_ema_bands(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate EMA bands for the Vegas Channel"""
        df = df.copy()
        # Calculate EMAs with min_periods to ensure we get values from the start
        df['ema_lower'] = df['close'].ewm(span=self.ema_short, adjust=False, min_periods=1).mean()
        df['ema_upper'] = df['close'].ewm(span=self.ema_long, adjust=False, min_periods=1).mean()
        return df

    def get_position_signals(self, symbol: str, daily_data: pd.DataFrame,
                           weekly_data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals based on Vegas Channel strategy
        Returns DataFrame with 'position' column (1: long, -1: short, 0: no position)
        """
        # Calculate EMAs for both timeframes
        daily = self.calculate_ema_bands(daily_data)
        weekly = self.calculate_ema_bands(weekly_data)

        # Initialize signals DataFrame
        signals = pd.DataFrame(index=daily.index)
        signals['position'] = 0
        current_position = self.positions.get(symbol, 0)

        # Generate signals
        for i in range(len(daily)):
            current_daily = daily.iloc[i]
            current_date = daily.index[i]

            # Find the most recent weekly data point
            weekly_mask = weekly.index <= current_date
            if not weekly_mask.any():
                continue
            current_weekly = weekly[weekly_mask].iloc[-1]

            # Exit conditions (check first)
            if current_position == 1:  # Long position
                if current_daily['close'] < current_daily['ema_lower']:
                    signals.loc[current_date, 'position'] = 0
                    current_position = 0
                    logger.info(f"{symbol}: Exiting long position at {current_date}")
                else:
                    signals.loc[current_date, 'position'] = 1

            elif current_position == -1:  # Short position
                if current_daily['close'] > current_daily['ema_upper']:
                    signals.loc[current_date, 'position'] = 0
                    current_position = 0
                    logger.info(f"{symbol}: Exiting short position at {current_date}")
                else:
                    signals.loc[current_date, 'position'] = -1

            # Entry conditions (only if no position)
            elif current_position == 0:
                if (current_weekly['close'] > current_weekly['ema_upper'] and
                    current_daily['close'] > current_daily['ema_upper']):
                    signals.loc[current_date, 'position'] = 1
                    current_position = 1
                elif (current_weekly['close'] < current_weekly['ema_lower'] and
                      current_daily['close'] < current_daily['ema_lower']):
                    signals.loc[current_date, 'position'] = -1
                    current_position = -1

        # Update current position
        self.positions[symbol] = current_position
        return signals

    def simulate_trading(self, market_data: Dict[str, Dict[str, pd.DataFrame]]) -> Dict[str, pd.DataFrame]:
        """
        Simulate trading for all symbols
        Returns dict of DataFrames with positions and performance metrics
        """
        results = {}
        active_positions = 0

        # Sort symbols by potential (using last day's returns as a simple metric)
        symbol_metrics = []
        for symbol, timeframes in market_data.items():
            daily_returns = timeframes['daily']['close'].pct_change()
            symbol_metrics.append((symbol, daily_returns.iloc[-1]))

        # Sort by absolute returns to prioritize strongest moves
        symbol_metrics.sort(key=lambda x: abs(x[1]), reverse=True)

        # Process symbols in order of priority
        for symbol, _ in symbol_metrics:
            timeframes = market_data[symbol]
            daily_data = timeframes['daily']
            weekly_data = timeframes['weekly']

            # Skip if we've reached maximum positions
            if active_positions >= self.max_positions:
                signals = pd.DataFrame(index=daily_data.index)
                signals['position'] = 0
                results[symbol] = pd.DataFrame({
                    'close': daily_data['close'],
                    'position': signals['position'],
                    'daily_returns': daily_data['close'].pct_change(),
                    'strategy_returns': 0,
                    'cumulative_returns': 1
                })
                continue

            # Generate signals
            signals = self.get_position_signals(symbol, daily_data, weekly_data)

            # Calculate returns
            daily_returns = daily_data['close'].pct_change()
            strategy_returns = signals['position'].shift(1) * daily_returns

            # Create results DataFrame
            results[symbol] = pd.DataFrame({
                'close': daily_data['close'],
                'position': signals['position'],
                'daily_returns': daily_returns,
                'strategy_returns': strategy_returns,
                'cumulative_returns': (1 + strategy_returns).cumprod()
            })

            # Update active positions count if this symbol has a position
            if signals['position'].iloc[-1] != 0:
                active_positions += 1

            logger.info(f"Completed simulation for {symbol}")

        return results
