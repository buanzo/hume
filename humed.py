#!/usr/bin/python3
import zmq
import json
import pidfile
import sqlite3
import datetime
import argparse
# import systemd.daemon
from pprint import pprint
# The Confuse library is awesome.
import confuse

DEBUG = True  # TODO: set to False :P
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

# Configuration template
# See:
# https://github.com/beetbox/confuse/blob/master/example/__init__.py
config_template = {
    'listen_url': str,
    'transfer_method': confuse.OneOf(['fluentd', 'logstash', 'kant']),
}


class Humed():
    def __init__(self, config):
        self.config = config
        if self.prepare_db() is False:
            sys.exit('Humed: Error preparing database')

    def prepare_db(self):
        print('Preparing DB')
        try:
            self.conn = sqlite3.connect(DBPATH)
        except Exception as ex:
            print(ex)
            print('Humed: cannot connect to sqlite3 on "{}"'.format(DBPATH))
        self.cursor = self.conn.cursor()
        try:
            sql = '''CREATE TABLE IF NOT EXISTS
                     transfers (ts timestamp, sent boolean, hume text)'''
            print(sql)
            self.cursor.execute(sql)
            self.conn.commit()
        except Exception as ex:
            print(ex)
            return(False)
        print('DB OK')
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

    def processs_transfers(self):
        # TODO: The master/slave thingy...
        pendientes = self.list_transfers(pending=True)
        pprint(pendientes)
        for item in pendientes:
            # TODO: send to master-hume
            print(item)
            # if sent ok then:
            # self.transfer_ok(archivo=archivo)
            # if error return(False)
        return(True)

    def run(self):
        # Humed main loop
        # TODO: 1 - Initiate process-pending-humes-thread
        # 2 - Bind and Initiate loop
        sock = zmq.Context().socket(zmq.PULL)
        url = self.config['listen_url'].get()
        print("Binding to '{}'".format(url))
        sock.bind(url)
        # 2a - Await hume message over zmp
        while True:
            hume = {}
            try:
                hume = json.loads(sock.recv())
            except Exception as ex:
                print(ex)
                print('Cannot json-loads the received message. Mmmmm...')
            # 2b - insert it into transfers
            self.add_transfer(hume)
            pprint(self.list_transfers(pending=True))
        # TODO: 2c - log errors and rowids
        # TODO: deal with exits/breaks


def main():
    # First, parse configuration
    config = confuse.Configuration('humed')
    # Config defaults
    config['listen_url'] = 'tcp://127.0.0.1:198'
    parser = argparse.ArgumentParser()
    parser.add_argument('--listen_url',
                        help='Listening url for humed zeromq')
#                        default='tcp://127.0.0.1:198')
    args = parser.parse_args()
    config.set_args(args)
    print('Reading configuration from {}/{}'.format(config.config_dir(),
                                                    confuse.CONFIG_FILENAME))
    print('-----[ CONFIG DUMP ]-----')
    print(config.dump())
    print('---[ CONFIG DUMP END ]---')
    try:
        with pidfile.PIDFile():
            print('Process started')
    except pidfile.AlreadyRunningError:
        print('Already running.')
        print('Exiting')
        sys.exit(1)

    # Initialize Stuff
    humed = Humed(config=config)

    # TODO: Tell systemd we are ready
    # systemd.daemon.notify('READY=1')

    print('Ready. serving...')
    humed.run()


if __name__ == '__main__':
    # TODO: Add argparse and have master and slave modes
    main()
