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
    times_dir = '{0}/data/times'.format (os.path.dirname (curr_dir))

    print ("Times saved to", times_dir)

    for l in lines:
        if l.value != 'Green-C':
            continue
        for d in ("0", "1"):
            tc = train.TrainCollection ()
            tc.load_base_train (l, direction_id=d)
            tc.set_data_path (times_dir)

            # for month in range (7, 13):
            for month in range (1, 4):
                start_time = datetime (2016, month, 7, 4, 0, 0)
                start_time = timezone ('US/Eastern').localize (start_time)
                end_time = datetime (2016, month, 21, 4, 0, 0)
                end_time = timezone ('US/Eastern').localize (end_time)
                # start_time = datetime (2017, month, week * 7 + 7, 4, 0, 0)
                # start_time = timezone ('US/Eastern').localize (start_time)
                # end_time = datetime (2017, month, week * 7 + 14, 3, 59, 59)
                # end_time = timezone ('US/Eastern').localize (end_time)

                print ("Getting times for", tc.base_train.name,
                        tc.base_train.direction_name,
                        "from", start_time.strftime("%Y-%m-%d %H:%M:%S %Z%z"),
                        "to", end_time.strftime("%Y-%m-%d %H:%M:%S %Z%z"), "...")
                tc.get_times (start_time, end_time)
