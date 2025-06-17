import os
import unittest

from unittest import mock

from humewatchdog import is_running, check_once

class TestWatchdog(unittest.TestCase):
    def test_is_running_true(self):
        pidfile = 'tmp.pid'
        with open(pidfile, 'w') as f:
            f.write(str(os.getpid()))
        try:
            self.assertTrue(is_running(pidfile))
        finally:
            os.remove(pidfile)

    def test_is_running_false(self):
        pidfile = 'tmp.pid'
        with open(pidfile, 'w') as f:
            f.write('999999')
        try:
            self.assertFalse(is_running(pidfile))
        finally:
            os.remove(pidfile)

    def test_alert_called_when_not_running(self):
        pidfile = 'tmp.pid'
        with open(pidfile, 'w') as f:
            f.write('999999')
        try:
            with mock.patch('subprocess.call') as call:
                check_once(pidfile, alert_cmd='echo alert', verbose=False)
                call.assert_called_once()
        finally:
            os.remove(pidfile)

if __name__ == '__main__':
    unittest.main()
