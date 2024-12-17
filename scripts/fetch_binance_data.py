import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from src.binance_data_fetcher import BinanceDataFetcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_last_month_dates():
    """Get start and end dates for February 2024"""
    reference_date = datetime(2024, 3, 1)
    last_day_prev = reference_date - timedelta(days=1)
    first_day_prev = last_day_prev.replace(day=1)
    return first_day_prev, last_day_prev

def validate_data(market_data):
    """Validate the fetched market data"""
    if not market_data:
        return False

    for symbol, timeframes in market_data.items():
        # Check if we have both daily and weekly data
        if not all(tf in timeframes for tf in ['daily', 'weekly']):
            logger.error(f"Missing timeframe data for {symbol}")
            return False

        # Check data length
        daily_data = timeframes['daily']
        weekly_data = timeframes['weekly']

        if len(daily_data) < 169:  # Need at least 169 days for EMA169
            logger.error(f"Insufficient daily data for {symbol}: {len(daily_data)} records")
            return False

        if len(weekly_data) < 24:  # Need at least 24 weeks for reliable weekly signals
            logger.error(f"Insufficient weekly data for {symbol}: {len(weekly_data)} records")
            return False

    return True

def main():
    """Main function to fetch and validate market data"""
    # Get date range for February 2024
    start_date, end_date = get_last_month_dates()

    logger.info("Fetching market data for February 2024:")
    logger.info(f"Start date: {start_date.strftime('%Y-%m-%d')}")
    logger.info(f"End date: {end_date.strftime('%Y-%m-%d')}")

    # Initialize data fetcher
    data_dir = Path("data/market_data")
    data_dir.mkdir(parents=True, exist_ok=True)
    data_fetcher = BinanceDataFetcher(data_dir=str(data_dir))

    try:
        # Fetch market data
        market_data = data_fetcher.fetch_market_data(start_date=start_date, end_date=end_date)

        # Validate the fetched data
        if validate_data(market_data):
            logger.info("Successfully fetched and validated market data")
        else:
            logger.error("Data validation failed")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Failed to fetch market data: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
