import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.strategy import VegasChannelStrategy

class TestVegasChannelStrategy(unittest.TestCase):
    def setUp(self):
        """Set up test data"""
        self.strategy = VegasChannelStrategy()

        # Generate test data
        self.dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
        self.weekly_dates = pd.date_range(start='2024-01-01', periods=5, freq='W')

        # Test case 1: Dual timeframe uptrend
        self.daily_uptrend = pd.DataFrame({
            'close': np.linspace(100, 150, 30),
            'volume': np.random.uniform(1000, 2000, 30)
        }, index=self.dates)

        self.weekly_uptrend = pd.DataFrame({
            'close': np.linspace(100, 150, 5),
            'volume': np.random.uniform(5000, 10000, 5)
        }, index=self.weekly_dates)

        # Test case 2: Dual timeframe downtrend
        self.daily_downtrend = pd.DataFrame({
            'close': np.linspace(150, 100, 30),
            'volume': np.random.uniform(1000, 2000, 30)
        }, index=self.dates)

        self.weekly_downtrend = pd.DataFrame({
            'close': np.linspace(150, 100, 5),
            'volume': np.random.uniform(5000, 10000, 5)
        }, index=self.weekly_dates)

    def test_ema_boundaries(self):
        """Test EMA144 and EMA169 as Vegas Channel boundaries"""
        daily = self.strategy.calculate_ema_bands(self.daily_uptrend)

        # Verify EMA periods
        ema_lower = self.daily_uptrend['close'].ewm(span=144, adjust=False).mean()
        ema_upper = self.daily_uptrend['close'].ewm(span=169, adjust=False).mean()

        pd.testing.assert_series_equal(daily['ema_lower'], ema_lower, check_names=False)
        pd.testing.assert_series_equal(daily['ema_upper'], ema_upper, check_names=False)

    def test_dual_timeframe_long_entry(self):
        """Test long entry requires both weekly and daily conditions"""
        # Create specific test case where only daily is above EMA169
        daily_data = pd.DataFrame({
            'close': np.array([170] * 30),
            'volume': np.random.uniform(1000, 2000, 30)
        }, index=self.dates)

        weekly_data = pd.DataFrame({
            'close': np.array([130] * 5),
            'volume': np.random.uniform(5000, 10000, 5)
        }, index=self.weekly_dates)

        market_data = {'TESTUSDT': {
            'daily': daily_data,
            'weekly': weekly_data
        }}

        results = self.strategy.simulate_trading(market_data)
        positions = results['TESTUSDT']['position']

        # Should not enter long position when only daily condition is met
        self.assertFalse((positions == 1).any())

    def test_dual_timeframe_short_entry(self):
        """Test short entry requires both weekly and daily conditions"""
        # Create specific test case where only daily is below EMA144
        daily_data = pd.DataFrame({
            'close': np.array([90] * 30),
            'volume': np.random.uniform(1000, 2000, 30)
        }, index=self.dates)

        weekly_data = pd.DataFrame({
            'close': np.array([130] * 5),
            'volume': np.random.uniform(5000, 10000, 5)
        }, index=self.weekly_dates)

        market_data = {'TESTUSDT': {
            'daily': daily_data,
            'weekly': weekly_data
        }}

        results = self.strategy.simulate_trading(market_data)
        positions = results['TESTUSDT']['position']

        # Should not enter short position when only daily condition is met
        self.assertFalse((positions == -1).any())

    def test_long_exit_condition(self):
        """Test long position exit when daily closes below EMA144"""
        # Create data with price crossing below EMA144
        prices = np.array([150] * 15 + [90] * 15)
        daily_data = pd.DataFrame({
            'close': prices,
            'volume': np.random.uniform(1000, 2000, 30)
        }, index=self.dates)

        weekly_data = pd.DataFrame({
            'close': [150, 150, 90, 90, 90],
            'volume': np.random.uniform(5000, 10000, 5)
        }, index=self.weekly_dates)

        # Initialize strategy with a long position
        self.strategy.positions = {'TESTUSDT': 1}  # Set initial long position

        market_data = {'TESTUSDT': {
            'daily': daily_data,
            'weekly': weekly_data
        }}

        results = self.strategy.simulate_trading(market_data)
        positions = results['TESTUSDT']['position']

        # Should exit long position when price drops below EMA144
        self.assertTrue((positions.iloc[15:] == 0).all())

    def test_short_exit_condition(self):
        """Test short position exit when daily closes above EMA169"""
        # Create data with price crossing above EMA169
        prices = np.array([90] * 15 + [170] * 15)
        daily_data = pd.DataFrame({
            'close': prices,
            'volume': np.random.uniform(1000, 2000, 30)
        }, index=self.dates)

        weekly_data = pd.DataFrame({
            'close': [90, 90, 170, 170, 170],
            'volume': np.random.uniform(5000, 10000, 5)
        }, index=self.weekly_dates)

        # Initialize strategy with a short position
        self.strategy.positions = {'TESTUSDT': -1}  # Set initial short position

        market_data = {'TESTUSDT': {
            'daily': daily_data,
            'weekly': weekly_data
        }}

        results = self.strategy.simulate_trading(market_data)
        positions = results['TESTUSDT']['position']

        # Should exit short position when price rises above EMA169
        self.assertTrue((positions.iloc[15:] == 0).all())

    def test_position_sizing(self):
        """Test position sizing rules"""
        # Create test data for multiple symbols
        symbols = [f'TEST{i}USDT' for i in range(60)]
        market_data = {}

        for symbol in symbols:
            market_data[symbol] = {
                'daily': self.daily_uptrend.copy(),
                'weekly': self.weekly_uptrend.copy()
            }

        # Run simulation
        results = self.strategy.simulate_trading(market_data)

        # Check number of active positions
        active_positions = sum(1 for symbol in results
                             if results[symbol]['position'].iloc[-1] != 0)
        self.assertLessEqual(active_positions, 50)

        # Check position sizes
        for symbol in results:
            positions = results[symbol]['position']
            self.assertTrue(positions.isin([-1, 0, 1]).all())

if __name__ == '__main__':
    unittest.main()
