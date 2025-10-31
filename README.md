# Trivia Game Project

This repository contains an asynchronous trivia game with a server, multiple client modes, and a suite of unit and integration tests.

## Requirements

- Python 3.11+ (project tested with Python 3.13)
- `requests` library for the AI client mode (`pip install requests`)
- (Optional) `pytest` is **not** required; the provided tests use the built-in `unittest` runner.

## Key Files

| Path | Description |
| --- | --- |
| `server.py` | Trivia game server implementation. |
| `client.py` | Async client supporting human, automated, and AI modes. |
| `helper.py`, `answer.py`, `questions.py` | Shared helpers for messaging, question generation, and answer logic. |
| `run_server.sh`, `run_client.sh` | Convenience scripts for launching the server or client (wrap the Python commands below). |
| `run_tests.sh` | Runs unit tests followed by integration tests. |
| `tests/unit/*` | Unit test suite. |
| `tests/integration/*` | Integration test harness, test cases, and fixtures. |
| `tests/config_files/*` | Sample JSON configs used by the automated tests. |
| `s.json`, `c.json`, etc. | Example runtime configuration files (server/client). |

## Configuration Files

### Server configuration (`server.py --config <path>`):

Example (`s.json`):

```json
{
  "port": 7777,
  "players": 2,
  "question_types": [
    "Usable IP Addresses of a Subnet",
    "Network and Broadcast Address of a Subnet"
  ],
  "question_formats": {
    "Mathematics": "Evaluate {}",
    "Roman Numerals": "Calculate the decimal value of {}",
    "Usable IP Addresses of a Subnet": "How many usable addresses in {}?",
    "Network and Broadcast Address of a Subnet": "Network and broadcast addresses of {}?"
  },
  "question_seconds": 10,
  "question_interval_seconds": 5.5,
  "ready_info": "Game starts in {question_interval_seconds} seconds!",
  "question_word": "Question",
  "correct_answer": "Woohoo! Great job! You got it!",
  "incorrect_answer": "Maybe next time :(",
  "points_noun_singular": "point",
  "points_noun_plural": "points",
  "final_standings_heading": "Final standings:",
  "one_winner": "The winner is: {}",
  "multiple_winners": "The winners are: {}"
}
```

### Client configuration (`client.py --config <path>`):

Required example fields (`c.json`):

```json
{
  "username": "player1",
  "client_mode": "you",
  "ollama_config": {
    "ollama_host": "localhost",
    "ollama_port": 11434,
    "ollama_model": "llama3"
  }
}
```

- `client_mode` can be `you`, `auto`, or `ai`.
- `ollama_config` is only required for the `ai` mode.

## Running the Trivia Game

1. **Start the server**:

   ```bash
   python3 server.py --config s.json
   ```

   or use the helper script:

   ```bash
   ./run_server.sh
   ```

2. **Start the client** (in another terminal):

   ```bash
   python3 client.py --config c.json
   ```

   or:

   ```bash
   ./run_client.sh
   ```

3. **Connect from the client**: when prompted, type a connect command, for example:

   ```
   CONNECT 0.0.0.0:7777
   ```

4. Follow the prompts to play. Use `DISCONNECT` to leave gracefully or `EXIT` to quit the client entirely.

## Running the Tests

### All tests

```bash
bash run_tests.sh
```

The script prints progress for unit tests first, then integration tests, and returns a non-zero exit code if any suite fails.

### Unit tests only

```bash
python3 -m unittest discover tests/unit -v
```

### Integration tests only

```bash
python3 tests/integration/run_integration_tests.py
```

### Regenerate integration fixtures (optional)

```bash
bash tests/integration/create_test_cases.sh
```

This replays the scripted scenarios to refresh the `*.expected` files.

## Notes

- The project is asynchronous and assumes TCP socket availability on the configured port.
- The client’s interactive commands (`CONNECT`, `DISCONNECT`, `EXIT`) are line-based; ensure each command is followed by `Enter`.
- AI mode requires a running Ollama instance matching the configuration values.
