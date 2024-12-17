import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import logging
from datetime import datetime, timedelta
from src.binance_data_fetcher import BinanceDataFetcher
from src.strategy import VegasChannelStrategy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Test Vegas Channel strategy with real Binance Futures data"""

    # Initialize data fetcher and strategy
    fetcher = BinanceDataFetcher(use_testnet=False)  # Use mainnet for real data
    strategy = VegasChannelStrategy()

    try:
        # Get top volume symbols
        symbols = fetcher.get_top_volume_symbols(limit=5)  # Start with top 5 for testing
        logger.info(f"Testing with symbols: {symbols}")

        # Calculate date range for last 180 days from current date
        end_date = datetime.now() - timedelta(days=1)  # Use yesterday as end date
        start_date = end_date - timedelta(days=180)
        logger.info(f"Fetching data from {start_date.date()} to {end_date.date()}")

        # Fetch historical data
        market_data = fetcher.fetch_market_data(start_date, end_date, symbols)

        if not market_data:
            logger.error("No market data available")
            return

        # Check if we have enough data for each symbol
        valid_symbols = []
        for symbol in market_data:
            if ('daily' in market_data[symbol] and 'weekly' in market_data[symbol] and
                len(market_data[symbol]['daily']) >= 169):  # Need at least 169 days for EMA169
                valid_symbols.append(symbol)

                # Log EMA values for verification
                daily_data = market_data[symbol]['daily']
                weekly_data = market_data[symbol]['weekly']

                # Calculate EMAs
                daily_ema_lower = daily_data['close'].ewm(span=144, adjust=False, min_periods=1).mean()
                daily_ema_upper = daily_data['close'].ewm(span=169, adjust=False, min_periods=1).mean()
                weekly_ema_lower = weekly_data['close'].ewm(span=144, adjust=False, min_periods=1).mean()
                weekly_ema_upper = weekly_data['close'].ewm(span=169, adjust=False, min_periods=1).mean()

                logger.info(f"\nEMA verification for {symbol}:")
                logger.info("Last 5 days of daily data:")
                logger.info(f"{'Date':<12} {'Close':>10} {'EMA144':>10} {'EMA169':>10}")
                logger.info("-" * 44)
                for i in range(-5, 0):
                    logger.info(f"{daily_data.index[i].date()!s:<12} "
                              f"{daily_data['close'].iloc[i]:10.2f} "
                              f"{daily_ema_lower.iloc[i]:10.2f} "
                              f"{daily_ema_upper.iloc[i]:10.2f}")

                logger.info("\nLast 3 weeks of weekly data:")
                logger.info(f"{'Date':<12} {'Close':>10} {'EMA144':>10} {'EMA169':>10}")
                logger.info("-" * 44)
                for i in range(-3, 0):
                    logger.info(f"{weekly_data.index[i].date()!s:<12} "
                              f"{weekly_data['close'].iloc[i]:10.2f} "
                              f"{weekly_ema_lower.iloc[i]:10.2f} "
                              f"{weekly_ema_upper.iloc[i]:10.2f}")
            else:
                logger.warning(f"Insufficient data for {symbol}, excluding from analysis")

        if not valid_symbols:
            logger.error("No symbols with sufficient data found")
            return

        logger.info(f"\nRunning strategy simulation for symbols: {valid_symbols}")

        # Run strategy simulation
        results = {}
        for symbol in valid_symbols:
            try:
                symbol_data = {
                    'daily': market_data[symbol]['daily'],
                    'weekly': market_data[symbol]['weekly']
                }
                symbol_results = strategy.simulate_trading({symbol: symbol_data})
                results.update(symbol_results)
            except Exception as e:
                logger.error(f"Error simulating {symbol}: {str(e)}")
                continue

        # Analyze results
        for symbol, data in results.items():
            positions = data['position']
            position_changes = positions.diff()[positions.diff() != 0]
            daily_data = market_data[symbol]['daily']
            weekly_data = market_data[symbol]['weekly']

            logger.info(f"\nResults for {symbol}:")
            logger.info(f"Number of trades: {len(position_changes)}")
            logger.info("\nPosition changes with context:")
            logger.info(f"{'Date':<12} {'Position':>8} {'Close':>10} {'Daily EMAs':>22} {'Weekly EMAs':>22}")
            logger.info("-" * 76)

            for date, pos_change in position_changes.items():
                # Get daily and weekly data for the date
                daily_idx = daily_data.index.get_loc(date)
                weekly_mask = weekly_data.index <= date
                if not weekly_mask.any():
                    continue
                weekly_idx = weekly_mask.sum() - 1

                daily_close = daily_data['close'].iloc[daily_idx]
                daily_ema_lower = daily_data['close'].iloc[:daily_idx+1].ewm(span=144, adjust=False).mean().iloc[-1]
                daily_ema_upper = daily_data['close'].iloc[:daily_idx+1].ewm(span=169, adjust=False).mean().iloc[-1]

                weekly_close = weekly_data['close'].iloc[weekly_idx]
                weekly_ema_lower = weekly_data['close'].iloc[:weekly_idx+1].ewm(span=144, adjust=False).mean().iloc[-1]
                weekly_ema_upper = weekly_data['close'].iloc[:weekly_idx+1].ewm(span=169, adjust=False).mean().iloc[-1]

                logger.info(f"{date.date()!s:<12} {pos_change:8.1f} {daily_close:10.2f} "
                          f"{daily_ema_lower:10.2f}/{daily_ema_upper:10.2f} "
                          f"{weekly_ema_lower:10.2f}/{weekly_ema_upper:10.2f}")

            # Calculate basic metrics
            returns = (positions * data['close'].pct_change()).fillna(0)
            cumulative_returns = (1 + returns).cumprod()

            logger.info(f"\nFinal cumulative return: {(cumulative_returns.iloc[-1] - 1) * 100:.2f}%")
            logger.info(f"Max drawdown: {((cumulative_returns / cumulative_returns.cummax() - 1).min() * 100):.2f}%")

    except Exception as e:
        logger.error(f"Error running strategy test: {str(e)}")
        raise

if __name__ == "__main__":
    main()
