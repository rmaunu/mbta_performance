#!/usr/bin/env python

from __future__ import print_function

import os
import json
import urllib2
import copy

import cache

from utils import line_names, ashmont_branch_stations, \
    braintree_branch_stations, mbta_traveltime_url, mbta_dwelltime_url, \
    get_epoch_time


class Stop (object):
    """
    This is a class to contain T-stop information taken from MBTA API.
    """

    def __init__ (self, stop_dict=None, existing_stop=None):
        """
        Args:
            stop_dict (dict, optional): dict containing stop information. Keys
                include: 'stop_name', 'parent_station_name', 'stop_id',
                'stop_order', 'stop_lon', 'stop_lat'
            existing_stop (:obj:`Stop`, optional): Existing `Stop` to copy
                information to this `Stop`.
        """

        self._next_track = None
        self._prev_track = None
        if existing_stop is not None:
            self.load_existing (existing_stop)
        elif stop_dict is not None:
            self.load_dict (stop_dict)

    def load_dict (self, stop_dict):
        """ Function to load stop information to object.

        Args:
            stop_dict (dict): dict containing stop information. Keys include:
                'stop_name', 'parent_station_name', 'stop_id', 'stop_order',
                'stop_lon', 'stop_lat'
        """

        self._stop_name = stop_dict['stop_name']
        self._station_name = stop_dict['parent_station_name']
        self._stop_id = stop_dict['stop_id']
        self._stop_order = stop_dict['stop_order']
        self._lon = stop_dict['stop_lon']
        self._lat = stop_dict['stop_lat']

    def load_existing (self, existing_stop):
        """ Function to copy existing `Stop` information to object.

        Args:
            existing_stop (:obj:`Stop`): Existing `Stop` to copy information to
                this `Stop`.
        """

        self._next_track = copy.deepcopy (existing_stop.next_track)
        self._prev_track = copy.deepcopy (existing_stop.prev_track)
        self._stop_name = copy.deepcopy (existing_stop.stop_name)
        self._station_name = copy.deepcopy (existing_stop.station_name)
        self._stop_id = copy.deepcopy (existing_stop.stop_id)
        self._stop_order = copy.deepcopy (existing_stop.stop_order)
        self._lon, self._lat = existing_stop.coord

    def __str__ (self):
        return ('<Stop: ' + self.stop_name + '>')

    def __repr__ (self):
        return ('<Stop: ' + self.stop_name + '>')

    def __iter__ (self):
        return self

    def next (self):
        return self.next_track

    @property
    def next_track (self):
        """ Next `Track` connected to `Stop`.

        Returns:
            `Track`: next `Track`
        """

        return self._next_track

    @property
    def prev_track (self):
        """ Prev `Track` connected to `Stop`.

        Returns:
            `Track`: previous `Track`
        """

        return self._prev_track

    @property
    def coord (self):
        """ `Stop` coordinates.

        Returns:
            tuple: (`Stop` longitude, `Stop` latitude)
        """

        return (self._lon, self._lat)

    @property
    def station_name (self):
        """ `Stop` station name.

        Returns:
            str: station name
        """

        return self._station_name

    @property
    def stop_name (self):
        """ `Stop` stop name.

        Returns:
            str: stop name
        """

        return self._stop_name

    @property
    def stop_id (self):
        """ `Stop` stop ID.

        Returns:
            str: stop ID
        """

        return self._stop_id


