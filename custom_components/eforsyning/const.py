"""Constants for the Eforsyning integration."""
from __future__ import annotations
from typing import Final
from datetime import timedelta
from homeassistant.const import (TEMP_CELSIUS,
                                 DEVICE_CLASS_ENERGY, DEVICE_CLASS_TEMPERATURE,
                                 DEVICE_CLASS_GAS, DEVICE_CLASS_MONETARY,
                                 ENERGY_KILO_WATT_HOUR, VOLUME_CUBIC_METERS)
from homeassistant.components.sensor import STATE_CLASS_MEASUREMENT

from .model import EforsyningSensorDescription

DOMAIN = "eforsyning"

# Default name for sensor prefix texts (possibly other things)
DEFAULT_NAME = "eForsyning"

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
        native_unit_of_measurement = TEMP_CELSIUS,
        device_class = DEVICE_CLASS_TEMPERATURE,
        icon = "mdi:thermometer",
        state_class = STATE_CLASS_MEASUREMENT,
        attribute_data = "Temp-Forward"
    ),
    EforsyningSensorDescription(
        key = "temp-return",
        name = "Water Temperature return",
        entity_registry_enabled_default = True,
        native_unit_of_measurement = TEMP_CELSIUS,
        device_class = DEVICE_CLASS_TEMPERATURE,
        icon = "mdi:thermometer",
        state_class = STATE_CLASS_MEASUREMENT,
        attribute_data = "Temp-Return"
    ),
    EforsyningSensorDescription(
        key = "temp-exp-return",
        name = "Water Temperature exp-return",
        entity_registry_enabled_default = True,
        native_unit_of_measurement = TEMP_CELSIUS,
        device_class = DEVICE_CLASS_TEMPERATURE,
        icon = "mdi:thermometer",
        state_class = STATE_CLASS_MEASUREMENT,
        attribute_data = "Temp-ExpReturn"
    ),
    EforsyningSensorDescription(
        key = "temp-cooling",
        name = "Water Temperature cooling",
        entity_registry_enabled_default = True,
        native_unit_of_measurement = TEMP_CELSIUS,
        device_class = DEVICE_CLASS_TEMPERATURE,
        icon = "mdi:thermometer",
        state_class = STATE_CLASS_MEASUREMENT,
        attribute_data = "Temp-Cooling"
    ),
)

HEATING_ENERGY_SENSOR_TYPES: Final[tuple[EforsyningSensorDescription, ...]] = (
    EforsyningSensorDescription(
        key = "energy-start",
        name = "Energy start",
        entity_registry_enabled_default = True,
        native_unit_of_measurement = ENERGY_KILO_WATT_HOUR,
        device_class = DEVICE_CLASS_ENERGY,
        icon = "mdi:lightning-bolt-circle",
        state_class = STATE_CLASS_MEASUREMENT,
        attribute_data = "kWh-Start"
    ),
    EforsyningSensorDescription(
        key = "energy-end",
        name = "Energy end",
        entity_registry_enabled_default = True,
        native_unit_of_measurement = ENERGY_KILO_WATT_HOUR,
        device_class = DEVICE_CLASS_ENERGY,
        icon = "mdi:lightning-bolt-circle",
        state_class = STATE_CLASS_MEASUREMENT,
        attribute_data = "kWh-End"
    ),
    EforsyningSensorDescription(
        key = "energy-used",
        name = "Energy used",
        entity_registry_enabled_default = True,
        native_unit_of_measurement = ENERGY_KILO_WATT_HOUR,
        device_class = DEVICE_CLASS_ENERGY,
        icon = "mdi:lightning-bolt-circle",
        state_class = STATE_CLASS_MEASUREMENT,
        attribute_data = "kWh-Used"
    ),
    EforsyningSensorDescription(
        key = "energy-exp-used",
        name = "Energy exp-used",
        entity_registry_enabled_default = True,
        native_unit_of_measurement = ENERGY_KILO_WATT_HOUR,
        device_class = DEVICE_CLASS_ENERGY,
        icon = "mdi:lightning-bolt-circle",
        state_class = STATE_CLASS_MEASUREMENT,
        attribute_data = "kWh-ExpUsed"
    ),
    EforsyningSensorDescription(
        key = "energy-exp-end",
        name = "Energy exp-end",
        entity_registry_enabled_default = True,
        native_unit_of_measurement = ENERGY_KILO_WATT_HOUR,
        device_class = DEVICE_CLASS_ENERGY,
        icon = "mdi:lightning-bolt-circle",
        state_class = STATE_CLASS_MEASUREMENT,
        attribute_data = "kWh-ExpEnd"
    ),
    EforsyningSensorDescription(
        key = "energy-total-used",
        name = "Energy total-used",
        entity_registry_enabled_default = True,
        native_unit_of_measurement = ENERGY_KILO_WATT_HOUR,
        device_class = DEVICE_CLASS_ENERGY,
        icon = "mdi:lightning-bolt-circle",
        state_class = STATE_CLASS_MEASUREMENT,
        attribute_data = None
    ),
    EforsyningSensorDescription(
        key = "energy-use-prognosis",
        name = "Energy use-prognosis",
        entity_registry_enabled_default = True,
        native_unit_of_measurement = ENERGY_KILO_WATT_HOUR,
        device_class = DEVICE_CLASS_ENERGY,
        icon = "mdi:lightning-bolt-circle",
        state_class = STATE_CLASS_MEASUREMENT,
        attribute_data = None
    ),
)

