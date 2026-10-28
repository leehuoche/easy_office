"""Clock injection keeps production timestamps and deterministic tests separate."""
import time


class SystemClock:
    def now(self):
        return time.time()


class ManualClock:
    def __init__(self, initial=0.0):
        self.value = float(initial)

    def now(self):
        return self.value

    def advance(self, seconds):
        if seconds < 0:
            raise ValueError("Clock cannot move backwards")
        self.value += seconds
