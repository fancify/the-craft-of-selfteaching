import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.vegas_channel import VegasChannel
from src.data_fetcher import DataFetcher
from src.strategy import Strategy

def analyze_btc_trades():
    # Initialize components
    data_fetcher = DataFetcher()
    vegas_channel = VegasChannel()
    strategy = Strategy(vegas_channel)

    # Fetch BTC data
    symbol = "BTCUSDT"
    daily_data = data_fetcher.fetch_daily_data(symbol)
    weekly_data = data_fetcher.fetch_weekly_data(symbol)

    # Calculate EMAs for both timeframes
    daily_data['ema144'] = daily_data['close'].ewm(span=144, adjust=False).mean()
    daily_data['ema169'] = daily_data['close'].ewm(span=169, adjust=False).mean()
    weekly_data['ema144'] = weekly_data['close'].ewm(span=144, adjust=False).mean()
    weekly_data['ema169'] = weekly_data['close'].ewm(span=169, adjust=False).mean()

    trades = []
    position = None

    for idx in range(len(daily_data)):
        date = daily_data.index[idx]
        price = daily_data['close'].iloc[idx]
        daily_upper = daily_data['ema144'].iloc[idx] > daily_data['ema169'].iloc[idx]
        daily_lower = daily_data['ema144'].iloc[idx] < daily_data['ema169'].iloc[idx]

        # Find corresponding weekly data
        weekly_idx = weekly_data.index.searchsorted(date)
        if weekly_idx > 0 and weekly_idx < len(weekly_data):
            weekly_upper = weekly_data['ema144'].iloc[weekly_idx-1] > weekly_data['ema169'].iloc[weekly_idx-1]
            weekly_lower = weekly_data['ema144'].iloc[weekly_idx-1] < weekly_data['ema169'].iloc[weekly_idx-1]

            # Trading logic
            if position is None:
                if weekly_upper and daily_upper:
                    trades.append({
                        'date': date,
                        'action': 'LONG',
                        'price': price,
                        'reason': '周线和日线均在Vegas通道上轨上方，开仓做多'
                    })
                    position = 'LONG'
                elif weekly_lower and daily_lower:
                    trades.append({
                        'date': date,
                        'action': 'SHORT',
                        'price': price,
                        'reason': '周线和日线均在Vegas通道下轨下方，开仓做空'
                    })
                    position = 'SHORT'
            elif position == 'LONG':
                if daily_lower:
                    trades.append({
                        'date': date,
                        'action': 'CLOSE_LONG',
                        'price': price,
                        'reason': '日线收在Vegas通道下轨下方，平多仓'
                    })
                    position = None
            elif position == 'SHORT':
                if daily_upper:
                    trades.append({
                        'date': date,
                        'action': 'CLOSE_SHORT',
                        'price': price,
                        'reason': '日线收在Vegas通道上轨上方，平空仓'
                    })
                    position = None

    # Convert to DataFrame for easier analysis
    trades_df = pd.DataFrame(trades)

    # Print trade analysis
    print(f"\nBTC交易记录分析:")
    print("=" * 80)

    for idx, trade in trades_df.iterrows():
        print(f"\n交易 #{idx+1}")
        print(f"时间: {trade['date'].strftime('%Y-%m-%d')}")
        print(f"操作: {trade['action']}")
        print(f"价格: {trade['price']:.2f}")
        print(f"原因: {trade['reason']}")
        print("-" * 40)

if __name__ == "__main__":
    analyze_btc_trades()
