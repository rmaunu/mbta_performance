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
    start_stop_num = get_first_train_stop (dwell_times)

    if not start_stop_num:
        return None

    start_dwell = dwell_times[start_stop_num].popleft ()

    # print (train.stops, train.tracks)

    # remove stops before the starting train position
    for stop, track in zip (train._stops, train._tracks):
        if stop.stop_id == start_stop_num:
            break
        else:
            train._stops.remove (stop)
            train._tracks.remove (track)

    if len (train.stops) == 1:
        # print ("Empty train ...")
        train._stops[0].load_event (start_dwell)
        return train

    finished_track = True
    for (i, (stop, track)) in enumerate (
            zip (train._stops, train._tracks)):
        # print (stop, track)
        if i == 0:
            stop.load_event (start_dwell)
            dep_t = stop.departure_time

            tt_deque = travel_times[
                (track.from_stop.stop_id, track.to_stop.stop_id)]

            have_found_tt = False
            for tt in tt_deque:
                if abs ((get_eastern_time_dt (tt['dep_dt']) - dep_t).seconds) < 10:
                    # print ("Found it!")
                    # print (tt)
                    have_found_tt = True
                    track.load_event (tt)
                    tt_deque.remove (tt)
                    break
                elif get_eastern_time_dt (tt['dep_dt']) > dep_t:
                    # print ("Didn't find it ...")
                    break

            if not have_found_tt:
                train._tracks.remove (track)
                finished_track = False
                continue
        elif not finished_track:
            train._stops.remove (stop)
            train._tracks.remove (track)
        else:
            prev_arr_t = train._tracks[i-1].arrival_time

            dt_deque = dwell_times[stop.stop_id]

            have_found_dt = False
            for dt in dt_deque:
                if abs ((get_eastern_time_dt (tt['arr_dt']) - prev_arr_t).seconds) < 10:
                    # print ("Found it!")
                    # print (dt)
                    have_found_dt = True
                    stop.load_event (dt)
                    dt_deque.remove (dt)
                    break
                elif get_eastern_time_dt (tt['arr_dt']) > prev_arr_t:
                    # print ("Didn't find it ...")
                    break

            if not have_found_dt:
                train._stops.remove (stop)
                train._tracks.remove (track)
                finished_track = False
                continue

            dep_t = stop.departure_time

            tt_deque = travel_times[
                (track.from_stop.stop_id, track.to_stop.stop_id)]

            have_found_tt = False
            for tt in tt_deque:
                if abs ((get_eastern_time_dt (tt['dep_dt']) - dep_t).seconds) < 60:
                    # print ("Found it!")
                    # print (tt)
                    have_found_tt = True
                    track.load_event (tt)
                    tt_deque.remove (tt)
                    break
                elif get_eastern_time_dt (tt['dep_dt']) > dep_t:
                    # print ("Didn't find it ...")
                    break

            if not have_found_tt:
                # print ("Did not finish...")
                train._tracks.remove (track)
                finished_track = False
                continue

    if finished_track:
        # Get dwell time for last stop in line
        stop = train._stops[-1]
        # print (stop)

        prev_arr_t = train._tracks[-1].arrival_time

        dt_deque = dwell_times[stop.stop_id]

        have_found_dt = False
        for dt in dt_deque:
            if abs ((get_eastern_time_dt (tt['arr_dt']) - prev_arr_t).seconds) < 10:
                # print ("Found it!")
                # print (dt)
                have_found_dt = True
                stop.load_event (dt)
                dt_deque.remove (dt)
                break
            elif get_eastern_time_dt (tt['arr_dt']) > prev_arr_t:
                # print ("Didn't find it ...")
                break

        if not have_found_dt:
            train._stops.remove (stop)
    else:
        # Pop last stop in line
        train._stops.pop ()

        # Get dwell time for last stop if not filled
        stop = train._stops[-1]
        if stop.dwell_time is None:
            # print (stop)
            prev_arr_t = train._tracks[-1].arrival_time

            dt_deque = dwell_times[stop.stop_id]

            have_found_dt = False
            for dt in dt_deque:
                if abs ((get_eastern_time_dt (tt['arr_dt']) - prev_arr_t).seconds) < 10:
                    # print ("Found it!")
                    # print (dt)
                    have_found_dt = True
                    stop.load_event (dt)
                    dt_deque.remove (dt)
                    break
                elif get_eastern_time_dt (tt['arr_dt']) > prev_arr_t:
                    # print ("Didn't find it ...")
                    break

            if not have_found_dt:
                train._stops.remove (stop)

    return train


