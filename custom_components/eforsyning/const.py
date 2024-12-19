"""Constants for the Eforsyning integration."""
from __future__ import annotations
from typing import Final
from datetime import timedelta
# Get Sensor classification and unit definitions:
from homeassistant.components.sensor import SensorStateClass
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import UnitOfTemperature
from homeassistant.const import UnitOfEnergy
from homeassistant.const import UnitOfVolume

from .model import EforsyningSensorDescription

DOMAIN = "eforsyning"

# Default name for sensor prefix texts (possibly other things)
DEFAULT_NAME = "eForsyning"

###################################
## DEV NOTE: suggested_unit_of_measurement does not seem to have any effect on existing sensors
###################################

######################################################################
##  NOTICE ON FAIR USE:
##  Please do not set this constant below 15 minutes.
##  Softværket who runs the API will impose an IP-ban if fair use
##  is not adhered to.
##
##  The dataset is updated every 24 hours in the morning.
##  The default min. time is to spread out load on the API and still
##  retrieve data.
######################################################################
# Every 6 hours seems appropriate to get an update ready in the morning
MIN_TIME_BETWEEN_UPDATES = timedelta(hours=6)
# Smallest appropriate interval.  Only relevant for development use.
#MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=15)

# Sensors:
# NOTE: For ALL sensors it is NOT the current day number which is received.
#       If using the history graph the data shown will be from the past.
#       The attributes of the sensor will tell the correct date of the sensor.
#       Use this information with a template sensor or apexcharts data generator to get it right.
# *  Year Total (resets once per year)
#    The year total sensor will have attributes storing all data points (for apexcharts)
# *  Month Total (resets once per month) - attribute stating last valid data date
# *  Day Total for "last valid" -  attribute stating last valid data date
# *  Make an hourly "last valid" sensor which returns the data from the correct hour some days ago.
#    This should be for those not setting up Apexchards using the attributes.
HEATING_TEMP_SENSOR_TYPES: Final[tuple[EforsyningSensorDescription, ...]] = (
    EforsyningSensorDescription(
        key = "temp-forward",
        name = "Water Temperature forward",
        entity_registry_enabled_default = True,
        native_unit_of_measurement = UnitOfTemperature.CELSIUS,
        device_class = SensorDeviceClass.TEMPERATURE,
        icon = "mdi:thermometer",
        state_class = SensorStateClass.MEASUREMENT,
        attribute_data = "Temp-Forward"
    ),
    EforsyningSensorDescription(
        key = "temp-return",
        name = "Water Temperature return",
        entity_registry_enabled_default = True,
        native_unit_of_measurement = UnitOfTemperature.CELSIUS,
        device_class = SensorDeviceClass.TEMPERATURE,
        icon = "mdi:thermometer",
        state_class = SensorStateClass.MEASUREMENT,
        attribute_data = "Temp-Return"
    ),
    EforsyningSensorDescription(
        key = "temp-exp-return",
        name = "Water Temperature exp-return",
        entity_registry_enabled_default = True,
        native_unit_of_measurement = UnitOfTemperature.CELSIUS,
        device_class = SensorDeviceClass.TEMPERATURE,
        icon = "mdi:thermometer",
        state_class = SensorStateClass.MEASUREMENT,
        attribute_data = "Temp-ExpReturn"
    ),
    EforsyningSensorDescription(
        key = "temp-cooling",
        name = "Water Temperature cooling",
        entity_registry_enabled_default = True,
        native_unit_of_measurement = UnitOfTemperature.CELSIUS,
        device_class = SensorDeviceClass.TEMPERATURE,
        icon = "mdi:thermometer",
        state_class = SensorStateClass.MEASUREMENT,
        attribute_data = "Temp-Cooling"
    ),

    # Yearly sensors
    #-----------------
    # TODO: Note that this sensor will pull data froma dataset where cooling, expected values and more is present both for temperature, energy and water
    #       Improvement could be to add all of these sensors as well.  Another one to disable least used sensors by default (but which ones are they?)
    EforsyningSensorDescription(
        key = "temp-return-year",
        name = "Water Temperature return year-to-date",
        entity_registry_enabled_default = True,
        native_unit_of_measurement = UnitOfTemperature.CELSIUS,
        device_class = SensorDeviceClass.TEMPERATURE,
        icon = "mdi:thermometer",
        state_class = SensorStateClass.MEASUREMENT,
        attribute_data = None
    ),
)

