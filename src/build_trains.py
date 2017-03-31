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

    for name in line_names[4:]:
        fig = plt.figure ()
        ax = fig.add_subplot (111)
        station_dict = None

        for d in ("0", "1"):
            ts = train.TrainSystem (name)
            ts.load_base_train (lines_dir, direction_id=d)
            print (ts.base_train.stops)
            print (ts.base_train.tracks)

            tt_files = sorted (glob ('{0}/{1}/{1}_{2}*'.format (
                traveltimes_dir, ts.name, d)))
            ts.load_travel_times (tt_files)

            dt_files = sorted (glob ('{0}/{1}/{1}_{2}*'.format (
                dwelltimes_dir, ts.name, d)))
            ts.load_dwell_times (dt_files)

            # ts.load_trains (num_trains=10000)
            ts.load_trains (num_trains=1000)

            if station_dict is None:
                station_dict = ts.base_train.station_dict
            ts.plot_trains (ax, curr_dir, station_dict)
            cache.save (ts, '{0}/{1}.pickle'.format (ana_dir, ts.name))

        ax.set_title (name)
        ax.set_xlabel ('Station Number')
        ax.set_ylabel ('Journey Time (s)')
        fig.savefig ('{0}/{1}_travel_time.pdf'.format (plot_dir, name))

