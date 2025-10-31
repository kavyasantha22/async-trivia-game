#!/usr/bin/env python3

from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
import time
import unittest
from pathlib import Path
from types import SimpleNamespace


def _run_with_suppressed_modules(
    runner: unittest.TextTestRunner,
    suite: unittest.TestSuite,
    *,
    modules_to_quiet: set[str],
) -> unittest.result.TestResult:
    suppressors: list[tuple[str, object]] = []
    try:
        for module_name in modules_to_quiet:
            if module_name in sys.modules:
                suppressors.append((module_name, sys.modules[module_name]))

        original_print_functions: dict[str, object] = {}
        for name, module in suppressors:
            if hasattr(module, "print"):
                original_print_functions[name] = module.print
                module.print = lambda *_, **__: None  # type: ignore[attr-defined]

        with contextlib.redirect_stdout(io.StringIO()):
            return runner.run(suite)
    finally:
        for name, module in suppressors:
            if name in original_print_functions:
                module.print = original_print_functions[name]



class _Color:
    GREEN = "\033[32m"
    RED = "\033[31m"
    YELLOW = "\033[33m"
    CYAN = "\033[36m"
    MAGENTA = "\033[35m"
    BLUE = "\033[34m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def _indent(text: str, prefix: str = "    ") -> str:
    return "\n".join(f"{prefix}{line}" for line in text.strip().splitlines())


class ColorizedTestResult(unittest.TextTestResult):
    """Custom test result that prints each outcome with ANSI colours."""

    def addSuccess(self, test: unittest.case.TestCase) -> None:  # type: ignore[override]
        super().addSuccess(test)
        self.stream.writeln(f"{_Color.GREEN}PASS {test.id()}{_Color.RESET}")

    def addFailure(self, test: unittest.case.TestCase, err) -> None:  # type: ignore[override]
        super().addFailure(test, err)
        details = self.failures[-1][1]
        self.stream.writeln(f"{_Color.RED}FAIL {test.id()}{_Color.RESET}")
        self.stream.writeln(_indent(details))

    def addError(self, test: unittest.case.TestCase, err) -> None:  # type: ignore[override]
        super().addError(test, err)
        details = self.errors[-1][1]
        self.stream.writeln(f"{_Color.RED}ERROR {test.id()}{_Color.RESET}")
        self.stream.writeln(_indent(details))


class ColorizedTextRunner(unittest.TextTestRunner):
    resultclass = ColorizedTestResult

    def __init__(self) -> None:
        super().__init__(stream=sys.stdout, verbosity=0, buffer=False)


def main() -> None:
    script_path = Path(__file__).resolve()
    project_root = script_path.parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # Provide a minimal pytest stub if the dependency is unavailable but imported by tests.
    try:  # pragma: no cover - environment dependent
        import pytest  # type: ignore  # noqa: F401
    except ModuleNotFoundError:
        sys.modules.setdefault("pytest", SimpleNamespace())

    unit_dir = script_path.parent
    test_files = sorted(unit_dir.rglob("*_testing.py"))

    suite = unittest.TestSuite()
    load_errors: list[tuple[Path, Exception]] = []

    for file_path in test_files:
        module_name = "unit_tests." + ".".join(file_path.relative_to(unit_dir).with_suffix("").parts)
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            load_errors.append((file_path, ImportError("Unable to create module spec")))
            continue
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        except Exception as exc:  # pragma: no cover - load failure feedback
            load_errors.append((file_path, exc))
            continue

        module_suite = unittest.defaultTestLoader.loadTestsFromModule(module)
        if module_suite.countTestCases():
            suite.addTests(module_suite)

    if load_errors:
        for path, exc in load_errors:
            print(f"{_Color.RED}Failed to import {path}:{_Color.RESET}")
            print(_indent(str(exc)))
        sys.exit(1)

    runner = ColorizedTextRunner()
    start = time.perf_counter()
    result = _run_with_suppressed_modules(runner, suite, modules_to_quiet={"server", "client"})
    duration = time.perf_counter() - start

    total = result.testsRun
    failed = len(result.failures)
    errored = len(result.errors)
    passed = total - failed - errored

    summary = (
        f"{_Color.BOLD}Summary:{_Color.RESET} "
        f"{_Color.GREEN}{passed} passed{_Color.RESET}, "
        f"{_Color.RED}{failed} failed{_Color.RESET}, "
        f"{_Color.RED}{errored} errors{_Color.RESET}"
    )
    timing = f"{_Color.BLUE}Duration: {duration:.2f}s{_Color.RESET}"

    print()
    print(summary)
    print(timing)

    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()

