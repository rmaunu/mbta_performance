#!/usr/bin/env python

from __future__ import print_function

import os
import json
import urllib2
import copy

import cache

from utils import get_line_stops, line_names, ashmont_branch_stations, \
    braintree_branch_stations, mbta_traveltime_url, mbta_dwelltime_url, \
    get_epoch_time

class Stop (object):
    def __init__ (self, direction, stop_dict=None, existing_stop=None):
        self._direction = direction
        if not existing_stop is None:
            self.load_existing (existing_stop)
        elif not stop_dict is None:
            self.load_dict (stop_dict)

    def load_dict (self, stop_dict):
        self._stop_name = stop_dict['stop_name']
        self._station_name = stop_dict['parent_station_name']
        self._stop_id = stop_dict['stop_id']
        self._stop_order = stop_dict['stop_order']
        self._lon = stop_dict['stop_lon']
        self._lat = stop_dict['stop_lat']

    def load_existing (self, existing_stop):
        self._stop_name = existing_stop.stop_name
        self._station_name = existing_stop.station_name
        self._stop_id = existing_stop.stop_id
        self._stop_order = existing_stop.stop_order
        self._lon, self._lat = existing_stop.coord

    def __str__ (self):
        return ('<Stop: ' + self.stop_name + '>')

    def __repr__ (self):
        return ('<Stop: ' + self.stop_name + '>')

    @property
    def coord (self):
        return (self._lon, self._lat)

    @property
    def direction (self):
        return self._direction

    @property
    def station_name (self):
        return self._station_name

    @property
    def stop_name (self):
        return self._stop_name

    @property
    def stop_id (self):
        return self._stop_id


class Track (object):
    def __init__ (self, stop_pair=None, existing_track=None):
        if not stop_pair is None:
            self.load_pair (stop_pair)
        elif not existing_track is None:
            self.load_existing (existing_track)

    def load_pair (self, stop_pair):
        self._from_stop = stop_pair[0]
        self._to_stop = stop_pair[1]

    def load_existing (self, existing_track):
        self._from_stop = existing_track.from_stop
        self._to_stop = existing_track.to_stop

    def __str__ (self):
        return ('<Track: ' + self.from_stop.stop_name + ' ---- ' +
                self.to_stop.stop_name + '>')

    def __repr__ (self):
        return ('<Track: ' + self.from_stop.stop_name + ' ---- ' +
                self.to_stop.stop_name + '>')

    @property
    def from_stop (self):
        return self._from_stop

    @property
    def to_stop (self):
        return self._to_stop


class Line (object):
    def __init__ (self, name, existing_line=None):
        self._name = name
        if not existing_line is None:
            self.load_existing (existing_line)
        else:
            self._direction_id = "0"
            self._direction_name = None
            self._stops = None
            self._tracks = None

    def load_existing (existing_line):
        self._direction_id = existing_line.direction_id
        self._direction_name = existing_line.direction_name
        self._stops = existing_line.stops
        self._tracks = existing_line.tracks

    def load (self, path, direction_id="0"):
        filepath = '{0}/{1}.json'.format (path, self.name)
        with open (filepath) as f:
            line_json = json.load (f)
            self._get_line_stops (line_json, direction_id=direction_id)
            self._get_tracks ()

    def _get_line_stops (self, line_json, direction_id="0"):
        self._direction_id = direction_id
        for line in line_json['direction']:
            if self.direction_id != line['direction_id']:
                continue
            self._direction_name = line['direction_name']
            self._stops = []
            for stop_dict in line['stop']:
                stop = Stop (self.direction_name, stop_dict)
                self._stops.append (stop)

            # MBTA API does not yield any travel times for the last leg: just
            # remove
            last_stop = self._stops.pop ()

    def _get_tracks (self):
        self._tracks = []
        for (i, stop) in enumerate (self.stops):
            if i == 0:
                continue
            prev_stop = self.stops[i-1]
            track = Track ((prev_stop, stop))
            self._tracks.append (track)


    def get_traveltimes (self, path, start_time, end_time):
        for track in self.tracks:
            appender = 'from_stop={0}&to_stop={1}&from_datetime={2}&to_datetime={3}'.format (
                track.from_stop.stop_id, track.to_stop.stop_id,
                get_epoch_time (start_time), get_epoch_time (end_time))
            url = mbta_traveltime_url + appender
            tt_json = urllib2.urlopen (url)

            out_file = '{0}/{1}_{2}_{3}_{4}_{5}_{6}.json'.format (
                path, self.name, self.direction_id,
                track.from_stop.stop_id, track.to_stop.stop_id,
                get_epoch_time (start_time),
                get_epoch_time (end_time))

            with open (out_file, 'w') as f:
                f.write (tt_json.read ())

    def get_dwelltimes (self, path, start_time, end_time):
        for stop in self.stops:
            appender = 'stop={0}&from_datetime={1}&to_datetime={2}'.format (
                stop.stop_id, get_epoch_time (start_time),
                get_epoch_time (end_time))
            url = mbta_dwelltime_url + appender

            dt_json = urllib2.urlopen (url)

            out_file = '{0}/{1}_{2}_{3}_{4}_{5}.json'.format (
                path, self.name, self.direction_id,
                stop.stop_id, get_epoch_time (start_time),
                get_epoch_time (end_time))

            with open (out_file, 'w') as f:
                f.write (dt_json.read ())

    @property
    def name (self):
        return self._name

    @property
    def direction_name (self):
        return self._direction_name

    @property
    def direction_id (self):
        return self._direction_id

    @property
    def stops (self):
        return self._stops

    @property
    def tracks (self):
        return self._tracks

