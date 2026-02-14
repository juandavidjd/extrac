"""
ODI Rate Limiter - Middleware Redis para FastAPI
================================================
Rate limiting por IP usando Redis como backend.
Si Redis no está disponible, usa un dict en memoria como fallback.
"""
import time
import logging
from typing import Optional, Dict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

log = logging.getLogger("odi.rate_limiter")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiter por IP con ventana deslizante.
    
    Args:
        app: FastAPI app
        redis_url: URL de Redis (default redis://127.0.0.1:6379)
        requests_per_minute: Límite de requests por minuto por IP
        burst_limit: Límite de burst (requests en 5 segundos)
        exclude_paths: Paths excluidos del rate limiting (e.g. /health)
    """

    def __init__(
        self,
        app,
        redis_url: str = "redis://127.0.0.1:6379",
        requests_per_minute: int = 30,
        burst_limit: int = 10,
        exclude_paths: Optional[list] = None,
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_limit = burst_limit
        self.exclude_paths = set(exclude_paths or ["/health", "/docs", "/openapi.json"])
        self.redis = None
        self._memory_store: Dict[str, list] = {}

        try:
            import redis as redis_lib
            self.redis = redis_lib.Redis.from_url(redis_url, decode_responses=True)
            self.redis.ping()
            log.info(f"Rate limiter: Redis connected ({requests_per_minute} req/min)")
        except Exception as e:
            log.warning(f"Rate limiter: Redis unavailable ({e}), using in-memory fallback")
            self.redis = None

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _check_rate_redis(self, key: str, now: float) -> tuple:
        """Check rate limit using Redis sorted sets."""
        pipe = self.redis.pipeline()
        window_start = now - 60

        # Clean old entries and count current window
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, 120)

        # Burst check (last 5 seconds)
        burst_key = f"{key}:burst"
        burst_start = now - 5
        pipe.zremrangebyscore(burst_key, 0, burst_start)
        pipe.zadd(burst_key, {str(now): now})
        pipe.zcard(burst_key)
        pipe.expire(burst_key, 10)

        results = pipe.execute()
        minute_count = results[2]
        burst_count = results[6]

        return minute_count, burst_count

    def _check_rate_memory(self, key: str, now: float) -> tuple:
        """Fallback in-memory rate check."""
        if key not in self._memory_store:
            self._memory_store[key] = []

        # Clean old entries
        window_start = now - 60
        self._memory_store[key] = [t for t in self._memory_store[key] if t > window_start]
        self._memory_store[key].append(now)

        minute_count = len(self._memory_store[key])
        burst_count = len([t for t in self._memory_store[key] if t > now - 5])

        # Periodic cleanup of stale keys
        if len(self._memory_store) > 1000:
            stale = [k for k, v in self._memory_store.items() if not v or v[-1] < now - 300]
            for k in stale:
                del self._memory_store[k]

        return minute_count, burst_count

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        client_ip = self._get_client_ip(request)
        now = time.time()
        key = f"odi:ratelimit:{client_ip}"

        try:
            if self.redis:
                minute_count, burst_count = self._check_rate_redis(key, now)
            else:
                minute_count, burst_count = self._check_rate_memory(key, now)
        except Exception as e:
            log.error(f"Rate limiter error: {e}")
            return await call_next(request)

        # Check burst limit
        if burst_count > self.burst_limit:
            log.warning(f"Rate limit BURST exceeded: {client_ip} ({burst_count}/{self.burst_limit} in 5s)")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "detail": f"Burst limit exceeded ({self.burst_limit} requests per 5 seconds)",
                    "retry_after": 5,
                },
                headers={"Retry-After": "5"},
            )

        # Check per-minute limit
        if minute_count > self.requests_per_minute:
            log.warning(f"Rate limit exceeded: {client_ip} ({minute_count}/{self.requests_per_minute}/min)")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "detail": f"Rate limit exceeded ({self.requests_per_minute} requests per minute)",
                    "retry_after": 60,
                },
                headers={"Retry-After": "60"},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(max(0, self.requests_per_minute - minute_count))
        return response
