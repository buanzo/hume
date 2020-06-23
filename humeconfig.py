#!/usr/bin/env python3
from pprint import pprint
import argparse
import confuse
import os
import sys

class HumeConfig():
    def __init__(self):
        pass

# config.dump() to create a string rep of a yaml config

def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('--user',
                        default=False,
                        action='store_true',
                        help="Create humed config for current non-root user only. By default humeconfig creates /etc/humed/config.yaml and needs root privileges.")
    parser.add_argument('--digitalocean',
                        default=False,
                        action='store_true',
                        help="Enables gathering droplet metadata. Requires --from-url.")
    parser.add_argument('--from-url',
                        default=None,
                        metavar='URL',
                        nargs=1,
                        help="Create config from url. It sends a POST request to the specified url including various metadata. Useful for provisioning.")
    parser.add_argument('--slack',
                        default=None,
                        metavar='WEBHOOK_URL',
                        nargs=1,
                        help="Humed will use slack transfer_method and indicated incoming webhook url.")
    parser.add_argument('--quiet',
                        default=False,
                        action='store_true',
                        help='Make no output, stderr included.')
    parser.add_argument('--porcelain',
                        default=False,
                        action='store_true',
                        help='Output full path to generated configuration file. Implies --silent.')
    parser.add_argument('--dry',
                        default=False,
                        action='store_true',
                        help='DRY RUN: Do not write to any file other than stdout. Stdout still shown if --quiet is False.')
    
    # Show parser help if run without arguments:
    if len(sys.argv) < 2:
        parser.print_help()
        sys.exit(1)

    # Prepare and run parser
    args = parser.parse_args()

if __name__ == '__main__':
    run()
