"""The Eforsyning integration."""
from __future__ import annotations
from custom_components.eforsyning.coordinator import EforsyningUpdateCoordinator

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN

# The eForsyning integration - not on PyPi, just bundled here.
# Contrary to:
# https://developers.home-assistant.io/docs/creating_component_code_review#4-communication-with-devicesservices
from custom_components.eforsyning.pyeforsyning.eforsyning import Eforsyning

# Development help
import logging
_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

#async def async_setup(hass: HomeAssistant, config: dict) -> bool:
#    """Set up the Novafos component if we want to do more before the async_setup_entry()"""
#      hass.data[DOMAIN] = {}
#    or
#      hass.data.setdefault(DOMAIN, {})
#    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Eforsyning from a config entry."""
    username = entry.data['username']
    password = entry.data['password']
    supplierid = entry.data['supplierid']
    entityname = entry.data['entityname']
    billing_period_skew = entry.data['billing_period_skew'] # This one is true if the billing period is from July to June
    is_water_supply = entry.data['is_water_supply'] # This one is true if the module is for eforsyning water delivery (false for regional heating)

    _LOGGER.debug(f"eForsyning ConfigData: {entry.data}")

    # Use the coordinator which handles regular fetch of API data.
    api = Eforsyning(username, password, supplierid, billing_period_skew, is_water_supply)
    coordinator = EforsyningUpdateCoordinator(hass, api, entry)
    # If you do not want to retry setup on failure, use
    #await coordinator.async_refresh()
    # This one repeats connecting to the API until first success.
    await coordinator.async_config_entry_first_refresh()

    # Add the HomeAssistant specific API to the eForsyning integration.
    # The Sensor entity in the integration will call function here to do its thing.
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator" : coordinator
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

async def async_migrate_entry(hass, config_entry: ConfigEntry) -> bool:
    """Handle migration of setup entry data from one version to the next."""
    _LOGGER.info("Migrating from version %s", config_entry.version)

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
