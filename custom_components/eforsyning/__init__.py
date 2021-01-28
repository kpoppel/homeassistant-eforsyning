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

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=60)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Eforsyning component."""
    hass.data[DOMAIN] = {}
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Eforsyning from a config entry."""
    username = entry.data['username']
    password = entry.data['password']
    supplierid = entry.data['supplierid']
    ## Assume people onyl have a single metering device.
    ## Feel free to expand the code to find all metering devices
    ## and iterate over them.
    asset_id = 1
    installation_id = 1
    
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

    def get_total_day(self):
        if self._data != None:
            return round(self._data.get_total_metering_data(), 3)
        else:
            return None

    def get_usage_hour(self, hour):
        if self._data != None:
            return round(self._data.get_metering_data(hour), 3)
        else:
            return None

    def get_data_date(self):
        if self._data != None:
            return self._data.data_date.date().strftime('%Y-%m-%d')
        else:
            return None

    def get_metering_point(self):
        return self._metering_point

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        _LOGGER.debug("Fetching data from Eforsyning")

        pass

        try: 
            data = self._client.get_latest(self._metering_point)
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

