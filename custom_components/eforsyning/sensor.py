"""Platform for Eforsyning sensor integration."""
import logging
from homeassistant.const import TEMP_CELSIUS
from homeassistant.helpers.entity import Entity
from custom_components.eforsyning.pyeforsyning.eforsyning import Eforsyning
from custom_components.eforsyning.pyeforsyning.models import TimeSeries

_LOGGER = logging.getLogger(__name__)
from .const import DOMAIN



async def async_setup_entry(hass, config, async_add_entities):
    """Set up the sensor platform."""
    
    eforsyning = hass.data[DOMAIN][config.entry_id]

    ## Sensors for
    # Year, Month, Day? We'll fetch data once per day.
    #   Temp  - forward temperature
    #   Temp  - return temperature
    #   Temp  - Expected return temperature
    #   Temp  - Measured return temperature
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
    temp_series = {"forward", "return", "exp-return", "meas-return"}
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


class EforsyningEnergy(Entity):
    """Representation of a Sensor."""

    def __init__(self, name, sensor_point, sensor_type, client):
        """Initialize the sensor."""
        self._state = None
        self._data_date = None
        self._data = client
        self._name = name
        self._sensor_value = f"{sensor_type}-{sensor_point}"
        self._unique_id = f"eforsyning-{self._sensor_value}"
        if sensor_type == "energy":
            self._unit = "MWh"
            self._icon = "mdi:flash-circle"
        elif sensor_type == "water":
            self._unit = "m³"
            self._icon = "mdi:water"
        else:
            self._unit = TEMP_CELSIUS
            self._icon = "mdi:thermometer"


    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def icon(self):
        return self._icon

    @property
    def unique_id(self):
        """The unique id of the sensor."""
        return self._unique_id

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def device_state_attributes(self):
        """Return state attributes."""
        attributes = dict()
        attributes['Metering date'] = self._data_date
        attributes['metering_date'] = self._data_date
        
        return attributes

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        self._unit

    def update(self):
        """Fetch new state data for the sensor.
        This is the only method that should fetch new data for Home Assistant.
        """
        _LOGGER.debug(f"Updating data")

        self._data.update()        

        self._data_date = self._data.get_data_date()
        self._state = self._data.get_data()
        _LOGGER.debug(f"Done updating data")

