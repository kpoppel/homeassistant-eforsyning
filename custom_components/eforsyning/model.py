"""Type definitions for Novafos integration."""
from __future__ import annotations

from dataclasses import dataclass
from homeassistant.components.sensor import SensorEntityDescription

@dataclass
class EforsyningSensorDescription(SensorEntityDescription):
    """Class describing Novafos sensor entities.
       See: https://github.com/home-assistant/core/blob/b6f432645d7bc6b4947a20afa28647eb1515e4f8/homeassistant/components/sensor/__init__.py#L214

       Things to set:
         key (str)
         device_class (EntityCategory)
         entity_registry_enabled_default (bool)
         force_update: bool = False
         icon: str | None = None
         name: str | None = None
         device_class: SensorDeviceClass | str | None = None
         native_unit_of_measurement: str | None = None
         state_class: SensorStateClass | str | None = None

      And our own if we so like:
        my_parameter: str | None = None
    """
    attribute_data: str | None = None


