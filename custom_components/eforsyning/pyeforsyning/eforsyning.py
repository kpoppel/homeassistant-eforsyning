'''
Primary public module for eforsyning.dk API wrapper.
'''
from datetime import datetime
from datetime import timedelta
import json
import requests
import logging
import hashlib
from .models import RawResponse
from .models import TimeSeries

# Test
import random

_LOGGER = logging.getLogger(__name__)

class Eforsyning:
    '''
    Primary exported interface for eforsyning.dk API wrapper.
    '''
    def __init__(self, username, password, supplierid, billing_period_skew):
        self._username = username
        self._password = password
        self._supplierid = supplierid
        self._billing_period_skew = billing_period_skew
        self._base_url = 'https://eforsyning.dk/'
        self._api_server = ""
        ## Assume people only have a single metering device.
        ## Feel free to expand the code to find all metering devices
        ## and iterate over them.
        ## Must be a string - see where it is used.
        self._asset_id = "1"
        self._installation_id = "1"

    def _get_ebrugerid(self, access_token):
        '''
        This method returns the "ebrugerid" which is different from the username.
        This id is used to get the installations.
        Parameter "id" in the returned data is the ebrugerid
        '''
        _LOGGER.debug(f"Getting userinfo from API (ebrugerinfo)")
        userinfoURL = self._api_server + "api/getebrugerinfo?id=" + access_token
        _LOGGER.debug(f"Trying: {userinfoURL}")
        result = requests.get(userinfoURL,
                                timeout = 5
                              )
        # Instead of converting with result.json() this is also possible:
        #    euser_id = str(result_dict['id'])

        result_json = result.json()

        _LOGGER.debug(f"Response from userinfo API. ebrugerinfo: {result.status_code}, Body: {result.text}, ebruger: {result_json['id']}")

        return result_json['id']

    def _get_intallations(self, access_token):
        '''
        Get the installations to set installation_id and asset_id
        Restriction:  We will find the first installation_id == 1 and
        extract the asset_id from this only.
        TODO: Consider enumeration of installations, or make a field in the
        configuration to set the metering number, which is tied to the
        installation_id and asset_id in the API.
        This implementation is the path of least effort, so be warned about this.
        '''
        # https://api2.dff-edb.dk/kongerslev/api/FindInstallationer?id=fec53bccc22d0d92a9ab7e439188bd3f
        _LOGGER.debug(f"Getting installations at supplier: {self._supplierid}")
 
        ebrugerid = self._get_ebrugerid(access_token)

        ## Get the URL to the REST API service
        installationsURL=self._api_server + "api/FindInstallationer?id=" + access_token
        _LOGGER.debug(f"Trying: {installationsURL}")
        data = {
                "Soegetekst": "",
                "Skip": "0",
                "Take": "10000",
                "EBrugerId": ebrugerid,
                "Huskeliste": "null",
                "MedtagTilknyttede": "true"
                }

        headers = self._create_headers()

        result = requests.post(installationsURL,
                                data = json.dumps(data),
                                timeout = 5,
                                headers=headers
                              )

        _LOGGER.debug(f"Response from API. Status: {result.status_code}, Body: {result.text}")

        result_json = result.json()
        # Data looks like this:
        #{"Installationer":[
        #  {"EjendomNr":<int>,
        #   "Adresse":"<str>",
        #   "InstallationNr":<int>,
        #   "ForbrugerNr":"<int>",
        #   "MålerNr":"<int>",
        #   "By":"<str>",
        #   "PostNr":"<int>",
        #   "AktivNr":<int>,
        #   "Målertype":"<str>"
        #  }
        # ]}
        result_json = result.json()
        installations = result_json['Installationer'][0]
        self._installation_id = str(installations['InstallationNr'])
        self._asset_id = str(installations['AktivNr'])

        _LOGGER.debug(f"Done getting installatons[0] {installations}")

        return installations

    def _get_time_series(self,
                        from_date=None,
                        to_date=None,
                        year = "0",
                        month = False,
                        day = False,
                        include_expected_reading = True
                       ):
        '''
        Call time series API on eforsyning.dk. Defaults to yesterdays data.
        NOTE: The API service actually don't care about the dates at this point in time.
              Regardless of what we ask for, all data in the requested resolution
              (Year, Monthly, Daily) is returned.  This means requesting daily data
              will return a massive array of 365'is data points!
        '''
        _LOGGER.debug(f"Getting time series")

        if from_date is None:
            from_date = datetime.now()-timedelta(days=1)
        if to_date is None:
            to_date = datetime.now()

        access_token = self._get_access_token()

        self._get_intallations(access_token)

        date_format = '%d-%m-%Y'
        parsed_from_date = from_date.strftime(date_format)
        parsed_to_date = to_date.strftime(date_format)

        headers = self._create_headers()

        post_meter_data_url = "api/getforbrug?id="+access_token+"&unr="+self._username+"&anr="+self._asset_id+"&inr="+self._installation_id # POST

        include_data_in_between = "false"
        if month or day:
            include_data_in_between = "true"

        data_filter = "afMaanedsvis"
        data_average = "false"
        if day:
            data_filter = "afDagsvis"
            data_average = "true"

        data_exp_read = "false"
        if include_expected_reading:
            data_exp_read = "true"

        data = {
                "Ejendomnr":self._username,
                "AktivNr":self._asset_id,
                "I_Nr":self._installation_id,
                "AarsMaerke":year,
                "ForbrugsAfgraensning_FraDato":parsed_from_date,
                "ForbrugsAfgraensning_TilDato":parsed_to_date,
                "ForbrugsAfgraensning_FraAflaesning":"0",
                "ForbrugsAfgraensning_TilAflaesning":"2",
                "ForbrugsAfgraensning_MedtagMellemliggendeMellemaflas":include_data_in_between, ## true || false

                "Optioner":"foBestemtBeboer, foSkabDetaljer, foMedtagWebAflaes",
                "AHoejDetail":"false", ## true || false

                "Aflaesningsfilter":data_filter, ## afMaanedsvis || afDagsvis || afUfiltreret
                "AflaesningsFilterDag":"ULTIMO",
                "AflaesningsUdjaevning":data_average, ## true || false (Create interpolated data it seems)

                "SletFiltreredeAflaesninger":"true", ## true || false (Get rid of filtered data?)
                "MedForventetForbrug":data_exp_read, ## true || false (Include or exclude expected reading values)
                "OmregnForbrugTilAktuelleEnhed":"true" # true || false
            }

        _LOGGER.debug(f"POST data to API. {data}")

        result = requests.post(self._api_server + post_meter_data_url,
                                data = json.dumps(data),
                                timeout = 5,
                                headers=headers
                              )

        _LOGGER.debug(f"Response from API. Status: {result.status_code}, Body: {result.text}")

        raw_response = RawResponse()
        raw_response.status = result.status_code
        raw_response.body = result.text

        _LOGGER.debug(f"Done getting time series")

        return raw_response

    def _get_api_server(self):
        _LOGGER.debug(f"Getting api server at supplier {self._supplierid}")
        ## Get the URL to the REST API service
        settingsURL="/umbraco/dff/dffapi/GetVaerkSettings?forsyningid="
        result = requests.get(self._base_url + settingsURL + self._supplierid)
        result_json = result.json()
        api_server = result_json['AppServerUri']

        _LOGGER.debug(f"Done getting api server {api_server}")

        return api_server

    def _get_access_token(self):
        _LOGGER.debug(f"Getting access token")

        if self._api_server == "":
            self._api_server = self._get_api_server()

        # With the API server URL we can authenticate and get a token:
        security_token_url = self._api_server + "system/getsecuritytoken/project/app/consumer/" + self._username
        result = requests.get(security_token_url)
        result.raise_for_status()
        result_json = result.json()
        token = result_json['Token']
        ## TODO exception if token is '' (this happens if the username is invalid)
        hashed_password = hashlib.md5(self._password.encode()).hexdigest()
        crypt_string = hashed_password + token
        access_token = hashlib.md5(crypt_string.encode()).hexdigest()

        # Use the new token to login to the API service
        auth_url = "system/login/project/app/consumer/"+self._username+"/installation/1/id/"

        result = requests.get(self._api_server + auth_url + access_token)
        result.raise_for_status()
        result_json = result.json()
        result_status = result_json['Result']
        if result_status == 1:
            _LOGGER.debug("Login success")
        else:
            _LOGGER.debug("Login failed. Bye.")

        _LOGGER.debug(f"Got access token: {access_token}")
        return access_token

    def _create_headers(self):
        return {
                'Content-Type': 'application/json',
                'Accept': 'application/json'}

    def get_latest(self):
        '''
        Get latest data.
        '''
        _LOGGER.debug(f"Getting latest data")

        # Calcuate the year parameter.  If the billing period is not skewed we
        # use the current year.  If it is skewed we must use the year before until
        # the billing period changes from July 1st.
        year = datetime.now().year
        month = datetime.now().month
        if self._billing_period_skew and month >= 1 and month <= 6:
            year = year - 1

        raw_data = self._get_time_series(year=year,
                                         day=True, # NOTE: Pulling daily data is required to get non-averaged temperature measurements
                                         from_date=datetime.now()-timedelta(days=1),
                                         to_date=datetime.now())

        if raw_data.status == 200:
            json_response = json.loads(raw_data.body)

            r = self._parse_result(json_response)

            keys = list(r.keys())

            keys.sort()
            keys.reverse()

            result = r[keys[0]]
        else:
            result = TimeSeries(raw_data.status, None, None, raw_data.body)

        _LOGGER.debug(f"Done getting latest data")
        return result

    def _stof(self, fstr):
        """Convert string with ',' string float to float"""
        return float(fstr.replace(',', '.'))

    def _parse_result(self, result):
        '''
        Parse result from API call. This is a JSON dict.
        '''
        _LOGGER.debug(f"Parsing results")
        parsed_result = {}

        metering_data = {}
        metering_data['year_start'] = result['AarStart']
        metering_data['year_end']   = result['AarSlut']
        for fl in result['ForbrugsLinjer']['TForbrugsLinje']:
            metering_data['temp-forward'] = self._stof(fl['Tempfrem'])
            metering_data['temp-return'] = self._stof(fl['TempRetur'])
            metering_data['temp-exp-return'] = self._stof(fl['Forv_Retur'])
            metering_data['temp-cooling'] = self._stof(fl['Afkoling'])
            for reading in fl['TForbrugsTaellevaerk']:
                unit = reading['Enhed_Txt']
                _LOGGER.debug(f"Energy use unit is: {unit}")
                multiplier = 1
                if unit == "MWh":
                    multiplier = 1000
                if reading['IndexNavn'] == "ENG1":
                    metering_data['energy-start'] = self._stof(reading['Start']) * multiplier
                    metering_data['energy-end'] = self._stof(reading['Slut']) * multiplier
                    metering_data['energy-used'] = self._stof(reading['Forbrug']) * multiplier
                    metering_data['energy-exp-used'] = self._stof(fl['ForventetForbrugENG1']) * multiplier
                    metering_data['energy-exp-end'] = self._stof(fl['ForventetAflaesningENG1']) * multiplier
                elif reading['IndexNavn'] == "M3":
                    metering_data['water-start'] = self._stof(reading['Start'])
                    metering_data['water-end'] = self._stof(reading['Slut'])
                    metering_data['water-used'] = self._stof(reading['Forbrug'])
                    metering_data['water-exp-used'] = self._stof(fl['ForventetForbrugM3'])
                    metering_data['water-exp-end'] = self._stof(fl['ForventetAflaesningM3'])
                else:
                    metering_data['extra-start'] = self._stof(reading['Start'])
                    metering_data['extra-end'] = self._stof(reading['Slut'])
                    metering_data['extra-used'] = self._stof(reading['Forbrug'])

        # Because we are fetching data from the full year (or so far)
        # The date is generated internally to be todays day of course.
        date = datetime.now()

# Fake data testing:
#        metering_data['temp-forward'] = random.randint(0, 100)
#        metering_data['temp-return'] = random.randint(0, 100)
#        metering_data['temp-exp-return'] = random.randint(0, 100)
#        metering_data['temp-cooling'] = random.randint(0, 100)
#        metering_data['energy-start'] = random.randint(0, 100)
#        metering_data['energy-end'] = random.randint(0, 100)
#        metering_data['energy-used'] = random.randint(0, 100)
#        metering_data['energy-exp-used'] = random.randint(0, 100)
#        metering_data['energy-exp-end'] = random.randint(0, 100)
#        metering_data['water-start'] = random.randint(0, 100)
#        metering_data['water-end'] = random.randint(0, 100)
#        metering_data['water-used'] = random.randint(0, 100)
#        metering_data['water-exp-used'] = random.randint(0, 100)
#        metering_data['water-exp-end'] = random.randint(0, 100)
#        date = datetime.strptime("2020-01-28T14:45:12Z", '%Y-%m-%dT%H:%M:%SZ')

        time_series = TimeSeries(200, date, metering_data)
        parsed_result[date] = time_series
        _LOGGER.debug(f"Done parsing results")
        return parsed_result