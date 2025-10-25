# timeouts.py
import signal
from contextlib import contextmanager

class TimeLimitError(Exception):
    pass

@contextmanager
def time_limit(seconds: float):
    if not seconds or seconds <= 0:
        yield
        return

    def _raise_timeout(signum, frame):
        raise TimeoutError("time limit exceeded")

    old_handler = signal.signal(signal.SIGALRM, _raise_timeout)
    try:
        signal.setitimer(signal.ITIMER_REAL, float(seconds))
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0.0) 
        signal.signal(signal.SIGALRM, old_handler)
