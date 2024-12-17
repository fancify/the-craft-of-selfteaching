from typing import Dict, Optional
from influxdb import InfluxDBClient
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MetricsCollector:
    """Collects and stores strategy metrics in InfluxDB."""

    def __init__(self, host: str = 'localhost', port: int = 8086,
                 database: str = 'vegas_strategy'):
        """Initialize InfluxDB client and ensure database exists.

        Args:
            host: InfluxDB host
            port: InfluxDB port
            database: Database name
        """
        try:
            self.client = InfluxDBClient(host=host, port=port)
            self._setup_database(database)
        except Exception as e:
            logger.error(f"Failed to initialize InfluxDB client: {str(e)}")
            raise

    def _setup_database(self, database: str) -> None:
        """Create database if it doesn't exist."""
        if database not in [db['name'] for db in self.client.get_list_database()]:
            self.client.create_database(database)
        self.client.switch_database(database)

    def record_position(self, symbol: str, position: float,
                       entry_price: float, timestamp: Optional[datetime] = None) -> bool:
        """Record position information.

        Args:
            symbol: Trading pair symbol
            position: Position size (positive for long, negative for short)
            entry_price: Entry price of the position
            timestamp: Optional timestamp (defaults to current time)

        Returns:
            bool: True if successful
        """
        try:
            point = {
                "measurement": "positions",
                "tags": {
                    "symbol": symbol
                },
                "time": timestamp or datetime.utcnow(),
                "fields": {
                    "position": float(position),
                    "entry_price": float(entry_price)
                }
            }
            self.client.write_points([point])
            return True
        except Exception as e:
            logger.error(f"Failed to record position: {str(e)}")
            return False

    def record_account_metrics(self, account_data: Dict) -> bool:
        """Record account metrics.

        Args:
            account_data: Dictionary containing account metrics
                Required keys:
                - totalWalletBalance: Total account balance
                - totalUnrealizedProfit: Unrealized PnL
                - totalMarginBalance: Margin balance

        Returns:
            bool: True if successful
        """
        try:
            point = {
                "measurement": "account",
                "time": datetime.utcnow(),
                "fields": {
                    "total_balance": float(account_data['totalWalletBalance']),
                    "unrealized_pnl": float(account_data['totalUnrealizedProfit']),
                    "margin_balance": float(account_data['totalMarginBalance'])
                }
            }
            self.client.write_points([point])
            return True
        except Exception as e:
            logger.error(f"Failed to record account metrics: {str(e)}")
            return False

    def record_trade(self, symbol: str, side: str, quantity: float,
                    price: float, timestamp: Optional[datetime] = None) -> bool:
        """Record trade execution details.

        Args:
            symbol: Trading pair symbol
            side: Trade side ('BUY' or 'SELL')
            quantity: Trade quantity
            price: Execution price
            timestamp: Optional timestamp (defaults to current time)

        Returns:
            bool: True if successful
        """
        try:
            point = {
                "measurement": "trades",
                "tags": {
                    "symbol": symbol,
                    "side": side
                },
                "time": timestamp or datetime.utcnow(),
                "fields": {
                    "quantity": float(quantity),
                    "price": float(price)
                }
            }
            self.client.write_points([point])
            return True
        except Exception as e:
            logger.error(f"Failed to record trade: {str(e)}")
            return False

    def get_current_positions(self) -> Dict:
        """Retrieve current positions for all symbols.

        Returns:
            Dict: Symbol to position details mapping
        """
        query = 'SELECT last(position), last(entry_price) FROM positions GROUP BY symbol'
        try:
            result = self.client.query(query)
            positions = {}
            for item in result.items():
                symbol = item[0][1]['symbol']
                data = next(item[1])
                positions[symbol] = {
                    'position': data['last_position'],
                    'entry_price': data['last_entry_price']
                }
            return positions
        except Exception as e:
            logger.error(f"Failed to get current positions: {str(e)}")
            return {}
