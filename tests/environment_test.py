import unittest

class TestEnvironment(unittest.TestCase):
    def test_imports(self):
        """Test that all required packages and modules are importable"""
        try:
            from src.vegas_channel import VegasChannel
            from src.binance_trader import BinanceTrader
            import pandas as pd
            import numpy as np
            self.assertTrue(True, "All imports successful")
        except ImportError as e:
            self.fail(f"Import failed: {str(e)}")

if __name__ == '__main__':
    unittest.main()