class TrainStop (Stop):

    def __init__ (self, direction, stop_dict=None, existing_stop=None,
                  event_dict=None):
        super (self.__class__, self).__init__ (direction, stop_dict=stop_dict,
                                               existing_stop=existing_stop)

        self._dwell_time = None
        self._arrival_time = None
        self._departure_time = None

        if not event_dict is None:
            self.load_event (event_dict)

    def load_event (self, event_dict):
        arr_time = get_eastern_time_dt (event_dict['arr_dt'])
        dep_time = get_eastern_time_dt (event_dict['dep_dt'])
        self._arrival_time = arr_time
        self._departure_time = dep_time
        self._dwell_time = int (event_dict['dwell_time_sec'])

    @property
    def dwell_time (self):
        return self._dwell_time

    @property
    def arrival_time (self):
        return self._arrival_time

    @property
    def departure_time (self):
        return self._departure_time

    def __str__ (self):
        return ('<TrainStop: ' + self.stop_name + '>')

    def __repr__ (self):
        return ('<TrainStop: ' + self.stop_name + '>')


class TrainTrack (Track):

    def __init__ (self, stop_pair=None, existing_track=None, event_dict=None):
        super (self.__class__, self).__init__ (stop_pair=stop_pair,
                                               existing_track=existing_track)
        self._travel_time = None
        self._benchmark_travel_time = None
        self._departure_time = None
        self._arrival_time = None

        if not event_dict is None:
            self.load_event (event_dict)

    def load_event (self, event_dict):
        dep_time = get_eastern_time_dt (event_dict['dep_dt'])
        arr_time = get_eastern_time_dt (event_dict['arr_dt'])
        self._departure_time = dep_time
        self._arrival_time = arr_time

        self._travel_time = int (event_dict['travel_time_sec'])
        self._benchmark_travel_time = int (event_dict['benchmark_travel_time_sec'])

    def __str__ (self):
        return ('<TrainTrack: ' + self.from_stop.stop_name + ' ---- ' +
                self.to_stop.stop_name + '>')

    def __repr__ (self):
        return ('<TrainTrack: ' + self.from_stop.stop_name + ' ---- ' +
                self.to_stop.stop_name + '>')

    @property
    def travel_time (self):
        return self._travel_time

    @property
    def benchmark_travel_time (self):
        return self._benchmark_travel_time

    @property
    def arrival_time (self):
        return self._arrival_time

    @property
    def departure_time (self):
        return self._departure_time


