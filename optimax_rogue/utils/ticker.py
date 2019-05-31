"""This module allows sleeping excess time when updates aren't taking very
long"""
import time

class Ticker:
    """A callable object that sleeps excess time between invocations

    Attributes:
        target_secs (float): the target time between calls
        last_at (float, optional): result from time.time() at end of last invocation
    """

    def __init__(self, target_secs: float):
        self.target_secs = target_secs
        self.last_at = None

    def __call__(self):
        if self.last_at is not None:
            dtime = time.time() - self.last_at
            if dtime < self.target_secs:
                time.sleep(self.target_secs - dtime)
        self.last_at = time.time()
