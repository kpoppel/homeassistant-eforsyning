"""The Eforsyning integration."""
from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from custom_components.eforsyning.pyeforsyning.eforsyning import Eforsyning

from homeassistant.util import Throttle
import asyncio
import logging
import sys
import requests

from .const import DOMAIN, MIN_TIME_BETWEEN_UPDATES

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)

PLATFORMS: list[Platform] = [Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Eforsyning component."""
    hass.data[DOMAIN] = {}
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Eforsyning from a config entry."""
    #_LOGGER.debug(entry.data)
    username = entry.data['username']
    password = entry.data['password']
    supplierid = entry.data['supplierid']
    entityname = entry.data['entityname']
    billing_period_skew = entry.data['billing_period_skew'] # This one is true if the billing period is from July to June
    
    hass.data[DOMAIN][entry.entry_id] = API(username, password, supplierid, entityname, billing_period_skew)

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

async def async_migrate_entry(hass, config_entry: ConfigEntry):
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

    return True

""" API for EForsyning.  Because of the @Throttle annotation it cannot live in the eforsyning module - but it should."""
class API:
    def __init__(self, username, password, supplierid, entityname, billing_period_skew):
        self._client = Eforsyning(username, password, supplierid, billing_period_skew)
        self._data = None

    def get_data(self, data_point):
        """ Get the sensor reading from the eforsyning library"""
        if self._data != None:
            return self._data.get_data_point(data_point)
        else:
            return None

    def get_data_date(self):
        if self._data != None:
            return self._data.data_date.date().strftime('%Y-%m-%d')
        else:
            return None

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        _LOGGER.debug("Fetching data from Eforsyning")
        # When asked to help with some debug data - and extra noise
        # Remove the comment from this line, and comment out the rest of the
        # lines down to the last line
        #self._data = self._client.get_latest()

        # From here -->
        try: 
            data = self._client.get_latest()
            if data.status == 200:
                self._data = data
            else:
                _LOGGER.warn(f"Error from eforsyning: {data.status} - {data.detailed_status}")
        except requests.exceptions.HTTPError as he:
            message = None
            if he.response.status_code == 401:
                message = f"Unauthorized error while accessing eforsyning.dk. Wrong or expired refresh token?"
            else:
                message = f"Exception: {e}"

            _LOGGER.warn(message)
        except: 
            e = sys.exc_info()[0]
            _LOGGER.warn(f"Exception: {e}")
        # <-- To here
        _LOGGER.debug("Done fetching data from Eforsyning")

