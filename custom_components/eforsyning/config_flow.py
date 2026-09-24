"""Config flow for Eforsyning integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlowResult
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector
from .const import DOMAIN, DEFAULT_NAME

from custom_components.eforsyning.pyeforsyning.eforsyning import (
    Eforsyning,
    LoginFailed,
    HTTPFailed,
)

import logging

_LOGGER = logging.getLogger(__name__)


# Username/password are the ones for the website
# supplierID is found by following the README.md instruction
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("username"): str,
        vol.Required("password"): str,
        vol.Required("supplierid"): str,
        vol.Optional("entityname", default="EForsyning"): str,
        vol.Required("billing_period_skew", default=False): bool,
        vol.Required("is_water_supply", default=False): bool,
        # vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    # Returns True or False.  The API is not built for async operation
    # therefore it is wrapped in an async executor function.
    try:
        api = Eforsyning(
            data["username"],
            data["password"],
            data["supplierid"],
            data["billing_period_skew"],
            data["is_water_supply"],
        )
        if not await hass.async_add_executor_job(api.authenticate):
            raise InvalidAuth
        installations = await hass.async_add_executor_job(api.get_installations)
    except LoginFailed:
        raise InvalidAuth
    except HTTPFailed:
        raise CannotConnect

    # Return info to store in the config entry.
    # title becomes the title on the integrations screen in the UI
    return {
        "title": f"Eforsyning {data['supplierid']}",
        "installations": installations,
    }


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Eforsyning."""

    VERSION = 3

    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def _installation_schema(self, default: str | None = None) -> vol.Schema:
        """Build a selector from the installations returned by the API."""
        options: list[selector.SelectOptionDict] = [
            selector.SelectOptionDict(
                value=str(installation["InstallationNr"]),
                label=(
                    f"{installation.get('Adresse', 'Unknown address')} - "
                    f"Meter {installation.get('MålerNr', 'unknown')} "
                    f"(installation {installation['InstallationNr']})"
                ),
            )
            for installation in self._installations
        ]
        return vol.Schema(
            {
                vol.Required(
                    "installation_id",
                    default=default or options[0]["value"],
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=options)
                )
            }
        )

    async def async_step_installation(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user select which installation this entry represents."""
        if user_input is None:
            return self.async_show_form(
                step_id="installation",
                data_schema=self._installation_schema(
                    self._pending_data.get("installation_id")
                ),
            )

        data = {**self._pending_data, **user_input}
        if self._pending_entry is None:
            return self.async_create_entry(
                title=self._pending_info["title"],
                data=data,
            )

        self.hass.config_entries.async_update_entry(
            self._pending_entry,
            title=self._pending_info["title"],
        )
        return self.async_update_reload_and_abort(
            self._pending_entry,
            data_updates=data,
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
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
            self._installations = info["installations"]
            self._pending_data = user_input
            self._pending_info = info
            self._pending_entry = None
            return await self.async_step_installation()

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration of an existing entry."""
        entry = self._get_reconfigure_entry()

        data_schema = vol.Schema(
            {
                vol.Required(
                    "username",
                    default=entry.data.get("username", ""),
                ): str,
                vol.Required(
                    "password",
                    default=entry.data.get("password", ""),
                ): str,
                vol.Required(
                    "supplierid",
                    default=entry.data.get("supplierid", ""),
                ): str,
                vol.Optional(
                    "entityname",
                    default=entry.data.get("entityname", "EForsyning"),
                ): str,
                vol.Required(
                    "billing_period_skew",
                    default=entry.data.get("billing_period_skew", False),
                ): bool,
                vol.Required(
                    "is_water_supply",
                    default=entry.data.get("is_water_supply", False),
                ): bool,
            }
        )

        if user_input is None:
            return self.async_show_form(
                step_id="reconfigure",
                data_schema=data_schema,
            )

        errors: dict[str, str] = {}

        try:
            info = await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception:
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            self._installations = info["installations"]
            selected_installation_id = entry.data.get("installation_id")
            existing_identity = entry.data.get("entity_identity") or (
                entry.entry_id
                if "installation_id" in entry.data
                else f"{entry.data.get('username')}-{entry.data.get('supplierid')}"
            )
            self._pending_data = {
                **user_input,
                "installation_id": selected_installation_id,
                "entity_identity": existing_identity,
            }
            self._pending_info = info
            self._pending_entry = entry
            return await self.async_step_installation()

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=data_schema,
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
