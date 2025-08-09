import time
from collections import deque

class Rolling:
    def __init__(self, window=300):
        self.window, self.events = window, deque()
    
    def observe(self, ok: bool, ms: int):
        now = time.time()
        self.events.append((now, ok, ms))
        while self.events and now - self.events[0][0] > self.window:
            self.events.popleft()
    
    def snapshot(self):
        arr = list(self.events)
        n = len(arr)
        if not n:
            return {"n": 0, "ok": 0, "p50": 0, "p95": 0}
        
        lat = [ms for _, _, ms in arr]
        lat.sort()
        ok = sum(1 for _, ok_, _ in arr if ok_)
        
        def pct(p):
            i = min(n - 1, int(p * (n - 1)))
            return lat[i]
        
        return {"n": n, "ok": ok, "p50": pct(0.5), "p95": pct(0.95)}

# Global metrics instance
metrics = Rolling()
