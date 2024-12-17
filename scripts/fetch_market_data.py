import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.synthetic_data import SyntheticDataGenerator
import pandas as pd
import logging
from datetime import datetime
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_data(data: dict) -> bool:
    """Validate fetched market data"""
    if not data:
        logger.error("No data fetched")
        return False

    for symbol, timeframes in data.items():
        # Check if we have both timeframes
        if 'daily' not in timeframes or 'weekly' not in timeframes:
            logger.error(f"Missing timeframe data for {symbol}")
            return False

        # Check data length
        daily_df = timeframes['daily']
        weekly_df = timeframes['weekly']

        # For one month of data
        if len(daily_df) < 28:  # Minimum days in a month
            logger.error(f"Insufficient daily data for {symbol}: {len(daily_df)} days")
            return False

        if len(weekly_df) < 4:  # Minimum weeks in a month
            logger.error(f"Insufficient weekly data for {symbol}: {len(weekly_df)} weeks")
            return False

        # Check for required columns
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in daily_df.columns or col not in weekly_df.columns:
                logger.error(f"Missing column {col} for {symbol}")
                return False

        # Check for null values
        for timeframe, df in timeframes.items():
            null_counts = df[required_cols].isnull().sum()
            if null_counts.any():
                logger.error(f"Found null values in {timeframe} data for {symbol}:\n{null_counts[null_counts > 0]}")
                return False

    return True

def main():
    # Get absolute path for data directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, 'data')

    # Generate synthetic market data for testing
    generator = SyntheticDataGenerator()

    # Generate market data for the last month
    logger.info("Generating synthetic market data...")
    market_data = generator.generate_market_data()

    # Validate data
    if not validate_data(market_data):
        logger.error("Data validation failed")
        return

    # Save metadata
    metadata = {
        'fetch_time': datetime.now().isoformat(),
        'symbols': list(market_data.keys()),
        'timeframes': ['daily', 'weekly'],
        'lookback_days': 30
    }

    # Create data directory if it doesn't exist
    os.makedirs(data_dir, exist_ok=True)

    # Save metadata
    with open(os.path.join(data_dir, 'metadata.json'), 'w') as f:
        json.dump(metadata, f, indent=2)

    # Save market data
    for symbol, timeframes in market_data.items():
        symbol_dir = os.path.join(data_dir, symbol)
        os.makedirs(symbol_dir, exist_ok=True)

        for timeframe, df in timeframes.items():
            df.to_csv(os.path.join(symbol_dir, f'{timeframe}.csv'))
            logger.info(f"Saved {timeframe} data for {symbol}")

    logger.info(f"Successfully saved data for {len(market_data)} symbols")

if __name__ == '__main__':
    main()
