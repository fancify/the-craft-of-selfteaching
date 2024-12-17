import logging
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_last_month_dates():
    """Calculate the start and end dates for the last complete month"""
    # Use March 2024 as the reference date since we want February 2024 data
    reference_date = datetime(2024, 3, 1)

    # Get last day of previous month (February)
    last_day_prev = reference_date - timedelta(days=1)

    # Get first day of previous month
    first_day_prev = last_day_prev.replace(day=1)

    return first_day_prev, last_day_prev

def main():
    start_date, end_date = get_last_month_dates()

    logger.info("Date calculations:")
    logger.info(f"Reference date: March 1, 2024")
    logger.info(f"Target month start: {start_date.strftime('%Y-%m-%d')}")
    logger.info(f"Target month end: {end_date.strftime('%Y-%m-%d')}")

    # Calculate timestamps for Binance API
    start_ts = int(start_date.timestamp() * 1000)
    end_ts = int((end_date + timedelta(days=1)).timestamp() * 1000)

    logger.info("\nTimestamp calculations:")
    logger.info(f"Start timestamp (ms): {start_ts}")
    logger.info(f"End timestamp (ms): {end_ts}")

    # Verify timestamps convert back to correct dates
    start_date_check = datetime.fromtimestamp(start_ts / 1000)
    end_date_check = datetime.fromtimestamp(end_ts / 1000)

    logger.info("\nTimestamp verification:")
    logger.info(f"Start date from timestamp: {start_date_check.strftime('%Y-%m-%d')}")
    logger.info(f"End date from timestamp: {end_date_check.strftime('%Y-%m-%d')}")

if __name__ == "__main__":
    main()
