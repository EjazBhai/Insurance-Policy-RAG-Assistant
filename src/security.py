"""API-key authentication and rate limiting (no heavy dependencies)."""
import hashlib
import hmac
import json
import secrets
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass


def new_api_key() -> str:
    return "pk_" + secrets.token_urlsafe(32)


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class User:
    name: str
    allowed: frozenset | None  # None = all documents, empty = none
    rate_limit_per_min: int = 20


class UserStore:
    """Holds users keyed by the SHA-256 hash of their API key.
    Plaintext keys are never stored."""

    def __init__(self, users: dict):
        self._users = []
        for name, cfg in users.items():
            sources = cfg.get("sources", [])
            allowed = None if "*" in sources else frozenset(sources)
            self._users.append((cfg["key_hash"],
                                User(name, allowed, int(cfg.get("rate_limit_per_min", 20)))))

    @classmethod
    def from_file(cls, path: str) -> "UserStore":
        with open(path, encoding="utf-8") as f:
            return cls(json.load(f)["users"])

    def authenticate(self, key: str) -> User | None:
        digest = hash_key(key)
        found = None
        for stored, user in self._users:  # compare against all: constant-time per entry
            if hmac.compare_digest(stored, digest):
                found = user
        return found


class RateLimiter:
    """In-memory sliding window. Per-process: use Redis if you run many replicas."""

    def __init__(self, window_seconds: int = 60):
        self.window = window_seconds
        self._hits = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, identity: str, limit: int, now: float | None = None):
        """Returns (allowed, retry_after_seconds)."""
        now = time.monotonic() if now is None else now
        with self._lock:
            q = self._hits[identity]
            while q and now - q[0] >= self.window:
                q.popleft()
            if len(q) >= limit:
                return False, max(1, int(self.window - (now - q[0])) + 1)
            q.append(now)
            return True, 0