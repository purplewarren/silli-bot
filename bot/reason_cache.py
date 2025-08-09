import time, hashlib, json

class TTLCache:
    def __init__(self, ttl=60, max_items=128):
        self.ttl, self.max = ttl, max_items
        self.store = {}
    
    def _key(self, payload: dict) -> str:
        s = json.dumps(payload, sort_keys=True)
        return hashlib.sha1(s.encode()).hexdigest()
    
    def get(self, payload):
        k = self._key(payload)
        v = self.store.get(k)
        if not v:
            return None
        data, exp = v
        if time.time() > exp:
            self.store.pop(k, None)
            return None
        return data
    
    def set(self, payload, data):
        if len(self.store) >= self.max:
            self.store.pop(next(iter(self.store)))
        self.store[self._key(payload)] = (data, time.time() + self.ttl)

# Global cache instance
cache = TTLCache()
