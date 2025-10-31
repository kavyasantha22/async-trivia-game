# Trivia Game Project

This repository contains an asynchronous trivia game (server + client) and automated tests.

## Requirements

- Python 3.11+ (developed with Python 3.13)
- `requests` (only needed when the client runs in `ai` mode)

## Files You Need

- `server.py` — trivia server
- `client.py` — async client (supports `you`, `auto`, `ai` modes)
- `s.json` — sample server configuration
- `c.json` — sample client configuration
- `run_tests.sh` — helper script to run all tests

## Run the Trivia Game

1. Terminal #1 — start the server:
   ```bash
   python3 server.py --config s.json
   ```
2. Terminal #2 — start the client:
   ```bash
   python3 client.py --config c.json
   ```
3. In the client prompt, connect to the server:
   ```
   CONNECT 0.0.0.0:7777
   ```
4. Play the round. Type `DISCONNECT` to leave or `EXIT` to shut down the client.

## Run the Tests

- All tests (unit + integration):
  ```bash
  bash run_tests.sh
  ```
- Unit tests only:
  ```bash
  python3 -m unittest discover tests/unit -v
  ```
- Integration tests only:
  ```bash
  python3 tests/integration/run_integration_tests.py
  ```

That’s it—once the server and client are running, follow the client prompts to play. Tests can be rerun at any time to verify changes.
