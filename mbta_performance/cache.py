#!/usr/bin/env python

from __future__ import print_function

import os
import socket
import time
import cPickle as pickle

def save (obj, filename):
    """Dump `obj` to `filename` using the pickle module."""

    outdir, outfile = os.path.split (filename)
    save_id = '{0}_nixtime_{2:.0f}_job_{1}'.format (
        socket.gethostname (), os.getpid (), time.time ())
    temp_filename = os.path.join (outdir, '.part_{0}_id_{1}'.format (
        outfile, save_id))

    with open (temp_filename, 'wb') as f:
        pickle.dump (obj, f, -1)

    os.rename (temp_filename, filename)


def resave (obj):
    """Dump `obj` to the filename from which it was loaded."""

    save (obj, obj.__cache_source_filename)


def load (filename):
    """Load `filename` using the pickle module."""

    with open (filename) as f:
        out = pickle.load (f)
        try:
            out.__cache_source_filename = filename
        except:
            pass
        return out
