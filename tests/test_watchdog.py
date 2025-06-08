import os
import unittest

from humewatchdog import is_running

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

if __name__ == '__main__':
    unittest.main()
