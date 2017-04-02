#!/usr/bin/env python

from __future__ import print_function

import os
import re
import copy
import json
import urllib2
import numpy as np
import matplotlib.pyplot as plt

from datetime import datetime, timedelta
from pytz import timezone
from collections import deque
from itertools import izip, cycle

from line import Stop, Track, Line
from utils import get_epoch_time, get_eastern_time_dt, line_names


def get_first_train_stop (dwell_times):
    """ Function to find the earliest train start in a set of ordered dwell
    times (a train starts at a stop).

    Args:
        dwell_times (dict): dictionary of dwell times. Keys of the dictionary
            are stop IDs. The value of each key is a list of stop dwell
            times ordered with earliest first.

    Returns:
        str: Key of the earliest train.
    """

    start_stop_num = ""
    start_stop_time = int (get_epoch_time (
        timezone ('UTC').localize (
            datetime (year=9999, month=1, day=1))))
    for (key, dt_deque) in dwell_times.iteritems ():
        if dt_deque and int (dt_deque[0]['dep_dt']) < start_stop_time:
            start_stop_time = int (dt_deque[0]['dep_dt'])
            start_stop_num = key
    # print (start_stop_num, start_stop_time)
    return start_stop_num

def get_next_train (train, travel_times, dwell_times):
    """ Function to find the earliest train in a set of ordered travel times and
    dwell times.

    Args:
        train (`Train`): Base train for the searched route
        travel_times (dict): dictionary of travel times. Keys of the dictionary
            are track identifiers. The value of each key is a list of track
            travel times ordered with earliest first.
        dwell_times (dict): dictionary of dwell times. Keys of the dictionary
            are stop identifiers. The value of each key is a list of stop dwell
            times ordered with earliest first.

    Returns:
        `Train`: a train with filled dwell and travel times
    """

    start_stop_num = get_first_train_stop (dwell_times)

    if not start_stop_num:
        return None

    start_dwell = dwell_times[start_stop_num].popleft ()

    # print (train.stops, train.tracks)

    # Get the first stop
    starting_stop = None
    for piece in train:
        if type (piece) is TrainTrack:
            continue
        if piece.stop_id == start_stop_num:
            starting_stop = piece
            break

    starting_stop.load_event (start_dwell)
    train._start = starting_stop
    prev_piece = starting_stop
    next_piece = next (starting_stop)
    while next_piece is not None:
        found_it = False
        if type (next_piece) is TrainTrack:
            dep_t = prev_piece.departure_time

            tt_deque = travel_times[
                (next_piece.prev_stop.stop_id, next_piece.next_stop.stop_id)]

            for tt in tt_deque:
                if abs ((get_eastern_time_dt (tt['dep_dt']) - dep_t).total_seconds ()) < 10:
                    # print ("Found it!")
                    # print (tt)
                    found_it = True
                    next_piece.load_event (tt)
                    tt_deque.remove (tt)
                    break
                elif get_eastern_time_dt (tt['dep_dt']) > dep_t:
                    # print ("Didn't find it ...")
                    break
        else:
            prev_arr_t = prev_piece.arrival_time

            dt_deque = dwell_times[next_piece.stop_id]

            for dt in dt_deque:
                if abs ((get_eastern_time_dt (dt['arr_dt']) - prev_arr_t).total_seconds ()) < 10:
                    # print ("Found it!")
                    # print (dt)
                    found_it = True
                    next_piece.load_event (dt)
                    dt_deque.remove (dt)
                    break
                elif get_eastern_time_dt (dt['arr_dt']) > prev_arr_t:
                    # print ("Didn't find it ...")
                    break

        if not found_it:
            train._end = prev_piece
            break
        else:
            prev_piece = next_piece
            next_piece = next (next_piece)

    return train


