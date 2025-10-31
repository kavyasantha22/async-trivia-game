import re
import sys
from pathlib import Path
import unittest

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from questions import (
    generate_mathematics_question,
    generate_roman_numerals_question,
    generate_usable_addresses_question,
    generate_network_broadcast_question,
)


class TestQuestionGeneration(unittest.TestCase):
    def test_generate_mathematics_question_pattern(self):
        pattern = re.compile(r"^(?:100|[1-9]\d?)(?: [+-] (?:100|[1-9]\d?)){1,4}$")
        for _ in range(20):
            question = generate_mathematics_question()
            self.assertRegex(question, pattern)

    def test_generate_roman_numerals_question_pattern(self):
        pattern = re.compile(r"^M{0,3}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$")
        for _ in range(20):
            question = generate_roman_numerals_question()
            self.assertRegex(question, pattern)

    def test_generate_usable_addresses_question_pattern(self):
        for _ in range(20):
            question = generate_usable_addresses_question()
            self._assert_valid_ip_cidr(question)

    def test_generate_network_broadcast_question_pattern(self):
        for _ in range(20):
            question = generate_network_broadcast_question()
            self._assert_valid_ip_cidr(question)

    def _assert_valid_ip_cidr(self, cidr_notation: str):
        pattern = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}/(3[0-2]|[12]?\d)$")
        self.assertRegex(cidr_notation, pattern)
        ip_part, mask_part = cidr_notation.split("/")
        octets = ip_part.split(".")
        self.assertEqual(len(octets), 4)
        for octet in octets:
            value = int(octet)
            self.assertGreaterEqual(value, 0)
            self.assertLessEqual(value, 255)
        cidr = int(mask_part)
        self.assertGreaterEqual(cidr, 0)
        self.assertLessEqual(cidr, 32)


