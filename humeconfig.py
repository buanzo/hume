#!/usr/bin/env python3
import os
import sys
import glob
import json
import argparse
import requests
from shutil import which
from pprint import pprint
from pathlib import Path

class HumeConfig():
    def __init__(self):
        self.config = []

    def from_url(self, url, digitalocean):
        printerr('FROM_URL = {}'.format(url))
        printerr('DIGITALOCEAN = {}'.format(digitalocean))
        return(False)

    def from_args(self, args):
        args = vars(args)
        methods = args['methods']
        self.config.append('endpoint: {}'.format(args['endpoint']))
        self.config.append('transfer_method: {}'.format(','.join(methods)))
        # Then the per-method config
        for method in args['methods']:
            # We will only process the methods that need additional options
            if method == 'slack':
                url = args['slack'][0]
                self.config.append('slack:')
                self.config.append('    webhook_url: {}'.format(url))
            elif method == 'rsyslog':
                rs = args['rsyslog'][0]
                proto = rs.split('://')[0]
                server = rs.split('://')[1].split(':')[0]
                port = rs.split(':')[2]
                self.config.append('rsyslog:')
                self.config.append('    proto: {}'.format(proto))
                self.config.append('    server: {}'.format(server))
                self.config.append('    port: {}'.format(port))

    def print_config(self):
        print('\n'.join(self.config))

    def save_config(self):
        try:
            os.mkdir('/etc/humed')
        except FileExistsError:
            pass
        except Exception as exc:
            printerr(exc)
            sys.exit(1)
        with open('/etc/humed/config.yaml', 'w') as f:
            for item in self.config:
                f.write("{}\n".format(item))
# config.dump() to create a string rep of a yaml config

# Avoid race conditions. Warning: this function OVERWRITES files, no questions asked
def safe_write(dest,content,mode=0o600,uid='root',gid='root'):
    if os.path.isfile(dest):
        os.remove(dest)
    original_umask = os.umask(0o177)  # 0o777 ^ 0o600
    try:
        handle = os.fdopen(os.open(dest, os.O_WRONLY | os.O_CREAT, mode), 'w')
    finally:
        os.umask(original_umask)
    handle.write(content)
    handle.close()
    

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
                        help='''Enables gathering droplet
metadata using. Requires --from-url.''')
    parser.add_argument('--from-url',
                        dest='from_url',
                        default=None,
                        metavar='URL',
                        nargs=1,
                        help='''Create config from url. It sends a POST
request to the specified url including various metadata.
Useful for provisioning.''')
    parser.add_argument('--endpoint',
                        metavar='ZMQ_ENDPOINT',
                        nargs=1,
                        default='tcp://127.0.0.1:198',
                        help='''ZMQ Endpoint hume client will send
messages to. A local address is recommended.''')
    parser.add_argument('--syslog',
                        action='store_true',
                        default=False,
                        help='Enable local syslog transfer_method in humed.')
    parser.add_argument('--rsyslog',
                        dest='rsyslog',
                        metavar='PROTO://SERVER:PORT',
                        default=None,
                        nargs=1,
                        help='''Humed will use remote syslog transfer_method.
Example: udp://rsyslog.example.net:514. Proto may be tcp or udp. All components
must be specified, including port.''')
    parser.add_argument('--slack',
                        default=None,
                        metavar='WEBHOOK_URL',
                        nargs=1,
                        help="Enable Slack using a webhook url.")
    parser.add_argument('--quiet',
                        default=False,
                        action='store_true',
                        help='Make no output, stderr included.')
    parser.add_argument('--dry',
                        default=False,
                        action='store_true',
                        help='Disable file writes.')
    parser.add_argument('--install-systemd',
                        default=False,
                        action='store_true',
                        dest='installsystemd',
                        help='''If /etc/humed/config.yaml exists, attempts to
install and enable humed systemd service unit.''')

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

    if args.installsystemd is True:
        # Verify /etc/humed/config.yaml exists and is a file:
        if not Path("/etc/humed/config.yaml").is_file():
            printerr('/etc/humed/config.yaml is not a file, or does not exist.')
            printerr('Create it using humeconfig\'s other parameters.')
            sys.exit(8)
        # We will try to validate which directory holds service units
        # at runtime. These are the two locations I have experience with
        CHECK_DIRS = ['/lib/systemd/system', '/usr/lib/systemd/system']
        TARGET_DIR = ''
        for dir in CHECK_DIRS:
            g = glob.glob('{dir}/*.service'.format(dir=dir))
            if len(g) > 0:
                TARGET_DIR = dir
                break
        if TARGET_DIR == '':  # no systemd service unit directory found
            printerr('''None of these locations seems to hold systemd service units.
Please open an issue at https://github.com/buanzo/hume/issues''')
            printerr('{}'.format(CHECK_DIRS))
            sys.exit(1)
        # Ok, we found where service units should go
        humed_path = which('humed')
        if humed_path is None:
            printerr('Could not find humed script in $PATH. Is it installed?')
            sys.exit(7)
        unit = '''
[Unit]
Description=The Hume Daemon

[Service]
Type=simple
ExecStart={humed_path}
Environment=PYTHONUNBUFFERED=1
Restart=on-failure

[Install]
WantedBy=default.target
'''.format(humed_path=humed_path)
        destination = '{unitdir}/humed.service'.format(unitdir=TARGET_DIR)
        safe_write(destination,
                   unit,
                   mode=0o640,
                   uid='root',
                   gid='root')
        print('{} has been created with these contents:'.format(destination))
        print('\n')
        print(unit)
        print('\n')
        print('Enable the service with:\nsudo systemctl enable humed\n')
        sys.exit(0)

    h = HumeConfig()
    if args.from_url is not None:  # --from-url ON
        printerr('--from-url specified. Ignoring humeconfig runtime options.')
        c = h.from_url(args.from_url,
                       digitalocean=args.digitalocean)
    else:  # if config is not coming from an URL, then effectively process args
        if args.slack is not None:  # --slack ON
            TRANSFER_METHODS.append('slack')
        if args.syslog is True:  # --syslog ON
            TRANSFER_METHODS.append('syslog')
        if args.rsyslog is not None:  # --rsyslog ON
            TRANSFER_METHODS.append('rsyslog')
        args.methods = TRANSFER_METHODS
        c = h.from_args(args)

    # if not --quiet, then dump generated config to stdout
    if args.quiet is False:
        h.print_config()

    # Test writability of /etc
    if dir_is_writable('/etc') is False:
        printerr('No write access to /etc. Not running as root?')
        if args.dry is True:  # if we cant write but its dry, we return OK
            sys.exit(0)
        sys.exit(1)

    # If we are still here and is not a dry run, proceed to write
    if args.dry is False:
        try:
            h.save_config()
        except Exception as exc:
            printerr('{}'.format(exc))
            sys.exit(1)


if __name__ == '__main__':
    run()