class Train (Line):

    def __init__ (self, name, existing_train=None):
        super (self.__class__, self).__init__ (name)
        self._station_dict = None

    def load_train (existing_train):
        self._direction_id = existing_line.direction_id
        self._direction_name = existing_line.direction_name
        self._stops = existing_line.stops
        self._tracks = existing_line.tracks

    def _get_line_stops (self, line_json, direction_id="0"):
        self._direction_id = direction_id
        for line in line_json['direction']:
            if self.direction_id != line['direction_id']:
                continue
            self._direction_name = line['direction_name']
            self._stops = []
            for stop_dict in line['stop']:
                stop = TrainStop (self.direction_name, stop_dict)
                self._stops.append (stop)

            # MBTA API does not yield any travel times for the last leg: just
            # remove
            # last_stop = self._stops.pop ()

    def _get_tracks (self):
        self._tracks = []
        for (i, stop) in enumerate (self.stops):
            if i == 0:
                continue
            prev_stop = self.stops[i-1]
            track = TrainTrack ((prev_stop, stop))
            self._tracks.append (track)

    def plot_train (self, ax, station_ref_dict):
        stop_idx = []
        iters = [iter (self.stops), iter(self.tracks)]
        stop_tracks = list (it.next () for it in cycle (iters))

        x_coords = []
        y_coords = []

        stop_count = 0
        total_time = 0
        for st in stop_tracks:
            if type (st) is TrainStop:
                x_coords.append (station_ref_dict[st.station_name])
                if stop_count != 0:
                    total_time += st.dwell_time
                y_coords.append (total_time)
                stop_count += 1
            else:
                total_time += st.travel_time
                x_coords.append (station_ref_dict[st.to_stop.station_name])
                y_coords.append (total_time)

        ax.plot (x_coords, y_coords, color='r', alpha=0.1)
        ax.grid (ls='-', color='grey', alpha=0.3)

    @property
    def station_dict (self):
        if self._station_dict is None:
            self._station_dict = {}
            for (i, s) in enumerate (self.stops):
                self._station_dict[s.station_name] = i
        return self._station_dict

class TrainSystem (object):

    def __init__ (self, name):
        self._name = name
        self._base_train = None
        self._trains = None
        self._travel_times = None
        self._dwell_times = None

    def load_base_train (self, lines_dir, direction_id="0"):
        self._base_train = Train (self.name)
        self._base_train.load (lines_dir, direction_id=direction_id)

    def load_travel_times (self, travel_times_files):
        self._travel_times = {}
        for f in travel_times_files:
            stops = re.findall (r'_(\d{5})_(\d{5})_', f)[0]

            # check if this stop combo is in the tracks
            is_in_tracks = False
            for track in self._base_train.tracks:
                if stops[0] == track.from_stop.stop_id and \
                        stops[1] == track.to_stop.stop_id:
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

                if not train.tracks:
                    # print ("Empty train ...")
                    continue
                elif "Red" in train.name and "Andrew" in train.stops[-1].stop_name:
                    # print ("Red train from wrong branch. Skipping ...")
                    continue

                if not train is None:
                    self._trains.append (train)
                else:
                    break

        else:
            count = 0
            while len (self.trains) < num_trains:
                train = copy.deepcopy (self._base_train)
                train = get_next_train (train, travel_times, dwell_times)

                if not train.tracks:
                    # print ("Empty train ...")
                    continue
                elif "Red" in train.name and "Andrew" in train.stops[-1].stop_name:
                    # print ("Red train from wrong branch. Skipping ...")
                    continue
                elif "Green" in train.name and "Kenmore" in train.stops[-1].stop_name:
                    continue
                elif "Green" in train.name and "Copley" in train.stops[-1].stop_name:
                    continue

                if not train is None:
                    self._trains.append (train)
                else:
                    break

            # print (self.trains)

    def plot_trains (self, ax, plot_dir, station_ref_dict):
        for t in self.trains:
            if station_ref_dict[t.stops[0].station_name] > 0 and \
                    station_ref_dict[t.stops[0].station_name] < len (station_ref_dict.keys ()) - 1 :
                continue
            t.plot_train (ax, station_ref_dict)

    @property
    def name (self):
        return self._name

    @property
    def base_train (self):
        return self._base_train

    @property
    def trains (self):
        return self._trains

if __name__ == '__main__':
        for route in route_names:
            print ("Getting", route, "line performace data from",
                   start_time.strftime("%Y-%m-%d %H:%M:%S %Z%z"), "to",
                   end_time.strftime("%Y-%m-%d %H:%M:%S %Z%z"))
            get_traveltimes (route, get_epoch_time (start_time),
                             get_epoch_time (end_time))
            get_dwelltimes (route, get_epoch_time (start_time),
                            get_epoch_time (end_time))
