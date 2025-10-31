#!/bin/bash

set -u

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

printf "Running unit tests...\n"
python3 -m unittest discover "$ROOT_DIR/tests/unit" -v
UNIT_STATUS=$?

printf "\nRunning integration tests...\n"
python3 "$ROOT_DIR/tests/integration/run_integration_tests.py"
INTEGRATION_STATUS=$?

if [[ "$UNIT_STATUS" -eq 0 && "$INTEGRATION_STATUS" -eq 0 ]]; then
  exit 0
else
  exit 1
fi
