import hashlib
import secrets
import time
from threading import Lock


class InMemoryOAuthStore:
    AUTH_CODE_TTL_SECONDS = 180
    REFRESH_TOKEN_TTL_SECONDS = 2592000  # 30 * 24 * 60 * 60

    def __init__(self) -> None:
        self._codes: dict[str, float] = {}
        self._refresh_tokens: dict[str, tuple[str, float]] = {}
        self._lock = Lock()

    def issue(self) -> str:
        code = secrets.token_urlsafe(32)
        with self._lock:
            self._purge_expired_locked()
            self._codes[code] = time.time() + self.AUTH_CODE_TTL_SECONDS
        return code

    def consume(self, code: str) -> bool:
        now = time.time()
        with self._lock:
            self._purge_expired_locked()
            expires_at = self._codes.pop(code, None)
            return expires_at is not None and expires_at >= now

    def issue_refresh(self, user_id: str) -> str:
        token = secrets.token_urlsafe(48)
        token_hash = _hash_token(token)
        with self._lock:
            self._purge_expired_locked()
            self._refresh_tokens[token_hash] = (
                user_id,
                time.time() + self.REFRESH_TOKEN_TTL_SECONDS,
            )
        return token

    def rotate_refresh(self, token: str) -> tuple[str, str] | None:
        old_hash = _hash_token(token)
        new_token = secrets.token_urlsafe(48)
        with self._lock:
            self._purge_expired_locked()
            record = self._refresh_tokens.pop(old_hash, None)
            if record is None:
                return None
            user_id, _ = record
            self._refresh_tokens[_hash_token(new_token)] = (
                user_id,
                time.time() + self.REFRESH_TOKEN_TTL_SECONDS,
            )
        return user_id, new_token

    def _purge_expired_locked(self) -> None:
        now = time.time()
        self._codes = {code: exp for code, exp in self._codes.items() if exp >= now}
        self._refresh_tokens = {token: record for token, record in self._refresh_tokens.items() if record[1] >= now}


class RedisOAuthStore:
    AUTH_CODE_TTL_SECONDS = 180
    REFRESH_TOKEN_TTL_SECONDS = 2592000
    _ROTATE_SCRIPT = """
    local user_id = redis.call('GET', KEYS[1])
    if not user_id then return 0 end
    redis.call('DEL', KEYS[1])
    redis.call('SET', KEYS[2], user_id, 'EX', ARGV[1])
    return user_id
    """

    def __init__(self, redis_url: str) -> None:
        try:
            import redis
        except ImportError as error:
            raise RuntimeError("REDIS_URL задан но пакет redis не установлен") from error
        self._redis = redis.Redis.from_url(redis_url, decode_responses=True)
        self._prefix = "smart-kettle:oauth:"

    def issue(self) -> str:
        code = secrets.token_urlsafe(32)
        self._redis.setex(self._key("code", code), self.AUTH_CODE_TTL_SECONDS, "1")
        return code

    def consume(self, code: str) -> bool:
        key = self._key("code", code)
        try:
            return self._redis.getdel(key) is not None
        except AttributeError:
            deleted = self._redis.eval(
                "local value = redis.call('GET', KEYS[1]); if value then redis.call('DEL', KEYS[1]) end; return value",
                1,
                key,
            )
            return deleted is not None

    def issue_refresh(self, user_id: str) -> str:
        token = secrets.token_urlsafe(48)
        self._redis.setex(
            self._key("refresh", _hash_token(token)),
            self.REFRESH_TOKEN_TTL_SECONDS,
            user_id,
        )
        return token

    def rotate_refresh(self, token: str) -> tuple[str, str] | None:
        new_token = secrets.token_urlsafe(48)
        user_id = self._redis.eval(
            self._ROTATE_SCRIPT,
            2,
            self._key("refresh", _hash_token(token)),
            self._key("refresh", _hash_token(new_token)),
            self.REFRESH_TOKEN_TTL_SECONDS,
        )
        if user_id == 0 or user_id is None:
            return None
        return str(user_id), new_token

    def _key(self, kind: str, value: str) -> str:
        return f"{self._prefix}{kind}:{value}"


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_oauth_store(redis_url: str | None):
    if redis_url:
        return RedisOAuthStore(redis_url)
    return InMemoryOAuthStore()
