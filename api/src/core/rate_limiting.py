"""
Rate Limiting Configuration

Provides Redis-backed rate limiting for the API using slowapi.
Different limits for different endpoint types (auth vs API).

Note: If slowapi is not installed, rate limiting is disabled (development mode).
"""

from collections.abc import Callable
from typing import Any

# Try to import slowapi - if not available, use dummy implementations
try:
    from slowapi import Limiter as _Limiter  # noqa: F811
    from slowapi.util import get_remote_address as _get_remote_address  # noqa: F811

    RATE_LIMITING_ENABLED = True

    # Use the real implementations
    class Limiter(_Limiter):  # type: ignore[misc, no-redef]
        """Real Limiter from slowapi."""

        pass

    def get_remote_address(request: Any) -> str:  # type: ignore[misc, no-redef]
        """Get remote address from request using slowapi."""
        return _get_remote_address(request)  # type: ignore[no-any-return]

except ImportError:
    RATE_LIMITING_ENABLED = False

    # Create dummy limiter class and decorator for when slowapi is not installed
    class Limiter:  # type: ignore[no-redef]
        """Dummy Limiter class when slowapi is not installed."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def limit(self, limits: Any) -> Callable[[Any], Any]:
            """Dummy decorator that does nothing when slowapi not installed."""

            def decorator(f: Any) -> Any:
                return f

            return decorator

        # Dummy middleware_class attribute for type checking
        middleware_class: Any = None

    def get_remote_address(request: Any) -> str:  # type: ignore[misc, no-redef]
        """Dummy get_remote_address when slowapi is not installed."""
        return "127.0.0.1"


from src.config import get_settings

# Get Redis URL from settings
settings = get_settings()

# Create limiter with Redis storage (or dummy if slowapi not installed)
if RATE_LIMITING_ENABLED:
    limiter = Limiter(
        key_func=get_remote_address,
        storage_uri=settings.redis_url,
        storage_options={"socket_connect_timeout": "30"},
        default_limits=["100/minute"],  # Default: 100 requests per minute
    )
else:
    limiter = Limiter(key_func=get_remote_address)  # Dummy limiter


# Rate limit configurations by endpoint type
class RateLimits:
    """Rate limit configurations for different endpoint categories."""

    # Authentication endpoints - strict limits to prevent brute force
    AUTH_STRICT = "5/minute,20/hour"  # 5 per minute, 20 per hour
    AUTH_LOGIN = "10/minute,50/hour"  # Slightly higher for login

    # Passkey/WebAuthn endpoints
    PASSKEY = "10/minute,30/hour"

    # MFA endpoints
    MFA = "5/minute,20/hour"

    # API endpoints - moderate limits
    API_GENERAL = "100/minute,1000/hour"
    API_WRITE = "60/minute,500/hour"  # POST/PUT/DELETE

    # Search endpoints - can be expensive
    SEARCH = "30/minute,200/hour"

    # Admin endpoints - very strict
    ADMIN = "20/minute,100/hour"

    # Health check - very permissive
    HEALTH = "1000/minute"

    # WebSocket connections
    WEBSOCKET = "10/minute"  # Connection attempts
