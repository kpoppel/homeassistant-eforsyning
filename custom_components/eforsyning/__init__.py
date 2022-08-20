"""The Eforsyning integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN, MIN_TIME_BETWEEN_UPDATES, DATA_API, DATA_COORDINATOR

# The eForsyning integration - not on PyPi, just bundled here.
# Contrary to:
# https://developers.home-assistant.io/docs/creating_component_code_review#4-communication-with-devicesservices
from custom_components.eforsyning.pyeforsyning.eforsyning import Eforsyning

import logging
import async_timeout

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

    # Register the API:
    hass.data.setdefault(DOMAIN, {})
    api = API(username, password, supplierid, billing_period_skew, is_water_supply)

    # Let the Coordinator know abou the API
    coordinator = Coordinator(hass, api)

    hass.data[DOMAIN][entry.entry_id] = {
        DATA_COORDINATOR: coordinator,
        DATA_API: api,
    }

    # Fetch initial data so we have data when entities subscribe
    #
    # If the refresh fails, async_config_entry_first_refresh will
    # raise ConfigEntryNotReady and setup will try again later
    #
    # If you do not want to retry setup on failure, use
    await coordinator.async_refresh()
    # Use this to keep retrying even if failed:
    #await coordinator.async_config_entry_first_refresh()

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)
    #await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
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

"""" Coordinator """
class Coordinator(DataUpdateCoordinator):
    """My custom coordinator."""

    def __init__(self, hass, api):
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="eForsyning_sensor",
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=MIN_TIME_BETWEEN_UPDATES,
        )
        self.api = api


    async def _async_update_data(self): # -> dict[str, dict[str, Any]]:
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        async def async_poll_api():
            # Poll non-async API here, grab the things I need from it, and set it to data
            data = await self.hass.async_add_executor_job(self.api.fetch_data)
            return data

        #async with async_timeout.timeout(10):
        #    return await async_poll_api()

#        # If the API returns exceptions, this would be the way to make it nice:
        try:
            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            async with async_timeout.timeout(10):
                return await async_poll_api()
        except Exception as err:
            _LOGGER.error(f"Error communicating with the API: {err}")
            # Propagate exception to parent to signal this failed.
            raise err


""" API for EForsyning.  Because of the @Throttle annotation it cannot live in the eforsyning module - but it should."""
from homeassistant.util import Throttle
import requests



## TODO: ERROR API is taken as a coordinator and needs async_add_listener() ????
class API:
    def __init__(self, username, password, supplierid, billing_period_skew, is_water_supply):
        self._client = Eforsyning(username, password, supplierid, billing_period_skew, is_water_supply)
        self.data = {}
        _LOGGER.debug("An eForsyning API class was created")

    #@Throttle(MIN_TIME_BETWEEN_UPDATES)
#    def update(self):
    def fetch_data(self):
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

