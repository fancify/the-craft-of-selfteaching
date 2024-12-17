import pandas as pd
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_data():
    data_dir = Path("data/market_data")
    
    # Analyze daily data
    daily_file = next(data_dir.glob("daily/BTCUSDT_daily_*.csv"))
    daily_data = pd.read_csv(daily_file)
    logger.info("\nDaily Data Summary:")
    logger.info(f"Shape: {daily_data.shape}")
    logger.info("\nStatistics:")
    logger.info(daily_data.describe())
    
    # Analyze weekly data
    weekly_file = next(data_dir.glob("weekly/BTCUSDT_weekly_*.csv"))
    weekly_data = pd.read_csv(weekly_file)
    logger.info("\nWeekly Data Summary:")
    logger.info(f"Shape: {weekly_data.shape}")
    logger.info("\nStatistics:")
    logger.info(weekly_data.describe())

if __name__ == "__main__":
    analyze_data()
