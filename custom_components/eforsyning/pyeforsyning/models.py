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
    
    def get_data_point(self, data_point):
        """ Legal data points to ask for (for regional heating) are:
                ['temp-forward']
                ['temp-return']
                ['temp-exp-return']
                ['temp-cooling']
                ['energy-start']
                ['energy-end']
                ['energy-used']
                ['energy-exp-used']
                ['energy-exp-end']
                ['water-start']
                ['water-end']
                ['water-used']
                ['water-exp-used']
                ['water-exp-end']

            For water metering:
                ['water-start']
                ['water-end']
                ['water-used']
                ['water-exp-used']
                ['water-exp-end']
                ['water-ytd-used']
                ['water-exp-ytd-used']
        """
        return self._metering_data[data_point]