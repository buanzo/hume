#!/usr/bin/env python3
#
# An http server that conforms to:
# https://prometheus.io/docs/alerting/latest/configuration/#webhook_config
#
# Enables hume support for Prometheus' AlertManager
#
# Maybe include a nice AlertManager template...
# https://prometheus.io/blog/2016/03/03/custom-alertmanager-templates/
#
# Author: Buanzo

import argparse
from hume import Hume
import json
import time
import datetime
import webhook_listener
from pprint import pprint

__version__ = '0.1'
__version_str = 'Hume AlertManager Receiver v{} by Buanzo'.format(__version__)


def construct_hume(alert):
    labels = alert['labels']
    print('construct_hume')
    # OK, let's handle this
    # First, lets extract/construct level, msg, tags and task
    try:
        status = alert['status'].strip()
    except Exception:
        status = 'unknown_status'

    try:
        level = labels['severity']
    except Exception:
        level = 'warning'  # Sensible default? alpha software, people!

    try:
        #task = '{}[{}]'.format(labels['instance_name'], labels['ip'])
        task = labels['name']
    except Exception:
        if 'instance_name' in labels.keys():
            task = labels['instance_name']
        else:
            task = 'Alertmanager'

    tags = []
    try:
        tags.append(labels['alertname'])
    except Exception:
        pass

    try:
        tags.append(labels['job'])
    except Exception:
        pass

    try:
        tags.append(labels['type'])
    except Exception:
        pass

    try:
        tags.append(labels['region'])
    except Exception:
        pass

    try:
        tags.append(labels['flavor'])
    except Exception:
        pass

    try:
        startsAt = alert['startsAt']
    except Exception:
        d = datetime.datetime.utcnow()
        startsAt = '{}Z'.format(d.isoformat("T"))

    try:
#        summary = alert['annotations']['description']
        summary = alert['annotations']['summary']
    except Exception:
        summary = 'n/a'

# TODO: hume.msg = "STATUS: "+status+"\nDETAILS: "+annotations.summary
    try:
        status = alert['status']
    except Exception:
        status = 'n/a'
    msg = "Alert is {}.\n\n{}".format(status,
                                           summary)
    try:
        hostname = labels['instance'].split(':')[0]
    except Exception:
        hostname = 'n/a'

    extra = {}
    try:
        extra['instance_name'] = labels['instance_name']
    except Exception:
        extra = None

    humePkt = {'level': level,
               'msg': msg,
               'tags': tags,
               'task': task}
    if extra is not None:
        humePkt['extra'] = extra
    return(humePkt)


def process_alertmanager_request(request, *args, **kwargs):
    method = request.method
    cLength = int(request.headers['Content-Length'])
    cType = request.headers['Content-Type']
    if cType == 'application/json' and cLength > 0 and cLength < 65535:
        print('Decoding Body...')
        try:
            body = request.body.read(cLength)
        except Exception as exc:
            print(exc)
            return
        try:
            body = body.decode('utf8')
        except Exception as exc:
            print(exc)
            return
        try:
            jBody = json.loads(body)
        except Exception as exc:
            print(exc)
            return
    else:
        return
    # print('DECODED JSON BODY:')
    # pprint(jBody)
    #pprint(jBody['alerts'])
    for alert in jBody['alerts']:
        print('ALERTA:')
        pprint(alert)
        print('HUME:')
        humePkt = construct_hume(alert)
        pprint(humePkt)
    try:
        Hume(humePkt).send()
    except Exception as exc:
        print('Error sending hume:')
        print(exc)
    return


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('--version',
                        action='version',
                        version=__version_str)
    parser.add_argument('-l', '--listen',
                        default='127.0.0.1',
                        dest='host',
                        help='Listening IP for receiver. Default: 127.0.0.1.')
    parser.add_argument('-p', '--port',
                        default=8090,
                        type=int,
                        nargs=1,
                        dest='port',
                        help='Listening port for receiver. Default is 8090.')
    parser.add_argument('-d', '--debug',
                        default=False,
                        action='store_true',
                        dest='debug',
                        help='Enables debugging messages')
    parser.add_argument('-t', '--threadpoolsize',
                        default=10,
                        type=int,
                        nargs=1,
                        dest='threadPool',
                        help='Receiver threading pool size. Default 10.')
    handlers = {"POST": process_alertmanager_request}
    args = parser.parse_args()
    if args.debug:
        print('Running with args:')
        print('host={}'.format(args.host))
        print('port={}'.format(args.port))
        print('threadPoolSize={}'.format(args.threadPool))
    webhook_receiver = webhook_listener.Listener(host=args.host,
                                                 port=args.port,
                                                 debug=args.debug,
                                                 threadPool=args.threadPool,
                                                 handlers=handlers)
    webhook_receiver.start()

    try:
        while True:
            time.sleep(300)
    except KeyboardInterrupt:
        webhook_receiver.stop()


if __name__ == '__main__':
    run()
