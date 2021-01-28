'''
All model classes for pyeforsyning
'''

class RawResponse:
    '''
    Class representing a raw response by http status code and http body.
    '''
    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, status):
        self._status = status

    @property
    def response(self):
        return self._response

    @response.setter
    def response(self, response):
        self._response = response

class TimeSeries:
    '''
    Class representing a parsed time series data for a single day.
    '''
    def __init__(self, status, data_date, metering_data, detailed_status=None):
        self._status = status
        self._data_date = data_date
        self._metering_data = metering_data
        self._detailed_status = detailed_status

    @property
    def status(self):
        return self._status

    @property
    def detailed_status(self):
        return self._detailed_status
    
    @property
    def data_date(self):
        return self._data_date
    
    def get_metering_data(self, hour):
        '''
        Get metering data for a single hour.
        hour=1: data between 00.00 and 01.00.
        hour=4: data between 03.00 and 04.00.
        '''
        return self._metering_data[hour-1]

    def get_total_metering_data(self):
        total = 0
        for v in self._metering_data:
            total += v

        return total