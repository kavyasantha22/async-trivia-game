import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from client import Client


class TestClientConstructMessages(unittest.TestCase):
    def test_construct_hi_message(self):
        client = Client(username="bob", mode="you")
        message = client._construct_hi_message()
        self.assertEqual(message["message_type"], "HI")
        self.assertEqual(message["username"], "bob")

    def test_construct_bye_message(self):
        client = Client(username="bob", mode="you")
        message = client._construct_bye_message()
        self.assertEqual(message["message_type"], "BYE")