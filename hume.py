#!/usr/bin/env python3
import os
import zmq
import sys
import stat
import psutil
import argparse
import json
from pprint import pprint
from datetime import datetime
from humetools import NotImplementedAction

__version__ = '1.0'

class Hume():
    def __init__(self, args):
        # self.config = {'url': 'ipc:///tmp/hume.sock'}
        self.config = {'url': 'tcp://127.0.0.1:198'}

        # args
        self.args = args

        # Prepare object to send
        # Might end up moving some of this stuff around
        # But I like focusing blocks to be developed
        # in such a way that the code can grow organically
        # and be coder-assistive
        self.reqObj = {}
        # To store information related to how hume was executed
        self.reqObj['process'] = {}
        # Hume-specific information
        self.reqObj['hume'] = {}
        self.reqObj['hume']['level'] = args.level
        self.reqObj['hume']['msg'] = args.msg
        self.reqObj['hume']['tags'] = args.tags
        self.reqObj['hume']['task'] = args.task
        self.reqObj['hume']['humecmd'] = args.humecmd
        self.reqObj['hume']['timestamp'] = self.get_timestamp()
        if self.args.append_pstree:
            self.reqObj['process']['tree'] = self.get_pstree()

        ln = self.get_lineno()
        if ln is not None:
            self.reqObj['process']['line_number'] = ln
        del ln

        if (len(self.reqObj['process']) == 0):
            del(self.reqObj['process'])

        # TODO: process args and add items to reqObj
        print(self.config['url'])

        if self.config['url'].startswith('ipc://'):
            if not self.test_unix_socket(config['url']):
                print('socket not writable or other error')
                sys.exit(1)

    def test_unix_socket(self, url):
        path = url.replace('ipc://', '')
        if not os.path.exists(path):
            return(False)
        mode = os.stat(path).st_mode
        isSocket = stat.S_ISSOCK(mode)
        if not isSocket:
            return(False)
        if os.access(path, os.W_OK):
            # OK, it's an actual socket we can write to
            return(True)
        return(False)

    def send(self, encrypt_to=None):
        # TODO: If we were to encrypt, we would encapsulate
        # self.reqObj to a special structure:
        # {'payload': ENCRYPTED_ASCII_ARMORED_CONTENT,
        #  'encrypted': True}
        # or something like that
        if encrypt_to is None:
            HUME = self.reqObj
        else:
            HUME = self.encrypt(gpg_encrypt_to)
        # The abstraction level of zeromq does not allow to
        # simply check for correctly sent messages. We should wait for a REPly
        # FIX: see if we can make REP/REQ work as required
        sock = zmq.Context().socket(zmq.PUSH)
        sock.setsockopt(zmq.SNDTIMEO, 5)
        sock.setsockopt(zmq.LINGER, 5)
        try:
            sock.connect(self.config['url'])
        except zmq.ZMQError as exc:
            print(exc)
            sys.exit(2)
        try:
            x = sock.send_string(json.dumps(self.reqObj))
        except zmq.ZMQError as exc:
            msg = "\033[1;33mEXCEPTION:\033[0;37m{}"
            print(msg.format(exc))
            sys.exit(3)
        return(None)

    def get_pstree(self):  # FIX: make better version
        ps_tree = []
        h = 0
        me = psutil.Process()
        parent = psutil.Process(me.ppid())
        while parent.ppid() != 0:
            ps_tree.append({'pid': parent.pid,
                            'cmdline': parent.cmdline(),
                            'order': h})
            parent = psutil.Process(parent.ppid())
            h = h+1
        return(ps_tree)

    def get_caller(self):
        me = psutil.Process()
        parent = psutil.Process(me.ppid())
        grandparent = psutil.Process(parent.ppid())
        return(grandparent.cmdline())

    def get_lineno(self):
        try:
            return(os.environ['LINENO'])
        except Exception:
            # TODO: add stderr warning about no LINENO
            return(None)

    def get_timestamp(self):
        return(datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f'))


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("-L", "--level",
                        choices=['ok', 'warn', 'error', 'info', 'critical', 'debug'],
                        default="info",
                        help="Level of update to send, defaults to 'info'")
    parser.add_argument("-c", "--hume-cmd",
                        choices=['counter-start',
                                 'counter-pause',
                                 'counter-stop',
                                 'counter-reset'],
                        default='',
                        dest='humecmd',
                        required=False,
                        help="[OPTIONAL] Command to attach to the update.")
    parser.add_argument("-m", "--msg",
                        required=True,
                        help="[REQUIRED] Message to include with this update")
    parser.add_argument("-t", "--task",
                        required=False,
                        default='',
                        help="[OPTIONAL] Task name, for example BACKUPTASK.")
    parser.add_argument('-a', '--append-pstree',
                        action='store_true',
                        help="Append process calling tree")
    parser.add_argument('-T', '--tags',
                        type=lambda arg: arg.split(','),
                        help="Comma-separated list of tags")
    parser.add_argument('-e', '--encrypt-to',
                        default=None,
                        action=NotImplementedAction,
                        dest='encrypt_to',
                        help="[OPTIONAL] Encrypt to this gpg pubkey id")
    args = parser.parse_args()
    Hume(args).send(encrypt_to=args.encrypt_to)


if __name__ == '__main__':
    run()
    sys.exit(0)
