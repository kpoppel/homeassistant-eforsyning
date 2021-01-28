'''
Primary public module for eforsyning.dk API wrapper.
'''
from datetime import datetime
from datetime import timedelta
import json
import requests
import logging
from .models import RawResponse
from .models import TimeSeries

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
        self._api_server = self._get_api_server()

    def get_customer_data(self):
        result = requests.get(api_server + "api/getebrugerinfo?id=" + crypt_id)
        euser_id = str(result_dict['id'])

        raw_response = RawResponse()
        raw_response.status = result.status_code
        raw_response.body = result.text

        return raw_response


    def get_time_series(self,
                        meetering_point,
                        from_date=None,  # Will be set to yesterday
                        to_date=None,  # Will be set to today
                        aggregation='Hour'):
        '''
        Call time series API on eforsyning.dk. Defaults to yester days data.
        '''
        pass

        if from_date is None:
            from_date = datetime.now()-timedelta(days=1)
        if to_date is None:
            to_date = datetime.now()

        
        access_token = self._get_access_token()

        date_format = '%Y-%m-%d'
        parsed_from_date = from_date.strftime(date_format)
        parsed_to_date = to_date.strftime(date_format)
        body = "{\"meteringPoints\": {\"meteringPoint\": [\"" + meetering_point + "\"]}}"

        headers = self._create_headers(access_token)

        response = requests.post(self._base_url + f'/api/MeterData/GetTimeSeries/ \
                                    {parsed_from_date}/{parsed_to_date}/{aggregation}',
                                 data=body,
                                 headers=headers,
                                 timeout=5
        )

        _LOGGER.debug(f"Response from API. Status: {response.status_code}, Body: {response.text}")

        raw_response = RawResponse()
        raw_response.status = response.status_code
        raw_response.body = response.text

        return raw_response

    def _get_api_server(self):
        ## Get the URL to the REST API service
        settingsURL="/umbraco/dff/dffapi/GetVaerkSettings?forsyningid="
        result = requests.get(self._base_url + settingsURL + self._supplierid)
        result_dict = json.loads(result.text)
        return result_dict['AppServerUri']

    def _get_access_token(self):
        # With the API server URL we can authenticate and get a token:
        security_token_url = "system/getsecuritytoken/project/app/consumer/"
        result = requests.get(self._api_server + security_token_url + self._username)
        result.raise_for_status()
        result_json = token_response.json()
        token = result_json['Token']
        hashed_password = hashlib.md5(password.encode()).hexdigest();
        crypt_string = hashed_password + token
        crypt_id = hashlib.md5(crypt_string.encode()).hexdigest()

        # Use the new token to login to the API service
        auth_url = "system/login/project/app/consumer/"+self._username+"/installation/1/id/"

        result = requests.get(self._api_server + auth_url + crypt_id)
        result.raise_for_status()
        result_json = token_response.json()
        result_status = token_json['Result']
        if result_status['Result'] == 1:
            __LOGGER.debug("Login success\n")
        else:
            __LOGGER.debug("Login failed. Bye.\n")

        _LOGGER.debug(f"Got short lived token: {crypt_id}")
        return crypt_id

    def _create_headers(self): #, access_token):
        return {
                #'Authorization': 'Bearer ' + access_token,
                'Content-Type': 'application/json',
                'Accept': 'application/json'}

    def get_yesterday_parsed(self, metering_point):
        '''
        Get data for yesterday and parse it.
        '''
        pass
        raw_data = self.get_time_series(metering_point)

        if raw_data.status == 200:
            json_response = json.loads(raw_data.body)

            result_dict = self._parse_result(json_response)
            (key, value) = result_dict.popitem()
            result = value
        else:
            result = TimeSeries(raw_data.status, None, None, raw_data.body)

        return result

    def get_latest(self, metering_point):
        '''
        Get latest data. Will look for one week.
        '''
        pass
        raw_data = self.get_time_series(metering_point,
                                        from_date=datetime.now()-timedelta(days=8),
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

        return result

    def _parse_result(self, result):
        '''
        Parse result from API call.
        '''
        pass
        parsed_result = {}

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
