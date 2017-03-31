#!/usr/bin/env python

from __future__ import print_function

import os
import json
import urllib2
import matplotlib.pyplot as plt

from datetime import datetime
from pytz import timezone
from glob import glob

import cache
import line
import train

from utils import ensure_dir, get_line_stops, line_names, ashmont_branch_stations, \
    braintree_branch_stations

if __name__ == '__main__':
    curr_dir = os.path.dirname (os.path.realpath (__file__))
    lines_dir = '{0}/data/lines'.format (os.path.dirname (curr_dir))
    traveltimes_dir = '{0}/data/traveltimes'.format (os.path.dirname (curr_dir))
    dwelltimes_dir = '{0}/data/dwelltimes'.format (os.path.dirname (curr_dir))
    ana_dir = ensure_dir ('{0}/data/ana'.format (os.path.dirname (curr_dir)))
    plot_dir = ensure_dir ('{0}/plots'.format (os.path.dirname (curr_dir)))

    for name in line_names[:1]:
        fig = plt.figure ()
        ax = fig.add_subplot (111)
        station_dict = None

        for d in ("0", "1"):
            tc = train.TrainCollection (name)
            tc.load_base_train (lines_dir, direction_id=d)

            print (tc.name, tc.base_train.direction_name)
            for p in tc.base_train:
                print (p)

            tt_files = sorted (glob ('{0}/{1}/{1}_{2}*'.format (
                traveltimes_dir, tc.name, d)))
            tc.load_travel_times (tt_files)

            dt_files = sorted (glob ('{0}/{1}/{1}_{2}*'.format (
                dwelltimes_dir, tc.name, d)))
            tc.load_dwell_times (dt_files)

            # tc.load_trains (num_trains=10000)
            tc.load_trains (num_trains=10000)

            if station_dict is None:
                station_dict = tc.base_train.station_dict
            tc.plot_trains (ax, curr_dir, station_dict)
            cache.save (tc, '{0}/{1}_{2}.pickle'.format (ana_dir, name, d))

        ax.set_title (name)
        ax.set_xlabel ('Station Number')
        ax.set_ylabel ('Journey Time (s)')
        fig.savefig ('{0}/{1}_travel_time_test.pdf'.format (plot_dir, name))

