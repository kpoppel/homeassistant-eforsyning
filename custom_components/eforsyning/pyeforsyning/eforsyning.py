'''
Primary public module for eforsyning.dk API wrapper.
'''
from datetime import datetime
from datetime import timedelta
import json
import requests
import http
import logging
import hashlib

# Test
import random

_LOGGER = logging.getLogger(__name__)

class LoginFailed(Exception):
    """"Exception class for bad credentials"""

class HTTPFailed(Exception):
    """Exception class for API HTTP failures"""

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
        self._user_id = None
        self._first_year = None
        self._installation_id = "1"
        self._access_token = ""
        self._latest_year = 2000
        self._latest_year_begin = ""
        self._latest_year_end = ""

    def _get_ebrugerinfo(self):
        '''
        This method returns the "ebrugerid" which is different from the username.
        This id is used to get the installations.
        Parameter "id" in the returned data is the ebrugerid
        Parameter "indflyttet" is the date the consumer was registered on the address.  It is useful when retrieving yearly data
          so that data is not retrieved before the consumer moved in.
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

        self._user_id = result_json['id']
        self._first_year = datetime.strptime(result_json['indflyttet'], '%d-%m-%Y').year

    def _get_installations(self):
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
 
        ## Get the URL to the REST API service
        installationsURL=self._api_server + "api/FindInstallationer?id=" + self._access_token
        _LOGGER.debug(f"Trying: {installationsURL}")
        data = {
                "Soegetekst": "",
                "Skip": "0",
                "Take": "10000",
                "EBrugerId": self._user_id,
                "Huskeliste": "null",
                "MedtagTilknyttede": "true"
                }

        headers = self._create_headers()

        result = requests.post(installationsURL,
                                data = json.dumps(data),
                                timeout = 10,
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

    def _get_latest_year(self):
        ''' Retrieve the latest available year.  This is the latest year data can be retrieved from.
            When passing over a payment period, which could be New Year or even July or October depending
            on the supplier financial year, data are reset and we start over.
            In the case of fetching data this could mean the no data can be retrieved while this marker is
            not updated.
        '''
        _LOGGER.debug(f"Getting installations at supplier: {self._supplierid}")
 
        ## Get the URL to the REST API service
        getaktuelaarsmaerkeURL=self._api_server + "api/getaktuelaarsmaerke?id=" + self._access_token
        _LOGGER.debug(f"Trying: {getaktuelaarsmaerkeURL}")
        headers = self._create_headers()

        result = requests.post(getaktuelaarsmaerkeURL,
                                timeout = 10,
                                headers=headers
                              )

        _LOGGER.debug(f"Response from API. Status: {result.status_code}, Body: {result.text}")

        result_json = result.json()
        # Data looks like this:
        #{"aarsmaerke":2022,
        # "aarsmaerke_start":"01-01-2022",
        # "aarsmaerke_slut":"31-12-2022"
        #}
        result_json = result.json()
        self._latest_year = int(result_json['aarsmaerke'])
        self._latest_year_begin = str(result_json['aarsmaerke_start'])
        self._latest_year_end = str(result_json['aarsmaerke_slut'])

        _LOGGER.debug(f"Done getting latest year data {self._latest_year}")

        return result_json

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

              "ForbrugsAfgraensning_FraAflaesning":"0|2|10"
              "ForbrugsAfgraensning_TilAflaesning":"0|2|10"
              
              0  returns yearly reading
              2  returns latest reading
              10 returns reading per date
        '''
        _LOGGER.debug(f"Getting time series")

        date_format = '%d-%m-%Y'
        parsed_from_date = "0"
        parsed_to_date = "0"
        if from_date is not None:
            parsed_from_date = from_date.strftime(date_format)
        if to_date is not None:
            parsed_to_date = to_date.strftime(date_format)


        headers = self._create_headers()

        post_meter_data_url = "api/getforbrug?id="+self._access_token+"&unr="+self._username+"&anr="+self._asset_id+"&inr="+self._installation_id # POST

        include_data_in_between = "false"
        if month or day:
            include_data_in_between = "true"

        # If requesting data for a
        # - monthly graph use afMaanedsvis
        # - daily graph use afDagsvis
        #
        # For the field "AflaesningsUdjaevning" set to
        # - true - if missing reading for a day, registered on the day after should be averaged on the days between the last good readings.
        #          A missing reading will effectively double the reading on the next day (if the consumption is constant)
        # - false - if missing readings should appear as zeroes - this could create a bumpt graph for daily readings.
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
                "ForbrugsAfgraensning_FraAflaesning":"0", ## 0|2|10
                "ForbrugsAfgraensning_TilAflaesning":"2", ## 0|2|10
                "ForbrugsAfgraensning_MedtagMellemliggendeMellemaflas":include_data_in_between, ## true || false (false when getting year data)

                "Optioner":"foBestemtBeboer, foSkabDetaljer, foMedtagWebAflaes",
                "AHoejDetail":"false", ## true || false

                "Aflaesningsfilter":data_filter, ## afMaanedsvis || afDagsvis || afUfiltreret
                "AflaesningsFilterDag":"ULTIMO", ## PRIMO || ULTIMO (pick data on first or last day of the week or month)
                "AflaesningsUdjaevning":data_average, ## true || false (Create interpolated data it seems) (true if getting monthyly)

                "SletFiltreredeAflaesninger":"true", ## true || false (Get rid of filtered data?)
                "MedForventetForbrug":data_exp_read, ## true || false (Include or exclude expected reading values) (true if getting monthly)
                "OmregnForbrugTilAktuelleEnhed":"true" # true || false

                # These ones seem to not cause any trouble if left out:
                #"aCallKey":0,
                #"ForbrugsAfgraensning_FraMellNr":"0",
                #"ForbrugsAfgraensning_TilJournalNr":"0",
                #"BestemtEnhed":"0",
                #"Godkendelser":"0",
                #"RadEksponent2":"0",
                #"RadEksponent1":"0",
                #"Belastningsfaktor":"0",
                #"ForbrugsAfgraensning_FraAfl_nr":"0"
                #"ForbrugsAfgraensning_TilMellnr":"0",
            }

        _LOGGER.debug(f"POST data to API. {data}")
        result = None
        try:
            result = requests.post(self._api_server + post_meter_data_url,
                                    data = json.dumps(data),
                                    timeout = 10,
                                    headers=headers
                                )
        except requests.exceptions.Timeout:
            _LOGGER.warning(f"API access timed out.  No data retrieved")
            return result

        except requests.exceptions.RequestException:
            _LOGGER.warning(f"RequestException {result}")
            raise HTTPFailed(result.raise_for_status())

        _LOGGER.debug(f"Done getting time series {result.status_code}, Body: {result.text}")

        return result.json()

    def _get_billing_details(self):
        ## Prices of the energy used can be fetched as well
        # https://<server URL>/vaerksid>/api/getberegnregnskab?id=<id>&unr=<forbrugernummer>&anr=0&inr=<installationsnummer>
        _LOGGER.debug(f"Getting billing details at supplier {self._supplierid}")
        ## Get the URL to the REST API service
        post_billing_data_url = "api/getberegnregnskab?id="+self._access_token+"&unr="+self._username+"&anr="+self._asset_id+"&inr="+self._installation_id # POST
        headers = self._create_headers()
        data = {
                "aktivnr" : 0,
                "beregnetVarmeRegnskab" : "faktisk"
                }
 
        _LOGGER.debug(f"POST to API")
        result = None
        try:
            result = requests.post(self._api_server + post_billing_data_url,
                                    data = json.dumps(data),
                                    timeout = 10,
                                    headers=headers
                                )
        except requests.exceptions.RequestException:
            raise HTTPFailed(result.raise_for_status())

        _LOGGER.debug(f"Done getting billing details {result.status_code}") #, Body: {result.text}")
        _LOGGER.debug(json.dumps(result.json(), sort_keys = False, indent = 4))
        return result.json()


    def _get_api_server(self):
        _LOGGER.debug(f"Getting api server at supplier {self._supplierid}")
        ## Get the URL to the REST API service
        settingsURL="umbraco/dff/dffapi/GetVaerkSettings?forsyningid="
        result = None
        try:
            result = requests.get(self._base_url + settingsURL + self._supplierid, headers=self._create_headers())
        except requests.exceptions.RequestException:
            raise HTTPFailed(result.raise_for_status())

        result_json = result.json()
        self._api_server = result_json['AppServerUri']

        _LOGGER.debug(f"Done getting api server {self._api_server}")

        return True

    def _get_access_token(self):
        _LOGGER.debug(f"Getting access token")

        # With the API server URL we can authenticate and get a token:
        security_token_url = self._api_server + "system/getsecuritytoken/project/app/consumer/" + self._username

        result = None
        try:
            result = requests.get(security_token_url, headers=self._create_headers())
        except requests.exceptions.RequestException as err:
            raise LoginFailed(f"Failure on HTTP request during access token aquisition: {err}")
            return False

        if result.status_code != 200:
            raise LoginFailed(f"Not able to get access token. HTTP status: {result.status_code}.  Probably a wrong username.")

        result_json = result.json()
        token = result_json['Token']
        if token == '':
            raise LoginFailed("Not able to get access token, it was empty.  Probably a wrong username.")

        hashed_password = hashlib.md5(self._password.encode()).hexdigest()
        crypt_string = hashed_password + token
        self._access_token = hashlib.md5(crypt_string.encode()).hexdigest()
        _LOGGER.debug(f"Got access token: {self._access_token}")

        return True

    def _login(self):
        # Use the new token to login to the API service
        auth_url = "system/login/project/app/consumer/"+self._username+"/installation/1/id/"
        result = None
        try:
            result = requests.get(self._api_server + auth_url + self._access_token, headers=self._create_headers())
        except requests.exceptions.RequestException:
            raise HTTPFailed(result.raise_for_status())

        result_json = result.json()
        result_status = result_json['Result']
        if result_status == 1:
            _LOGGER.debug("Login success")
        else:
            raise LoginFailed("Login failed. Bye.")

        return True

    def authenticate(self):
        """ Perform the login process:
            First retrieve the API server, next get an access token, last use the token to authenticate.
            If any of these raises an exception, login failed miserably.
        """
        try:
            self._x_session_id = ''.join(random.choice("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ") for i in range(8))
            self._get_api_server()
            self._get_access_token()
            self._login()
        except (LoginFailed, HTTPFailed) as err:
            _LOGGER.error(err)
            return False
        return True

    def _create_headers(self):
        return {
                #'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-Session-ID': self._x_session_id,
                'X-Correlation-ID': ''.join(random.choice("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ") for i in range(8)),
                'User-Agent': 'HomeAssistant - eforsyning integration, Python requests module'
                }

    def get_latest(self):
        '''
        Get latest data.
        '''
        _LOGGER.debug(f"Getting latest data")
        self._get_ebrugerinfo()
        self._get_installations()
        self._get_latest_year()

        # This is for heating data only - fetch yearly stats
        if self._is_water_supply == False:
            # Retrieve year data for the past max. 5 years.
            year_result = []
            years_to_fetch = min(self._latest_year - self._first_year, 5)
            start_year = self._latest_year - years_to_fetch
            for year_count in range(years_to_fetch + 1):
                year_data = self._get_time_series(year=start_year + year_count)
                result = self._parse_result_totals_line(year_data)
                year_result.append(result)

            # Format data so Homeassistant sensor can understand it.
            year_data = {
                'year': year_result,
                'temp-return-year': year_result[-1]['Temp-Return']
            }

        # NOTE:
        # If the current year is later than the latest year it _may_ mean that data fetched is no longer valid
        # For people with January-December payment years this means trouble because monthly and yearly totals
        # are not updated. It semms this first happens after the first month has passed? (yet to be seen)
        # So if the current year is > than lastest_year try to fetch daily data using the current year.
        # If this looks sensible, use that data for further processing, otherwise do as normal.
        # The only parameter if significance is the year.  dates are just ignored, so a date range of 1 day is ignored in "day" mode.
        #
        # Two failure situations things can happen I think:
        #    {"response":"TForb: Opslag på årsmærke fejlede(TForbrug.Beregn): 2024"}
        # or a situation where there are no lines returned
        #  {
        #  "ForbrugsLinjer": {
        #   "AktuelLinjeNr": "0",
        #   "AntLinjer": "0",
        #   "Text": "",
        #   "Pris": "0"
        #  },
        # If none of these, all should be okay actually.
        #
        # The latest year marker is set by the heating company but could be a manual process on their side.
        day_data = None

        # Try "invalid" year first if January and the year marker is not updated.
        _LOGGER.debug(f"{datetime.now().month} - {datetime.now().year} - {self._latest_year}")
        if datetime.now().month == 1 and datetime.now().year > self._latest_year:
            day_data = self._get_time_series(year=datetime.now().year,
                                            day=True, # NOTE: Pulling daily data is required to get non-averaged temperature measurements
                                            from_date=datetime.now()-timedelta(days=1),
                                            to_date=datetime.now())
            if 'response' in day_data or day_data['ForbrugsLinjer']['AntLinjer'] == "0":
                _LOGGER.debug("Fetching new year data did not result in valid data.  Getting current dataset from %s", self._latest_year)
                day_data = None

        
        if day_data == None:
            # Fetch the daily use data using the API based yearly marker
            day_data = self._get_time_series(year=self._latest_year,
                                            day=True, # NOTE: Pulling daily data is required to get non-averaged temperature measurements
                                            from_date=datetime.now()-timedelta(days=1),
                                            to_date=datetime.now())

        # if there is a connection error, no data is returned, so don't try to parse it.
        if day_data:
            if self._is_water_supply == False:
                result = self._parse_result_heating(day_data)
                # Handle data from the billing
                billing_data = self._get_billing_details()
                billing_result = self._parse_result_billing(billing_data)
            else:
                result = self._parse_result_water(day_data)
                # Pretty sure the billing record will *not* look the same for water data
                billing_result = {}
                year_data = {}

            _LOGGER.debug("Done parsing latest data")
            return result | billing_result | year_data
        else:
            return None

    def _stof(self, fstr, filter_above=None, scale=1):
        """Convert string with ',' string float to float.
           If the string is empty just return 0.0.
           If the value is above the filter_above value, return 0.0
           The scaling factor multiplies the value and rounds off to 3 decimals.
        """
        if fstr == "":
            return 0.0

        # Remove thousand . and convert decimal , to . - then convert to float value
        val = float(fstr.replace('.','').replace(',', '.'))
        
        # Cull values above filter_above.  Some times data deliverd are missing decimal comma!
        if filter_above and val > filter_above:
            return 0.0

        # Scale value and round value to remove float artifacts resulting in small decimal errors
        val = round(val*scale, 3)

        return val

    def _parse_result_totals_line(self, result):
        '''
        When requesting yearly data a new field appears "IaltLinje".  This section total up important stats for the year.
        This function does the parsing and returns a dictionary of the chosen values.

        The intereting parts are depicted below:

        "IaltLinje": {
            "FraDatoStr": "dd-mm-yyyy",
            "TilDatoStr": "dd-mm-yyyy",

            "Tempfrem": "<float>",       <-- notice the case here - inconsistent!
            "TempRetur": "<float>",      <-- this is the return temperature.  Keep below Forv_Retur.
            "Forv_Retur": "<int 37?>",   <-- return temperature is probably benchmarked against this value (pay more if you go above)
            "Afkoling": "<float>",

            "NeutraltOmraadeOvre": "<int 37?>",  <-- Same value as Forv_Retur, dos it have a purpose?
            "NeutraltOmraadeNedre": "<int 37?>"  <-- Same value as Forv_Retur, dos it have a purpose?

            <<--  These values may  be interesting as it summarises expected consumption with actual for that year.-->>
            "ForventetForbrugM3": "<float>",
            "ForventetForbrugENG1": "<float>",
            "TForbrugsTaellevaerk": [
            {
                "IndexNavn": "ENG1", <- Identifier
                "Enhed_Txt": "MWh",
                "Forbrug": "<float>"
            },{
                "IndexNavn": "M3",  <- Identifier
                "Enhed_Txt": "M3",
                "Forbrug": "<float>"
            }],
        }
        '''
        _LOGGER.debug(f"Parsing results - IaltLinje for non-day data.")
        data = {
            'from-date': result['IaltLinje']['FraDatoStr'],
            'to-date': result['IaltLinje']['TilDatoStr'],
            'temp-forward': self._stof(result['IaltLinje']['Tempfrem']),
            'temp-return': self._stof(result['IaltLinje']['TempRetur']),
            'temp-exp-return': self._stof(result['IaltLinje']['Forv_Retur']),
            'temp-cooling': self._stof(result['IaltLinje']['Afkoling']),
            'water-exp-used': result['IaltLinje']['ForventetForbrugM3'],
            'energy-exp-used': result['IaltLinje']['ForventetForbrugENG1']
        }
        # It appears some data returned does not have this field.  Handle gracefully.
        if 'TForbrugsTaellevaerk' in result['IaltLinje']:
            for meter in result['IaltLinje']['TForbrugsTaellevaerk']:
                if meter['IndexNavn'] == "ENG1":
                    data['energy-used'] = meter['Forbrug']
                elif meter['IndexNavn'] == "M3":
                    data['water-used'] = meter['Forbrug']
        else:
            data['energy-used'] = 0.0
            data['water-used'] = 0.0

        # Data collected - put into a format like the heating data.
        # Leaving a mapping part here because I would like to rename all these fields to be 
        # without case someday... some day...
        metering_data = {
            "DateFrom" : data['from-date'],
            "DateTo" : data['to-date'],

            "kWh-Used" : data['energy-used'],
            "kWh-ExpUsed" : data['energy-exp-used'],

            "M3-Used" : data['water-used'],
            "M3-ExpUsed" : data['water-exp-used'],

            "Temp-Forward" : data['temp-forward'],
            "Temp-Return" : data['temp-return'],
            "Temp-ExpReturn" : data['temp-exp-return'],
            "Temp-Cooling" : data['temp-cooling']
        }

        return metering_data

    def _parse_result_heating(self, result):
        '''
        Parse result from API call. This is a JSON dict.

        The data fields ENG2 and TV2 is energy sent into the heating unit and energy returned to the network.
        The unit is typically M3*T (volume * temperature).
        The average incoming and outgoing temperatures can be calculated by ENG2/<today M3 consumption> and TV2/<today M3 consumption>
        The cooling is then (ENG2-TV2)/<today M3 consumption>
        These numbers are of little information value for the end-user as this is already available on ENG1.
        '''
        _LOGGER.debug(f"Parsing results - heating metering")

        metering_data = {}

        # Extract data from the latest data point
        metering_data['year_start'] = result['AarStart']
        metering_data['year_end']   = result['AarSlut']

        # Save all relevant day data so it can be extracted by users of the API (like HomeAssistant attributes)
        metering_data['data'] = []
        for fl in result['ForbrugsLinjer']['TForbrugsLinje']:
            metering_data['temp-forward'] = self._stof(fl['Tempfrem'], filter_above=150)
            metering_data['temp-return'] = self._stof(fl['TempRetur'], filter_above=150)
            metering_data['temp-exp-return'] = self._stof(fl['Forv_Retur'], filter_above=150)
            metering_data['temp-cooling'] = self._stof(fl['Afkoling'], filter_above=150)

            ## NOTE: No longer putting the ENG2 ans TV2 fields in the attributes.
            ##       They are numbers for energy delivered and sent back supposedly in units of M3*T
            ##       Hence dividing the number by M3 used the temperature in and out can be calculated.
            ##       The numbers have no real meaning for tracking the consumption and just
            ##       clutter the attributes.
            ##       If you want them back, unceommen the relevant lines.
            # Some may not have these fields.
            #metering_data['energy-eng2-start'] = None
            #metering_data['energy-eng2-end'] = None
            #metering_data['energy-eng2-used'] = None
            #metering_data['energy-tv2-start'] = None
            #metering_data['energy-tv2-end'] = None
            #metering_data['energy-tv2-used'] = None

            for reading in fl['TForbrugsTaellevaerk']:
                unit = reading['Enhed_Txt']
                #_LOGGER.debug(f"Energy use unit is: {unit}")
                multiplier = 1
                if unit == "MWh":
                    multiplier = 1000
                elif unit == "Gj":
                    # 1 kWh = 0.0036 GJ, so the conversion is <n GJ> * 1/0.0036 = m kWh
                    multiplier = float(1/0.0036)

                if reading['IndexNavn'] == "M3":
                    metering_data['water-start'] = self._stof(reading['Start'])
                    metering_data['water-end'] = self._stof(reading['Slut'])
                    metering_data['water-used'] = self._stof(reading['Forbrug'])
                    metering_data['water-exp-used'] = self._stof(fl['ForventetForbrugM3'])
                    metering_data['water-exp-end'] = self._stof(fl['ForventetAflaesningM3'])
                elif reading['IndexNavn'] == "ENG1":
                    metering_data['energy-start'] = self._stof(reading['Start'], scale=multiplier)
                    metering_data['energy-end'] = self._stof(reading['Slut'], scale=multiplier)
                    metering_data['energy-used'] = self._stof(reading['Forbrug'], scale=multiplier)
                    metering_data['energy-exp-used'] = self._stof(fl['ForventetForbrugENG1'], scale=multiplier)
                    metering_data['energy-exp-end'] = self._stof(fl['ForventetAflaesningENG1'], scale=multiplier)
                #elif reading['IndexNavn'] == "ENG2":
                #    metering_data['energy-eng2-start'] = self._stof(reading['Start'], scale=multiplier)
                #    metering_data['energy-eng2-end'] = self._stof(reading['Slut'], scale=multiplier)
                #    metering_data['energy-eng2-used'] = self._stof(reading['Forbrug'], filter_above=10000, scale=multiplier)
                #elif reading['IndexNavn'] == "TV2":
                #    metering_data['energy-tv2-start'] = self._stof(reading['Start'], scale=multiplier)
                #    metering_data['energy-tv2-end'] = self._stof(reading['Slut'], scale=multiplier)
                #    metering_data['energy-tv2-used'] = self._stof(reading['Forbrug'], filter_above=10000, scale=multiplier)
                else:
                    # This would be "TIME_"
                    metering_data['extra-start'] = self._stof(reading['Start'])
                    metering_data['extra-end'] = self._stof(reading['Slut'])
                    metering_data['extra-used'] = self._stof(reading['Forbrug'])

            metering_data['data'].append({
                "DateFrom" : datetime.strptime(fl["FraDatoStr"], "%d-%m-%Y").strftime("%Y-%m-%d"),
                "DateTo" : datetime.strptime(fl["TilDatoStr"], "%d-%m-%Y").strftime("%Y-%m-%d"),
 
                "kWh-Start" : metering_data['energy-start'],
                "kWh-End" : metering_data['energy-end'],
                "kWh-Used" : metering_data['energy-used'],
                "kWh-ExpUsed" : metering_data['energy-exp-used'],
                "kWh-ExpEnd" : metering_data['energy-exp-end'],

                "M3-Start" : metering_data['water-start'],
                "M3-End" : metering_data['water-end'],
                "M3-Used" : metering_data['water-used'],
                "M3-ExpUsed" : metering_data['water-exp-used'],
                "M3-ExpEnd" : metering_data['water-exp-end'],

                "Temp-Forward" : metering_data['temp-forward'],
                "Temp-Return" : metering_data['temp-return'],
                "Temp-ExpReturn" : metering_data['temp-exp-return'],
                "Temp-Cooling" : metering_data['temp-cooling'],

                #"kWh-ENG2-Start" : metering_data['energy-eng2-start'],
                #"kWh-ENG2-End" : metering_data['energy-eng2-end'],
                #"kWh-ENG2-Used" : metering_data['energy-eng2-used'],

                #"kWh-TV2-Start" : metering_data['energy-tv2-start'],
                #"kWh-TV2-End" : metering_data['energy-tv2-end'],
                #"kWh-TV2-Used" : metering_data['energy-tv2-used'],
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
            # Initialise data - just in case data is missing - which would be really weird
            metering_data['water-start'] = 0.0
            metering_data['water-end'] = 0.0
            metering_data['water-used'] = 0.0
            for reading in fl['TForbrugsTaellevaerk']:
                if reading['IndexNavn'] == "M3":
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

    def _parse_result_billing(self, result):
        '''
        Parse result from API call. This is a JSON dict.
        In the JSON these are the data points:
          faktlini[0..27].ekstra|enhedPris|linieType|antalEnheder|enhed|tekst|prisEnhed|opl4|opl3|opl2|opl1|ialt
        
        linieType = 0, 1, 3, 10, 12, 13, 18, 20
          0  = [13 lines] Skip - as only text
          1  = [1 line] Fixed m3 contribution
          3  = [5 lines] Looks related to consumption data (MWh, prognosis on MWh, price for GJ and such)
          7  = [1 line] Fixed yearly subscription fee
          10 = [1 line] Amount VAT
          12 = [5 lines] Amounts related to totals and remaining payment incl./excl. VAT
          13 = [1 line] Skip as it is empty
          18 = [2 lines] Amount already billed and amount in arrears (restance) (don't worry if this has a value - the report is drawn as if all payment should have been made)
          20 = [1 line] Expected payment remainder of the billing year (= -<ammount arrears>)
          22 = [6 lines] forward temperature, return temperature, expected return temperature and return temperature fee

        Depending on the line, the remaining fields have or does not have a value.
        In terms of sensors, the interesting data to pull out would be:
          - Prognosis for MWh consumption
          -

        There is another format with only [0..15] lines of information, with records in a different order.
        This basically means the parser cannot rely on specific indices but need to inder the records from other
        properties instead.

        This:
            idx[0]:
                {
                "ekstra": "kr.",
                "enhedPris": "433,80",  <--- have this in attributes to calculate price
                "linieType": "3",
                "antalEnheder": "3,361",  <--- this is consumption year-to-date in MWh (energy-total-used)
                "enhed": "MWh",
                "tekst": "MWh",
                "prisEnhed": "kr./MWh",
                "opl4": "MWh",
                "opl3": "19,560", <-- (a)
                "opl2": "MWh",
                "opl1": "16,199", <-- (b) : (b)-(a) == antalEnheder
                "ialt": "1.458,00"   <--- this is price of MWh year-to-date in MWh
                },

            idx[1]
                {
                "ekstra": "",
                "enhedPris": "",
                "linieType": "3",
                "antalEnheder": "108,66", <--- M3 used year-to-date (water-total-used)
                "enhed": "M3",
                "tekst": "",
                "prisEnhed": "",
                "opl4": "M3",
                "opl3": "617,98", <--- meter reading now
                "opl2": "M3",
                "opl1": "509,32", <--- meter reading at start of billing period
                "ialt": ""
                },

            idx[4]
                {
                "ekstra": "kr.",
                "enhedPris": "433,80",
                "linieType": "3",
                "antalEnheder": "2,144", <--- this is the prognosis on MWh remainder of billing year (energy-use-prognosis (calculate as used+this number))
                "enhed": "MWh",
                "tekst": "Prognose: 27-08-2022 til 31-12-2022",
                "prisEnhed": "kr./MWh",
                "opl4": "",
                "opl3": "",
                "opl2": "",
                "opl1": "",
                "ialt": "930,07" <--- this is the price of that prognosis
                },

            idx[n] (example with GJ unit instead of MWh)
                {
                "ekstra": "kr.",
                "enhedPris": "124,00",
                "linieType": "3",
                "antalEnheder": "3,37",
                "enhed": "Gj",
                "tekst": "12345678",
                "prisEnhed": "kr./Gj",
                "opl4": "Gj",
                "opl3": "213,40",
                "opl2": "Gj",
                "opl1": "210,03",
                "ialt": "417,88"
                },

            idx[n] (example with GJ unit instead of MWh)
                {
                "ekstra": "kr.",
                "enhedPris": "124,00",
                "linieType": "3",
                "antalEnheder": "46,78",
                "enhed": "Gj",
                "tekst": "Forventet forbrug: 15-01-2023 til 31-12-2023",
                "prisEnhed": "kr./Gj",
                "opl4": "",
                "opl3": "",
                "opl2": "",
                "opl1": "",
                "ialt": "5.800,72"
                },

            idx[6]
                {
                "ekstra": "kr.",
                "enhedPris": "",
                "linieType": "12",
                "antalEnheder": "",
                "enhed": "",
                "tekst": "Samlet varmeforbrug",
                "prisEnhed": "",
                "opl4": "",
                "opl3": "",
                "opl2": "",
                "opl1": "",
                "ialt": "2.388,07"  <--- total billing amount ytd+prognosis MWh
                },

            idx[7]
                {
                "ekstra": "kr.",
                "enhedPris": "13,14",
                "linieType": "1",
                "antalEnheder": "170,25",  <--- prognosis on M3 use (water-use-prognosis)
                "enhed": "m3",
                "tekst": "Fastbidrag",
                "prisEnhed": "kr./m3",
                "opl4": "",
                "opl3": "",
                "opl2": "dage",
                "opl1": "365",  <-- see, this is for the whole year...
                "ialt": "2.237,09" <--- total billing based on the prognosis of M3 use
                }

            idx[10]
                {
                "ekstra": "kr.",
                "enhedPris": "4.625,16",
                "linieType": "10",
                "antalEnheder": "25,00",
                "enhed": "%",
                "tekst": "Moms",
                "prisEnhed": "kr.",
                "opl4": "",
                "opl3": "",
                "opl2": "",
                "opl1": "",
                "ialt": "1.156,29" <--- total bill VAT amount
                },

            idx[12]
                {
                "ekstra": "kr.",
                "enhedPris": "",
                "linieType": "12",
                "antalEnheder": "",
                "enhed": "",
                "tekst": "Total (incl.moms)",
                "prisEnhed": "",
                "opl4": "",
                "opl3": "",
                "opl2": "",
                "opl1": "",
                "ialt": "5.781,45"  <--- total bill (idx[6]+idx[7]+idx[10])
                },

            idx[13]
                {
                "ekstra": "kr.",
                "enhedPris": "",
                "linieType": "18",
                "antalEnheder": "",
                "enhed": "",
                "tekst": "Tidl. opkrævet (incl. moms)",
                "prisEnhed": "",
                "opl4": "",
                "opl3": "",
                "opl2": "",
                "opl1": "",
                "ialt": "-4.770,00"  <--- amount already billed
                },

            idx[16]
                {
                "ekstra": "kr.",
                "enhedPris": "",
                "linieType": "18",
                "antalEnheder": "",
                "enhed": "",
                "tekst": "Restance",
                "prisEnhed": "",
                "opl4": "",
                "opl3": "",
                "opl2": "",
                "opl1": "",
                "ialt": "1.590,00"  <--- amount arrears (how this number is calculated is not clear)
                },                


            idx[19]
                {
                "ekstra": "kr.",
                "enhedPris": "",
                "linieType": "12",
                "antalEnheder": "",
                "enhed": "",
                "tekst": "Til indbetaling ",
                "prisEnhed": "",
                "opl4": "",
                "opl3": "",
                "opl2": "",
                "opl1": "",
                "ialt": "1.011,45"  <-- amount to be paid remainder of the year
                },

        Putting eveything together:
        Sensors:
         energy-total-used (idx[0][antalEnheder])
         energy-use-prognosis (idx[0][antalEnheder]+idx[4][antalEnheder])
         water-total-used (idx[1][antalEnheder])
         water-use-prognosis (idx[7][antalEnheder])
         amount-remaining (idx[19][ialt])

         Attributes:
           data_fetch_date (when the data was fetched)
           MWh_Price  (idx[0][enhedPris])
           M3_Price (idx[7][enhedPris])
           Amount_MWh (idx[6][ialt])
           Amount_M3 (idx[7][ialt])
           Amount_VAT (idx[10][ialt])
           Amount_Total (idx[12][ialt])
           Amount_Paid (-idx[13][ialt])
           Amount_Remaining (idx[19][ialt])
        '''
        _LOGGER.debug(f"Parsing results - billing")

        # Only one field - which has an array of data
        result = result['faktlini']

        energy_prognosis = 0.0
        energy_price = 0.0
        energy_total_used = 0.0
        energy_total_used_price = 0.0
        m3_prognosis = 0.0
        m3_price = 0.0
        m3_total_used = 0.0
        m3_prognosis_price = 0.0
        m3_prognosis_price = 0.0
        amount_vat = 0.0
        amount_energy = 0.0
        amount_total = 0.0
        amount_advance = 0.0
        amount_remaining = 0.0

        multiplier = 1000 # scaling factor to kWh frm MWh
        multiplier_gj = 227.78 # Scaling factor to kWh from from GJ

        for record in result:
            if record['linieType'] == "0":
                continue
            elif record['linieType'] == "1":
                # Fixed payment - differences here, some have a unit price
                m3_prognosis_price = self._stof(record['ialt'])
                if record['enhed'] == "m3":
                    m3_prognosis = self._stof(record['antalEnheder'])
                    m3_price = round(m3_prognosis_price/m3_prognosis, 2)
                continue
            elif record['linieType'] == "3":
                if "Afkøling" in record['tekst']:
                    # Average cooling - not used
                    continue
                elif any(test_str in record['tekst'] for test_str in ["Prognose", "Forventet forbrug"]):
                    if record['enhed'] == "MWh":
                        # Prognosis heating in MWh scaled to kWh
                        energy_prognosis = self._stof(record['antalEnheder'], scale=multiplier)
                        continue
                    elif record['enhed'] == "Gj":
                        # Prognosis heating in GJ scaled to kWh
                        energy_prognosis = self._stof(record['antalEnheder'], scale=multiplier_gj)
                        continue
                    else:
                        # Not a prognosis in MWh or GJ - not used
                        continue
                elif record['enhed'] == "MWh":
                    # Price of comsumption of energy.
                    # If there are more records like these, it would seen the price may have been adjusted.
                    # Calculate the average MWh price in that case.
                    energy_total_used_price += self._stof(record['ialt'])
                    energy_total_used += self._stof(record['antalEnheder'], scale=multiplier)
                    energy_price = round(multiplier*energy_total_used_price/energy_total_used, 2)
                    continue
                elif record['enhed'] == "Gj":
                    # Price of comsumption of energy.
                    # If there are more records like these, it would seen the price may have been adjusted.
                    # Calculate the average GJ price in that case.
                    energy_total_used_price += self._stof(record['ialt'])
                    energy_total_used += self._stof(record['antalEnheder'], scale=multiplier_gj)
                    energy_price = round(multiplier_gj*energy_total_used_price/energy_total_used, 2)
                    continue
                elif record['enhed'] == "M3":
                    # Consumption in M3 (water passed through the system)
                    m3_total_used += self._stof(record['antalEnheder'])
                    continue
                else:
                    # Something else
                    continue
            elif record['linieType'] == "10":
                # Amount VAT
                amount_vat = self._stof(record['ialt'])
                continue
            elif record['linieType'] == "12":
                if record['tekst'] == "Samlet varmeforbrug":
                    # Price of MWh totalled
                    amount_energy = self._stof(record['ialt'])
                    continue
                elif any(test_str in record['tekst'] for test_str in ["Total (incl.moms)", "Total, inkl. moms"]):
                    # Price totalled incl. VAT
                    amount_total = self._stof(record['ialt'])
                    continue
                elif record['tekst'] == "\u00c5rets forventede resultat":
                    # Price totalled incl. VAT
                    amount_total = self._stof(record['ialt'])
                    continue
                elif any(test_str in record['tekst'] for test_str in ["Til udbetaling", "Tilbagebetaling"]):
                    # Remaining expected remuneration (indicated by a negative number)
                    amount_remaining = -self._stof(record['ialt'])
                    continue
                elif any(test_str in record['tekst'] for test_str in ["Til indbetaling", "For lidt opkr\u00e6vet", "Forel\u00f8big beregnet efterbetaling"]):
                    # Remaining expected payment (indicated by a positive number)
                    amount_remaining = self._stof(record['ialt'])
                    continue
                else:
                    # Something else, like amount excl. VAT, too much paid, too little paid - not used
                    continue
            elif record['linieType'] == "13":
                continue
            elif record['linieType'] == "18":
                if "Restance" in record['tekst']:
                    continue
                else:
                    # Advance payments (negative number in the report)
                    amount_advance = -self._stof(record['ialt'])
                    continue
            elif record['linieType'] == "20":
                # Expected future payments (positive), or paid-back (negative)
                # Not used
                continue
            elif record['linieType'] == "22":
                # If return temperature is too high, you have to pay a extra fee.
                continue

        metering_data = {}
        metering_data['energy-total-used'] = energy_total_used
        metering_data['energy-use-prognosis'] =  energy_total_used + energy_prognosis
        metering_data['water-total-used'] = m3_total_used
        metering_data['water-use-prognosis'] = m3_prognosis
        metering_data['amount-remaining'] = amount_remaining

        # Save all relevant other data so it can be extracted by users of the API (like HomeAssistant attributes)
        metering_data['billing'] = {
            "Date": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "MWh-Price" : energy_price,
            "M3-Price" : m3_price,
            "Amount-MWh" : amount_energy,
            "Amount-M3" : m3_prognosis_price,
            "Amount-VAT" : amount_vat,
            "Amount-Total" : amount_total,
            "Amount-Paid" : amount_advance,
            "Amount-Remaining" : amount_remaining,
        }

        _LOGGER.debug(f"Done parsing results")
        return metering_data
