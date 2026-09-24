from unittest.mock import AsyncMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.eforsyning.const import DOMAIN


def test_integration_can_be_imported() -> None:
    # This is a deliberately cheap smoke test: pytest collects this file and
    # proves the integration package can be imported before HA starts it.
    assert DOMAIN == "eforsyning"


async def test_setup_entry_uses_mocked_api(hass, enable_custom_integrations) -> None:
    # MockConfigEntry is the test equivalent of an entry created in HA's UI.
    # Version 3 is the current entry version, so this test exercises setup
    # rather than the legacy migration path.
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=3,
        data={
            "username": "user",
            "password": "password",
            "supplierid": "supplier",
            "entityname": "Test heating",
            "billing_period_skew": False,
            "is_water_supply": True,
        },
    )
    entry.add_to_hass(hass)

    class FakeApi:
        # The integration calls these methods from an executor. The fake keeps
        # the same synchronous API while returning deterministic test data.
        def __init__(self, *args) -> None:
            pass

        def authenticate(self) -> bool:
            return True

        def get_latest(self) -> dict[str, float]:
            return {"water-start": 1.0}

    with (
        # The integration module imported Eforsyning directly, so patch that
        # module-level name with the fake client used by this setup test.
        patch("custom_components.eforsyning.Eforsyning", FakeApi),
        # Platform setup is a separate concern. Mock forwarding so the test
        # can inspect coordinator data without constructing every sensor.
        patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            new=AsyncMock(),
        ) as forward_setups,
    ):
        # async_setup loads the integration, creates the coordinator, performs
        # its first refresh, and stores it in hass.data.
        assert await hass.config_entries.async_setup(entry.entry_id)

    # The fake API result crossed the same coordinator boundary as real data.
    assert hass.data[DOMAIN][entry.entry_id]["coordinator"].data == {"water-start": 1.0}
    # AsyncMock records awaits, so this verifies that platform setup was handed
    # off exactly once after the coordinator became ready.
    forward_setups.assert_awaited_once()
