#!/usr/bin/env python

from __future__ import print_function

import time

from datetime import datetime
from pytz import timezone
from utils import get_mbta_tweets_api, get_mbta_tweets_scrape

if __name__ == '__main__':
    # get_mbta_tweets_api ()

    for month in range (1, 13):
        start_time = datetime (2016, month, 15, 4, 0, 0)
        start_time = timezone ('US/Eastern').localize (start_time)
        end_time = datetime (2016, month, 22, 3, 59, 59)
        end_time = timezone ('US/Eastern').localize (end_time)

        print ("Getting MBTA tweets from",
               start_time.strftime("%Y-%m-%d %H:%M:%S %Z%z"), "to",
               end_time.strftime("%Y-%m-%d %H:%M:%S %Z%z"))

        get_mbta_tweets_scrape ("MBTA", start_time, end_time)

        time.sleep (120)