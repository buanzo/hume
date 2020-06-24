#!/usr/bin/env python3
from pprint import pprint
import json
import requests
import argparse
import os
import sys

class HumeConfig():
    def __init__(self):
        pass

# config.dump() to create a string rep of a yaml config

# print msg to stderr
def printerr(msg):
    print("{}".format(msg), file=sys.stderr)

# Test if we can write to dir
def dir_is_writable(dir):
    return(os.access(dir, os.W_OK))

def run():
    # In the future humed will support multiple simultaneous transfer
    # methods. Humeconfig will support that from the start, but will
    # output a warning if more than one is specified at runtime.
    TRANSFER_METHODS = []

    # Prepare parser
    parser = argparse.ArgumentParser()
    parser.add_argument('--digitalocean',
                        default=False,
                        action='store_true',
                        help="Enables gathering droplet metadata. Requires --from-url.")
    parser.add_argument('--from-url',
                        dest='from_url',
                        default=None,
                        metavar='URL',
                        nargs=1,
                        help="Create config from url. It sends a POST request to the specified url including various metadata. Useful for provisioning.")
    parser.add_argument('--endpoint',
                        metavar='ZMQ_ENDPOINT',
                        nargs=1,
                        default='tcp://127.0.0.1:198',
                        help='ZMQ Endpoint hume client will send messages to. A local address is recommended.')
    parser.add_argument('--syslog',
                        action='store_true',
                        default=False,
                        help='Enable local syslog transfer_method in humed.')
    parser.add_argument('--remote-syslog',
                        dest='rsyslog',
                        metavar='PROTO://SERVER:PORT',
                        nargs=1,
                        help='Humed will use remote syslog transfer_method. Example: udp://rsyslog.example.net:514. Proto may be tcp or udp. All components must be specified, including port.')
    parser.add_argument('--slack',
                        default=None,
                        metavar='WEBHOOK_URL',
                        nargs=1,
                        help="Humed will use slack transfer_method and indicated incoming webhook url.")
    parser.add_argument('--quiet',
                        default=False,
                        action='store_true',
                        help='Make no output, stderr included.')
    parser.add_argument('--dry',
                        default=False,
                        action='store_true',
                        help='DRY RUN: Do not write to any file other than stdout. Stdout still shown if --quiet is False.')
    
    # Show parser help if run without arguments:
    if len(sys.argv) < 2:
        parser.print_help()
        sys.exit(1)

    # Run parser
    args = parser.parse_args()
    
    # Combinatorial validations
    if args.digitalocean is True and args.from_url is None:
        printerr('--digitalocean indicated but --from-url is missing.')
        sys.exit(1)

    if args.from_url is not None:  # --from-url ON
        printerr('--from-url specified. Ignoring humeconfig runtime options.')
        h = HumeConfig(from_url=args.from_url,digitalocean=args.digitalocean)
    else:  # if config is not coming from an URL, then effectively process args:
        if args.slack is not None:  # --slack ON
            TRANSFER_METHODS.append('slack')
        if args.syslog is not None:  # --syslog ON
            TRANSFER_METHODS.append('syslog')
        if args.rsyslog is not None:  # --remote-syslog ON
            TRANSFER_METHODS.append('remote-syslog')
        h = HumeConfig(args,methods=TRANSFER_METHODS)
    
    # if not --quiet, then dump generated config to stdout
    if args.quiet is False:
        print(h.dump_config())

    # Test writability of /etc
    if dir_is_writable('/etc') is False:
        printerr('No write access to /etc. Not running as root?')
        sys.exit(1)

    if args.dry is True:
        sys.exit(0)  # if /etc is writable but is a dry-run, we return OK
    else:
        h.save_config()
    
if __name__ == '__main__':
    run()
