from typing import Dict, List, Optional
import pandas as pd

class PositionManager:
    """
    Manages position sizing and leverage controls for the Vegas Channel strategy.
    """

    def __init__(self, total_margin: float, max_coins: int = 50):
        """
        Initialize position manager

        Args:
            total_margin: Total margin available for trading
            max_coins: Maximum number of coins to trade (default: 50)
        """
        self.total_margin = total_margin
        self.max_coins = max_coins
        self.margin_per_coin = total_margin / max_coins
        self.positions: Dict[str, Dict] = {}  # Current positions by symbol

    def can_open_position(self, symbol: str) -> bool:
        """Check if we can open a new position"""
        return (len(self.positions) < self.max_coins and
                symbol not in self.positions)

    def calculate_position_size(self, symbol: str, current_price: float) -> Optional[float]:
        """
        Calculate position size for a new trade
        No leverage - position size is exactly margin_per_coin / price
        """
        if not self.can_open_position(symbol):
            return None

        return self.margin_per_coin / current_price

    def open_position(self, symbol: str, price: float, size: float,
                     position_type: str) -> bool:
        """
        Open a new position

        Args:
            symbol: Trading pair symbol
            price: Entry price
            size: Position size
            position_type: 'long' or 'short'
        """
        if not self.can_open_position(symbol):
            return False

        self.positions[symbol] = {
            'entry_price': price,
            'size': size,
            'type': position_type,
            'margin': self.margin_per_coin
        }
        return True

    def close_position(self, symbol: str) -> bool:
        """Close an existing position"""
        if symbol not in self.positions:
            return False

        del self.positions[symbol]
        return True

    def get_position(self, symbol: str) -> Optional[Dict]:
        """Get current position details for a symbol"""
        return self.positions.get(symbol)

    def get_all_positions(self) -> Dict[str, Dict]:
        """Get all current positions"""
        return self.positions.copy()

    def calculate_position_value(self, symbol: str,
                               current_price: float) -> Optional[float]:
        """Calculate current value of a position"""
        position = self.get_position(symbol)
        if not position:
            return None

        return position['size'] * current_price

    def calculate_unrealized_pnl(self, symbol: str,
                                current_price: float) -> Optional[float]:
        """Calculate unrealized PnL for a position"""
        position = self.get_position(symbol)
        if not position:
            return None

        if position['type'] == 'long':
            return (current_price - position['entry_price']) * position['size']
        else:  # short
            return (position['entry_price'] - current_price) * position['size']
