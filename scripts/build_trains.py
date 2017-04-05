#!/usr/bin/env python

from __future__ import print_function

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
import urllib2
import matplotlib.pyplot as plt

from datetime import datetime
from pytz import timezone
from glob import glob

from mbta_performance import cache
from mbta_performance import line
from mbta_performance import train
from mbta_performance.utils import ensure_dir, lines

if __name__ == '__main__':
    curr_dir = os.path.dirname (os.path.realpath (__file__))
    lines_dir = '{0}/data/lines'.format (os.path.dirname (curr_dir))
    traveltimes_dir = '{0}/data/traveltimes'.format (os.path.dirname (curr_dir))
    dwelltimes_dir = '{0}/data/dwelltimes'.format (os.path.dirname (curr_dir))
    ana_dir = ensure_dir ('{0}/data/ana'.format (os.path.dirname (curr_dir)))
    plot_dir = ensure_dir ('{0}/plots'.format (os.path.dirname (curr_dir)))

    # for name in line_names[4:]:
    # for name in line_names[:1]:
    for l in lines:
        if 'Blue' in l.value:
            continue
        fig = plt.figure ()
        ax = fig.add_subplot (111)
        fig.subplots_adjust(bottom=0.4)
        station_dict = None

        for d in ("0", "1"):
            tc = train.TrainCollection ()
            tc.load_base_train (lines_dir, l, direction_id=d)

            print (tc.name, tc.base_train.direction_name)
            for p in tc.base_train:
                print (p)

            tc.load_travel_times (traveltimes_dir)
            tc.load_dwell_times (dwelltimes_dir)

            tc.load_trains (num_trains=10000)
            # tc.load_trains (num_trains=1000)

            if station_dict is None:
                station_dict = tc.base_train.station_dict
            tc.plot_trains (ax, station_dict)
            cache.save (tc, '{0}/{1}_{2}.pickle'.format (
                ana_dir, tc.name, tc.base_train.direction_name))

        x_locs = range (len (tc.base_train.stops))
        x_labs = [station_dict[i] for i in x_locs]

        ax.set_xlim (x_locs[0], x_locs[-1])
        ax.set_ylim (ymin=0)
        ax.set_xticks (x_locs)
        ax.set_xticklabels (x_labs, rotation=90.)
        ax.set_title (l.value)
        ax.set_ylabel ('Journey Time (minutes)')
        fig.savefig ('{0}/{1}_travel_time.pdf'.format (plot_dir, l.value))

