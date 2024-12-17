import unittest
import pandas as pd
import numpy as np
from src.vegas_channel import VegasChannel

class TestVegasChannel(unittest.TestCase):
    def setUp(self):
        self.vegas = VegasChannel()
        self.test_data = pd.DataFrame({
            'close': np.random.random(100) * 1000
        })

    def test_calculate(self):
        result = self.vegas.calculate(self.test_data)
        self.assertIsInstance(result, pd.DataFrame)

    def test_get_signals(self):
        signals = self.vegas.get_signals(self.test_data)
        self.assertIsInstance(signals, pd.DataFrame)

if __name__ == '__main__':
    unittest.main()
