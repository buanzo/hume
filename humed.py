#!/usr/bin/python3
import logging
from logging import getLogger
import sys
import zmq
import json
import socket
import sqlite3
import datetime
import argparse
import socket
import requests
from logging.handlers import SysLogHandler
from pid.decorator import pidfile
from queue import Queue
from threading import Thread
from humetools import printerr, pprinterr
# The Confuse library is awesome.
import confuse

DEVMODE = False

# Basic list of TRANSFER_METHODS
# We extend TRANSFER_METHODS by testing for optional modules
# TODO: kant will be our own
TRANSFER_METHODS = ['syslog', 'rsyslog', 'slack', 'kant']

# availability test for logstash (see optional_requirements.txt)
try:
    from logstash_async.handler import AsynchronousLogstashHandler as AsyncLSH
except ImportError:
    # logstash not available
    pass
else:
    # You gotta love try/except/else/finally
    TRANSFER_METHODS.append('logstash')

# TODO: add determination for fluentd-logger, we still need to find a GOOD
# implementation

# Configuration template
# See:
# https://github.com/beetbox/confuse/blob/master/example/__init__.py
config_template = {  # TODO: add debug. check confuse.Bool()
    'endpoint': confuse.String(),
    'transfer_method': confuse.OneOf(TRANSFER_METHODS),
    'rsyslog': {
        'server': confuse.String(),
        'proto': confuse.OneOf(['tcp', 'udp']),
        'port': confuse.Integer(),
    },
    'logstash': {
        'host': confuse.String(),
        'port': confuse.Integer(),
    },
    'slack': {
        'webhook_default': confuse.String(),  # for ok and info messages
        'webhook_warning': confuse.String(),
        'webhook_error': confuse.String(),
        'webhook_critical': confuse.String(),
        'webhook_debug': confuse.String(),
    },
}


