import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.strategy import VegasChannelStrategy
import pandas as pd
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_market_data(data_dir: str) -> dict:
    """Load market data from CSV files"""
    with open(os.path.join(data_dir, 'metadata.json'), 'r') as f:
        metadata = json.load(f)

    market_data = {}
    for symbol in metadata['symbols']:
        symbol_dir = os.path.join(data_dir, symbol)

        daily_df = pd.read_csv(os.path.join(symbol_dir, 'daily.csv'))
        weekly_df = pd.read_csv(os.path.join(symbol_dir, 'weekly.csv'))

        # Convert timestamp to datetime index
        daily_df['timestamp'] = pd.to_datetime(daily_df['timestamp'])
        weekly_df['timestamp'] = pd.to_datetime(weekly_df['timestamp'])
        daily_df.set_index('timestamp', inplace=True)
        weekly_df.set_index('timestamp', inplace=True)

        market_data[symbol] = {
            'daily': daily_df,
            'weekly': weekly_df
        }

    return market_data

def format_simulation_results(results: dict) -> str:
    """Format simulation results for output"""
    output = []
    output.append("=== Vegas Channel Strategy Simulation Results ===\n")

    for symbol, df in results.items():
        total_return = (df['cumulative_returns'].iloc[-1] - 1) * 100
        win_rate = (df['strategy_returns'] > 0).mean() * 100
        max_drawdown = ((df['cumulative_returns'].cummax() - df['cumulative_returns'])
                       / df['cumulative_returns'].cummax()).max() * 100

        output.append(f"\n{symbol}:")
        output.append(f"总收益率: {total_return:.2f}%")
        output.append(f"胜率: {win_rate:.2f}%")
        output.append(f"最大回撤: {max_drawdown:.2f}%")
        output.append(f"当前持仓: {'多头' if df['position'].iloc[-1] == 1 else '空头' if df['position'].iloc[-1] == -1 else '空仓'}")
        output.append("-" * 50)

    return "\n".join(output)

def main():
    # Load market data
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, 'data')

    logger.info("Loading market data...")
    market_data = load_market_data(data_dir)

    # Initialize and run strategy
    logger.info("Running strategy simulation...")
    strategy = VegasChannelStrategy()
    results = strategy.simulate_trading(market_data)

    # Format and save results
    output = format_simulation_results(results)

    results_dir = os.path.join(data_dir, 'results')
    os.makedirs(results_dir, exist_ok=True)

    # Save formatted results
    with open(os.path.join(results_dir, 'simulation_summary.txt'), 'w', encoding='utf-8') as f:
        f.write(output)

    # Save detailed results
    for symbol, df in results.items():
        df.to_csv(os.path.join(results_dir, f'{symbol}_detailed.csv'))

    logger.info("Simulation complete. Results saved to data/results/")
    print("\n" + output)

if __name__ == '__main__':
    main()
