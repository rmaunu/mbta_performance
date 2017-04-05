#!/usr/bin/env python

from __future__ import print_function

import os
import sys
import json
import urllib2

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime
from pytz import timezone

from mbta_performance import train, cache
from mbta_performance.utils import ensure_dir, lines

if __name__ == '__main__':
    curr_dir = os.path.dirname (os.path.realpath (__file__))
    lines_dir = '{0}/data/lines'.format (os.path.dirname (curr_dir))
    traveltimes_dir = '{0}/data/traveltimes_test'.format (os.path.dirname (curr_dir))
    dwelltimes_dir = '{0}/data/dwelltimes_test'.format (os.path.dirname (curr_dir))

    print ("Travel times saved to", traveltimes_dir)
    print ("Dwell times saved to", dwelltimes_dir)

    for l in lines:
        if l.value != 'Green-C':
            continue
        for d in ("0", "1"):
            tc = train.TrainCollection ()
            tc.load_base_train (lines_dir, l, direction_id=d)

            # for month in range (7, 13):
            for month in range (1, 4):
                for week in range (2):
                    start_time = datetime (2016, month, week * 7 + 7, 4, 0, 0)
                    start_time = timezone ('US/Eastern').localize (start_time)
                    end_time = datetime (2016, month, week * 7 + 14, 3, 59, 59)
                    end_time = timezone ('US/Eastern').localize (end_time)
                    # start_time = datetime (2017, month, week * 7 + 7, 4, 0, 0)
                    # start_time = timezone ('US/Eastern').localize (start_time)
                    # end_time = datetime (2017, month, week * 7 + 14, 3, 59, 59)
                    # end_time = timezone ('US/Eastern').localize (end_time)

                    print ("Getting travel times for", tc.base_train.name,
                           tc.base_train.direction_name,
                           "from", start_time.strftime("%Y-%m-%d %H:%M:%S %Z%z"),
                           "to", end_time.strftime("%Y-%m-%d %H:%M:%S %Z%z"), "...")
                    tc.get_traveltimes (traveltimes_dir, start_time, end_time)
                    print ("Getting dwell times for", tc.base_train.name,
                           tc.base_train.direction_name,
                           "from", start_time.strftime("%Y-%m-%d %H:%M:%S %Z%z"),
                           "to", end_time.strftime("%Y-%m-%d %H:%M:%S %Z%z"), "...")
                    tc.get_dwelltimes (dwelltimes_dir, start_time, end_time)