class TrainStop (Stop):
    """ This is a class to contain T-stop for a train. """

    def __init__ (self, stop_dict=None, existing_stop=None, event_dict=None):
        """
        Args:
            stop_dict (dict, optional): dict containing stop information. Keys
                include: 'stop_name', 'parent_station_name', 'stop_id',
                'stop_order', 'stop_lon', 'stop_lat'
            existing_stop (:obj:`Stop`, optional): Existing `Stop` to copy
                information to this `Stop`.
            event_dict (dict, optional): dictionary containing dwell information
                for a train stop. Expected keys are: 'arr_dt', 'dep_dt', and
                'dwell_time_sec'
        """

        super (self.__class__, self).__init__ (stop_dict=stop_dict,
                                               existing_stop=existing_stop)

        self._dwell_time = None
        self._arrival_time = None
        self._departure_time = None

        if event_dict is not None:
            self.load_event (event_dict)

    def load_event (self, event_dict):
        """ Function to load a dwell time event.

        Args:
            event_dict (dict): dictionary contained dwell information for a
                train stop. Expected keys are: 'arr_dt', 'dep_dt', and
                'dwell_time_sec'
        """

        arr_time = get_eastern_time_dt (event_dict['arr_dt'])
        dep_time = get_eastern_time_dt (event_dict['dep_dt'])
        self._arrival_time = arr_time
        self._departure_time = dep_time
        self._dwell_time = int (event_dict['dwell_time_sec'])

    def __str__ (self):
        return ('<TrainStop: ' + self.stop_name + '>')

    def __repr__ (self):
        return ('<TrainStop: ' + self.stop_name + '>')

    @property
    def dwell_time (self):
        """ Train dwell time

        Returns:
            float: train dwell time (seconds)
        """

        return self._dwell_time

    @property
    def arrival_time (self):
        """ Train arrival time at stop

        Returns:
            datetime: train arrival time
        """

        return self._arrival_time

    @property
    def departure_time (self):
        """ Train departure time from stop

        Returns:
            datetime: train departure time
        """

        return self._departure_time


class TrainTrack (Track):
    """ This is a class to contain track between a pair of T-stops for a train. """

    def __init__ (self, stop_pair=None, existing_track=None, event_dict=None):
        """
        Args:
            stop_pair (tuple or list, optional): iterable containing a pair of
                :obj:`Stop`s.
            existing_track (:obj:`Track`, optional): Existing `Track` to copy
                information to this `Track`.
            event_dict (dict, optional): dictionary containing travel information
                for between stops. Expected keys are: 'arr_dt', 'dep_dt',
                'travel_time_sec', and 'benchmark_travel_time_sec'
        """

        super (self.__class__, self).__init__ (stop_pair=stop_pair,
                                               existing_track=existing_track)
        self._travel_time = None
        self._benchmark_travel_time = None
        self._departure_time = None
        self._arrival_time = None

        if event_dict is not None:
            self.load_event (event_dict)

    def load_event (self, event_dict):
        """ Function to load a travel time event.

        Args:
            event_dict (dict): dictionary containing travel information for
                between stops. Expected keys are: 'arr_dt', 'dep_dt',
                'travel_time_sec', and 'benchmark_travel_time_sec'
        """

        self._departure_time = get_eastern_time_dt (event_dict['dep_dt'])
        self._arrival_time = get_eastern_time_dt (event_dict['arr_dt'])
        self._travel_time = int (event_dict['travel_time_sec'])
        self._benchmark_travel_time = int (event_dict['benchmark_travel_time_sec'])

    def __str__ (self):
        return ('<TrainTrack: ' + self.prev_stop.stop_name + ' ---- ' +
                self.next_stop.stop_name + '>')

    def __repr__ (self):
        return ('<TrainTrack: ' + self.prev_stop.stop_name + ' ---- ' +
                self.next_stop.stop_name + '>')

    @property
    def travel_time (self):
        """ Train travel time

        Returns:
            float: train travel time (seconds)
        """

        return self._travel_time

    @property
    def benchmark_travel_time (self):
        """ Expected train travel time

        Returns:
            float: expected train travel time (seconds)
        """

        return self._benchmark_travel_time

    @property
    def departure_time (self):
        """ Train departure time from first stop

        Returns:
            datetime: train departure time from first stop
        """

        return self._departure_time


    @property
    def arrival_time (self):
        """ Train arrival time at second stop

        Returns:
            datetime: train arrival time at second stop
        """

        return self._arrival_time


