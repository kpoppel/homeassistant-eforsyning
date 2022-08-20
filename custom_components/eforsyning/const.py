"""Constants for the Eforsyning integration."""
from datetime import timedelta

DOMAIN = "eforsyning"

# Default name for sensor prefix texts (possibly other things)
DEFAULT_NAME = "eForsyning"

# Every 6 hours seems appropriate to get an update ready in the morning
MIN_TIME_BETWEEN_UPDATES = timedelta(hours=6)
# Sure, let's bash the API service.. But useful when trying to get results fast.
#MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=1)

DATA_COORDINATOR = "eforsyning_coordinator"
DATA_API = "eforsyning_api"