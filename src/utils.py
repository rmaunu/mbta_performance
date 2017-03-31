#!/usr/bin/env python

from __future__ import print_function

import os
import re
import json
import tweepy
import requests
import urllib2

from datetime import datetime, timedelta
from pytz import timezone
from itertools import izip
from bs4 import BeautifulSoup

line_names = ('Red-Ashmont', 'Red-Braintree', 'Orange', 'Blue', 'Green-B',
              'Green-C', 'Green-D', 'Green-E')
ashmont_branch_stations = ('Ashmont', 'Shawmut', 'Fields Corner', 'Savin Hill')
braintree_branch_stations = ('Braintree', 'Quincy Adams', 'Quincy Center',
                             'Wollaston', 'North Quincy')

mbta_stopsbyline_url = \
    'http://realtime.mbta.com/developer/api/v2/stopsbyline?api_key=wX9NwuHnZU2ToO7GmGR9uw'
mbta_traveltime_url = \
    'http://realtime.mbta.com/developer/api/v2.1/traveltimes?api_key=wX9NwuHnZU2ToO7GmGR9uw&format=json&'
mbta_dwelltime_url = \
    'http://realtime.mbta.com/developer/api/v2.1/dwells?api_key=wX9NwuHnZU2ToO7GmGR9uw&format=json&'
twitter_search_url = 'https://twitter.com/search?l=&q=%23MBTA%20'

def get_twitter_api_keys (filepath):
    import ConfigParser
    config = ConfigParser.ConfigParser ()
    config.read (filepath)
    consumer_key = config.get ("keys", "CONSUMER_KEY")
    consumer_secret = config.get ("keys", "CONSUMER_SECRET")
    access_key = config.get ("keys", "ACCESS_KEY")
    access_secret = config.get ("keys", "ACCESS_SECRET")

    return consumer_key, consumer_secret, access_key, access_secret

def get_epoch_time (dt):
    epoch = datetime.utcfromtimestamp(0)
    epoch = timezone('UTC').localize (epoch)
    return str (int ((dt - epoch).total_seconds ()))

def get_eastern_time_dt (utc):
    dt = datetime.utcfromtimestamp (int (utc))
    dt = timezone ('US/Eastern').localize (dt)
    return (dt)

def ensure_dir (path):
    if not os.path.exists (path):
        os.mkdir (path)
    return path

def pairwise(it):
    it = iter(it)
    while True:
        yield next(it), next(it)

def get_line_stops ():
    for line in line_names:
        appender = '&line={0}&format=json'.format (line)
        url = mbta_stopsbyline_url + appender

        line_json = urllib2.urlopen (url)

        curr_dir = os.path.dirname (os.path.realpath (__file__))
        data_dir = ensure_dir ('{0}/data/lines'.format (
            os.path.dirname (curr_dir)
        ))

        with open ('{0}/{1}.json'.format (data_dir, line), 'w') as f:
            f.write (line_json.read ())

def get_dwelltimes (line, start_time, end_time):
    curr_dir = os.path.dirname (os.path.realpath (__file__))
    lines_dir = '{0}/data/lines'.format (os.path.dirname (curr_dir))
    dwelltimes_dir = ensure_dir ('{0}/data/dwelltimes/{1}'.format (
        os.path.dirname (curr_dir), line))

    with open ('{0}/{1}.json'.format (lines_dir, line)) as f:
        line_json = json.load (f)

    for direction in line_json['direction']:
        stops_in_line = []

        for stop in direction['stop']:
            stops_in_line.append (stop['stop_id'])

        for stop in set (stops_in_line):
            appender = 'stop={0}&from_datetime={1}&to_datetime={2}'.format (
                stop, start_time, end_time)
            url = mbta_dwelltime_url + appender

            dt_json = urllib2.urlopen (url)

            with open ('{0}/{1}_{2}_{3}.json'.format (
                    dwelltimes_dir, stop, start_time, end_time), 'w') as f:
                f.write (dt_json.read ())

def get_mbta_tweets_api (username="MBTA"):

    consumer_key, consumer_secret, access_key, access_secret = \
        get_twitter_api_keys ("/home/rmaunu/.twitter/.api_keys")

    curr_dir = os.path.dirname (os.path.realpath (__file__))
    tweets_dir = ensure_dir ('{0}/data/tweets'.format (
        os.path.dirname (curr_dir)))

    auth = tweepy.OAuthHandler (consumer_key, consumer_secret)
    auth.set_access_token (access_key, access_secret)
    api = tweepy.API (auth)

    all_tweets = []

    number_of_tweets = 200

    new_tweets = api.user_timeline (screen_name=username,
                                    count=number_of_tweets)
    all_tweets.extend (new_tweets)
    oldest = all_tweets[-1].id - 1

    # Is only able to download tweets from the last 3 weeks
    # while True: ## iterate through all tweets
    for i in range (1): ## iterate through all tweets
        tweets = api.user_timeline(screen_name=username,
                                   count=number_of_tweets,
                                   max_id=oldest)

        if all_tweets[0] in tweets:
            idx = tweets.index (all_tweets[0])
            all_tweets.extend (tweets[:idx])
            break
        else:
            all_tweets.extend(tweets)
            oldest = all_tweets[-1].id - 1

        # time.sleep (2)

    all_tweets_dict = {}
    all_tweets_dict[u'tweets'] = []
    for tweet in all_tweets:
        tweet_dict = {}
        tweet_dict[str (tweet.id)] = {u'time': get_epoch_time (tweet.created_at),
                                      u'text': tweet.text}
        all_tweets_dict[u'tweets'].append (tweet_dict)

    with open ('{0}/tweets_api.json'.format (tweets_dir), 'w') as f:
        json.dump (all_tweets_dict, f)

    print (all_tweets_dict)

def get_mbta_tweets_scrape (username, start_date, end_date,
                            timestep=timedelta(days=1)):

    curr_dir = os.path.dirname (os.path.realpath (__file__))
    tweets_dir = ensure_dir ('{0}/data/tweets'.format (
        os.path.dirname (curr_dir)))

    date_list = [start_date]
    current_date = start_date
    while current_date < end_date:
        current_date += timestep
        date_list.append (current_date)

    headers = {"user-agent" : "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
                              " (KHTML, like Gecko) Chrome/41.0.2227.0"
                              " Safari/537.36"}

    all_tweets = {}
    all_tweets[u'tweets'] = []

    for dates in pairwise (date_list):
        appender = 'from%3A{0}%20since%3A{1}%20until%3A{2}'.format (
            username, dates[0].strftime ('%Y-%m-%d'), dates[1].strftime ('%Y-%m-%d'))

        url = twitter_search_url + appender

        page = requests.get (twitter_search_url + appender, headers=headers)
        soup = BeautifulSoup (page.text, "html.parser")

        divs = soup.find_all ('div', {"class" : "tweet"})
        timestamps = soup.find_all ('span', {"class" : "js-short-timestamp"})
        for div, timestamp in izip (divs, timestamps):
            tweet = {}
            tweet[div[u'data-tweet-id']] = {}
            tweet[div[u'data-tweet-id']]['time'] = timestamp['data-time']
            ps = div.find_all ("p", {"class": "tweet-text"})
            for p in ps:
                tweet[div[u'data-tweet-id']][u'text'] = p.text

            all_tweets[u'tweets'].append (tweet)

    with open ('{0}/tweets_scraped_{1}_{2}.json'.format (
            tweets_dir, get_epoch_time (start_date),
            get_epoch_time (end_date)), 'w') as f:
        json.dump (all_tweets, f)
