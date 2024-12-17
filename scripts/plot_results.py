import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from src.synthetic_data import SyntheticDataGenerator
from src.strategy import VegasChannelStrategy
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def plot_strategy_results(market_data: dict, results: dict, symbol: str, strategy: VegasChannelStrategy):
    """Plot strategy results for a single symbol"""
    try:
        daily_data = market_data[symbol]['daily'].copy()
        positions = results[symbol]['position']

        # Calculate EMAs
        daily_data = strategy.calculate_ema_bands(daily_data)

        # Create figure with price and EMAs
        plt.figure(figsize=(15, 10))

        # Plot price and EMAs
        plt.subplot(2, 1, 1)
        plt.plot(daily_data.index, daily_data['close'], label='Price', alpha=0.7)
        plt.plot(daily_data.index, daily_data['ema_lower'], label='EMA144', alpha=0.7)
        plt.plot(daily_data.index, daily_data['ema_upper'], label='EMA169', alpha=0.7)

        # Plot positions
        long_entries = daily_data['close'][positions == 1]
        short_entries = daily_data['close'][positions == -1]

        if not long_entries.empty:
            plt.plot(long_entries.index, long_entries, '^',
                    color='green', label='Long Entry', markersize=10)
        if not short_entries.empty:
            plt.plot(short_entries.index, short_entries, 'v',
                    color='red', label='Short Entry', markersize=10)

        plt.title(f'{symbol} Price and Positions')
        plt.legend()
        plt.grid(True)

        # Plot cumulative returns
        plt.subplot(2, 1, 2)
        returns = (positions * daily_data['close'].pct_change()).fillna(0)
        cumulative_returns = (1 + returns).cumprod()
        plt.plot(cumulative_returns.index, cumulative_returns, label='Strategy Returns')
        plt.title('Cumulative Returns')
        plt.legend()
        plt.grid(True)

        plt.tight_layout()
        plt.savefig(f'results_{symbol}.png')
        plt.close()

        logger.info(f"Generated plot for {symbol}")

    except Exception as e:
        logger.error(f"Error plotting results for {symbol}: {str(e)}")

def main():
    """Generate and plot strategy results"""
    # Initialize components
    data_generator = SyntheticDataGenerator(volatility=0.02, trend=0.0001)
    strategy = VegasChannelStrategy()
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'DOGEUSDT']

    # Generate data
    end_date = datetime.now() - timedelta(days=1)
    start_date = end_date - timedelta(days=30)
    market_data = data_generator.generate_market_data(symbols, start_date, end_date)

    # Run strategy
    results = {}
    for symbol in symbols:
        symbol_results = strategy.simulate_trading({
            symbol: {
                'daily': market_data[symbol]['daily'],
                'weekly': market_data[symbol]['weekly']
            }
        })
        results[symbol] = symbol_results[symbol]
        plot_strategy_results(market_data, results, symbol, strategy)

    logger.info("Results plots have been generated for all symbols.")

if __name__ == "__main__":
    main()