class Train (Line):
    """ This is a class to contain the information of a single T-train as it
    traverses its line.
    """

    def __init__ (self, existing_train=None):
        """
        Args:
            name (str): name of the line
            existing_train (:obj:`Train`, optional): Existing `Train` to copy
                information to this `Train`.
        """

        super (self.__class__, self).__init__ ()
        self._station_dict = None
        if existing_train is not None:
            self.load_existing (existing_train)

    def load_existing (self, existing_train):
        """ Function to copy existing `Train` information to object.

        Args:
            existing_train (:obj:`Train`): Existing `Train` to copy information
                to this `Train`.
        """

        self._name = existing_train.name
        self._direction_id = existing_train.direction_id
        self._direction_name = existing_train.direction_name
        self._stops = existing_train.stops
        self._tracks = existing_train.tracks
        self._start = existing_train.start
        self._end = existing_train.end
        self._current = existing_train._current

    def _get_line_stops (self, line_json, direction_id="0"):
        """ Function to load MBTA JSON stops to `TrackStop`s in the `Train`.

        Args:
            line_json (json): MBTA route JSON
            direction_id (str, optional): direction ID of the desired `Train`
        """

        self._direction_id = direction_id
        for line in line_json['direction']:
            if self.direction_id != line['direction_id']:
                continue
            self._direction_name = line['direction_name']
            self._stops = []
            for stop_dict in line['stop']:
                stop = TrainStop (stop_dict=stop_dict)
                self._stops.append (stop)

            self._start = self._stops[0]
            self._end = self._stops[-1]
            self._current = self.start

            # MBTA API does not yield any travel times for the last leg: just
            # remove
            # last_stop = self._stops.pop ()

    def _get_tracks (self):
        """ Function to load MBTA JSON stops into `TrainTrack`s to `Train`,
        having loaded the `TrainStop`s.
        """

        self._tracks = []
        for (i, stop) in enumerate (self._stops):
            if i == 0:
                continue
            prev_stop = self._stops[i-1]
            track = TrainTrack ((prev_stop, stop))
            prev_stop._next_track = track
            stop._prev_track = track
            self._tracks.append (track)

    def plot_train (self, ax, station_ref_dict):
        """ Function to plot the travel time of a train.

        Args:
            ax (matplotlib.pyplot.Axes): axes to plot travel time to
            station_ref_dict (dict): dictionary of the in-sequence station
                number (value) of a given station name (key). See
                `Train.station_dict`.

        """
        x_coords = []
        y_coords = []

        start_time = self.start.departure_time
        for piece in self:
            try:
                if type (piece) is TrainStop:
                    y_coords.append (
                        (piece.departure_time - start_time).total_seconds () / 60.)
                    x_coords.append (station_ref_dict[piece.station_name])
                else:
                    y_coords.append (
                        (piece.arrival_time - start_time).total_seconds () / 60.)
                    x_coords.append (station_ref_dict[piece.next_stop.station_name])
            except:
                pass

        ax.plot (x_coords, y_coords, color='r', alpha=0.1)
        ax.grid (ls='-', color='grey', alpha=0.3)

    def _set_start (self):
        self._start = self._stops[0]
        for s in self._stops:
            if s._arrival_time is not None:
                self._start = s
                break

    def _set_end (self):
        self._end = self._stops[-1]
        end = None
        for s in self:
            if s._arrival_time is not None:
                end = s
        self._end = end

    def __getitem__ (self, key):
        """ Get selection of `TrainStop`s and `TrainTrack`s

        Args:
            key (int or slice): indices of stops to select.

        Returns:
            `Train`: train with selection of stops and tracks
        """

        stops = self.stops[key]
        stops[0]._prev_track = None
        stops[-1]._next_track = None

        if type (key) is slice:
            try:
                t_key = slice (key.start, key.stop-1)
            except:
                # For the case where the second index is None
                t_key = slice (key.start, key.stop)
            tracks = self.tracks[t_key]
        else:
            tracks = None

        out_t = Train (self)
        out_t._stops = stops
        out_t._tracks = tracks
        out_t._set_start ()
        out_t._current = out_t._start
        out_t._set_end ()
        return out_t

    @property
    def station_dict (self):
        """ In-order number of a station along the line

        Returns:
            dict: in-order number (value) of a given station name (key)
        """

        if self._station_dict is None:
            self._station_dict = {}
            for (i, s) in enumerate (self.stops):
                self._station_dict[s.station_name] = i
                self._station_dict[i] = s.station_name
        return self._station_dict

    @property
    def total_travel_time (self):
        """ End-to-end travel time of the train

        Returns:
            tuple: total travel time, start station index, and end station index
        """

        start_station_num = self.station_dict[self.start.station_name]

        try:
            end_station_num = self.station_dict[self.end.station_name]
        except:
            end_station_num = self.station_dict[self.end.next_stop.station_name]

        # Get travel time
        try:
            start_time = self.start.departure_time
            end_time = self.end.arrival_time
            travel_time = (end_time - start_time).total_seconds ()
        except:
            travel_time = None

        return (travel_time, start_station_num, end_station_num)

