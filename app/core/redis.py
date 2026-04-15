from __future__ import annotations

import json
import logging
import inspect
import time
from typing import Any

from redis.asyncio import Redis

from app.core.config import settings

logger = logging.getLogger(__name__)


class InMemoryRedis:
    def __init__(self) -> None:
        self._data: dict[str, tuple[str, float | None]] = {}

    def _cleanup(self, key: str) -> None:
        value = self._data.get(key)
        if value is None:
            return
        _, expires_at = value
        if expires_at and expires_at <= time.time():
            self._data.pop(key, None)

    async def ping(self) -> bool:
        return True

    async def get(self, key: str) -> str | None:
        self._cleanup(key)
        value = self._data.get(key)
        return None if value is None else value[0]

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        expires_at = time.time() + ex if ex else None
        self._data[key] = (value, expires_at)
        return True

    async def setex(self, key: str, ttl: int, value: str) -> bool:
        return await self.set(key, value, ex=ttl)

    async def incr(self, key: str) -> int:
        self._cleanup(key)
        current = int((await self.get(key)) or "0") + 1
        expires_at = self._data.get(key, ("", None))[1]
        self._data[key] = (str(current), expires_at)
        return current

    async def expire(self, key: str, ttl: int) -> bool:
        if key not in self._data:
            return False
        self._data[key] = (self._data[key][0], time.time() + ttl)
        return True

    async def delete(self, *keys: str) -> int:
        deleted = 0
        for key in keys:
            if key in self._data:
                self._data.pop(key, None)
                deleted += 1
        return deleted

    async def close(self) -> None:
        return None


redis_client: Redis | InMemoryRedis | None = None


async def connect_redis() -> Redis | InMemoryRedis:
    global redis_client
    if redis_client is not None:
        return redis_client

    try:
        client = Redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
        await client.ping()
        redis_client = client
        logger.info("Connected to Redis at %s", settings.redis_url)
    except Exception as exc:
        logger.warning("Redis unavailable, using in-memory fallback: %s", exc)
        redis_client = InMemoryRedis()
    return redis_client


async def get_redis() -> Redis | InMemoryRedis:
    return await connect_redis()


async def close_redis() -> None:
    global redis_client
    if redis_client is None:
        return
    close_method = getattr(redis_client, "aclose", None) or getattr(redis_client, "close", None)
    if close_method is not None:
        result = close_method()
        if inspect.isawaitable(result):
            await result
    redis_client = None


async def redis_get_json(key: str) -> dict[str, Any] | None:
    client = await get_redis()
    raw = await client.get(key)
    if raw is None:
        return None
    return json.loads(raw)


async def redis_set_json(key: str, value: dict[str, Any], ttl_seconds: int) -> None:
    client = await get_redis()
    await client.setex(key, ttl_seconds, json.dumps(value, default=str))
