from __future__ import annotations

import os
from typing import Any, Dict, Optional


class FeatureStore:
    def get_listing_features(self, listing_id: str) -> Optional[Dict[str, float]]:
        raise NotImplementedError


class InMemoryFeatureStore(FeatureStore):
    def __init__(self):
        self._data: Dict[str, Dict[str, float]] = {}

    def get_listing_features(self, listing_id: str) -> Optional[Dict[str, float]]:
        return self._data.get(str(listing_id))


class RedisFeatureStore(FeatureStore):
    def __init__(self, host: str, port: int):
        try:
            import redis
        except Exception as e:  # pragma: no cover
            raise RuntimeError(
                "Missing dependency 'redis'. Install it with: python -m pip install redis"
            ) from e
        self._client = redis.Redis(host=host, port=port)

    def get_listing_features(self, listing_id: str) -> Optional[Dict[str, float]]:
        key = f"listing:{listing_id}"
        data = self._client.hgetall(key)
        if not data:
            return None
        out: Dict[str, float] = {}
        for k, v in data.items():
            try:
                out[k.decode("utf-8")] = float(v)
            except Exception:
                continue
        return out


def default_feature_store() -> FeatureStore:
    url = os.environ.get("SMART_PRICING_REDIS_HOST", "").strip()
    if not url:
        return InMemoryFeatureStore()
    port = int(os.environ.get("SMART_PRICING_REDIS_PORT", "6379"))
    return RedisFeatureStore(host=url, port=port)

