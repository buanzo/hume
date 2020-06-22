#!/usr/bin/python3
import logging
import sys
import zmq
import json
import socket
import pidfile
import sqlite3
import datetime
import argparse
import socket
import requests
from logging.handlers import SysLogHandler
# import systemd.daemon
from pprint import pprint
# The Confuse library is awesome.
import confuse

DEBUG = False  # TODO: set to False :P

# hume is VERY related to logs
# better /var/humed/humed.sqlite3 ?
DBPATH = '/var/log/humed.sqlite3'
if DEBUG:
    DBPATH = './humed.sqlite3'

# Basic list of TRANSFER_METHODS
# We extend TRANSFER_METHODS by testing for optional modules
TRANSFER_METHODS = ['syslog', 'remote_syslog', 'slack', 'kant']  # TODO: kant will be our own

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
    'remote_syslog': {
        'server': confuse.String(),
        'proto': confuse.OneOf(['tcp','udp']),
        'port': confuse.Integer(),
    },
    'logstash': {
        'host': confuse.String(),
        'port': confuse.Integer(),
    },
    'slack': {
        'webhook_url': confuse.String(),
    },
}


class Humed():
    def __init__(self, config):
        # We will only expose config if needed
        # self.config = config
        self.debug = config['debug'].get()
        self.endpoint = config['endpoint'].get()
        self.transfer_method = config['transfer_method'].get()
        self.transfer_method_args = config[self.transfer_method].get()
        # TODO: improve
        self.logger = logging.getLogger('humed-{}'.format(self.transfer_method))
        self.logger.setLevel(logging.INFO)
        if self.transfer_method is 'logstash':
            host = self.transfer_method_args['host'].get()
            port = self.transfer_method_args['host'].get()
            self.logger.addHandler(AsyncLSH(host,
                                            port,
                                            database_path='logstash.db'))
        # We will replace this with a plugin-oriented approach ASAP
        elif self.transfer_method is 'remote_syslog':
            server = self.config['remote_syslog']['server'].get()
            port = self.config['remote_syslog']['port'].get()
            proto = self.config['remote_syslog']['proto'].get()
            sa = (server,port)
            if proto is 'udp':
                self.logger.addHandler(SysLogHandler(address=sa,
                                                     socktype=socket.SOCK_DGRAM))
            elif proto is 'tcp':
                self.logger.addHandler(SysLogHandler(address=sa,
                                                     socktype=socket.SOCK_STREAM))
        elif self.transfer_method is 'syslog':
            self.logger.addHandler(logging.handlers.SysLogHandler())
        # no 'else' because confuse takes care of validating config options

        if self.prepare_db() is False:
            sys.exit('Humed: Error preparing database')

    def prepare_db(self):
        try:
            self.conn = sqlite3.connect(DBPATH)
        except Exception as ex:
            print(ex)
            print('Humed: cannot connect to sqlite3 on "{}"'.format(DBPATH))
        self.cursor = self.conn.cursor()
        try:
            sql = '''CREATE TABLE IF NOT EXISTS
                     transfers (ts timestamp, sent boolean, hume text)'''
            self.cursor.execute(sql)
            self.conn.commit()
        except Exception as ex:
            print(ex)
            return(False)
        return(True)

    def transfer_ok(self, rowid):  # add a DELETE somewhere sometime :P
        try:
            sql = 'UPDATE transfers SET sent=1 WHERE rowid=?'
            self.cursor.execute(sql, (rowid,))
            self.conn.commit()
        except Exception as ex:
            print(ex)
            return(False)
        return(True)

    def add_transfer(self, hume):
        try:
            hume = json.dumps(hume)
        except Exception as ex:
            print('Humed - add_transfer() json dumps exception:')
            print(ex)
            return(None)  # FIX: should we exit?
        try:
            now = datetime.datetime.now()
            sql = 'INSERT INTO transfers(ts, sent, hume) VALUES (?,?,?)'
            self.cursor.execute(sql, (now, 0, hume,))
            self.conn.commit()
        except Exception as ex:
            print('Humed: add_transfer() Exception:')
            print(ex)
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
            self.cursor.execute(sql)
            rows = self.cursor.fetchall()
        except Exception as ex:
            print(ex)

        for row in rows:
            lista.append(row)
        return(lista)

    def process_transfers(self):
        # TODO: The master/slave thingy...
        pendientes = self.list_transfers(pending=True)
        for item in pendientes:
            # TODO: send to master-hume
            if self.transfer_method == 'logstash':
                ret = self.logstash(item=item)
            elif self.transfer_method == 'syslog':
                ret = self.syslog(item=item)  # using std SysLogHandler
            elif self.transfer_method == 'remote_syslog':
                ret = self.syslog(item=item)  # using std SysLogHandler
            elif self.transfer_method == 'slack':
                ret = self.slack(item=item)
            if ret is True:
                self.transfer_ok(rowid=item[0])
        return(True)

    def slack(self,item=None):
        if item is None:
            return(False)  # FIX: should not happen
        rowid = item[0]
        ts = item[1]
        try:
            humepkt = json.loads(item[3])
        except Exception as ex:
            return(False)  # FIX: malformed json at this stage? mmm
        hume = humepkt['hume']
        pprint(hume)
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
        message = "[{ts}] - {level} {task}: '{msg}' {tagstr}".format(level=level,
                                                                     msg=msg,
                                                                     task=task,
                                                                     ts=ts,
                                                                     tagstr=tagstr)
        # https://api.slack.com/reference/surfaces/formatting#escaping
        message = message.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
        # Remember, text becomes a fallback if 'blocks' are in use:
        # https://api.slack.com/messaging/composing/layouts#adding-blocks
        slackmsg = {'text': message,}
        # TODO: use blocks for a nicer message format
        webhook = self.transfer_method_args['webhook_url']
        ret = requests.post(webhook,
                            headers={'Content-Type': 'application/json'},
                            data=json.dumps(slackmsg))
        if ret.status_code == 200:
            return(True)
        return(False)

    def logstash(self,item=None):
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
        hostname = socket.getfqdn()  # FIX: add a hostname configuration keyword
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
        # ok         -> info
        # info       -> info
        # warn       -> warning
        # error      -> error
        # critical   -> critical
        # debug      -> debug
        try:
            if level == 'ok' or level == 'info':
                # https://python-logstash-async.readthedocs.io/en/stable/usage.html#
                self.logger.info('hume({}): {}'.format(hostname, msg), extra=extra)
            elif level == 'warn':
                self.logger.warning('hume({}) {}'.format(hostname, msg), extra=extra)
            elif level == 'error':
                self.logger.error('hume({}): {}'.format(hostname, msg), extra=extra)
            elif level == 'critical':
                self.logger.critical('hume({}): {}'.format(hostname, msg), extra=extra)
            elif level == 'debug':
                self.logger.debug('hume({}): {}'.format(hostname, msg), extra=extra)
        except Exception:  # TODO: improve exception handling
            return(False)
        else:
            return(True)

    def syslog(self,item=None):
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
        #       cons: makes development of other transfer methods more cumbersome?
        level = hume['level']
        msg = hume['msg']
        task = hume['task']
        tags = hume['tags']
        humecmd = hume['humecmd']
        timestamp = hume['timestamp']
        # hostname
        hostname = socket.getfqdn()  # FIX: add a hostname configuration keyword
        
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
        sock = zmq.Context().socket(zmq.PULL)
        # print("Binding to '{}'".format(self.endpoint))
        sock.bind(self.endpoint)
        # 2a - Await hume message over zmp
        while True:
            hume = {}
            try:
                hume = json.loads(sock.recv())
            except Exception as ex:
                print(ex)
                print('Cannot json-loads the received message. notgood')
            except KeyboardInterrupt as kb:
                print('CTRL-C called, exiting now')
                sys.exit(255)
            else:
                self.add_transfer(hume)
                self.process_transfers()
        # TODO: 2c - log errors and rowids
        # TODO: deal with exits/breaks


