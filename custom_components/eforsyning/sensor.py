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
    #   Water - forward temperature
    #   Water - return temperature
    #   Water - Expected return temperature
    #   Water - Measured return temperature
    #   ENG1  - Start MWh
    #   ENG1  - End MWh
    #   ENG1  - Consumption MWh
    #   ENG1  - Expected consumption MWh
    #   ENG1  - Expected End MWh
    #   M3    - Start M3
    #   M3    - End M3
    #   M3    - Consumption M3
    #   M3    - Expected consumption M3
    #   M3    - Expected End M3
    # Extra data (don't know what this is):
    #   ENG2  - Start MWh
    #   ENG2  - End MWh
    #   ENG2  - Consumption MWh
    #   TV2  - Start MWh
    #   TV2  - End MWh
    #   TV2  - Consumption MWh
    # The daily datalog should only be one sensor reading.
    # So
    temp_series = {"forward", "return", "expected-return", "actual-return"}
    energy_series = {"start", "end", "used", "expected-used", "expected-end"}
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

    def __init__(self, name, sensor_point, sensor_unit, client):
        """Initialize the sensor."""
        self._state = None
        self._data_date = None
        self._data = client
        self._name = name
        self._sensor_type = sensor_type
        self-_unique_id = f"eforsyning-{sensor_unit}-{sensor_point}"

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

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
        if self._sensor_type == "energy":
            return "MWh"
        elif self._sensor_type == "water":
            return "m³"
        else:
            return TEMP_CELSIUS

    def update(self):
        """Fetch new state data for the sensor.
        This is the only method that should fetch new data for Home Assistant.
        """
        self._state = 100
        return
        self._data.update()        

        self._data_date = self._data.get_data_date()

        if self._sensor_type == 'total':
            self._state = self._data.get_total_day()
        else:
            self._state = self._data.get_usage_hour(self._hour)