class Humed():
    def __init__(self, config):
        # We will only expose config if needed
        # self.config = config
        self.debug = config['debug'].get()
        # Database path depends on debug
        self.dbpath = '/var/log/humed.sqlite3'
        if DEVMODE:
            self.dbpath = './humed.sqlite3'
        self.endpoint = config['endpoint'].get()
        self.transfer_method = config['transfer_method'].get()
        self.transfer_method_args = config[self.transfer_method].get()
        # Queue and Worker
        self.queue = Queue()
        worker = Thread(target=self.worker_process_transfers)
        worker.daemon = True
        worker.start()

        # TODO: improve
        self.logger = getLogger('humed-{}'.format(self.transfer_method))
        self.logger.setLevel(logging.INFO)
        if self.transfer_method is 'logstash':
            host = self.transfer_method_args['host'].get()
            port = self.transfer_method_args['host'].get()
            self.logger.addHandler(AsyncLSH(host,
                                            port,
                                            database_path='logstash.db'))
        # We will replace this with a plugin-oriented approach ASAP
        elif self.transfer_method is 'rsyslog':
            server = self.config['rsyslog']['server'].get()
            port = self.config['rsyslog']['port'].get()
            proto = self.config['rsyslog']['proto'].get()
            sa = (server, port)
            if proto is 'udp':
                socktype = socket.SOCK_DGRAM
            elif proto is 'tcp':
                socktype = socket.SOCK_STREAM
            else:
                printerr('Unknown proto "{}" in __init__')
                sys.exit(127)
            self.logger.addHandler(SysLogHandler(address=sa,
                                                 socktype=socktype))
        elif self.transfer_method is 'syslog':
            self.logger.addHandler(logging.handlers.SysLogHandler())
        # no 'else' because confuse takes care of validating config options

        if self.prepare_db() is False:
            sys.exit('Humed: Error preparing database')

    def worker_process_transfers(self):  # TODO
        while True:
            item = self.queue.get()
            if self.debug:
                pprinterr(item)
            pendientes = self.list_transfers(pending=True)
            if self.debug:
                printerr('Pending Items to send: {}'.format(len(pendientes)))
                printerr('Methods: {}'.format(self.transfer_method))
            for item in pendientes:
                if self.transfer_method == 'logstash':
                    ret = self.logstash(item=item)
                elif self.transfer_method == 'syslog':
                    ret = self.syslog(item=item)  # using std SysLogHandler
                elif self.transfer_method == 'rsyslog':
                    ret = self.syslog(item=item)  # using std SysLogHandler
                elif self.transfer_method == 'slack':
                    ret = self.slack(item=item)
                if ret is True:
                    self.transfer_ok(rowid=item[0])
            self.queue.task_done()

    def get_sqlite_conn(self):
        try:
            conn = sqlite3.connect(self.dbpath)
        except Exception as ex:
            printerr(ex)
            printerr('Error connecting to sqlite3 on "{}"'.format(self.dbpath))
            return(None)
        return(conn)

    def prepare_db(self):
        try:
            self.conn = sqlite3.connect(self.dbpath)
        except Exception as ex:
            printerr(ex)
            printerr('Humed: cant connect sqlite3 on "{}"'.format(self.dbpath))
        self.cursor = self.conn.cursor()
        try:
            sql = '''CREATE TABLE IF NOT EXISTS
                     transfers (ts timestamp, sent boolean, hume text)'''
            self.cursor.execute(sql)
            self.conn.commit()
        except Exception as ex:
            printerr(ex)
            return(False)
        return(True)

    def transfer_ok(self, rowid):  # add a DELETE somewhere sometime :P
        try:
            sql = 'UPDATE transfers SET sent=1 WHERE rowid=?'
            conn = self.get_sqlite_conn()
            cursor = conn.cursor()
            cursor.execute(sql, (rowid,))
            conn.commit()
        except Exception as ex:
            printerr(ex)
            return(False)
        return(True)

    def add_transfer(self, hume):
        try:
            hume = json.dumps(hume)
        except Exception as ex:
            printerr('Humed - add_transfer() json dumps exception:')
            printerr(ex)
            return(None)  # FIX: should we exit?
        try:
            now = datetime.datetime.now()
            sql = 'INSERT INTO transfers(ts, sent, hume) VALUES (?,?,?)'
            self.cursor.execute(sql, (now, 0, hume,))
            self.conn.commit()
        except Exception as ex:
            printerr('Humed: add_transfer() Exception:')
            printerr(ex)
            return(None)
        return(self.cursor.lastrowid)

    def list_transfers(self, pending=False):
        if pending is True:
            sql = 'SELECT rowid,* FROM transfers WHERE sent = 0'
        else:
            sql = 'SELECT rowid,* FROM transfers'
        lista = []
        rows = []
        try:
            conn = self.get_sqlite_conn()
            cursor = conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
        except Exception as ex:
            printerr(ex)

        for row in rows:
            lista.append(row)
        return(lista)

    def process_transfers(self):
        pendientes = self.list_transfers(pending=True)
        if self.debug:
            printerr('Pending Items to send: {}'.format(len(pendientes)))
            printerr('Methods: {}'.format(self.transfer_method))
        for item in pendientes:
            if self.transfer_method == 'logstash':
                ret = self.logstash(item=item)
            elif self.transfer_method == 'syslog':
                ret = self.syslog(item=item)  # using std SysLogHandler
            elif self.transfer_method == 'rsyslog':
                ret = self.syslog(item=item)  # using std SysLogHandler
            elif self.transfer_method == 'slack':
                ret = self.slack(item=item)
            if ret is True:
                self.transfer_ok(rowid=item[0])
        return(True)

    def slack(self, item=None):
        if item is None:
            return(False)  # FIX: should not happen
        rowid = item[0]
        ts = item[1]
        try:
            humepkt = json.loads(item[3])
        except Exception as ex:
            return(False)  # FIX: malformed json at this stage? mmm
        hume = humepkt['hume']
        if self.debug:
            pprinterr(hume)
        level = hume['level']
        tags = hume['tags']
        task = hume['task']
        msg = hume['msg']
        if tags is None:
            tagstr = ""
        else:
            tagstr = ','.join(tags)
        # Make sure to read:
        # https://api.slack.com/reference/surfaces/formatting
        m = "[{ts}] - {level} {task}: '{msg}' {tagstr}".format(level=level,
                                                               msg=msg,
                                                               task=task,
                                                               ts=ts,
                                                               tagstr=tagstr)
        # https://api.slack.com/reference/surfaces/formatting#escaping
        m = m.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        # Remember, text becomes a fallback if 'blocks' are in use:
        # https://api.slack.com/messaging/composing/layouts#adding-blocks
        slackmsg = {'text': m, }
        # TODO: use blocks for a nicer message format
        # choose appropriate channel by config key
        if level in ['ok', 'info']:
            chan = 'webhook_default'
        else:
            chan = 'webhook_{}'.format(level)
        # if the config key does not exist, fallback to default:
        if chan not in self.transfer_method_args.keys():
            chan = 'webhook_default'
        webhook = self.transfer_method_args[chan]
        if self.debug:
            printerr('Using {}="{}" for level "{}"'.format(chan,
                                                           webhook,
                                                           level))
        ret = requests.post(webhook,
                            headers={'Content-Type': 'application/json'},
                            data=json.dumps(slackmsg))
        if self.debug:
            pprinterr(slackmsg)
            pprinterr(ret)
        if ret.status_code == 200:
            return(True)
        return(False)

    def logstash(self, item=None):
        if item is None:
            return(False)  # FIX: should not happen
        rowid = item[0]
        ts = item[1]
        try:
            humepkt = json.loads(item[3])
        except Exception as ex:
            return(False)  # FIX: malformed json at this stage? mmm
        hume = humepkt['hume']
        if 'process' in humepkt.keys():  # This data is optional in hume (-a)
            process = humepkt['process']
        else:
            process = None
        # Extract info from hume to prepare logstash call
        # TODO: implement configuration for "LOG FORMAT" to use when sending
        level = hume['level']
        msg = hume['msg']
        task = hume['task']
        tags = hume['tags']
        humecmd = hume['humecmd']
        timestamp = hume['timestamp']
        # hostname
        # FIX: add a hostname configuration keyword
        hostname = socket.getfqdn()
        # extra field for logstash message
        extra = {
            'tags': tags,
            'task': task,
            'humelevel': level,
            'humecmd': humecmd,
            'timestamp': timestamp
        }
        if process is not None:
            extra['process'] = process
        # Hume level does not relate completely, because 'ok' is not
        # a syslog severity, closest is info but...  TODO: think about this
        # hume level -> syslog severity
        # ----------------------------
        # ok         -> info (or default)
        # info       -> info (or default)
        # warning    -> warning
        # error      -> error
        # critical   -> critical
        # debug      -> debug
        try:
            if level == 'ok' or level == 'info':
                # https://python-logstash-async.readthedocs.io/en/stable/usage.html#
                self.logger.info('hume({}): {}'.format(hostname, msg),
                                 extra=extra)
            elif level == 'warning':
                self.logger.warning('hume({}) {}'.format(hostname, msg),
                                    extra=extra)
            elif level == 'error':
                self.logger.error('hume({}): {}'.format(hostname, msg),
                                  extra=extra)
            elif level == 'critical':
                self.logger.critical('hume({}): {}'.format(hostname, msg),
                                     extra=extra)
            elif level == 'debug':
                self.logger.debug('hume({}): {}'.format(hostname, msg),
                                  extra=extra)
        except Exception:  # TODO: improve exception handling
            return(False)
        else:
            return(True)

    def syslog(self, item=None):
        # This function handles both local and remote syslog
        # according to logging.handlers.SysLogHandler()
        if item is None:
            return(False)  # FIX: should not happen

        # Required data:
        rowid = item[0]
        ts = item[1]
        try:
            humepkt = json.loads(item[3])
        except Exception as ex:
            return(False)  # FIX: malformed json at this stage? mmm
        hume = humepkt['hume']

        # Optional data
        if 'process' in humepkt.keys():  # This data is optional in hume (-a)
            process = humepkt['process']
        else:
            process = None

        # Extract info from hume to prepare syslog message
        # TODO: decide if we should split these in the parent caller
        #       pros: tidier
        #       cons: makes development of other transfer methods
        #       more cumbersome? although... PLUGINS!
        level = hume['level']
        msg = hume['msg']
        task = hume['task']
        tags = hume['tags']
        humecmd = hume['humecmd']
        timestamp = hume['timestamp']
        # hostname
        # FIX: add a hostname configuration keyword
        # FIX: redundant code. more reasons to PLUGINS asap
        hostname = socket.getfqdn()

        # We dont have the 'extra' field for syslog, in contrast to logstash
        msg = '[{}-{}-{}] TAGS=[{}] HUMECMD={} MSG={}'.format(timestamp,
                                                              task,
                                                              humelevel,
                                                              tags,
                                                              humecmd,
                                                              msg)
        if process is not None:
            msg = '{} PROC={}'.format(msg,
                                      json.dumps(extra['process']))
        else:
            msg = '{} PROC=None'.format(msg)
        # Hume level does not relate completely, because 'ok' is not
        # a syslog severity, closest is info but...  TODO: think about this
        # hume level -> syslog severity
        # ----------------------------
        # ok         -> info
        # info       -> info
        # warn       -> warning
        # error      -> error
        # critical   -> critical
        # debug      -> debug
        try:
            if level == 'ok' or level == 'info':
                # https://python-logstash-async.readthedocs.io/en/stable/usage.html#
                self.logger.info('hume({}): {}'.format(hostname, msg))
            elif level == 'warn':
                self.logger.warning('hume({}) {}'.format(hostname, msg))
            elif level == 'error':
                self.logger.error('hume({}): {}'.format(hostname, msg))
            elif level == 'critical':
                self.logger.critical('hume({}): {}'.format(hostname, msg))
            elif level == 'debug':
                self.logger.debug('hume({}): {}'.format(hostname, msg))
        except Exception:  # TODO: improve exception handling
            return(False)
        else:
            return(True)

    def run(self):
        # Humed main loop
        sock = zmq.Context().socket(zmq.REP)
        sock.setsockopt(zmq.LINGER, 0)
        sock.bind(self.endpoint)
        # Check for pending transfers first
        self.queue.put(('work'))
        # Await hume message over zmp and dispatch job thru queue
        while True:
            hume = {}
            poller = zmq.Poller()
            poller.register(sock, zmq.POLLIN)
            if poller.poll(1000):
                msg = sock.recv()
            else:
                continue
            try:
                hume = json.loads(msg)
            except Exception as ex:
                printerr(ex)
                printerr('Cannot json-loads the received message. notgood')
                sock.send_string('Invalid JSON message')
            except KeyboardInterrupt as kb:
                printerr('CTRL-C called, exiting now')
                sys.exit(255)
            else:
                sock.send_string('OK')
                rowid = self.add_transfer(hume)
                self.queue.put(('work'))
                if self.debug:
                    printerr(rowid)
        # TODO: 2c - log errors and rowids
        # TODO: deal with exits/breaks


@pidfile()
def main():
    # First, parse configuration
    config = confuse.Configuration('humed')
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug',
                        default=False,
                        action='store_true',
                        help='Enables debug messages')
    args = parser.parse_args()
    config.set_args(args)
    config.debug = args.debug
    try:
        valid = config.get(template=config_template)
    except confuse.NotFoundError:
        pass
    except Exception as ex:
        pprinterr(ex)
        printerr('Humed: Config file validation error: {}'.format(ex))
        sys.exit(2)
    if config.debug:
        printerr('-----[ CONFIG DUMP ]-----')
        printerr(config.dump())
        printerr('Available Transfer Methods: {}'.format(TRANSFER_METHODS))
        printerr('---[ CONFIG DUMP END ]---')

    # Initialize Stuff - configuration will be tested in Humed __init__
    humed = Humed(config=config)

    if config.debug:
        printerr('Ready. serving...')
    humed.run()


if __name__ == '__main__':
    # TODO: Add argparse and have master and slave modes
    main()