class Track (object):
    """
    This is a class to contain tracks that connect a pair of T-stops, taken
    from MBTA API.
    """

    def __init__ (self, stop_pair=None, existing_track=None):
        """
        Args:
            stop_pair (tuple or list, optional): iterable containing a pair of
                :obj:`Stop`s.
            existing_track (:obj:`Track`, optional): Existing `Track` to copy
                information to this `Track`.
        """

        if stop_pair is not None:
            self.load_pair (stop_pair)
        elif existing_track is not None:
            self.load_existing (existing_track)

    def load_pair (self, stop_pair):
        """ Function to load a `Stop` pair to `Track`.

        Args:
            stop_pair (tuple or list): iterable containing a pair of
                :obj:`Stop`s.
        """

        self._prev_stop = stop_pair[0]
        self._next_stop = stop_pair[1]

    def load_existing (self, existing_track):
        """ Function to copy existing `Track` information to object.

        Args:
            existing_track (:obj:`Track`): Existing `Track` to copy information to
                this `Track`.
        """

        self._prev_stop = copy.deepcopy (existing_track.prev_stop)
        self._next_stop = copy.deepcopy (existing_track.next_stop)

    def __str__ (self):
        return ('<Track: ' + self.prev_stop.stop_name + ' ---- ' +
                self.next_stop.stop_name + '>')

    def __repr__ (self):
        return ('<Track: ' + self.prev_stop.stop_name + ' ---- ' +
                self.next_stop.stop_name + '>')

    def __iter__ (self):
        return self

    def next (self):
        return self.next_stop

    @property
    def prev_stop (self):
        """ Previous `Stop` of `Track`.

        Returns:
            `Stop`: previous `Stop`
        """

        return self._prev_stop

    @property
    def next_stop (self):
        """ Next `Stop` of `Track`.

        Returns:
            `Stop`: next `Stop`
        """

        return self._next_stop


