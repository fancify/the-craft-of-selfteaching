import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import json
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_timeframe_data(df: pd.DataFrame, timeframe: str) -> bool:
    """Validate data for a specific timeframe"""
    # Check if we have enough data for EMA calculation
    min_periods = 169  # Longest EMA period
    if len(df) < min_periods:
        logger.error(f"Insufficient {timeframe} data: {len(df)} periods < required {min_periods}")
        return False

    # Check for missing dates
    date_range = pd.date_range(df.index.min(), df.index.max(),
                              freq='D' if timeframe == 'daily' else 'W')
    missing_dates = date_range.difference(df.index)
    if len(missing_dates) > 0:
        logger.warning(f"Missing {len(missing_dates)} {timeframe} dates")
        logger.debug(f"Missing dates: {missing_dates}")

    # Check for required columns
    required_cols = ['open', 'high', 'low', 'close', 'volume']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        logger.error(f"Missing columns in {timeframe} data: {missing_cols}")
        return False

    # Check for null values
    null_counts = df[required_cols].isnull().sum()
    if null_counts.any():
        logger.error(f"Found null values in {timeframe} data:\n{null_counts[null_counts > 0]}")
        return False

    return True

def main():
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')

    # Load metadata
    with open(os.path.join(data_dir, 'metadata.json'), 'r') as f:
        metadata = json.load(f)

    logger.info(f"Validating data for {len(metadata['symbols'])} symbols...")

    validation_results = {
        'total_symbols': len(metadata['symbols']),
        'valid_symbols': 0,
        'invalid_symbols': [],
        'validation_time': datetime.now().isoformat()
    }

    for symbol in metadata['symbols']:
        symbol_dir = os.path.join(data_dir, symbol)

        try:
            # Load daily and weekly data
            daily_df = pd.read_csv(os.path.join(symbol_dir, 'daily.csv'), index_col='timestamp', parse_dates=True)
            weekly_df = pd.read_csv(os.path.join(symbol_dir, 'weekly.csv'), index_col='timestamp', parse_dates=True)

            # Validate both timeframes
            daily_valid = validate_timeframe_data(daily_df, 'daily')
            weekly_valid = validate_timeframe_data(weekly_df, 'weekly')

            if daily_valid and weekly_valid:
                validation_results['valid_symbols'] += 1
                logger.info(f"✓ {symbol}: Valid data")
            else:
                validation_results['invalid_symbols'].append(symbol)
                logger.warning(f"✗ {symbol}: Invalid data")

        except Exception as e:
            logger.error(f"Error validating {symbol}: {e}")
            validation_results['invalid_symbols'].append(symbol)

    # Save validation results
    with open(os.path.join(data_dir, 'validation_results.json'), 'w') as f:
        json.dump(validation_results, f, indent=2)

    logger.info(f"\nValidation Summary:")
    logger.info(f"Total Symbols: {validation_results['total_symbols']}")
    logger.info(f"Valid Symbols: {validation_results['valid_symbols']}")
    logger.info(f"Invalid Symbols: {len(validation_results['invalid_symbols'])}")

    if validation_results['invalid_symbols']:
        logger.info("Invalid symbols:")
        for symbol in validation_results['invalid_symbols']:
            logger.info(f"  - {symbol}")

if __name__ == '__main__':
    main()
