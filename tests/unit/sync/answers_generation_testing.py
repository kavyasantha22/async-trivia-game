import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from answer import generate_answer
import unittest

# if __name__ == "__main__":
#     unittest.main(model)

class TestAnswerGeneration(unittest.TestCase):
    def test_mathematics(self):
        qtype = "Mathematics"
        MATH_CASES = [
            ("1 + 5 - 2 + 7 - 8", "3"),
            ("12 + 4 - 6 + 9 - 5", "14"),
            ("3 - 8 + 10 - 2 + 7", "10"),
            ("15 - 3 + 2 + 6 - 4", "16"),
            ("20 - 5 - 7 + 8 + 1", "17"),
            ("9 + 11 - 13 + 5 - 2", "10"),
        ]
        for case in MATH_CASES:
            self.assertEqual(generate_answer(qtype, case[0]), case[1])


    def test_roman_numerals(self):
        qtype = "Roman Numerals"
        ROMAN_CASES = [
            ("IX", "9"),
            ("IV", "4"),
            ("XLII", "42"),
            ("MCMLXXXIV", "1984"),
            ("MMXX", "2020"),
        ]
        for case in ROMAN_CASES:
            self.assertEqual(generate_answer(qtype, case[0]), case[1])


    def test_network_and_broadcast(self):
        qtype = "Network and Broadcast Address of a Subnet"
        NETWORK_CASES = [
            ("192.168.1.10/24", "192.168.1.0 and 192.168.1.255"),
            ("10.0.0.25/8", "10.0.0.0 and 10.255.255.255"),
            ("172.16.5.3/20", "172.16.0.0 and 172.16.15.255"),
            ("203.0.113.12/30", "203.0.113.12 and 203.0.113.15"),
        ]
        for case in NETWORK_CASES:
            self.assertEqual(generate_answer(qtype, case[0]), case[1])


    def test_usable_ip_addresses(self):
        qtype = "Usable IP Addresses of a Subnet"
        USABLE_CASES = [
            ("10.0.0.1/24", "254"),
            ("10.0.0.1/31", "1"),
            ("172.16.5.42/16", "65534"),
            ("192.168.1.1/30", "2"),
            ("192.168.1.1/32", "0"),
        ]
        for case in USABLE_CASES:
            self.assertEqual(generate_answer(qtype, case[0]), case[1])

