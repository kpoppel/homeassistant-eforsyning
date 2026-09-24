from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import SOURCE_USER
from homeassistant.data_entry_flow import FlowResultType

from custom_components.eforsyning.const import DOMAIN


async def test_user_flow_creates_entry(hass, enable_custom_integrations) -> None:
    # `hass` and `enable_custom_integrations` are pytest fixtures injected by
    # pytest-homeassistant-custom-component. The first enables the async Home
    # Assistant test instance; the second lets it load this local integration.
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    # A config flow is interactive. Initialising it without input should show
    # the form, just as clicking "Add integration" does in the UI.
    assert result["type"] == "form"
    assert result["step_id"] == "user"

    # This dictionary is the same data a user would submit through the form.
    user_input = {
        "username": "user",
        "password": "password",
        "supplierid": "supplier",
        "entityname": "Test heating",
        "billing_period_skew": False,
        "is_water_supply": False,
    }
    with (
        # validate_input creates an Eforsyning object and calls authenticate().
        # Patch that method because this test is about the HA flow, not HTTP.
        patch(
            "custom_components.eforsyning.config_flow.Eforsyning.authenticate",
            return_value=True,
        ),
        # Creating a config entry normally starts integration setup. Mock that
        # async function so this test does not also refresh the coordinator.
        patch(
            "custom_components.eforsyning.async_setup_entry",
            new_callable=AsyncMock,
            return_value=True,
        ),
    ):
        # async_configure resumes the paused flow using its flow_id and input.
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=user_input
        )

    # A successful flow returns a create-entry result containing the submitted
    # values, ready for Home Assistant to persist.
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Eforsyning supplier"
    assert result["data"] == user_input
