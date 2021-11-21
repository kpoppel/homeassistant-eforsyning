"""Platform for Eforsyning sensor integration."""
import logging
from homeassistant.const import (TEMP_CELSIUS,
                                 DEVICE_CLASS_ENERGY, DEVICE_CLASS_TEMPERATURE,
                                 DEVICE_CLASS_GAS,
                                 ENERGY_MEGA_WATT_HOUR, VOLUME_CUBIC_METERS)
from homeassistant.components.sensor import (SensorEntity, STATE_CLASS_MEASUREMENT, STATE_CLASS_TOTAL,
                                            STATE_CLASS_TOTAL_INCREASING)
#from homeassistant.helpers.entity import Entity
from custom_components.eforsyning.pyeforsyning.eforsyning import Eforsyning
from custom_components.eforsyning.pyeforsyning.models import TimeSeries

_LOGGER = logging.getLogger(__name__)
from .const import DOMAIN



async def async_setup_entry(hass, config, async_add_entities):
    """Set up the sensor platform."""
    
    eforsyning = hass.data[DOMAIN][config.entry_id]

    ## Sensors far
    # Year, Month, Day? We'll fetch data once per day.
    # NOTE: Measurement type?
    #   measurement     : The current value, right now.
    #   total           : accumulated in/de-crease of a value. The absolute value is not interesting
    #   total_increasing: accumulated monotonically increasing value. The absolute value is not interesting
    # So, for a statistic where the daily, montly or yearly spend is more important than knowing the absolute value
    # then total or total_increasing is good for this.
    # For now well make all of it "measurement", and see how that goes.
    #
    #   Temp  - forward temperature
    #   Temp  - return temperature
    #   Temp  - Expected return temperature
    #   Temp  - Measured cooling temperature (difference between forward and return temperatures)
    #   ENG1  - Start MWh
    #   ENG1  - End MWh
    #   ENG1  - Consumption MWh
    #   ENG1  - Expected consumption MWh
    #   ENG1  - Expected End MWh
    #   Water - Start M3
    #   Water - End M3
    #   Water - Consumption M3
    #   Water - Expected consumption M3
    #   Water - Expected End M3
    # Extra data (don't know what this is):
    #   ENG2  - Start MWh
    #   ENG2  - End MWh
    #   ENG2  - Consumption MWh
    #   TV2  - Start MWh
    #   TV2  - End MWh
    #   TV2  - Consumption MWh
    # The daily datalog should only be one sensor reading.
    # So
    temp_series = {"forward", "return", "exp-return", "cooling"}
    energy_series = {"start", "end", "used", "exp-used", "exp-end"}
    sensors = []

    for s in temp_series:
        sensors.append(EforsyningEnergy(f"Eforsyning Water Temperature {s}", s, "temp", eforsyning))

    for s in energy_series:
        sensors.append(EforsyningEnergy(f"Eforsyning Energy {s}", s, "energy", eforsyning))

    for s in energy_series:
        sensors.append(EforsyningEnergy(f"Eforsyning Water {s}", s, "water", eforsyning))

    #sensors.append(EforsyningEnergy("", "", eforsyning))
    async_add_entities(sensors)


class EforsyningEnergy(SensorEntity):
    """Representation of a Sensor."""

    def __init__(self, name, sensor_point, sensor_type, client):
        """Initialize the sensor."""
        self._state = None
        self._data_date = None
        self._data = client

        self._attr_name = name

        self._sensor_value = f"{sensor_type}-{sensor_point}"
        self._attr_unique_id = f"eforsyning-{self._sensor_value}"
        if sensor_type == "energy":
            self._attr_native_unit_of_measurement = ENERGY_MEGA_WATT_HOUR
            self._attr_icon = "mdi:lightning-bolt-circle"
            self._attr_state_class = STATE_CLASS_TOTAL
            self._attr_device_class = DEVICE_CLASS_ENERGY
            self._attr_state_class = STATE_CLASS_MEASUREMENT #STATE_CLASS_TOTAL_INCREASING
        elif sensor_type == "water":
            self._attr_native_unit_of_measurement = VOLUME_CUBIC_METERS
            self._attr_icon = "mdi:water"
            self._attr_state_class = STATE_CLASS_MEASUREMENT #STATE_CLASS_TOTAL
            # Only gas can be measured in m3
            self._attr_device_class = DEVICE_CLASS_GAS
        else:
            self._attr_native_unit_of_measurement = TEMP_CELSIUS
            self._attr_icon = "mdi:thermometer"
            self._attr_device_class = DEVICE_CLASS_TEMPERATURE
            self._attr_state_class = STATE_CLASS_MEASUREMENT

    @property
    def device_state_attributes(self):
        """Return state attributes."""
        attributes = dict()
        attributes['Metering date'] = self._data_date
        attributes['metering_date'] = self._data_date
        return attributes

    def update(self):
        """Fetch new state data for the sensor.
        This is the only method that should fetch new data for Home Assistant.
        """
        _LOGGER.debug(f"Setting status for {self._attr_name}")

        self._data.update()        

        self._data_date = self._data.get_data_date()
        self._attr_native_value = self._data.get_data(self._sensor_value)
        _LOGGER.debug(f"Done setting status for {self._attr_name} = {self._attr_native_value} {self._attr_native_unit_of_measurement}")

