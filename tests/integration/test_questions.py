#!/usr/bin/env python3
"""Utility to emit deterministic question samples for integration testing."""

from __future__ import annotations

import json
import sys

from questions import (
    generate_mathematics_question,
    generate_network_broadcast_question,
    generate_roman_numerals_question,
    generate_usable_addresses_question,
    set_seed,
)


def main() -> int:
    seed = sys.argv[1] if len(sys.argv) > 1 else "integration"
    set_seed(seed)

    samples = {
        "seed": seed,
        "mathematics": generate_mathematics_question(),
        "roman": generate_roman_numerals_question(),
        "usable_ip": generate_usable_addresses_question(),
        "network_broadcast": generate_network_broadcast_question(),
    }

    print(json.dumps(samples, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
