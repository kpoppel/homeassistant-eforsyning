from unittest.mock import Mock, patch

from custom_components.eforsyning.pyeforsyning.eforsyning import Eforsyning


def response(status_code: int, body: dict) -> Mock:
    # The API client only needs these two Response attributes in these tests.
    # A Mock lets us provide them without making an actual HTTP request.
    result = Mock()
    result.status_code = status_code
    result.json.return_value = body
    return result


def make_api() -> Eforsyning:
    # Keep credentials and other constructor arguments in one place so each
    # test focuses on the behavior it is trying to verify.
    return Eforsyning(
        username="user",
        password="password",
        supplierid="supplier",
        billing_period_skew=False,
        is_water_supply=False,
    )


def test_authenticate_uses_api_server_and_returns_true() -> None:
    api = make_api()

    # authenticate() makes three requests in order: find the supplier API
    # server, obtain a token, and log in. These responses replace that entire
    # network conversation. The list is consumed one item per requests.get().
    responses = [
        response(200, {"AppServerUri": "https://supplier.example/"}),
        response(200, {"Token": "server-token"}),
        response(200, {"Result": 1}),
    ]

    with patch(
        # Patch the name used by the module under test. Patching requests.get
        # globally would affect unrelated code and make the test less precise.
        "custom_components.eforsyning.pyeforsyning.eforsyning.requests.get",
        side_effect=responses,
    ) as get:
        # The context manager restores requests.get automatically afterwards.
        assert api.authenticate() is True

    # Calls made through a Mock are recorded. These assertions verify both the
    # number of network calls and that later URLs use the discovered server.
    assert get.call_count == 3
    assert (
        get.call_args_list[0].args[0].endswith("GetVaerkSettings?forsyningid=supplier")
    )
    assert get.call_args_list[1].args[0] == (
        "https://supplier.example/system/getsecuritytoken/project/app/consumer/user"
    )
    assert (
        "/system/login/project/app/consumer/user/installation/1/id/"
        in (get.call_args_list[2].args[0])
    )


def test_authenticate_returns_false_for_empty_token() -> None:
    api = make_api()

    # The first response is valid, but the empty token is an authentication
    # failure. This is a separate example of a short response sequence.
    responses = [
        response(200, {"AppServerUri": "https://supplier.example/"}),
        response(200, {"Token": ""}),
    ]

    with patch(
        "custom_components.eforsyning.pyeforsyning.eforsyning.requests.get",
        side_effect=responses,
    ):
        # No live service is contacted: every requests.get call receives one
        # of the Mock responses above.
        assert api.authenticate() is False


def test_installations_selects_configured_installation() -> None:
    # This test starts after authentication because _get_installations() only
    # needs the authenticated session values shown below. Keeping the setup
    # local avoids repeating the three-request authentication test here.
    api = make_api()
    api._user_id = "user-id"
    api._api_server = "https://supplier.example/"
    api._access_token = "access-token"
    api._x_session_id = "session"
    # InstallationNr is the stable value stored by the config flow. It must
    # select the matching API record rather than relying on list position.
    api._configured_installation_id = "22"

    # The API returns two installations. The second record is deliberately
    # selected so the test would fail if the implementation always used [0].
    installations = [
        {"InstallationNr": 11, "AktivNr": 111, "MålerNr": "meter-1"},
        {"InstallationNr": 22, "AktivNr": 222, "MålerNr": "meter-2"},
    ]
    with patch(
        # Mock only the installation request. The response shape mirrors the
        # production FindInstallationer response and prevents network access.
        "custom_components.eforsyning.pyeforsyning.eforsyning.requests.post",
        return_value=response(200, {"Installationer": installations}),
    ):
        result = api._get_installations()

    # Returning the complete list lets the config flow build its named select
    # options, while the client stores the selected installation and asset IDs
    # for subsequent consumption and billing requests.
    assert result == installations
    assert api._installation_id == "22"
    assert api._asset_id == "222"