HEATING_ENERGY_SENSOR_TYPES: Final[tuple[EforsyningSensorDescription, ...]] = (
    EforsyningSensorDescription(
        key = "energy-start",
        name = "Energy start",
        entity_registry_enabled_default = False,
        native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR,
        suggested_unit_of_measurement = UnitOfEnergy.MEGA_WATT_HOUR,
        device_class = SensorDeviceClass.ENERGY,
        icon = "mdi:lightning-bolt-circle",
        state_class = SensorStateClass.TOTAL_INCREASING,
        attribute_data = "kWh-Start"
    ),
    EforsyningSensorDescription(
        key = "energy-end",
        name = "Energy end",
        entity_registry_enabled_default = False,
        native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR,
        suggested_unit_of_measurement = UnitOfEnergy.MEGA_WATT_HOUR,
        device_class = SensorDeviceClass.ENERGY,
        icon = "mdi:lightning-bolt-circle",
        state_class = SensorStateClass.TOTAL_INCREASING,
        attribute_data = "kWh-End"
    ),
    EforsyningSensorDescription(
        key = "energy-used",
        name = "Energy used",
        entity_registry_enabled_default = True,
        native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR,
        device_class = SensorDeviceClass.ENERGY,
        icon = "mdi:lightning-bolt-circle",
        state_class = SensorStateClass.TOTAL,
        attribute_data = "kWh-Used"
    ),
    EforsyningSensorDescription(
        key = "energy-exp-used",
        name = "Energy exp-used",
        entity_registry_enabled_default = True,
        native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR,
        device_class = SensorDeviceClass.ENERGY,
        icon = "mdi:lightning-bolt-circle",
        state_class = SensorStateClass.TOTAL,
        attribute_data = "kWh-ExpUsed"
    ),
    EforsyningSensorDescription(
        key = "energy-exp-end",
        name = "Energy exp-end",
        entity_registry_enabled_default = False,
        native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR,
        suggested_unit_of_measurement = UnitOfEnergy.MEGA_WATT_HOUR,
        device_class = SensorDeviceClass.ENERGY,
        icon = "mdi:lightning-bolt-circle",
        state_class = SensorStateClass.TOTAL_INCREASING,
        attribute_data = "kWh-ExpEnd"
    ),
    EforsyningSensorDescription(
        key = "energy-total-used",
        name = "Energy total-used",
        entity_registry_enabled_default = True,
        native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR,
        suggested_unit_of_measurement = UnitOfEnergy.MEGA_WATT_HOUR,
        device_class = SensorDeviceClass.ENERGY,
        icon = "mdi:lightning-bolt-circle",
        state_class = SensorStateClass.TOTAL_INCREASING,
        attribute_data = None
    ),
    EforsyningSensorDescription(
        key = "energy-use-prognosis",
        name = "Energy use-prognosis",
        entity_registry_enabled_default = True,
        native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR,
        suggested_unit_of_measurement = UnitOfEnergy.MEGA_WATT_HOUR,
        device_class = SensorDeviceClass.ENERGY,
        icon = "mdi:lightning-bolt-circle",
        state_class = SensorStateClass.TOTAL,
        attribute_data = None
    ),
)

HEATING_WATER_SENSOR_TYPES: Final[tuple[EforsyningSensorDescription, ...]] = (
    EforsyningSensorDescription(
        key = "water-start",
        name = "Water start",
        entity_registry_enabled_default = False,
        native_unit_of_measurement = UnitOfVolume.CUBIC_METERS,
        device_class = SensorDeviceClass.WATER,
        icon = "mdi:water",
        state_class = SensorStateClass.TOTAL_INCREASING,
        attribute_data = "M3-Start"
    ),
    EforsyningSensorDescription(
        key = "water-end",
        name = "Water end",
        entity_registry_enabled_default = False,
        native_unit_of_measurement = UnitOfVolume.CUBIC_METERS,
        device_class = SensorDeviceClass.WATER,
        icon = "mdi:water",
        state_class = SensorStateClass.TOTAL_INCREASING,
        attribute_data = "M3-End"
    ),
    EforsyningSensorDescription(
        key = "water-used",
        name = "Water used",
        entity_registry_enabled_default = True,
        native_unit_of_measurement = UnitOfVolume.CUBIC_METERS,
        device_class = SensorDeviceClass.WATER,
        icon = "mdi:water",
        state_class = SensorStateClass.TOTAL,
        attribute_data = "M3-Used"
    ),
    EforsyningSensorDescription(
        key = "water-exp-used",
        name = "Water exp-used",
        entity_registry_enabled_default = True,
        native_unit_of_measurement = UnitOfVolume.CUBIC_METERS,
        device_class = SensorDeviceClass.WATER,
        icon = "mdi:water",
        state_class = SensorStateClass.TOTAL,
        attribute_data = "M3-ExpUsed"
    ),
    EforsyningSensorDescription(
        key = "water-exp-end",
        name = "Water exp-end",
        entity_registry_enabled_default = False,
        native_unit_of_measurement = UnitOfVolume.CUBIC_METERS,
        device_class = SensorDeviceClass.WATER,
        icon = "mdi:water",
        state_class = SensorStateClass.TOTAL_INCREASING,
        attribute_data = "M3-ExpEnd"
    ),
    EforsyningSensorDescription(
        key = "water-total-used",
        name = "Water total-used",
        entity_registry_enabled_default = True,
        native_unit_of_measurement = UnitOfVolume.CUBIC_METERS,
        device_class = SensorDeviceClass.WATER,
        icon = "mdi:water",
        state_class = SensorStateClass.TOTAL_INCREASING,
        attribute_data = None
    ),
    EforsyningSensorDescription(
        key = "water-use-prognosis",
        name = "Water use-prognosis",
        entity_registry_enabled_default = True,
        native_unit_of_measurement = UnitOfVolume.CUBIC_METERS,
        device_class = SensorDeviceClass.WATER,
        icon = "mdi:water",
        state_class = SensorStateClass.TOTAL,
        attribute_data = None
    ),
)

