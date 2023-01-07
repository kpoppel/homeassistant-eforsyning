"""Platform for Eforsyning sensor integration."""
from __future__ import annotations
from typing import Any, cast
#from datetime import datetime

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
#from homeassistant.const import CONF_NAME
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

import logging
_LOGGER = logging.getLogger(__name__)

from .const import DOMAIN, WATER_SENSOR_TYPES, HEATING_TEMP_SENSOR_TYPES, HEATING_ENERGY_SENSOR_TYPES, HEATING_WATER_SENSOR_TYPES, BILLING_SENSOR_TYPES
from .model import EforsyningSensorDescription

import uuid

async def async_setup_entry(
    hass:HomeAssistant,
    config:ConfigEntry,
    async_add_entities:AddEntitiesCallback) -> None:
    """Set up the sensor platform."""
    # Use the name for the unique id of each sensor. eforsyning_<supplierid>?
    #name: str = config.data[CONF_NAME]
    name: str = config.data['entityname']
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][config.entry_id]["coordinator"]
    # coordinator has a 'data' field.  This is set to the returned API data value.
    # _async_update_data updates the field.
    # From this field the sensors will get their values afterwards.

    # What data is available here:
    #_LOGGER.fatal(f"Config: {config.as_dict()}")
    
    ## Sensors so far for regional heating data:
    # Year, Month, Day? We'll fetch data once per day.
    # NOTE: Measurement type?
    #   measurement     : The current value, right now.
    #   total           : accumulated in/de-crease of a value. The absolute value is not interesting
    #                     Can be "manually" reset using "last_reset".  Maybe this is useful here along with
    #                     the billing period.
    #   total_increasing: accumulated monotonically increasing value. The absolute value is not interesting
    #                     Also a decreasing value automatically becomes a signal that a new metering cycle has begun.
    # So, for a statistic where the daily, montly or yearly spend is more important than knowing the absolute value
    # then total or total_increasing is good for this.
    # For now well make all of it "measurement", and see how that goes.
    #
    # As the data looks like, the metering data never resets, warranting a "total" + "last_reset" method on the billing date.
    # Using this type makes it possible to follow the use of water and energy rather than the total meter value.
    # Perhaps just make another sensor with this property, so both absolute and aggregated is available (if the other data is not stored)
    #
    #   Temp  - forward temperature (actual measurement)
    #   Temp  - return temperature (actual measurement)
    #   Temp  - Expected return temperature (forecast actual measurement)
    #   Temp  - Measured cooling temperature (difference between forward and return temperatures) (calculation of actual)
    #   ENG1  - Start MWh (absolute)
    #   ENG1  - End MWh (absolute)
    #   ENG1  - Consumption MWh (positive increase)
    #   ENG1  - Expected consumption MWh (forecast positive increase)
    #   ENG1  - Expected End MWh (forecast of absolute)
    #   Water - Start M3 (absolute)
    #   Water - End M3 (asolute)
    #   Water - Consumption M3 (positive increase)
    #   Water - Expected consumption M3 (forecast positive increase)
    #   Water - Expected End M3 (forecast absolute)
    # Extra data (don't know what this is):
    #   ENG2  - Start MWh
    #   ENG2  - End MWh
    #   ENG2  - Consumption MWh
    #   TV2  - Start MWh
    #   TV2  - End MWh
    #   TV2  - Consumption MWh
    # The daily datalog should only be one sensor reading.
    #
    #
    # For Water metering a different set of sensors are necessary:
    #
    #   Water - Start M3 (absolute)
    #   Water - End M3 (absolute)
    #   Water - Consumption M3 (positive increase)
    #   Water - Expected End M3 (forecast absolute)
    #   Water - Total consumption M3 since last billing period (positive increase)
    #   Water - Expected Full Year End Total M3 (forecast positive increase)
    #   Water - Expected Year To Date consumption (positive increase) - This one needs to be calculated from the data.
    #
    # In the JSON these are the data points:
    #   ForbrugsLinjer.TForbrugsLinje[last].TForbrugsTaellevaerk[0].Slut|Start|Forbrug
    #   ForbrugsLinjer.TForbrugsLinje[last].ForventetAflaesningM3|ForventetForbrugM3
    #   IaltLinje.TForbrugsTaellevaerk[0].Forbrug
    #   IaltLinje.ForventetForbrugM3
    #   ForbrugsLinjer.TForbrugsLinje[last].ForventetAflaesningM3 - ForbrugsLinjer.TForbrugsLinje[0].ForventetAflaesningM3

    # The sensors are defined in the const.py file
    sensors: list[EforsyningSensor] = []
    if(config.data['is_water_supply']):
        for description in WATER_SENSOR_TYPES:
            sensors.append(EforsyningSensor(name, coordinator, description, config))
    else:
        for description in HEATING_TEMP_SENSOR_TYPES:
            sensors.append(EforsyningSensor(name, coordinator, description, config))
        for description in HEATING_ENERGY_SENSOR_TYPES:
            sensors.append(EforsyningSensor(name, coordinator, description, config))
        for description in HEATING_WATER_SENSOR_TYPES:
            sensors.append(EforsyningSensor(name, coordinator, description, config))
        for description in BILLING_SENSOR_TYPES:
            sensors.append(EforsyningSensor(name, coordinator, description, config))

    async_add_entities(sensors)


class EforsyningSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Sensor.
       An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available
    """
    entity_description: EforsyningSensorDescription

    def __init__(self, name, coordinator, description, config):
        """Initialise the coordinator"""
        super().__init__(coordinator)

        """Initialize the sensor."""
        self.entity_description = description
        self._attrs: dict[str, Any] = {}

        _LOGGER.debug(f"Registering Sensor for {self.entity_description.name}")

        self._attr_name = f"{name} {description.name}"
        # Select a uuid based in username and supplierid as more instances can be loaded
        my_uuid = str(uuid.uuid3(uuid.NAMESPACE_URL, f"{config.data['username']}-{config.data['supplierid']}"))
        self._attr_unique_id = f"eforsyning-{my_uuid}-{description.key}"

        # Note: Data is stored in self.coordinator.data

    @property
    def extra_state_attributes(self):
        """Return extra state attributes.
           Filter attributes so they are relevant for the individual sensor.
        """
        self._attrs = {}
        if self.coordinator.data:
            if self.entity_description.key == "amount-remaining":
                self._attrs["data"] = self.coordinator.data["billing"]
            elif self.entity_description.key == "temp-return-year":
                self._attrs["data"] = self.coordinator.data["year"]
            elif self.entity_description.attribute_data:
                self._attrs["data"] = []
                for data_point in self.coordinator.data["data"]:
                    self._attrs["data"].append({
                        "date" : data_point["DateTo"],
                        "value" : data_point[self.entity_description.attribute_data],
                    })

        return self._attrs

    @property
    def native_value(self) -> StateType:
        if self.coordinator.data:
            return cast(float, self.coordinator.data[self.entity_description.key])
        else:
            return None
