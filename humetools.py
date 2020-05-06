#!/usr/bin/env python3
import sys
import argparse

""" This class allows to work on getting your Argparse object
    ready even if nothing useful happens when used.

    Save this git on some file then import the class.

    Usage:
    Just set action=NotImplementedAction when calling add_argument, like this:

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--missing",
                        help="This will do something in the future",
                        action=NotImplementedAction)

    GIST URL: https://gist.github.com/buanzo/2a004348340ef79b0139ab38f719cf1e
"""


class NotImplementedAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        msg = 'Argument "{}" still not implemented.'.format(option_string)
        sys.exit(msg)
