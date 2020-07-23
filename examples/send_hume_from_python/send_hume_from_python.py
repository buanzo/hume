#!/usr/bin/env python3
#
# Example of sending a hume message directly from Python
# 
#
from hume import Hume

msg = {
#    'level': 'warning',
    'msg': 'Hello World',
    'extra': {'instance_name': 'hola'},
#    'tags': ['test','example'],
    'task': 'EXAMPLE',}

Hume(msg).send()
