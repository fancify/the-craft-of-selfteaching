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

        # Process each symbol
        all_results = []
        logger.info(f"\nRunning strategy simulation for {len(symbols)} symbols")

        for symbol in symbols:
            try:
                logger.info(f"Processing {symbol}")
                symbol_data = market_data[symbol]

                # Run strategy simulation with proper data structure
                results = strategy.simulate_trading({
                    symbol: {
                        'daily': symbol_data['daily'],
                        'weekly': symbol_data['weekly']
                    }
                })

                if results and symbol in results:
                    # Calculate metrics for this symbol
                    symbol_returns = (results[symbol]['position_value'] *
                                    results[symbol]['close'].pct_change()).fillna(0)

                    metrics = calculate_metrics(symbol_returns)
                    metrics['symbol'] = symbol
                    all_results.append(metrics)

                    logger.info(f"Results for {symbol}:")
                    logger.info(f"Total Return: {metrics['total_return']:.2%}")
                    logger.info(f"Max Drawdown: {metrics['max_drawdown']:.2%}")
                    logger.info(f"Win Rate: {metrics['win_rate']:.2%}")
                    logger.info(f"Avg Win: {metrics['avg_win']:.2%}")
                    logger.info(f"Avg Loss: {metrics['avg_loss']:.2%}")
                    logger.info(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
                    logger.info("---")

            except Exception as e:
                logger.error(f"Error simulating {symbol}: {str(e)}")
                continue

        if all_results:
            # Calculate portfolio-level metrics
            logger.info("\n=== Portfolio Performance ===")
            portfolio_metrics = {
                'total_return': np.mean([r['total_return'] for r in all_results]),
                'max_drawdown': np.mean([r['max_drawdown'] for r in all_results]),
                'sharpe_ratio': np.mean([r['sharpe_ratio'] for r in all_results]),
                'win_rate': np.mean([r['win_rate'] for r in all_results]),
                'avg_win': np.mean([r['avg_win'] for r in all_results]),
                'avg_loss': np.mean([r['avg_loss'] for r in all_results])
            }

            logger.info(f"Total Return: {portfolio_metrics['total_return']:.2%}")
            logger.info(f"Max Drawdown: {portfolio_metrics['max_drawdown']:.2%}")
            logger.info(f"Sharpe Ratio: {portfolio_metrics['sharpe_ratio']:.2f}")
            logger.info(f"Win Rate: {portfolio_metrics['win_rate']:.2%}")
            logger.info(f"Average Win: {portfolio_metrics['avg_win']:.2%}")
            logger.info(f"Average Loss: {portfolio_metrics['avg_loss']:.2%}")

            logger.info("\n=== Individual Symbol Performance ===")
            for result in all_results:
                logger.info(f"{result['symbol']}:")
                logger.info(f"  Total Return: {result['total_return']:.2%}")
                logger.info(f"  Sharpe Ratio: {result['sharpe_ratio']:.2f}")
                logger.info(f"  Win Rate: {result['win_rate']:.2%}")

        else:
            logger.error("No valid results generated")

    except Exception as e:
        logger.error(f"Error in backtest simulation: {str(e)}")
        raise

if __name__ == "__main__":
    main()