WATER_SENSOR_TYPES: Final[tuple[EforsyningSensorDescription, ...]] = (
    EforsyningSensorDescription(
        key = "water-start",
        name = "Water start",
        entity_registry_enabled_default = False,
        native_unit_of_measurement = UnitOfVolume.CUBIC_METERS,
        device_class = SensorDeviceClass.WATER,
        icon = "mdi:water",
        state_class = SensorStateClass.TOTAL_INCREASING,
        attribute_data = "Start",
        last_reset = None
    ),
    EforsyningSensorDescription(
        key = "water-end",
        name = "Water end",
        entity_registry_enabled_default = False,
        native_unit_of_measurement = UnitOfVolume.CUBIC_METERS,
        device_class = SensorDeviceClass.WATER,
        icon = "mdi:water",
        state_class = SensorStateClass.TOTAL_INCREASING,
        attribute_data = "End",
        last_reset = None
    ),
    EforsyningSensorDescription(
        key = "water-used",
        name = "Water used",
        entity_registry_enabled_default = True,
        native_unit_of_measurement = UnitOfVolume.CUBIC_METERS,
        device_class = SensorDeviceClass.WATER,
        icon = "mdi:water",
        state_class = SensorStateClass.MEASUREMENT,
        attribute_data = "Used",
        last_reset = None
    ),
    EforsyningSensorDescription(
        key = "water-exp-used",
        name = "Water exp-used",
        entity_registry_enabled_default = True,
        native_unit_of_measurement = UnitOfVolume.CUBIC_METERS,
        device_class = SensorDeviceClass.WATER,
        icon = "mdi:water",
        state_class = SensorStateClass.MEASUREMENT,
        attribute_data = "ExpUsed",
        last_reset = None
    ),
    EforsyningSensorDescription(
        key = "water-exp-end",
        name = "Water exp-end",
        entity_registry_enabled_default = False,
        native_unit_of_measurement = UnitOfVolume.CUBIC_METERS,
        device_class = SensorDeviceClass.WATER,
        icon = "mdi:water",
        state_class = SensorStateClass.TOTAL_INCREASING,
        attribute_data = "ExpEnd",
        last_reset = None
    ),
    EforsyningSensorDescription(
        key = "water-ytd-used",
        name = "Water ytd-used",
        entity_registry_enabled_default = True,
        native_unit_of_measurement = UnitOfVolume.CUBIC_METERS,
        device_class = SensorDeviceClass.WATER,
        icon = "mdi:water",
        state_class = SensorStateClass.TOTAL_INCREASING,
        attribute_data = None,
        last_reset = None
    ),
    EforsyningSensorDescription(
        key = "water-exp-ytd-used",
        name = "Water exp-ytd-used",
        entity_registry_enabled_default = True,
        native_unit_of_measurement = UnitOfVolume.CUBIC_METERS,
        device_class = SensorDeviceClass.WATER,
        icon = "mdi:water",
        state_class = SensorStateClass.TOTAL_INCREASING,
        attribute_data = None,
        last_reset = None
    ),
    EforsyningSensorDescription(
        key = "water-exp-fy-used",
        name = "Water exp-fy-used",
        entity_registry_enabled_default = True,
        native_unit_of_measurement = UnitOfVolume.CUBIC_METERS,
        device_class = SensorDeviceClass.WATER,
        icon = "mdi:water",
        state_class = SensorStateClass.TOTAL,
        attribute_data = None,
        last_reset = None
    ),
)

BILLING_SENSOR_TYPES: Final[tuple[EforsyningSensorDescription, ...]] = (
    EforsyningSensorDescription(
        key = "amount-remaining",
        name = "Amount remaining",
        entity_registry_enabled_default = True,
        native_unit_of_measurement = "kr",
        device_class = SensorDeviceClass.MONETARY,
        icon = "mdi:cash-100",
        state_class = SensorStateClass.TOTAL,
        attribute_data = None # This one has a separate data entry with attributes.
    ),
)
