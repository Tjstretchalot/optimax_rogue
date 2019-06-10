"""This module allows sleeping excess time when updates aren't taking very
long"""
import time
import typing

class Ticker:
    """A callable object that sleeps excess time between invocations

    Attributes:
        target_secs (float): the target time between calls
        last_at (float, optional): result from time.time() at end of last invocation
        secondary_target_secs (float): the target we are going for for the specified time
            killer. if it doesn't use all its time and target_secs < secondary_target_secs,
            we return early
        time_killer (callable, optional): if available, a function that can be passed
            a target amount of time in seconds which might use some of it
    """

    def __init__(self, target_secs: float, secondary_target_secs: float = 0.0,
                 time_killer: typing.Callable = None):
        self.target_secs = target_secs
        self.time_killer = time_killer
        self.secondary_target_secs = secondary_target_secs
        self.last_at = None

    def __call__(self):
        if self.last_at is not None:
            dtime = time.time() - self.last_at
            if dtime < self.target_secs:
                if self.time_killer and dtime < self.secondary_target_secs:
                    self.time_killer(self.secondary_target_secs - dtime)
                    dtime = time.time() - self.last_at
                if dtime < self.target_secs:
                    time.sleep(self.target_secs - dtime)
        self.last_at = time.time()
