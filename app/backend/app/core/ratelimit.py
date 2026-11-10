"""Простой ограничитель частоты запросов в памяти процесса.

Подходит для одного процесса (демо и небольшой хостинг). При нескольких
процессах лимит действует отдельно в каждом: этого достаточно, чтобы публичный
эндпоинт нельзя было использовать для перегрузки сервиса.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from typing import Deque, Dict


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_seconds: float) -> None:
        self.limit = limit
        self.window = window_seconds
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, now: float | None = None) -> bool:
        moment = time.monotonic() if now is None else now
        with self._lock:
            hits = self._hits[key]
            while hits and moment - hits[0] > self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                return False
            hits.append(moment)
            # не даём словарю расти бесконечно
            if len(self._hits) > 5000:
                for stale in [k for k, v in self._hits.items() if not v]:
                    self._hits.pop(stale, None)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()
