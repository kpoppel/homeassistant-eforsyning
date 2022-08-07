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
    def __init__(self, username, password, supplierid, billing_period_skew, is_water_supply):
        self._username = username
        self._password = password
        self._supplierid = supplierid
        self._billing_period_skew = billing_period_skew
        self._is_water_supply = is_water_supply
        self._base_url = 'https://eforsyning.dk/'
        self._api_server = ""
        ## Assume people only have a single metering device.
        ## Feel free to expand the code to find all metering devices
        ## and iterate over them.
        ## Must be a string - see where it is used.
        self._asset_id = "1"
        self._installation_id = "1"
        self._access_token = ""

    def _get_ebrugerid(self):
        '''
        This method returns the "ebrugerid" which is different from the username.
        This id is used to get the installations.
        Parameter "id" in the returned data is the ebrugerid
        '''
        _LOGGER.debug(f"Getting userinfo from API (ebrugerinfo)")
        userinfoURL = self._api_server + "api/getebrugerinfo?id=" + self._access_token
        _LOGGER.debug(f"Trying: {userinfoURL}")
        result = requests.get(userinfoURL,
                                timeout = 5
                              )
        # Instead of converting with result.json() this is also possible:
        #    euser_id = str(result_dict['id'])

        result_json = result.json()

        if result.status_code == 200:
            _LOGGER.debug(f"Response from userinfo API. ebrugerinfo: {result.status_code}, Body: {result.text}, ebruger: {result_json['id']}")
        else:
            _LOGGER.error(f"Response from userinfo API. ebrugerinfo: {result.status_code}, Body: {result.text}")

        return result_json['id']

    def _get_intallations(self):
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
 
        ebrugerid = self._get_ebrugerid()

        ## Get the URL to the REST API service
        installationsURL=self._api_server + "api/FindInstallationer?id=" + self._access_token
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
              will return an array of data from start of billing period to today's date.
        '''
        _LOGGER.debug(f"Getting time series")

        if from_date is None:
            from_date = datetime.now()-timedelta(days=1)
        if to_date is None:
            to_date = datetime.now()

        date_format = '%d-%m-%Y'
        parsed_from_date = from_date.strftime(date_format)
        parsed_to_date = to_date.strftime(date_format)

        headers = self._create_headers()

        post_meter_data_url = "api/getforbrug?id="+self._access_token+"&unr="+self._username+"&anr="+self._asset_id+"&inr="+self._installation_id # POST

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

        if result.status_code != 200:
            _LOGGER.error("Not able to get access token.  Probably a wrong username.")
            return False

        result_json = result.json()
        token = result_json['Token']
        ## TODO exception if token is '' (this happens if the username is invalid)

        hashed_password = hashlib.md5(self._password.encode()).hexdigest()
        crypt_string = hashed_password + token
        self._access_token = hashlib.md5(crypt_string.encode()).hexdigest()
        _LOGGER.debug(f"Got access token: {self._access_token}")
        return True

    def _login(self):
        # Use the new token to login to the API service
        auth_url = "system/login/project/app/consumer/"+self._username+"/installation/1/id/"

        result = requests.get(self._api_server + auth_url + self._access_token)
        result.raise_for_status()
        result_json = result.json()
        result_status = result_json['Result']
        if result_status == 1:
            _LOGGER.debug("Login success")
        else:
            _LOGGER.error("Login failed. Bye.")
            return False

        return True

    def _create_headers(self):
        return {
                'Content-Type': 'application/json',
                'Accept': 'application/json'}

    def get_latest(self):
        '''
        Get latest data.
        '''
        _LOGGER.debug(f"Getting latest data")

        if not self._get_access_token():
            return None

        if not self._login():
            return None

        self._get_intallations()

        # Calculate the year parameter.  If the billing period is not skewed we
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

            if self._is_water_supply == False:
                result = self._parse_result_heating(json_response)
            else:
                result = self._parse_result_water(json_response)

            #_LOGGER.debug(f"line 300 eforsyning.py: Result: {result}")
        else:
            result = None
            #result = TimeSeries(raw_data.status, None, None, raw_data.body)

        _LOGGER.debug("Done getting latest data (status code:%d)", raw_data.status)
        return result

    def _stof(self, fstr):
        """Convert string with ',' string float to float.
           If the string is empty just return 0.0.
        """
        if fstr == "":
            return 0.0
        return float(fstr.replace(',', '.'))

    def _parse_result_heating(self, result):
        '''
        Parse result from API call. This is a JSON dict.
        '''
        _LOGGER.debug(f"Parsing results - heating metering")

        metering_data = {}
        # Extract data from the latest data point
        metering_data['year_start'] = result['AarStart']
        metering_data['year_end']   = result['AarSlut']

        # Save all relevant day data so it can be extracted by users of the API (like HomeAssistant attributes)
        metering_data['data'] = []
        for fl in result['ForbrugsLinjer']['TForbrugsLinje']:
            metering_data['temp-forward'] = self._stof(fl['Tempfrem'])
            metering_data['temp-return'] = self._stof(fl['TempRetur'])
            metering_data['temp-exp-return'] = self._stof(fl['Forv_Retur'])
            metering_data['temp-cooling'] = self._stof(fl['Afkoling'])
            for reading in fl['TForbrugsTaellevaerk']:
                unit = reading['Enhed_Txt']
                #_LOGGER.debug(f"Energy use unit is: {unit}")
                multiplier = 1
                if unit == "MWh":
                    multiplier = 1000

                if reading['IndexNavn'] == "M3":
                    metering_data['water-start'] = self._stof(reading['Start'])
                    metering_data['water-end'] = self._stof(reading['Slut'])
                    metering_data['water-used'] = self._stof(reading['Forbrug'])
                    metering_data['water-exp-used'] = self._stof(fl['ForventetForbrugM3'])
                    metering_data['water-exp-end'] = self._stof(fl['ForventetAflaesningM3'])
                elif reading['IndexNavn'] == "ENG1":
                    metering_data['energy-start'] = self._stof(reading['Start']) * multiplier
                    metering_data['energy-end'] = self._stof(reading['Slut']) * multiplier
                    metering_data['energy-used'] = self._stof(reading['Forbrug']) * multiplier
                    metering_data['energy-exp-used'] = self._stof(fl['ForventetForbrugENG1']) * multiplier
                    metering_data['energy-exp-end'] = self._stof(fl['ForventetAflaesningENG1']) * multiplier
                elif reading['IndexNavn'] == "ENG2":
                    metering_data['energy-eng2-start'] = self._stof(reading['Start']) * multiplier
                    metering_data['energy-eng2-end'] = self._stof(reading['Slut']) * multiplier
                    metering_data['energy-eng2-used'] = self._stof(reading['Forbrug']) * multiplier
                elif reading['IndexNavn'] == "TV2":
                    metering_data['energy-tv2-start'] = self._stof(reading['Start']) * multiplier
                    metering_data['energy-tv2-end'] = self._stof(reading['Slut']) * multiplier
                    metering_data['energy-tv2-used'] = self._stof(reading['Forbrug']) * multiplier
                else:
                    # This would be "TIME_"
                    metering_data['extra-start'] = self._stof(reading['Start'])
                    metering_data['extra-end'] = self._stof(reading['Slut'])
                    metering_data['extra-used'] = self._stof(reading['Forbrug'])

            metering_data['data'].append({
                "DateFrom" : datetime.strptime(fl["FraDatoStr"], "%d-%m-%Y").strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "DateTo" : datetime.strptime(fl["TilDatoStr"], "%d-%m-%Y").strftime("%Y-%m-%dT%H:%M:%S.000Z"),

                "kWh-Start" : metering_data['energy-start'],
                "kWh-End" : metering_data['energy-start'],
                "kWh-Used" : metering_data['energy-used'],
                "kWh-ExpUsed" : metering_data['energy-exp-used'],
                "kWh-ExpEnd" : metering_data['energy-exp-end'],

                "M3-Start" : metering_data['water-start'],
                "M3-End" : metering_data['water-start'],
                "M3-Used" : metering_data['water-used'],
                "M3-ExpUsed" : metering_data['water-exp-used'],
                "M3-ExpEnd" : metering_data['water-exp-end'],

                "Temp-forward" : metering_data['temp-forward'],
                "Temp-Return" : metering_data['temp-return'],
                "Temp-ExpReturn" : metering_data['temp-exp-return'],
                "Temp-Cooling" : metering_data['temp-cooling'],

                "kWh-ENG2-Start" : metering_data['energy-eng2-start'],
                "kWh-ENG2-End" : metering_data['energy-eng2-end'],
                "kWh-ENG2-Used" : metering_data['energy-eng2-used'],

                "kWh-TV2-Start" : metering_data['energy-tv2-start'],
                "kWh-TV2-End" : metering_data['energy-tv2-end'],
                "kWh-TV2-Used" : metering_data['energy-tv2-used'],
            })

        _LOGGER.debug(f"Done parsing results")
        return metering_data

    def _parse_result_water(self, result):
        '''
        Parse result from API call. This is a JSON dict.
        In the JSON these are the data points:
          ForbrugsLinjer.TForbrugsLinje[last].TForbrugsTaellevaerk[0].Slut|Start|Forbrug  (water-start, water-end, water-used)
          ForbrugsLinjer.TForbrugsLinje[last].ForventetAflaesningM3|ForventetForbrugM3 (water-exp-end, water-exp-used)
          IaltLinje.TForbrugsTaellevaerk[0].Forbrug (water-ytd-used)
          IaltLinje.ForventetForbrugM3 (water-exp-fy-used)
          ForbrugsLinjer.TForbrugsLinje[last].ForventetAflaesningM3 - ForbrugsLinjer.TForbrugsLinje[0].ForventetAflaesningM3 (water-exp-ytd-used)

        '''
        _LOGGER.debug(f"Parsing results - water metering")

        metering_data = {}
        # Extract data from the latest data point
        metering_data['year_start'] = result['AarStart']
        metering_data['year_end']   = result['AarSlut']
        metering_data['water-ytd-used'] = self._stof(result['IaltLinje']['TForbrugsTaellevaerk'][0]['Forbrug'])
        metering_data['water-exp-fy-used'] = self._stof(result['IaltLinje']['ForventetForbrugM3'])
        # Calculate expected year to date consumption
        start = self._stof(result['ForbrugsLinjer']['TForbrugsLinje'][0]['ForventetAflaesningM3'])
        end = self._stof(result['ForbrugsLinjer']['TForbrugsLinje'][-1]['ForventetAflaesningM3'])
        metering_data['water-exp-ytd-used'] = end - start

        # Save all relevant day data so it can be extracted by users of the API (like HomeAssistant attributes)
        metering_data['data'] = []
        for fl in result['ForbrugsLinjer']['TForbrugsLinje']:
            metering_data['water-exp-used'] = self._stof(fl['ForventetForbrugM3'])
            metering_data['water-exp-end'] = self._stof(fl['ForventetAflaesningM3'])
            for reading in fl['TForbrugsTaellevaerk']:
                metering_data['water-start'] = self._stof(reading['Start'])
                metering_data['water-end'] = self._stof(reading['Slut'])
                metering_data['water-used'] = self._stof(reading['Forbrug'])

            metering_data['data'].append({
                "DateFrom" : datetime.strptime(fl["FraDatoStr"], "%d-%m-%Y").strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "DateTo" : datetime.strptime(fl["TilDatoStr"], "%d-%m-%Y").strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "Start" : metering_data['water-start'],
                "End" : metering_data['water-start'],
                "Used" : metering_data['water-used'],
                "ExpUsed" : metering_data['water-exp-used'],
                "ExpEnd" : metering_data['water-exp-end'],
            })

        _LOGGER.debug(f"Done parsing results")
        return metering_data