class Line (object):
    """ This is a class to contain the information of a T-line in a single
    direction, taken from MBTA API.
    """

    def __init__ (self, existing_line=None):
        """
        Args:
            name (str): name of the line
            existing_line (:obj:`Line`, optional): Existing `Line` to copy
                information to this `Line`.
        """

        if existing_line is not None:
            self.load_existing (existing_line)
        else:
            self._name = None
            self._direction_id = None
            self._direction_name = None
            self._stops = None
            self._tracks = None
            self._start = None
            self._end = None
            self._current = None

    def load_existing (self, existing_line):
        """ Function to copy existing `Line` information to object.

        Args:
            existing_track (:obj:`Line`): Existing `Line` to copy information to
                this `Line`.
        """

        self._name = copy.deepcopy (existing_line.name)
        self._direction_id = copy.deepcopy (existing_line.direction_id)
        self._direction_name = copy.deepcopy (existing_line.direction_name)
        self._stops = copy.deepcopy (existing_line.stops)
        self._tracks = copy.deepcopy (existing_line.tracks)
        self._start = self._stops[0]
        self._end = self._stops[-1]
        self._current = self._start

    def load (self, path, name, direction_id="0"):
        """ Function to load MBTA route JSON to `Line`.

        Args:
            path (str): directory path that contains the route JSON (file name
                assumed to be <`Line.name`>.json)
            direction_id (str, optional): direction ID of the desired `Line`
        """

        self._name = name

        filepath = '{0}/{1}.json'.format (path, self.name)
        with open (filepath) as f:
            line_json = json.load (f)
            self._get_line_stops (line_json, direction_id=direction_id)
            self._get_tracks ()

    def _get_line_stops (self, line_json, direction_id="0"):
        """ Function to load MBTA JSON stops to `Stop`s in the `Line`.

        Args:
            line_json (json): MBTA route JSON
            direction_id (str, optional): direction ID of the desired `Line`
        """

        self._direction_id = direction_id
        for line in line_json['direction']:
            if self.direction_id != line['direction_id']:
                continue
            self._direction_name = line['direction_name']
            self._stops = []
            for stop_dict in line['stop']:
                stop = Stop (stop_dict)
                self._stops.append (stop)

            self._start = self._stops[0]
            self._end = self._stops[-1]
            self._current = self.start

            # MBTA API does not yield any travel times for the last leg: just
            # remove
            # last_stop = self._stops.pop ()

    def _get_tracks (self):
        """ Function to load MBTA JSON stops into `Track`s to `Line`, having
        loaded the `Stop`s.
        """

        self._tracks = []
        for (i, stop) in enumerate (self._stops):
            if i == 0:
                continue
            prev_stop = self._stops[i-1]
            track = Track ((prev_stop, stop))
            prev_stop._next_track = track
            stop._prev_track = track
            self._tracks.append (track)

    def get_traveltimes (self, path, start_time, end_time):
        """ Function to download MBTA travel time JSONs for a specified time
        period.

        Args:
            path (str): directory to save travel times to
            start_time (datetime): start time of travel times
            end_time (datetime): end time of travel times

        Returns:
            Files of MBTA JSON travel times for each `Track` in the `Line`. File
            name of the form:
                <`Line.name`>_<`Line.direction_id`>_<First Stop ID>_<Second Stop ID>_<Start Time>_<End Time>.json
        """

        for track in self.tracks:
            appender = 'from_stop={0}&to_stop={1}&from_datetime={2}&to_datetime={3}'.format (
                track.prev_stop.stop_id, track.next_stop.stop_id,
                get_epoch_time (start_time), get_epoch_time (end_time))
            url = mbta_traveltime_url + appender

            tt_json = urllib2.urlopen (url)

            out_file = '{0}/{1}_{2}_{3}_{4}_{5}_{6}.json'.format (
                path, self.name, self.direction_id,
                track.prev_stop.stop_id, track.next_stop.stop_id,
                get_epoch_time (start_time),
                get_epoch_time (end_time))

            with open (out_file, 'w') as f:
                f.write (tt_json.read ())

    def get_dwelltimes (self, path, start_time, end_time):
        """ Function to download MBTA train dwell time JSONs for a specified time
        period.

        Args:
            path (str): directory to save dwell times to
            start_time (datetime): start time of travel times
            end_time (datetime): end time of travel times

        Returns:
            Files of MBTA JSON dwell times for each `Stop` in the `Line`. File
            name of the form:
                <`Line.name`>_<`Line.direction_id`>_<Stop ID>_<Start Time>_<End Time>.json
        """

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

    def __getitem__ (self, key):
        """ Get selection of `Stop`s and `Track`s

        Args:
            key (int or slice): indices of stops to select.

        Returns:
            `Line`: train with selection of stops and tracks
        """

        stops = copy.deepcopy (self.stops[key])
        stops[0]._prev_track = None
        stops[-1]._next_track = None

        if type (key) is slice:
            try:
                t_key = slice (key.start, key.stop-1)
            except:
                # For the case where the second index is None
                t_key = slice (key.start, key.stop)
            tracks = copy.deepcopy (self.tracks[t_key])
        else:
            tracks = None

        out_l = Line (self)
        out_l._stops = stops
        out_l._tracks = tracks
        out_l._start = out_l._stops[0]
        out_l._current = out_l._start
        out_l._end = out_l._stops[-1]
        return out_l

    def __iter__ (self):
        self._current = self.start
        return self

    def next (self):
        current_piece = self._current
        if current_piece is None:
            raise StopIteration ()
        elif current_piece == self._end:
            self._current = None
        else:
            self._current = next (self._current)
        return current_piece

    @property
    def name (self):
        """ `Line` name.

        Returns:
            str: line name
        """

        return self._name

    @property
    def direction_name (self):
        """ `Line` direction name.

        Returns:
            str: line direction name
        """

        return self._direction_name

    @property
    def direction_id (self):
        """ `Line` direction ID.

        Returns:
            str: line direction ID
        """

        return self._direction_id

    @property
    def stops (self):
        """ `Line` stops.

        Returns:
            list: list of each `Line` `Stop`
        """

        return self._stops

    @property
    def tracks (self):
        """ `Line` tracks.

        Returns:
            list: list of each `Line` `Track`
        """

        return self._tracks

    @property
    def start (self):
        """ `Line` start

        Returns:
            `Stop`: line start
        """

        return self._start

    @property
    def end (self):
        """ `Line` end

        Returns:
            `Stop` or `Track`: line end
        """

        return self._end

