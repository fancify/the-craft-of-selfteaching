from typing import Dict, List
from binance.client import Client
from binance.enums import *
import pandas as pd
from dotenv import load_dotenv
import os

class BinanceTrader:
    """Handles Binance futures trading operations"""

    def __init__(self):
        load_dotenv('../config/config.env')
        self.client = Client(
            os.getenv('BINANCE_API_KEY'),
            os.getenv('BINANCE_API_SECRET')
        )
        self.max_positions = int(os.getenv('MAX_POSITIONS', 50))

    def get_tradeable_contracts(self) -> List[str]:
        """Get list of tradeable futures contracts"""
        exchange_info = self.client.futures_exchange_info()
        return [symbol['symbol'] for symbol in exchange_info['symbols']
                if symbol['status'] == 'TRADING']

    def get_position_size(self, symbol: str) -> float:
        """Calculate position size based on account balance"""
        account = self.client.futures_account()
        total_balance = float(account['totalWalletBalance'])
        return total_balance / self.max_positions