HEATING_WATER_SENSOR_TYPES: Final[tuple[EforsyningSensorDescription, ...]] = (
    EforsyningSensorDescription(
        key = "water-start",
        name = "Water start",
        entity_registry_enabled_default = True,
        native_unit_of_measurement = VOLUME_CUBIC_METERS,
        device_class = DEVICE_CLASS_GAS,
        icon = "mdi:water",
        state_class = STATE_CLASS_MEASUREMENT,
        attribute_data = "M3-Start"
    ),
    EforsyningSensorDescription(
        key = "water-end",
        name = "Water end",
        entity_registry_enabled_default = True,
        native_unit_of_measurement = VOLUME_CUBIC_METERS,
        device_class = DEVICE_CLASS_GAS,
        icon = "mdi:water",
        state_class = STATE_CLASS_MEASUREMENT,
        attribute_data = "M3-End"
    ),
    EforsyningSensorDescription(
        key = "water-used",
        name = "Water used",
        entity_registry_enabled_default = True,
        native_unit_of_measurement = VOLUME_CUBIC_METERS,
        device_class = DEVICE_CLASS_GAS,
        icon = "mdi:water",
        state_class = STATE_CLASS_MEASUREMENT,
        attribute_data = "M3-Used"
    ),
    EforsyningSensorDescription(
        key = "water-exp-used",
        name = "Water exp-used",
        entity_registry_enabled_default = True,
        native_unit_of_measurement = VOLUME_CUBIC_METERS,
        device_class = DEVICE_CLASS_GAS,
        icon = "mdi:water",
        state_class = STATE_CLASS_MEASUREMENT,
        attribute_data = "M3-ExpUsed"
    ),
    EforsyningSensorDescription(
        key = "water-exp-end",
        name = "Water exp-end",
        entity_registry_enabled_default = True,
        native_unit_of_measurement = VOLUME_CUBIC_METERS,
        device_class = DEVICE_CLASS_GAS,
        icon = "mdi:water",
        state_class = STATE_CLASS_MEASUREMENT,
        attribute_data = "M3-ExpEnd"
    ),
    EforsyningSensorDescription(
        key = "water-total-used",
        name = "Water total-used",
        entity_registry_enabled_default = True,
        native_unit_of_measurement = VOLUME_CUBIC_METERS,
        device_class = DEVICE_CLASS_GAS,
        icon = "mdi:water",
        state_class = STATE_CLASS_MEASUREMENT,
        attribute_data = None
    ),
    EforsyningSensorDescription(
        key = "water-use-prognosis",
        name = "Water use-prognosis",
        entity_registry_enabled_default = True,
        native_unit_of_measurement = VOLUME_CUBIC_METERS,
        device_class = DEVICE_CLASS_GAS,
        icon = "mdi:water",
        state_class = STATE_CLASS_MEASUREMENT,
        attribute_data = None
    ),
)

