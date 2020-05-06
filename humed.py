#!/usr/bin/python3
import zmq
import json
import pidfile
import sqlite3
import datetime
#import systemd.daemon
from pprint import pprint

DEBUG=True  # TODO: set to False :P
DBPATH='/var/log/humed.sqlite3'  # hume is VERY related to logs
                                 # better /var/humed/humed.sqlite3 ?
if DEBUG:
    DBPATH='./humed.sqlite3'

class Humed():
    def __init__(self,listen_url='tcp://127.0.0.1:198'):
        self.config = {}
        self.config['listen_url'] = listen_url
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
            #if sent ok then:
            #self.transfer_ok(archivo=archivo)
            # if error return(False)
        return(True)
    
    def run(self):
        # Humed main loop
        # TODO: 1 - Initiate process-pending-humes-thread
        # 2 - Bind and Initiate loop
        sock = zmq.Context().socket(zmq.PULL)
        sock.bind(self.config['listen_url'])
        # 2a - Await hume message over zmp
        while True:
            hume = {}
            try:
                hume = json.loads(sock.recv())
            except Exception as ex:
                print(ex)
                print('Seems we cant json parse the received message. Mmmmm...')
            # 2b - insert it into transfers
            self.add_transfer(hume)
            #pprint(self.list_transfers(pending=True))
        # TODO: 2c - log errors and rowids
        # TODO: deal with exits/breaks

        
def main():
    print('Starting process')
    try:
        with pidfile.PIDFile():
            print('Process started')
    except pidfile.AlreadyRunningError:
        print('Already running.')
        print('Exiting')
        sys.exit(1)

    # Initialize Stuff
    print('initializing hume daemon')
    humed = Humed()

    # TODO: Tell systemd we are ready
    #systemd.daemon.notify('READY=1')

    print('Ready. serving...')
    humed.run()

if __name__ == '__main__':
    # TODO: Add argparse and have master and slave modes
    main()
