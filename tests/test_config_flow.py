from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import SOURCE_USER
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

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
        patch(
            "custom_components.eforsyning.config_flow.Eforsyning.get_installations",
            return_value=[
                {
                    "InstallationNr": 1,
                    "AktivNr": 10,
                    "MålerNr": "meter-1",
                    "Adresse": "Main Street 1",
                }
            ],
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

        # Credentials are validated before installations are fetched, so the
        # flow pauses on a second form instead of creating the entry immediately.
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "installation"
        # The selector schema accepts the stable InstallationNr value returned
        # by the API. Its label is supplied from the installation metadata.
        assert result["data_schema"]({"installation_id": "1"}) == {
            "installation_id": "1"
        }
        # Submitting the selection resumes the same flow and combines it with
        # the credentials and integration options from the first step.
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"installation_id": "1"}
        )

    # A successful flow returns a create-entry result containing the submitted
    # values, ready for Home Assistant to persist.
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Eforsyning supplier"
    assert result["data"] == {**user_input, "installation_id": "1"}


async def test_reconfigure_preserves_entity_identity(
    hass, enable_custom_integrations
) -> None:
    # Build an entry in the same state as an installation that has already
    # completed the identity migration. The stored identity is deliberately
    # different from the username/supplier combination so the test can detect
    # an accidental fallback to the old identity scheme.
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "username": "user",
            "password": "password",
            "supplierid": "supplier",
            "entityname": "Test heating",
            "billing_period_skew": False,
            "is_water_supply": False,
            "installation_id": "1",
            "entity_identity": "stable-entry-identity",
        },
        title="Eforsyning supplier",
        version=3,
    )
    # Register the entry with Home Assistant so _get_reconfigure_entry() can
    # resolve it when the reconfigure flow starts.
    await hass.config_entries.async_add(entry)

    with (
        # Reconfiguration validates credentials before showing the installation
        # selector. Patch authentication and installation retrieval so this
        # test covers flow state and persistence without making HTTP requests.
        patch(
            "custom_components.eforsyning.config_flow.Eforsyning.authenticate",
            return_value=True,
        ),
        # Completing a config flow normally reloads the integration. Mock the
        # setup callback because coordinator refreshes are outside this test.
        patch(
            "custom_components.eforsyning.config_flow.Eforsyning.get_installations",
            return_value=[
                {
                    "InstallationNr": 1,
                    "AktivNr": 10,
                    "MålerNr": "meter-1",
                    "Adresse": "Main Street 1",
                }
            ],
        ),
        patch(
            "custom_components.eforsyning.async_setup_entry",
            new_callable=AsyncMock,
            return_value=True,
        ),
    ):
        # Reconfigure is initiated for the registered entry and first displays
        # the credentials form, just as it would from Home Assistant's UI.
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": "reconfigure",
                "entry_id": entry.entry_id,
            },
            data={"entry_id": entry.entry_id},
        )
        # Submit the credentials. Successful validation advances the flow to
        # the second step where the user chooses an InstallationNr.
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                "username": "user",
                "password": "password",
                "supplierid": "supplier",
                "entityname": "Test heating",
                "billing_period_skew": False,
                "is_water_supply": False,
            },
        )
        # Submit the existing installation selection to complete reconfigure.
        await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"installation_id": "1"}
        )

    # Reconfigure must preserve an identity that was already migrated. If it
    # changed here, Home Assistant would see a new unique ID and create
    # duplicate sensors for the same installation.
    assert (
        hass.config_entries.async_get_entry(entry.entry_id).data["entity_identity"]
        == "stable-entry-identity"
    )
