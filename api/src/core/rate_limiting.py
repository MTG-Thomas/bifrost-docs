"""
Rate Limiting Configuration

Provides Redis-backed rate limiting for the API using slowapi.
Different limits for different endpoint types (auth vs API).

Note: If slowapi is not installed, rate limiting is disabled (development mode).
"""

try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    RATE_LIMITING_ENABLED = True
except ImportError:
    RATE_LIMITING_ENABLED = False
    # Create dummy limiter class and decorator for when slowapi is not installed
    class Limiter:
        def __init__(self, *args, **kwargs):
            pass

        def limit(self, limits):
            """Dummy decorator that does nothing when slowapi not installed."""
            def decorator(f):
                return f
            return decorator

    def get_remote_address(request):
        return "127.0.0.1"

from src.config import get_settings

# Get Redis URL from settings
settings = get_settings()

# Create limiter with Redis storage (or dummy if slowapi not installed)
if RATE_LIMITING_ENABLED:
    limiter = Limiter(
        key_func=get_remote_address,
        storage_uri=settings.redis_url,
        storage_options={"socket_connect_timeout": 30},
        default_limits=["100/minute"],  # Default: 100 requests per minute
    )
else:
    limiter = Limiter()  # Dummy limiter

# Rate limit configurations by endpoint type
class RateLimits:
    """Rate limit configurations for different endpoint categories."""

    # Authentication endpoints - strict limits to prevent brute force
    AUTH_STRICT = ["5/minute", "20/hour"]  # 5 per minute, 20 per hour
    AUTH_LOGIN = ["10/minute", "50/hour"]  # Slightly higher for login

    # Passkey/WebAuthn endpoints
    PASSKEY = ["10/minute", "30/hour"]

    # MFA endpoints
    MFA = ["5/minute", "20/hour"]

    # API endpoints - moderate limits
    API_GENERAL = ["100/minute", "1000/hour"]
    API_WRITE = ["60/minute", "500/hour"]  # POST/PUT/DELETE

    # Search endpoints - can be expensive
    SEARCH = ["30/minute", "200/hour"]

    # Admin endpoints - very strict
    ADMIN = ["20/minute", "100/hour"]

    # Health check - very permissive
    HEALTH = ["1000/minute"]

    # WebSocket connections
    WEBSOCKET = ["10/minute"]  # Connection attempts
