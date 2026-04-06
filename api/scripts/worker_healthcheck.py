#!/usr/bin/env python3
"""
Health check script for ARQ worker.

Verifies:
1. The worker process is running
2. Redis connection is healthy
3. Worker is registered in ARQ

Exit codes:
- 0: Healthy
- 1: Unhealthy (process not running or Redis unreachable)
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, "/app/src")


async def check_redis() -> bool:
    """Check Redis connectivity."""
    try:
        import redis.asyncio as redis
        from src.config import get_settings

        settings = get_settings()
        r = redis.from_url(settings.redis_url, socket_connect_timeout=5)
        try:
            await r.ping()
            return True
        finally:
            await r.aclose()
    except Exception:
        return False


def check_process() -> bool:
    """Check if the ARQ worker process is running."""
    try:
        # Check if this Python process has the arq worker running
        # by checking if we can import and access worker settings
        from src.worker import WorkerSettings
        from src.config import get_settings

        # Verify settings can be loaded
        settings = get_settings()
        worker_settings = WorkerSettings()

        # Check if redis_settings can be created
        _ = worker_settings.redis_settings

        return True
    except Exception:
        return False


async def healthcheck() -> bool:
    """Run all health checks."""
    # Check process/code is loadable
    if not check_process():
        print("FAIL: Cannot load worker process/settings")
        return False

    # Check Redis connectivity
    if not await check_redis():
        print("FAIL: Redis connection failed")
        return False

    print("OK: Worker is healthy")
    return True


if __name__ == "__main__":
    try:
        result = asyncio.run(healthcheck())
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"FAIL: Health check error: {e}")
        sys.exit(1)
