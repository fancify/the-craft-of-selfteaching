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
        df['ema_lower'] = df['close'].ewm(span=144, adjust=False, min_periods=1).mean()
        df['ema_upper'] = df['close'].ewm(span=169, adjust=False, min_periods=1).mean()
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

        # Initialize signals DataFrame with current position
        signals = pd.DataFrame(index=daily.index)
        current_position = self.positions.get(symbol, 0)
        signals['position'] = 0  # Initialize all positions to 0

        # Debug: Print initial state
        logger.info(f"\nInitial state for {symbol}:")
        logger.info(f"Initial position: {current_position}")
        logger.info(f"First close price: {daily['close'].iloc[0]:.2f}")
        logger.info(f"First EMA144: {daily['ema_lower'].iloc[0]:.2f}")
        logger.info(f"First EMA169: {daily['ema_upper'].iloc[0]:.2f}")

        # If we have an initial position, maintain it for first 14 days
        if current_position != 0:
            signals.loc[signals.index[:14], 'position'] = current_position

        # Process remaining days
        for i in range(14, len(daily)):
            current_daily = daily.iloc[i]
            current_date = daily.index[i]
            prev_position = signals.loc[signals.index[i-1], 'position']

            # Find the most recent weekly data point
            weekly_mask = weekly.index <= current_date
            if not weekly_mask.any():
                continue
            current_weekly = weekly[weekly_mask].iloc[-1]

            # Check exit conditions if we have a position
            if prev_position == 1:  # Long position
                if current_daily['close'] < current_daily['ema_lower']:
                    # Exit long position and maintain zero position
                    signals.loc[signals.index[i:], 'position'] = 0
                    break
                else:
                    signals.loc[current_date, 'position'] = 1

            elif prev_position == -1:  # Short position
                if current_daily['close'] > current_daily['ema_upper']:
                    # Exit short position and maintain zero position
                    signals.loc[signals.index[i:], 'position'] = 0
                    break
                else:
                    signals.loc[current_date, 'position'] = -1

            # Check entry conditions only if no position
            elif prev_position == 0:
                if (current_weekly['close'] > current_weekly['ema_upper'] and
                    current_daily['close'] > current_daily['ema_upper']):
                    # Enter long position
                    signals.loc[current_date, 'position'] = 1

                elif (current_weekly['close'] < current_weekly['ema_lower'] and
                      current_daily['close'] < current_daily['ema_lower']):
                    # Enter short position
                    signals.loc[current_date, 'position'] = -1

        # Debug: Print final positions
        logger.info(f"\nFinal positions for {symbol}:")
        logger.info(f"First position: {signals['position'].iloc[0]}")
        logger.info(f"Last position: {signals['position'].iloc[-1]}")
        logger.info(f"Position transitions: {signals['position'].diff()[signals['position'].diff() != 0]}")

        # Update current position
        self.positions[symbol] = signals['position'].iloc[-1]
        return signals

    def simulate_trading(self, market_data: dict) -> dict:
        """
        Simulate trading for all symbols in market_data
        Returns dict with results for each symbol
        """
        results = {}
        active_positions = sum(1 for pos in self.positions.values() if pos != 0)

        # Debug: Print initial positions
        logger.info(f"\nInitial positions before simulation: {self.positions}")

        # Sort symbols by volume for position allocation
        symbols = sorted(market_data.keys(),
                         key=lambda x: market_data[x]['daily']['volume'].mean(),
                         reverse=True)

        for symbol in symbols:
            # Get initial position for this symbol
            initial_position = self.positions.get(symbol, 0)

            # Skip if we've reached maximum positions and no initial position
            if active_positions >= self.max_positions and initial_position == 0:
                logger.info(f"Maximum positions ({self.max_positions}) reached. Skipping {symbol}")
                results[symbol] = {
                    'position': pd.Series(0, index=market_data[symbol]['daily'].index),
                    'position_value': 0,
                    'close': market_data[symbol]['daily']['close']
                }
                continue

            # Get trading signals
            signals = self.get_position_signals(symbol, market_data[symbol]['daily'],
                                                 market_data[symbol]['weekly'])

            # Calculate position value (equal weight for all positions)
            position_value = 1.0 / self.max_positions if (active_positions < self.max_positions or initial_position != 0) else 0

            # Store results
            results[symbol] = {
                'position': signals['position'],
                'position_value': signals['position'] * position_value,
                'close': market_data[symbol]['daily']['close']
            }

            # Update active positions count if we have a position
            if abs(signals['position'].iloc[-1]) > 0 and initial_position == 0:
                active_positions += 1

            # Debug: Print final positions for symbol
            logger.info(f"\nFinal positions for {symbol}:")
            logger.info(f"Initial position: {initial_position}")
            logger.info(f"First position: {signals['position'].iloc[0]}")
            logger.info(f"Last position: {signals['position'].iloc[-1]}")
            logger.info(f"Position value: {position_value}")

        return results
