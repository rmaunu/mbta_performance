#!/usr/bin/env python

from __future__ import print_function

import os
import json
import urllib2

from datetime import datetime
from pytz import timezone

import cache
import train

from utils import ensure_dir, get_line_stops, line_names, ashmont_branch_stations, \
    braintree_branch_stations

if __name__ == '__main__':
    curr_dir = os.path.dirname (os.path.realpath (__file__))
    lines_dir = '{0}/data/lines'.format (os.path.dirname (curr_dir))
    traveltimes_dir = '{0}/data/traveltimes'.format (os.path.dirname (curr_dir))
    dwelltimes_dir = '{0}/data/dwelltimes'.format (os.path.dirname (curr_dir))

    for name in line_names:
        for d in ("0", "1"):
            tc = train.TrainCollection ()
            tc.load_base_train (lines_dir, name, direction_id=d)

            # for month in range (1, 4):
            for month in range (7, 13):
                for week in range (2):
                    # start_time = datetime (2016, month, week * 7 + 7, 4, 0, 0)
                    # start_time = timezone ('US/Eastern').localize (start_time)
                    # end_time = datetime (2016, month, week * 7 + 14, 3, 59, 59)
                    # end_time = timezone ('US/Eastern').localize (end_time)
                    start_time = datetime (2017, month, week * 7 + 7, 4, 0, 0)
                    start_time = timezone ('US/Eastern').localize (start_time)
                    end_time = datetime (2017, month, week * 7 + 14, 3, 59, 59)
                    end_time = timezone ('US/Eastern').localize (end_time)

                    tt_out_dir = ensure_dir ('{0}/{1}'.format (traveltimes_dir, name))
                    dt_out_dir = ensure_dir ('{0}/{1}'.format (dwelltimes_dir, name))

                    print ("Getting travel times for", l.name, l.direction_name,
                        "from", start_time.strftime("%Y-%m-%d %H:%M:%S %Z%z"),
                        "to", end_time.strftime("%Y-%m-%d %H:%M:%S %Z%z"), "...")
                    print ("Output saved to", tt_out_dir)
                    tc.base_train.get_traveltimes (tt_out_dir, start_time, end_time)

                    print ("Getting dwell times for", l.name, l.direction_name,
                        "from", start_time.strftime("%Y-%m-%d %H:%M:%S %Z%z"),
                        "to", end_time.strftime("%Y-%m-%d %H:%M:%S %Z%z"), "...")
                    print ("Output saved to", dt_out_dir)
                    tc.base_train.get_dwelltimes (dt_out_dir, start_time, end_time)

