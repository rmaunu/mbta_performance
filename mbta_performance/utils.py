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
from enum import Enum

ashmont_branch_stations = ('Ashmont', 'Shawmut', 'Fields Corner', 'Savin Hill')
braintree_branch_stations = ('Braintree', 'Quincy Adams', 'Quincy Center',
                             'Wollaston', 'North Quincy')

class lines (Enum):
    red_ashmont = 'Red-Ashmont'
    red_braintree = 'Red-Braintree'
    orange = 'Orange'
    blue = 'Blue'
    green_b = 'Green-B'
    green_c = 'Green-C'
    green_d = 'Green-D'
    green_e = 'Green-E'

mbta_traveltime_url = \
    'http://realtime.mbta.com/developer/api/v2.1/traveltimes?api_key=wX9NwuHnZU2ToO7GmGR9uw&format=json&'
mbta_dwelltime_url = \
    'http://realtime.mbta.com/developer/api/v2.1/dwells?api_key=wX9NwuHnZU2ToO7GmGR9uw&format=json&'
twitter_search_url = 'https://twitter.com/search?l=&q=%23MBTA%20'

def get_epoch_time (dt):
    epoch = datetime.utcfromtimestamp(0)
    epoch = timezone('UTC').localize (epoch)
    try:
        out_str = str (int ((dt - epoch).total_seconds ()))
    except:
        dt = timezone('UTC').localize (dt)
        out_str = str (int ((dt - epoch).total_seconds ()))

    return out_str

def get_eastern_time_utc (utc):
    """ Function to get Eastern Time `datetime` of a given UTC time stamp.

    Args:
        utc (int or str): UTC time stamp

    Returns:
        `datetime`: Eastern Time localized `datetime` of UTC time stamp
    """
    dt = datetime.utcfromtimestamp (int (utc))
    dt = timezone ('UTC').localize (dt)
    dt = dt.astimezone (timezone ('US/Eastern'))
    return (dt)

def localize_eastern_dt (dt):
    """ Function to localize given datetime to US Eastern Time.

    Args:
        dt (`datetime`): Input `datetime`

    Returns:
        `datetime`: Same `datetime` but localized to Eastern Time if the time
            zone had not been set, or converted to Eastern Time if another time
            zone was set.
    """

    if dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None:
        dt = dt.astimezone (timezone ('US/Eastern'))
    else:
        dt = timezone ('US/Eastern').localize (dt)

    return dt


def ensure_dir (path):
    """Make sure ``path`` exists and is a directory."""

    if not os.path.isdir (path):
        try:
            os.makedirs (path)   # throws if exists as file
        except OSError as e:
            if e.errno != os.errno.EEXIST:
                raise
    return path

def pairwise (it):
    it = iter(it)
    while True:
        yield next(it), next(it)

def get_twitter_api_keys (filepath):
    import ConfigParser
    config = ConfigParser.ConfigParser ()
    config.read (filepath)
    consumer_key = config.get ("keys", "CONSUMER_KEY")
    consumer_secret = config.get ("keys", "CONSUMER_SECRET")
    access_key = config.get ("keys", "ACCESS_KEY")
    access_secret = config.get ("keys", "ACCESS_SECRET")

    return consumer_key, consumer_secret, access_key, access_secret

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
