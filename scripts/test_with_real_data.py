import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from src.synthetic_data import SyntheticDataGenerator
from src.strategy import VegasChannelStrategy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def calculate_metrics(returns):
    """Calculate trading performance metrics"""
    cumulative_returns = (1 + returns).cumprod()

    metrics = {
        'total_return': (cumulative_returns.iloc[-1] - 1) * 100,
        'max_drawdown': ((cumulative_returns / cumulative_returns.cummax() - 1).min() * 100),
        'sharpe_ratio': np.sqrt(252) * returns.mean() / returns.std() if len(returns) > 1 else 0,
        'win_rate': (returns > 0).mean() * 100 if len(returns) > 0 else 0,
        'avg_win': returns[returns > 0].mean() * 100 if len(returns[returns > 0]) > 0 else 0,
        'avg_loss': returns[returns < 0].mean() * 100 if len(returns[returns < 0]) > 0 else 0,
    }
    return metrics

def main():
    """Test Vegas Channel strategy with real Binance Futures data for the last month"""

    # Initialize synthetic data generator and strategy
    data_generator = SyntheticDataGenerator(volatility=0.02, trend=0.0001)
    strategy = VegasChannelStrategy()
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'DOGEUSDT']
    logger.info(f"Testing with symbols: {symbols}")

    try:
        # Calculate date range for last 30 days
        end_date = datetime.now() - timedelta(days=1)
        start_date = end_date - timedelta(days=30)
        logger.info(f"Generating synthetic data from {start_date.date()} to {end_date.date()}")

        # Generate synthetic market data (includes historical data for EMA calculation)
        market_data = data_generator.generate_market_data(symbols, start_date, end_date)

        # Check if we have enough data for each symbol
        valid_symbols = []
        for symbol in market_data:
            if ('daily' in market_data[symbol] and 'weekly' in market_data[symbol] and
                len(market_data[symbol]['daily']) >= 169):
                valid_symbols.append(symbol)
            else:
                logger.warning(f"Insufficient data for {symbol}, excluding from analysis")

        if not valid_symbols:
            logger.error("No symbols with sufficient data found")
            return

        logger.info(f"\nRunning strategy simulation for {len(valid_symbols)} symbols")

        # Run strategy simulation
        all_results = {}
        portfolio_returns = pd.Series(0, index=pd.date_range(start=start_date, end=end_date, freq='D'))

        for symbol in valid_symbols:
            try:
                # Trim data to simulation period
                daily_data = market_data[symbol]['daily']
                weekly_data = market_data[symbol]['weekly']

                daily_mask = (daily_data.index >= start_date) & (daily_data.index <= end_date)
                simulation_daily = daily_data[daily_mask]

                symbol_data = {
                    'daily': daily_data,  # Keep full history for EMA calculation
                    'weekly': weekly_data
                }

                symbol_results = strategy.simulate_trading(symbol_data)
                all_results[symbol] = symbol_results

                # Calculate symbol returns and add to portfolio
                symbol_returns = (symbol_results['position'] *
                                simulation_daily['close'].pct_change()).fillna(0)
                portfolio_returns = portfolio_returns.add(symbol_returns / len(valid_symbols), fill_value=0)

            except Exception as e:
                logger.error(f"Error simulating {symbol}: {str(e)}")
                continue

        # Print portfolio-level metrics
        logger.info("\n=== Portfolio Performance ===")
        portfolio_metrics = calculate_metrics(portfolio_returns)
        logger.info(f"Total Return: {portfolio_metrics['total_return']:.2f}%")
        logger.info(f"Max Drawdown: {portfolio_metrics['max_drawdown']:.2f}%")
        logger.info(f"Sharpe Ratio: {portfolio_metrics['sharpe_ratio']:.2f}")
        logger.info(f"Win Rate: {portfolio_metrics['win_rate']:.2f}%")
        logger.info(f"Average Win: {portfolio_metrics['avg_win']:.2f}%")
        logger.info(f"Average Loss: {portfolio_metrics['avg_loss']:.2f}%")

        # Print individual symbol results
        logger.info("\n=== Individual Symbol Performance ===")
        for symbol in all_results:
            positions = all_results[symbol]['position']
            daily_data = market_data[symbol]['daily']
            simulation_mask = (daily_data.index >= start_date) & (daily_data.index <= end_date)
            simulation_data = daily_data[simulation_mask]

            returns = (positions * simulation_data['close'].pct_change()).fillna(0)
            metrics = calculate_metrics(returns)

            logger.info(f"\n{symbol}:")
            logger.info(f"Total Return: {metrics['total_return']:.2f}%")
            logger.info(f"Number of Trades: {(positions.diff() != 0).sum()}")
            logger.info(f"Win Rate: {metrics['win_rate']:.2f}%")

    except Exception as e:
        logger.error(f"Error running strategy test: {str(e)}")
        raise

if __name__ == "__main__":
    main()
