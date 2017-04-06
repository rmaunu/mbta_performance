#!/usr/bin/env python

from __future__ import print_function

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from itertools import izip
from datetime import datetime, timedelta
from mbta_performance import train


class TestTrain (unittest.TestCase):

    def setUp (self):
        pass

    def testBasicTrain (self):
        curr_dir = os.path.dirname (os.path.realpath (__file__))
        lines_dir = '{0}/test_data/lines'.format (curr_dir)

        t = train.Train ()
        for p in t:
            print (p)
        self.assertTrue (t.total_travel_time is None)

        t.load (lines_dir, train.lines.blue)
        for p in t:
            print (p)

        self.assertEqual (len (t.stops), 12)
        self.assertEqual (len (t[:5].stops), 5)
        self.assertEqual (len (t[5].stops), 1)
        self.assertEqual (len (t.tracks), 11)
        self.assertEqual (t.stops[4].station_name, 'Orient Heights')
        self.assertTrue (t.total_travel_time[0] is None)

    def testTrainCollection (self):
        curr_dir = os.path.dirname (os.path.realpath (__file__))
        lines_dir = '{0}/test_data/lines'.format (curr_dir)
        tt_dir = '{0}/test_data/travel_times'.format (curr_dir)
        dt_dir = '{0}/test_data/dwell_times'.format (curr_dir)

        tc = train.TrainCollection ()
        self.assertTrue (tc.base_train is None)

        tc.load_base_train (lines_dir, train.lines.blue)
        for p in tc.base_train:
            print (p)
        for t in tc:
            print (t)

        try:
            for t in tc[:5]:
                print (t)
        except LookupError:
            print ("Caught premature slice")

        try:
            tc.load_trains ()
        except LookupError:
            print ("Caught premature load trains")

        tc.load_travel_times (tt_dir)
        tc.load_dwell_times (dt_dir)

        tc.load_trains (merge=False)
        print (len (tc.trains))
        self.assertEqual (len (tc.trains), 2370)
        for p in tc.trains[-1]:
            print (p)
        print (tc.trains[0].total_travel_time)
        self.assertEqual (tc.trains[0].total_travel_time[0], 1146.)
        self.assertEqual (tc.trains[0].total_travel_time[1], (u'Wonderland', 0))
        self.assertEqual (tc.trains[0].total_travel_time[2], (u'Government Center', 10))

        tc.load_trains (num_trains=100, merge=False)
        self.assertEqual (len (tc.trains), 100)

        tc.load_trains (num_trains=100, merge=True)
        self.assertNotEqual (len (tc.trains), 200)

        tc.load_trains (merge=True)
        print (len (tc.trains))
        self.assertEqual (len (tc.trains), 1374)  # can change based on the the merging criteria. this is likely of x2 the expected value
        for p in tc.trains[-1]:
            print (p)

        self.assertEqual (tc.median_train.total_travel_time[0], 1166.)
        print (tc.median_train.total_travel_time)

if __name__ == '__main__':
    unittest.main ()

