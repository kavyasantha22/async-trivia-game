#!/usr/bin/env python3

import io
import subprocess
import sys
import difflib
import json
from pathlib import Path
import time
from contextlib import redirect_stdout, redirect_stderr

INTEGRATION_DIR = Path(__file__).resolve().parent
TEST_TIMEOUT = 2

RESET = "\033[0m"
GREEN = "\033[32m"
RED = "\033[31m"
CYAN = "\033[36m"
BOLD = "\033[1m"


def build_client(json_path: Path) -> subprocess.Popen:
    json.load(json_path.open("r", encoding="utf-8"))
    return subprocess.Popen(
        [sys.executable, "client.py", "--config", str(json_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def build_server(json_path: Path) -> subprocess.Popen:
    json.load(json_path.open("r", encoding="utf-8"))
    return subprocess.Popen([sys.executable, "server.py", "--config", str(json_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def build_ollama() -> subprocess.Popen:
    return subprocess.Popen([
        sys.executable,
        "ollama.py",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def run_integration_test(folder: Path, test_name: str) -> None:
    input_file = folder / f"{test_name}.in"
    actual_file = folder / f"{test_name}.actual"
    expected_file = folder / f"{test_name}.expected"

    for path in (input_file, expected_file):
        if not path.exists():
            raise FileNotFoundError(f"Missing file for {test_name}: {path}")

    client = build_client(folder / "client.json")
    server = build_server(folder / "server.json")
    ollama = build_ollama()

    time.sleep(1)

    with input_file.open("r", encoding="utf-8") as fh:
        stdin_data = fh.read()

    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        stdout, stderr = client.communicate(stdin_data.encode("utf-8"), timeout=TEST_TIMEOUT)

    combined_output = stdout.decode("utf-8") + stderr.decode("utf-8")
    actual_file.write_text(combined_output, encoding="utf-8")

    actual_lines = actual_file.read_text(encoding="utf-8").splitlines()
    expected_lines = expected_file.read_text(encoding="utf-8").splitlines()

    if actual_lines == expected_lines:
        print(f"{GREEN}PASS {test_name}{RESET}")
    else:
        print(f"{RED}FAIL {test_name}{RESET}")

    _cleanup_processes(client, server, ollama)


def _cleanup_processes(client: subprocess.Popen, server: subprocess.Popen, ollama: subprocess.Popen | None) -> None:
    for proc in (client, server, ollama):
        if proc is None:
            continue
        if proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=TEST_TIMEOUT)
            except (PermissionError, ProcessLookupError, OSError):
                continue
            except subprocess.TimeoutExpired:
                try:
                    proc.kill()
                    proc.wait(timeout=1)
                except (PermissionError, ProcessLookupError, OSError):
                    continue


if __name__ == "__main__":
    for test_folder in sorted(INTEGRATION_DIR.glob("test_*")):
        for expected_file in sorted(test_folder.glob("*.expected")):
            run_integration_test(test_folder, expected_file.stem)