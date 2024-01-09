from unittest import TestCase

from jchannel import init


class InitTest(TestCase):
    def test_stub(self):
        self.assertIsNotNone(init)
