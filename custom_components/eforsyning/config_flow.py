"""Config flow for Eforsyning integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.const import CONF_NAME

from .const import DEFAULT_NAME, DOMAIN

import logging
_LOGGER = logging.getLogger(__name__)

from custom_components.eforsyning.pyeforsyning.eforsyning import Eforsyning, LoginFailed, HTTPFailed

# Username/password are the ones for the website
# supplierID is found by following the README.md instruction
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("username") : str,
        vol.Required("password") : str,
        vol.Required("supplierid") : str,
        vol.Optional("entityname", default='EForsyning') : str,
        vol.Required("billing_period_skew", default=False) : bool,
        vol.Required("is_water_supply", default=False) : bool,
        #vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
    }
)

async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    # Returns True or False.  The API is not built for async operation
    # therefore it is wrapped in an async executor function.
    try:
        api = Eforsyning(data["username"], data["password"], data["supplierid"], data["billing_period_skew"], data["is_water_supply"])
        await hass.async_add_executor_job(api.authenticate)
    except LoginFailed:
        raise InvalidAuth
    except HTTPFailed:
        raise CannotConnect

    # Return info to store in the config entry.
    # title becomes the title on the integrations screen in the UI
    return {"title": f"Eforsyning {data['supplierid']}"}

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Eforsyning."""

    VERSION = 3
    
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        _LOGGER.debug(f"Setup Step User_input = {user_input}")

        try:
            info = await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""