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
    def __init__(self, username, password, supplierid):
        self._username = username
        self._password = password
        self._supplierid = supplierid
        self._base_url = 'https://eforsyning.dk/'
        self._api_server = ""
        ## Assume people only have a single metering device.
        ## Feel free to expand the code to find all metering devices
        ## and iterate over them.
        asset_id = 1
        installation_id = 1

#    def _get_customer_data(self):
#        result = requests.get(api_server + "api/getebrugerinfo?id=" + crypt_id)
#        euser_id = str(result_dict['id'])
#
#        raw_response = RawResponse()
#        raw_response.status = result.status_code
#        raw_response.body = result.text
#
#        return raw_response


    def _get_time_series(self,
                        from_date=None,  # Will be set to yesterday
                        to_date=None,    # Will be set to today
                        year = "0",
                        month = False,
                        day = False,
                        include_expected_reading = True
                       ):
        '''
        Call time series API on eforsyning.dk. Defaults to yesterdays data.
        '''
        _LOGGER.debug(f"get the time series")

        if from_date is None:
            from_date = datetime.now()-timedelta(days=1)
        if to_date is None:
            to_date = datetime.now()

        _LOGGER.debug(f"1")
        
        access_token = self._get_access_token()

        _LOGGER.debug(f"2")

        date_format = '%d-%m-%Y'
        parsed_from_date = from_date.strftime(date_format)
        parsed_to_date = to_date.strftime(date_format)

        _LOGGER.debug(f"3")

        headers = self._create_headers(access_token)

        _LOGGER.debug(f"4")

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

        _LOGGER.debug(f"Data for POST: {data}")

        result = requests.post(self._api_server + post_meter_data_url,
                                data = json.dumps(data),
                                timeout = 5,
                                headers=headers
                              )

        _LOGGER.debug(f"Response from API. Status: {result.status_code}, Body: {result.text}")

        raw_response = RawResponse()
        raw_response.status = result.status_code
        raw_response.body = result.text

        _LOGGER.debug(f"Done getting the time series")

        return raw_response

    def _get_api_server(self):
        _LOGGER.debug(f"getting api server")
        ## Get the URL to the REST API service
        settingsURL="/umbraco/dff/dffapi/GetVaerkSettings?forsyningid="
        result = requests.get(self._base_url + settingsURL + self._supplierid)
        result_json = result.json()
        _LOGGER.debug(f"result JSON {result_json}")
        api_server = result_json['AppServerUri']

        _LOGGER.debug(f"Done getting api server {api_server}")

        return api_server

    def _get_access_token(self):
        _LOGGER.debug(f"getting access token")

        if self._api_server == "":
            self._api_server = self._get_api_server()

        # With the API server URL we can authenticate and get a token:
        security_token_url = self._api_server + "system/getsecuritytoken/project/app/consumer/" + self._username
        _LOGGER.debug(f"token URL: {security_token_url}")
        result = requests.get(security_token_url)
        result.raise_for_status()
        result_json = result.json()
        token = result_json['Token']
        _LOGGER.debug(f"result for token: {result_json} - {token}")
        ## TODO exception if token is ''
        hashed_password = hashlib.md5(self._password.encode()).hexdigest()
        crypt_string = hashed_password + token
        access_token = hashlib.md5(crypt_string.encode()).hexdigest()

        _LOGGER.debug(f"access token: {access_token}")

        # Use the new token to login to the API service
        auth_url = "system/login/project/app/consumer/"+self._username+"/installation/1/id/"

        result = requests.get(self._api_server + auth_url + access_token)
        result.raise_for_status()
        result_json = result.json()
        result_status = result_json['Result']
        if result_status['Result'] == 1:
            _LOGGER.debug("Login success\n")
        else:
            _LOGGER.debug("Login failed. Bye.\n")

        _LOGGER.debug(f"Got access token: {access_token}")
        return access_token

    def _create_headers(self): #, access_token):
        return {
                #'Authorization': 'Bearer ' + access_token,
                'Content-Type': 'application/json',
                'Accept': 'application/json'}

#    def get_yesterday_parsed(self, metering_point):
#        '''
#        Get data for yesterday and parse it.
#        '''
#        return
#
#        raw_data = self.get_time_series(metering_point)
#
#        if raw_data.status == 200:
#            json_response = json.loads(raw_data.body)
#
#            result_dict = self._parse_result(json_response)
#            (key, value) = result_dict.popitem()
#            result = value
#        else:
#            result = TimeSeries(raw_data.status, None, None, raw_data.body)
#
#        return result

    def get_latest(self):
        '''
        Get latest data. Will look for one day except eforsyning returns for a full year.
        '''
        _LOGGER.debug(f"Getting latest data")

        raw_data = self._get_time_series(year="2020",
                                         day=True,
                                         from_date=datetime.now()-timedelta(days=1),
                                         to_date=datetime.now())

        _LOGGER.debug(f"Getting latest data")

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

    def _parse_result(self, result):
        '''
        Parse result from API call.
        '''
        _LOGGER.debug(f"Parsing results")
        parsed_result = {}

        metering_data = {}
        metering_data['temp-forward'] = random.randint(0, 100)
        metering_data['temp-return'] = random.randint(0, 100)
        metering_data['temp-exp-return'] = random.randint(0, 100)
        metering_data['temp-meas-return'] = random.randint(0, 100)
        metering_data['energy-start'] = random.randint(0, 100)
        metering_data['energy-end'] = random.randint(0, 100)
        metering_data['energy-used'] = random.randint(0, 100)
        metering_data['energy-exp-used'] = random.randint(0, 100)
        metering_data['energy-exp-end'] = random.randint(0, 100)
        metering_data['water-start'] = random.randint(0, 100)
        metering_data['water-end'] = random.randint(0, 100)
        metering_data['water-used'] = random.randint(0, 100)
        metering_data['water-exp-used'] = random.randint(0, 100)
        metering_data['water-exp-end'] = random.randint(0, 100)

        time_series = TimeSeries(200, "20200128", metering_data)
        parsed_result['20200128'] = time_series
        _LOGGER.debug(f"Done parsing results")
        return parsed_result

        if 'result' in result and len(result['result']) > 0:
            market_document = result['result'][0]['MyEnergyData_MarketDocument']
            if 'TimeSeries' in market_document and len(market_document['TimeSeries']) > 0:
                time_series = market_document['TimeSeries'][0]

                if 'Period' in time_series and len(time_series['Period']) > 0:
                    for period in time_series['Period']:
                        metering_data = []

                        point = period['Point']
                        for i in point:
                            metering_data.append(float(i['out_Quantity.quantity']))

                        date = datetime.strptime(period['timeInterval']['end'], '%Y-%m-%dT%H:%M:%SZ')

                        time_series = TimeSeries(200, date, metering_data)

                        parsed_result[date] = time_series
                else:
                    parsed_result['none'] = TimeSeries(404,
                                                       None,
                                                       None,
                                                       f"Data most likely not available yet-1: {result}")
            else:
                parsed_result['none'] = TimeSeries(404,
                                                   None,
                                                   None,
                                                   f"Data most likely not available yet-2: {result}")
        else:
            parsed_result['none'] =  TimeSeries(404,
                                                None,
                                                None,
                                                f"Data most likely not available yet-3: {result}")

        return parsed_result
