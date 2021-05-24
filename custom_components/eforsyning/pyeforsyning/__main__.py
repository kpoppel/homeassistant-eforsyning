'''
Main for pyeforsyning
'''
import argparse
import logging
from . import Eforsyning

def main():
    '''
    Main method
    '''
    parser = argparse.ArgumentParser("pyeforsyning")
    parser.add_argument("--log", action="store", required=False)
    parser.add_argument("--refresh-token", action="store", required=True)
    parser.add_argument('--metering-point', action='store', required=True)

    args = parser.parse_args()

    _configureLogging(args)

    result = Eforsyning(args.refresh_token).get_latest(args.metering_point)
    if result.status == 200:
        total = 0
        _LOGGER.debug(f"Date: {result.data_date}")
        for hour in range(24):
            data = result.get_metering_data(hour)
            total += data
            _LOGGER.debug(f"Hour {hour}-{hour+1}: {data} MWh")

        _LOGGER.debug(f"Total: {total} MWh")
    else:
        _LOGGER.debug(f"Error getting data. Status: {result.status}. Error: {result.detailed_status}")

def _configureLogging(args):
    if args.log:
        numeric_level = getattr(logging, args.log.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError('Invalid log level: %s' % args.log)
        
        logging.basicConfig(level=numeric_level)

if __name__ == "__main__":
    main()
