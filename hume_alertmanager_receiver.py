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
    print('DECODED JSON BODY:\n{}'.format(jBody))

    # OK, let's handle this
    # First, lets extract/construct level, msg, tags and task
    try:
        status = jBody['status'].strip()
    except Exception:
        status = 'unknown_status'
    try:
        level = jBody['commonLabels']['severity']
    except Exception:
        level = 'warning'  # Sensible default? alpha software, people!
    try:
        task = jBody['commonLabels']['service']
    except Exception:
        task = 'unknown_task'
    try:
        tags = [jBody['commonLabels']['instance']]
    except Exception:
        tags = []

    try:
        startsAt = jBody['alerts'][0]['labels']['startsAt']
    except Exception:
        d = datetime.datetime.utcnow()
        startsAt = '{}Z'.format(d.isoformat("T"))

    try:
        summary = jBody['commonAnnotations']['summary']
    except Exception:
        summary = 'n/a'
    msg = "Current Status: {} - Annotation: {} - Date: {}".format(status,
                                                                  summary,
                                                                  startsAt)
    humePkt = {'level': level,
               'msg': msg,
               'tags': tags,
               'task': task,}
    pprint(humePkt)
    try:
        Hume(humePkt).send()
    except Exception as exc:
        print('Error sending hume:')
        print(exc)
    return


handlers = {"POST": process_alertmanager_request}
webhook_receiver = webhook_listener.Listener(handlers=handlers)
#webhook_receiver = webhook_listener.Listener(host=args.host,
#                                             port=args.port,
#                                             handlers=handlers,
#                                             debug=args.debug,
#                                             threadPool=args.threadPool)
webhook_receiver.start()

try:
    while True:
        print("Still alive...")
        time.sleep(300)
except KeyboardInterrupt:
    webhook_receiver.stop()

    