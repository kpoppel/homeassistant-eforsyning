"""The Eforsyning integration."""
import asyncio
import logging
import sys

import voluptuous as vol
from homeassistant.util import Throttle
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.eforsyning.pyeforsyning.eforsyning import Eforsyning

from .const import DOMAIN

import requests

_LOGGER = logging.getLogger(__name__)


CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)

PLATFORMS = ["sensor"]

# Every 6 hours seems appropriate to get an update ready in the morning
MIN_TIME_BETWEEN_UPDATES = timedelta(hours=6)
# Sure, let's bash the API service.. But useful when trying to get results fast.
#MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=1)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Eforsyning component."""
    hass.data[DOMAIN] = {}
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Eforsyning from a config entry."""
    username = entry.data['username']
    password = entry.data['password']
    supplierid = entry.data['supplierid']
    
    hass.data[DOMAIN][entry.entry_id] = HassEforsyning(username, password, supplierid)

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

class HassEforsyning:
    def __init__(self, username, password, supplierid):
        self._client = Eforsyning(username, password, supplierid)

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

        _LOGGER.debug("Done fetching data from Eforsyning")

