import time
from collections import defaultdict, deque
from fastapi import Request, HTTPException, status


class SlidingWindowRateLimiter:
    """
    In-memory, IP-based sliding-window rate limiter.
    Maintains a rolling window of request timestamps per client IP.
    """

    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # Maps client_ip -> deque of float timestamps
        self._clients: dict[str, deque[float]] = defaultdict(deque)

    def is_allowed(self, client_ip: str) -> tuple[bool, int]:
        """
        Determines whether the client IP has exceeded max_requests in the window.
        Returns:
            (allowed: bool, retry_after_seconds: int)
        """
        now = time.time()
        cutoff = now - self.window_seconds
        timestamps = self._clients[client_ip]

        # 1. Evict timestamps outside the rolling window from the left
        while timestamps and timestamps[0] <= cutoff:
            timestamps.popleft()

        # 2. Check if current window has capacity
        if len(timestamps) >= self.max_requests:
            # Earliest request in the current window dictates when the next slot opens
            oldest_timestamp = timestamps[0]
            retry_after = int(self.window_seconds - (now - oldest_timestamp)) + 1
            return False, max(retry_after, 1)

        # 3. Request is allowed; record current timestamp
        timestamps.append(now)
        return True, 0


# Global limiter instance: 10 requests per 60 seconds per IP
rate_limiter = SlidingWindowRateLimiter(max_requests=10, window_seconds=60)


async def check_rate_limit(request: Request):
    """
    FastAPI dependency that extracts client IP and enforces the sliding window.
    Throws HTTP 429 with standard Retry-After header if limit exceeded.
    """
    # Handles both direct connections and reverse proxies (e.g. Docker, Nginx)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else "127.0.0.1"

    allowed, retry_after = rate_limiter.is_allowed(client_ip)

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: maximum {rate_limiter.max_requests} requests per minute.",
            headers={"Retry-After": str(retry_after)}
        )