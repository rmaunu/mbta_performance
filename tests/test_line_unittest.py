#!/usr/bin/env python

from __future__ import print_function

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from itertools import izip
from datetime import datetime, timedelta
from mbta_performance import line

ref_stop = {'stop_name': 'test stop',
            'parent_station_name': 'test station',
            'stop_id': '1', 'stop_order': '0',
            'stop_lon': 100., 'stop_lat': -40.}

ref_stop2 = {'stop_name': 'next test stop',
             'parent_station_name': 'next test station',
             'stop_id': '2', 'stop_order': '1',
             'stop_lon': 100., 'stop_lat': -45.}

class TestLine (unittest.TestCase):

    def setUp (self):
        pass

    def equalStops (self, stop1, stop2):
        self.assertTrue (stop1.stop_name == stop2.stop_name)
        self.assertTrue (stop1.station_name == stop2.station_name)
        self.assertTrue (stop1.stop_id == stop2.stop_id)
        self.assertTrue (stop1.stop_order == stop2.stop_order)
        self.assertTrue (stop1.coord == stop2.coord)

    def unequalStops (self, stop1, stop2):
        self.assertFalse (stop1.stop_name == stop2.stop_name)
        self.assertFalse (stop1.station_name == stop2.station_name)
        self.assertFalse (stop1.stop_id == stop2.stop_id)
        self.assertFalse (stop1.stop_order == stop2.stop_order)
        self.assertFalse (stop1.coord == stop2.coord)

    def testNewStop (self):
        new_stop = line.Stop ()
        new_stop.load_dict (ref_stop)

        new_stop_copy = line.Stop (existing_stop=new_stop)

        new_stop2 = line.Stop ()
        new_stop2.load_dict (ref_stop2)

        self.equalStops (new_stop, new_stop_copy)
        self.unequalStops (new_stop, new_stop2)

    def testNewTrack (self):
        new_stop = line.Stop ()
        new_stop.load_dict (ref_stop)
        new_stop2 = line.Stop ()
        new_stop2.load_dict (ref_stop2)

        new_track = line.Track (stop_pair=(new_stop, new_stop2))
        new_track_copy = line.Track (existing_track=new_track)
        new_track2 = line.Track (stop_pair=(new_stop2, new_stop))

        self.assertEqual (new_track.prev_stop, new_stop)
        self.assertEqual (new_track2.prev_stop, new_stop2)
        self.assertEqual (new_track.next_stop, new_stop2)
        self.assertEqual (new_track2.next_stop, new_stop)
        self.assertEqual (new_track.prev_stop, new_track2.next_stop)
        self.assertEqual (new_track.next_stop, new_track2.prev_stop)

        # copied track is not literally equal, but it's values are the same
        self.assertFalse (new_track.prev_stop == new_track_copy.prev_stop)
        self.equalStops (new_track.prev_stop, new_track_copy.prev_stop)

        self.assertFalse (new_track.next_stop == new_track_copy.next_stop)
        self.equalStops (new_track.next_stop, new_track_copy.next_stop)

    def testLine (self):
        curr_dir = os.path.dirname (os.path.realpath (__file__))
        lines_dir = '{0}/test_data/lines'.format (curr_dir)

        new_line = line.Line ()
        new_line.load (lines_dir, line.lines.blue, direction_id="0")
        new_line_copy = line.Line (existing_line=new_line)
        new_line2 = line.Line ()
        new_line2.load (lines_dir, line.lines.blue, direction_id="1")

        print ("Direction 0 (with copy):")
        for p1, p2 in izip (new_line, new_line_copy):
            if type (p1) is line.Stop:
                self.equalStops (p1, p2)
            else:
                self.equalStops (p1.prev_stop, p2.prev_stop)
                self.equalStops (p1.next_stop, p2.next_stop)
            print (p1, p2)
        print ()

        print ("Direction 0 (slice stops 1 to 5):")
        for p in new_line[1:6]:
            print (p)
        print ()

        print ("Direction 1 (copy):")
        for p in new_line2:
            print (p)
        print ()

    def testGetLineTimes (self):
        curr_dir = os.path.dirname (os.path.realpath (__file__))
        lines_dir = '{0}/test_data/lines'.format (curr_dir)

        new_line = line.Line ()
        new_line.load (lines_dir, line.lines.blue, direction_id="0")

        start_time = datetime (year=2017, month=1, day=10)
        td = timedelta (days=1)
        new_line[:3].get_traveltimes ("./test_data", start_time,
                                      start_time + td, dry=True)
        new_line[:3].get_dwelltimes ("./test_data", start_time,
                                     start_time + td, dry=True)

        try:
            new_line[:3].get_traveltimes ("./test_data", start_time + td,
                                        start_time, dry=True)
        except ValueError:
            print ("Dates in wrong order caught in `get_traveltimes`")

        try:
            new_line[:3].get_dwelltimes ("./test_data", start_time + td,
                                        start_time, dry=True)
        except ValueError:
            print ("Dates in wrong order caught in `get_dwelltimes`")

        start_time = datetime (year=2017, month=1, day=10)
        td = timedelta (days=20)  # Too many days for single query
        new_line[:3].get_traveltimes ("./test_data", start_time,
                                      start_time + td, dry=True)
        new_line[:3].get_dwelltimes ("./test_data", start_time,
                                     start_time + td, dry=True)

if __name__ == '__main__':
    unittest.main ()