WATER_SENSOR_TYPES: Final[tuple[EforsyningSensorDescription, ...]] = (
    EforsyningSensorDescription(
        key = "water-start",
        name = "Water start",
        entity_registry_enabled_default = True,
        native_unit_of_measurement = VOLUME_CUBIC_METERS,
        device_class = DEVICE_CLASS_GAS,
        icon = "mdi:water",
        state_class = STATE_CLASS_MEASUREMENT,
        attribute_data = "Start"
    ),
    EforsyningSensorDescription(
        key = "water-end",
        name = "Water end",
        entity_registry_enabled_default = True,
        native_unit_of_measurement = VOLUME_CUBIC_METERS,
        device_class = DEVICE_CLASS_GAS,
        icon = "mdi:water",
        state_class = STATE_CLASS_MEASUREMENT,
        attribute_data = "End"
    ),
    EforsyningSensorDescription(
        key = "water-used",
        name = "Water used",
        entity_registry_enabled_default = True,
        native_unit_of_measurement = VOLUME_CUBIC_METERS,
        device_class = DEVICE_CLASS_GAS,
        icon = "mdi:water",
        state_class = STATE_CLASS_MEASUREMENT,
        attribute_data = "Used"
    ),
    EforsyningSensorDescription(
        key = "water-exp-used",
        name = "Water exp-end",
        entity_registry_enabled_default = True,
        native_unit_of_measurement = VOLUME_CUBIC_METERS,
        device_class = DEVICE_CLASS_GAS,
        icon = "mdi:water",
        state_class = STATE_CLASS_MEASUREMENT,
        attribute_data = "ExpUsed"
    ),
    EforsyningSensorDescription(
        key = "water-exp-end",
        name = "Water exp-end",
        entity_registry_enabled_default = True,
        native_unit_of_measurement = VOLUME_CUBIC_METERS,
        device_class = DEVICE_CLASS_GAS,
        icon = "mdi:water",
        state_class = STATE_CLASS_MEASUREMENT,
        attribute_data = "ExpEnd"
    ),
    EforsyningSensorDescription(
        key = "water-ytd-used",
        name = "Water ytd-used",
        entity_registry_enabled_default = True,
        native_unit_of_measurement = VOLUME_CUBIC_METERS,
        device_class = DEVICE_CLASS_GAS,
        icon = "mdi:water",
        state_class = STATE_CLASS_MEASUREMENT,
        attribute_data = None
    ),
    EforsyningSensorDescription(
        key = "water-exp-ytd-used",
        name = "Water exp-ytd-used",
        entity_registry_enabled_default = True,
        native_unit_of_measurement = VOLUME_CUBIC_METERS,
        device_class = DEVICE_CLASS_GAS,
        icon = "mdi:water",
        state_class = STATE_CLASS_MEASUREMENT,
        attribute_data = None
    ),
    EforsyningSensorDescription(
        key = "water-exp-fy-used",
        name = "Water exp-fy-used",
        entity_registry_enabled_default = True,
        native_unit_of_measurement = VOLUME_CUBIC_METERS,
        device_class = DEVICE_CLASS_GAS,
        icon = "mdi:water",
        state_class = STATE_CLASS_MEASUREMENT,
        attribute_data = None
    ),
)

BILLING_SENSOR_TYPES: Final[tuple[EforsyningSensorDescription, ...]] = (
    EforsyningSensorDescription(
        key = "amount-remaining",
        name = "Amount remaining",
        entity_registry_enabled_default = True,
        native_unit_of_measurement = "kr",
        device_class = DEVICE_CLASS_MONETARY,
        icon = "mdi:cash-100",
        state_class = STATE_CLASS_MEASUREMENT,
        attribute_data = None # This one has a separate data entry with attributes.
    ),
)
