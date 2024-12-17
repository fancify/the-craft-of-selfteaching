import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from src.vegas_channel import VegasChannel

def load_sample_data(symbol: str = "BTCUSDT", timeframe: str = "1d", periods: int = 200) -> pd.DataFrame:
    """Load sample data for strategy analysis"""
    # Generate sample data for testing
    np.random.seed(42)
    dates = pd.date_range(end=pd.Timestamp.now(), periods=periods, freq='D')
    close = pd.Series(np.random.randn(periods).cumsum() + 100, index=dates)
    return pd.DataFrame({'close': close})

def analyze_strategy(data: pd.DataFrame, vegas: VegasChannel) -> None:
    """Analyze Vegas Channel strategy performance"""
    # Calculate Vegas Channel indicators
    data = vegas.calculate(data)

    # Get trading signals
    signals = vegas.get_signals(data)
    data['signal'] = signals['signal']

    # Calculate returns
    data['returns'] = data['close'].pct_change()
    data['strategy_returns'] = data['signal'].shift(1) * data['returns']

    # Calculate performance metrics
    total_return = (1 + data['strategy_returns']).prod() - 1
    sharpe_ratio = np.sqrt(252) * data['strategy_returns'].mean() / data['strategy_returns'].std()
    max_drawdown = (data['close'] / data['close'].cummax() - 1).min()

    print(f"\nStrategy Performance Metrics:")
    print(f"Total Return: {total_return:.2%}")
    print(f"Sharpe Ratio: {sharpe_ratio:.2f}")
    print(f"Max Drawdown: {max_drawdown:.2%}")

    # Plot strategy visualization
    plt.figure(figsize=(15, 10))
    plt.subplot(2, 1, 1)
    plt.plot(data.index, data['close'], label='Price', alpha=0.7)
    plt.plot(data.index, data['vegas_middle'], label='Vegas Middle', alpha=0.7)
    plt.plot(data.index, data['vegas_upper'], label='Vegas Upper', alpha=0.7)
    plt.plot(data.index, data['vegas_lower'], label='Vegas Lower', alpha=0.7)
    plt.fill_between(data.index, data['vegas_upper'], data['vegas_lower'], alpha=0.1)

    # Plot buy signals
    buy_signals = data[data['signal'] == 1]
    plt.scatter(buy_signals.index, buy_signals['close'],
               marker='^', color='g', label='Buy Signal', alpha=0.7)

    plt.title('Vegas Channel Strategy Analysis')
    plt.legend()
    plt.grid(True)

    # Plot equity curve
    plt.subplot(2, 1, 2)
    cumulative_returns = (1 + data['strategy_returns']).cumprod()
    plt.plot(data.index, cumulative_returns, label='Strategy Returns')
    plt.title('Equity Curve')
    plt.legend()
    plt.grid(True)

    plt.tight_layout()
    plt.savefig('strategy_analysis.png')
    plt.close()

def main():
    # Load sample data
    data = load_sample_data()

    # Initialize Vegas Channel strategy
    vegas = VegasChannel(period=20, std_multiplier=2.0)

    # Analyze strategy with default parameters
    print("\nAnalyzing strategy with default parameters:")
    analyze_strategy(data, vegas)

    # Optimize parameters
    print("\nOptimizing strategy parameters...")
    optimal_period, optimal_multiplier = vegas.optimize_parameters(data)
    print(f"Optimal parameters - Period: {optimal_period}, Multiplier: {optimal_multiplier:.2f}")

    # Analyze strategy with optimized parameters
    print("\nAnalyzing strategy with optimized parameters:")
    vegas = VegasChannel(period=optimal_period, std_multiplier=optimal_multiplier)
    analyze_strategy(data, vegas)

if __name__ == "__main__":
    main()
