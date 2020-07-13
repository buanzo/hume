#!/usr/bin/env python3
import os
import re
import sys
import argparse
from pprint import pprint


class NotImplementedAction(argparse.Action):
    """ This class allows to work on getting your Argparse object
    ready even if nothing useful happens when used.

    Usage:
    Just set action=NotImplementedAction when calling add_argument, like this:

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--missing",
                        help="This will do something in the future",
                        action=NotImplementedAction)

    GIST URL: https://gist.github.com/buanzo/2a004348340ef79b0139ab38f719cf1e
    """
    def __call__(self, parser, namespace, values, option_string=None):
        msg = 'Argument "{}" still not implemented.'.format(option_string)
        sys.exit(msg)


# Guess.
def printerr(msg):
    print("{}".format(msg), file=sys.stderr)


def pprinterr(o):
    pprint(o, stream=sys.stderr)


def valueOrDefault(o, k, d):
    # This function tries to find a key
    # or an attribute named k.
    # If it finds either, it returns d.
    if isinstance(o, dict):
        if k in o.keys():
            return(o[k])
    try:
        r = getattr(o, k)
    except AttributeError:
        return(d)
    return(r)


def envOrDefault(v, d):
    # return the contents of an env var 'v'
    # or default d.
    ov = os.environ.get(v)
    if ov is None:
        return(d)
    else:
        return(str(ov).strip())


def is_valid_hostname(hostname):
    if len(hostname) > 255:
        return False
    if hostname[-1] == ".":
        hostname = hostname[:-1] # strip exactly one dot from the right, if present
    allowed = re.compile("(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
    return all(allowed.match(x) for x in hostname.split("."))