def main():
    # First, parse configuration
    config = confuse.Configuration('humed')
    # Config defaults
    config['endpoint'] = 'tcp://127.0.0.1:198'
    config['remote_syslog']['server'] = 'localhost'
    config['remote_syslog']['proto'] = 'udp'
    config['remote_syslog']['port'] = 514
    parser = argparse.ArgumentParser()
    config['debug'] = DEBUG
    parser.add_argument('--debug',
                        help='Enables debug messages')
    args = parser.parse_args()
    config.set_args(args)
    try:
        valid = config.get(template=config_template)
    except Exception as ex:
        print('Humed: Config file validation error: {}'.format(ex))
        sys.exit(2)
    print('-----[ CONFIG DUMP ]-----')
    print(config.dump())
    print('Available Transfer Methods: {}'.format(TRANSFER_METHODS))
    print('---[ CONFIG DUMP END ]---')
    try:
        with pidfile.PIDFile():
            print('Process started')
    except pidfile.AlreadyRunningError:
        print('Already running.')
        print('Exiting')
        sys.exit(1)

    # Initialize Stuff - configuration will be tested in Humed __init__
    humed = Humed(config=config)

    # TODO: Tell systemd we are ready
    # systemd.daemon.notify('READY=1')

    print('Ready. serving...')
    humed.run()


if __name__ == '__main__':
    # TODO: Add argparse and have master and slave modes
    main()
