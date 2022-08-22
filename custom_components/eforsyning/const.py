"""Constants for the Eforsyning integration."""
from datetime import timedelta

DOMAIN = "eforsyning"

# Default name for sensor prefix texts (possibly other things)
DEFAULT_NAME = "eForsyning"

######################################################################
##  NOTICE ON FAIR USE:
##  Please do not set this constant below 15 minutes.
##  Softværket who runs the API will impose an IP-ban if fair use
##  is not adhered to.
##
##  The dataset is updated every 24 hours in the morning.
##  The default min. time is to spread out load on the API and still
##  retrieve data.
######################################################################
# Every 6 hours seems appropriate to get an update ready in the morning
MIN_TIME_BETWEEN_UPDATES = timedelta(hours=6)
# Smallest appropriate interval.  Only relevant for development use.
#MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=15)
