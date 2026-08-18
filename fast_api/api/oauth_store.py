import secrets
import time
from threading import Lock


class InMemoryCodeStore:
    AUTH_CODE_TTL_SECONDS = 180

    def __init__(self) -> None:
        self._codes: dict[str, float] = {}
        self._lock = Lock()

    def issue(self) -> str:
        code = secrets.token_urlsafe(32)
        expires_at = time.time() + self.AUTH_CODE_TTL_SECONDS
        with self._lock:
            self._purge_expired_locked()
            self._codes[code] = expires_at
        return code

    def consume(self, code: str) -> bool:
        now = time.time()
        with self._lock:
            self._purge_expired_locked()
            expires_at = self._codes.pop(code, None)
            if expires_at is None:
                return False
            return expires_at >= now

    def _purge_expired_locked(self) -> None:
        now = time.time()
        expired = [c for c, exp in self._codes.items() if exp < now]
        for c in expired:
            self._codes.pop(c, None)


code_store = InMemoryCodeStore()
