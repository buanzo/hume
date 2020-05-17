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

# Location of json config file
# The good thing about WSL is that we actually have /etc
CONFIGPATH = '/etc/humed/humed.json'
if DEBUG:
    CONFIGPATH = './humed.json'

# Basic list of TRANSFER_METHODS
# We extend TRANSFER_METHODS by testing for optional modules
TRANSFER_METHODS = ['syslog', 'remote_syslog', 'kant']  # TODO: kant will be our own

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
    'listen_url': confuse.String(),
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
}


class Humed():
    def __init__(self, config):
        # We will only expose config if needed
        # self.config = config
        self.debug = config['debug'].get()
        self.listen_url = config['listen_url'].get()
        self.transfer_method = config['transfer_method'].get()
        self.transfer_method_args = config[self.transfer_method].get()
        # TODO: improve
        self.logger = logging.getLogger('humed-{}'.format(self.transfer_method))
        self.logger.setLevel(logging.INFO)
        if self.transfer_method is 'logstash':
            host = self.transfer_method_args['host'].get()
            port = self.transfer_method_args['host'].get()
            self.logger.addHandler(AsyncLSH(host, port, database_path='logstash.db'))
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

    def transfer_ok(self, rowid):
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
                self.logstash(item=item)
            elif self.transfer_method == 'syslog':
                self.syslog(item=item)
            # if sent ok then:
            # self.transfer_ok(archivo=archivo)
            # if error return(False)
        return(True)

    def logstash(self,item=None):
        if item is None:
            return()  # FIX: should not happen
        rowid = item[0]
        ts = item[1]
        try:
            humepkt = json.loads(item[3])
        except Exception as ex:
            return()  # FIX: malformed json at this stage? mmm
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

    def run(self):
        # Humed main loop
        sock = zmq.Context().socket(zmq.PULL)
        # print("Binding to '{}'".format(self.listen_url))
        sock.bind(self.listen_url)
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
    config['listen_url'] = 'tcp://localhost:198'
    config['remote_syslog']['address'] = 'localhost'
    config['remote_syslog']['proto'] = 'udp'
    config['remote_syslog']['port'] = 514
    parser = argparse.ArgumentParser()
    parser.add_argument('--listen_url',
                        help='Listening url for humed zeromq')
    config['debug'] = DEBUG
    parser.add_argument('--debug',
                        help='Enable debug')
    args = parser.parse_args()
    config.set_args(args)
    print('Reading configuration from {}/{}'.format(config.config_dir(),
                                                    confuse.CONFIG_FILENAME))
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
