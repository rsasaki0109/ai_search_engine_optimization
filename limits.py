"""Process-local budgets for the single-instance public beta."""
from collections import deque
from contextlib import contextmanager
import threading
import time

class CapacityError(ValueError):
    pass

class RuntimeLimits:
    def __init__(self, jobs=3, per_minute=30, clock=time.monotonic):
        self.slots=threading.BoundedSemaphore(jobs)
        self.per_minute=per_minute
        self.clock=clock
        self.recent=deque()
        self.lock=threading.Lock()

    def admit(self,cost=1):
        with self.lock:
            now=self.clock()
            while self.recent and self.recent[0]<=now-60:self.recent.popleft()
            if len(self.recent)+cost>self.per_minute:return False
            self.recent.extend([now]*cost)
            return True

    @contextmanager
    def job(self):
        if not self.slots.acquire(blocking=False):
            raise CapacityError('ただいま診断が混み合っています。少し待って再試行してください。')
        try:yield
        finally:self.slots.release()