class TrainCollection (object):
    """ This is a meta-class to extract and hold a collection of `Train`s from
    the same T-line and direction. """

    def __init__ (self, existing_collection=None):
        """
        Args:
            name (str): name of the line
        """

        if existing_collection is None:
            self._name = None
            self._base_train = None
            self._trains = None
            self._travel_times = None
            self._dwell_times = None
        else:
            self.load_existing (existing_collection)

    def load_existing (self, existing_collection):
        """ Function to copy existing `TrainCollection` information to object.

        Args:
            existing_collection (:obj:`Train`): Existing `TrainCollection` to
                copy information to this `TrainCollection`.
        """

        self._name = existing_collection.name
        self._base_train = existing_collection.base_train
        self._trains = existing_collection.trains
        self._travel_times = existing_collection._travel_times
        self._dwell_times = existing_collection._dwell_times

    def load_base_train (self, path, name, direction_id="0"):
        """ Function to load the base route for the `Train` (see `Train.load`).

        Args:
            path (str): directory path that contains the route JSON (file name
                assumed to be <`Line.name`>.json)
            direction_id (str, optional): direction ID of the desired `Line`
        """

        self._name = name
        self._base_train = Train ()
        self._base_train.load (path, self.name, direction_id=direction_id)

    def load_travel_times (self, travel_times_files):
        """ Function to load the travel times of the train line.

        Args:
            travel_times_files (list): list of files containing the travel times
                obtained by `Train.get_traveltimes`
        """

        self._travel_times = {}
        for f in travel_times_files:
            stops = re.findall (r'_(\d{5})_(\d{5})_', f)[0]

            # check if this stop combo is in the tracks
            is_in_tracks = False
            for track in self._base_train.tracks:
                if stops[0] == track.prev_stop.stop_id and \
                        stops[1] == track.next_stop.stop_id:
                    is_in_tracks = True
            if not is_in_tracks:
                continue

            with open (f) as f_json:
                tt_json = json.load (f_json)
            if stops in self._travel_times:
                self._travel_times[stops].extend (tt_json['travel_times'])
            else:
                self._travel_times[stops] = tt_json['travel_times']

    def load_dwell_times (self, dwell_times_files):
        """ Function to load the dwell times of the train line.

        Args:
            dwell_times_files (list): list of files containing the dwell times
                obtained by `Train.get_dwelltimes`
        """

        self._dwell_times = {}
        for f in dwell_times_files:
            stop_num = re.findall (r'_(\d{5})_', f)[0]

            # check if this stop is in the train stops
            is_in_stops = False
            for stop in self._base_train.stops:
                if stop_num == stop.stop_id:
                    is_in_stops = True
            if not is_in_stops:
                continue

            with open (f) as f_json:
                dt_json = json.load (f_json)
            if stop_num in self._dwell_times:
                self._dwell_times[stop_num].extend (dt_json['dwell_times'])
            else:
                self._dwell_times[stop_num] = dt_json['dwell_times']

    def load_trains (self, num_trains=None):
        """ Function to load all available trains from travel and dwell times.

        Args:
            num_trains (int, optional): number of trains to load
        """

        self._trains = []

        travel_times = copy.deepcopy (self._travel_times)
        dwell_times = copy.deepcopy (self._dwell_times)

        # convert lists to deques for easy popping
        for (key, val) in travel_times.iteritems ():
            travel_times[key] = deque (val)
        for (key, val) in dwell_times.iteritems ():
            dwell_times[key] = deque (val)

        # strategy: peak at the departure times at each station, pop earliest,
        #   then chain through rest of stops to get dwell times and travel times
        if num_trains is None:
            while True:
                train = copy.deepcopy (self._base_train)
                train = get_next_train (train, travel_times, dwell_times)

                try:
                    if not train.tracks:
                        # print ("Empty train ...")
                        continue
                    elif "Red" in train.name and \
                            ("Andrew" in train.start.stop_name or
                            "Andrew" in train.end.stop_name):
                        # print ("Red train from wrong branch. Skipping ...")
                        continue
                    elif "Green" in train.name and \
                            ("Kenmore" in train.start.stop_name or
                            "Kenmore" in train.end.stop_name):
                        continue
                    elif "Green" in train.name and \
                            ("Copley" in train.start.stop_name or
                            "Copley" in train.end.stop_name):
                        continue
                except:
                    pass

                if train is not None:
                    found_t = self._find_same_train (train)
                    if found_t is None:
                        self._trains.append (train)
                else:
                    break

        else:
            count = 0
            while len (self.trains) < num_trains:
                train = copy.deepcopy (self._base_train)
                train = get_next_train (train, travel_times, dwell_times)

                try:
                    if not train.tracks:
                        # print ("Empty train ...")
                        continue
                    elif "Red" in train.name and \
                            ("Andrew" in train.start.stop_name or
                            "Andrew" in train.end.stop_name):
                        # print ("Red train from wrong branch. Skipping ...")
                        continue
                    elif "Green" in train.name and \
                            ("Kenmore" in train.start.stop_name or
                            "Kenmore" in train.end.stop_name):
                        continue
                    elif "Green" in train.name and \
                            ("Copley" in train.start.stop_name or
                            "Copley" in train.end.stop_name):
                        continue
                except:
                    pass

                if train is not None:
                    found_t = self._find_same_train (train)
                    if found_t is None:
                        self._trains.append (train)
                else:
                    break

            # print (self.trains)

    def _merge_trains (self, train1, train2):
        """ Function to merge two trains into one

        Args:
            train1 (Train): first train
            train2 (Train): second train

        Returns:
            `Train`: merged train
        """

        # print ("Found it!")
        train1._end = train2._end
        piece2 = train2.start
        for piece1 in train1:
            try:
                if piece1.stop_name == piece2.stop_name:
                    while piece2 != train2.end:
                        piece1._arrival_time = piece2._arrival_time
                        piece1._departure_time = piece2._departure_time
                        try:
                            piece1._travel_time = piece2._travel_time
                        except:
                            piece1._dwell_time = piece2._dwell_time
                        piece1 = next (piece1)
                        piece2 = next (piece2)
                    return train1
            except:
                continue

    def _find_same_train (self, train):
        """ Function to find if the first leg of a train has already been loaded

        Args:
            train (Train): train to find

        Returns:
            `Train`: merged train if first leg is found, None otherwise
        """

        if self.base_train.station_dict[train.start.station_name] <= 1:
            return None
        else:
            for t in self._trains[::-1]:
                try:
                    station_num_diff = \
                        self.base_train.station_dict[train.start.station_name] - \
                        self.base_train.station_dict[t.end.station_name]
                except:
                    if t.end.next_stop is not None:
                        station_num_diff = \
                            self.base_train.station_dict[train.start.station_name] - \
                            self.base_train.station_dict[t.end.next_stop.station_name]
                    else:
                        continue

                if station_num_diff <= 0:
                    continue
                elif station_num_diff > 4:
                    continue

                time_diff = (train.start.departure_time - t.end.departure_time).total_seconds ()

                if time_diff / station_num_diff >= 30. and time_diff / station_num_diff < 180.:
                    t = self._merge_trains (t, train)
                    # t._end = train.end
                    return t
                elif time_diff / station_num_diff > 1000:
                    return None

    def plot_trains (self, ax, station_ref_dict):
        """ Function to plot the travel times of all `Train`s in the collection.

        Args:
            ax (matplotlib.pyplot.Axes): axes to plot travel time to
            station_ref_dict (dict): dictionary of the in-sequence station
                number (value) of a given station name (key). See
                `Train.station_dict`.

        """

        for t in self.trains:
            if station_ref_dict[t.start.station_name] > 0 and \
                    station_ref_dict[t.start.station_name] < (len (t.stops) - 1):
                continue
            t.plot_train (ax, station_ref_dict)

    def __getitem__ (self, key):
        out_tc = TrainCollection (self)
        out_tc._trains = self.trains[key]
        return out_tc

    def __iter__ (self):
        return iter (self.trains)

    @property
    def name (self):
        """ `TrainCollection` name.

        Returns:
            str: name of the train line
        """

        return self._name

    @property
    def base_train (self):
        """ `TrainCollection` base train.

        Returns:
            `Train`: base train of the line
        """

        return self._base_train

    @property
    def trains (self):
        """ `TrainCollection` trains.

        Returns:
            list: list of `Trains` in the collection
        """

        return self._trains
