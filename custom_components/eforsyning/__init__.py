"""The Eforsyning integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN, MIN_TIME_BETWEEN_UPDATES

# The eForsyning integration - not on PyPi, just bundled here.
# Contrary to:
# https://developers.home-assistant.io/docs/creating_component_code_review#4-communication-with-devicesservices
from custom_components.eforsyning.pyeforsyning.eforsyning import Eforsyning

import logging

PLATFORMS: list[Platform] = [Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Eforsyning from a config entry."""
    #_LOGGER.debug(entry.data)
    _LOGGER.debug("async_setup_entry, %s", entry.domain)
    username = entry.data['username']
    password = entry.data['password']
    supplierid = entry.data['supplierid']
    entityname = entry.data['entityname']
    billing_period_skew = entry.data['billing_period_skew'] # This one is true if the billing period is from July to June
    is_water_supply = entry.data['is_water_supply'] # This one is true if the module is for eforsyning water delivery (false for regional heating)
    
    # Add the HomeAssistant specific API to the eForsyning integration.
    # The Sensor entity in the integration will call function here to do its thing.
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = API(username, password, supplierid, billing_period_skew, is_water_supply)

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

async def async_migrate_entry(hass, config_entry: ConfigEntry) -> bool:
    """Handle migration of setup entry data from one version to the next."""
    _LOGGER.debug("Migrating from version %s", config_entry.version)

    if config_entry.version == 1:

        new = {**config_entry.data}
        # Data:
        # {'supplierid': '...', 'password': '...', 'username': '...', 'billing_period_skew': <False or True>}
        new['entityname'] = "eforsyning"

        config_entry.version = 2
        hass.config_entries.async_update_entry(config_entry, data=new)

        _LOGGER.info("Migration to version %s successful", config_entry.version)

    if config_entry.version == 2:
        new = {**config_entry.data}
        # Data:
        # {'supplierid': '...', 'password': '...', 'username': '...', 'billing_period_skew': <False or True>, entityname = eforsyning}
        new['is_water_supply'] = False

        config_entry.version = 3
        hass.config_entries.async_update_entry(config_entry, data=new)

        _LOGGER.info("Migration to version %s successful", config_entry.version)

    return True

""" API for EForsyning.  Because of the @Throttle annotation it cannot live in the eforsyning module - but it should."""
from homeassistant.util import Throttle
import requests

class API:
    def __init__(self, username, password, supplierid, billing_period_skew, is_water_supply):
        self._client = Eforsyning(username, password, supplierid, billing_period_skew, is_water_supply)
        self.data = {}
        _LOGGER.debug("An eForsyning API class was created")

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        _LOGGER.debug("Fetching data from Eforsyning")
        # When asked to help with some debug data - and extra noise
        # Remove the comment from this line, and comment out the rest of the
        # lines down to the last line
        self.data = self._client.get_latest()

        # From here -->
        #try: 
        #    data = self._client.get_latest()
        #    if data.status == 200:
        #        self.data = data
        #    else:
        #        _LOGGER.warn(f"Error from eforsyning: {data.status} - {data.detailed_status}")
        #except requests.exceptions.HTTPError as he:
        #    message = None
        #    if he.response.status_code == 401:
        #        message = f"Unauthorized error while accessing eforsyning.dk. Wrong or expired refresh token?"
        #    else:
        #        message = f"Exception: {e}"
        #
        #    _LOGGER.warn(message)
        #except: 
        #    e = sys.exc_info()[0]
        #    _LOGGER.warn(f"Exception: {e}")
        # <-- To here
        _LOGGER.debug("Done fetching data from Eforsyning")

