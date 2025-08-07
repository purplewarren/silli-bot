# bot/families.py
import json, os, threading
from pathlib import Path
from typing import List, Set

class FamiliesStore:
    def __init__(self, path: str = "data/families.json"):
        self.path = Path(path)
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write(set())

    def _read(self) -> Set[int]:
        if not self.path.exists():
            return set()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return set(int(x) for x in data)
        except Exception:
            return set()

    def _write(self, s: Set[int]) -> None:
        self.path.write_text(json.dumps(sorted(list(s))), encoding="utf-8")

    def add(self, chat_id: int) -> None:
        with self._lock:
            s = self._read()
            if int(chat_id) not in s:
                s.add(int(chat_id))
                self._write(s)

    def remove(self, chat_id: int) -> None:
        with self._lock:
            s = self._read()
            if int(chat_id) in s:
                s.remove(int(chat_id))
                self._write(s)

    def list(self) -> List[int]:
        with self._lock:
            return sorted(list(self._read())) 