"""Constants for the Eforsyning integration."""
from datetime import timedelta

DOMAIN = "eforsyning"

# Every 6 hours seems appropriate to get an update ready in the morning
MIN_TIME_BETWEEN_UPDATES = timedelta(hours=6)
# Sure, let's bash the API service.. But useful when trying to get results fast.
#MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=1)
