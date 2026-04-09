from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional


class EventPublisher:
    def publish(self, topic: str, payload: Dict[str, Any]) -> None:
        raise NotImplementedError


class NoopPublisher(EventPublisher):
    def publish(self, topic: str, payload: Dict[str, Any]) -> None:
        return


class KafkaPublisher(EventPublisher):
    def __init__(self, bootstrap_servers: str):
        try:
            from kafka import KafkaProducer
        except Exception as e:  # pragma: no cover
            raise RuntimeError(
                "Missing dependency 'kafka-python'. Install it with: python -m pip install kafka-python"
            ) from e

        self._producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )

    def publish(self, topic: str, payload: Dict[str, Any]) -> None:
        self._producer.send(topic, payload)


def default_publisher() -> EventPublisher:
    brokers = os.environ.get("SMART_PRICING_KAFKA_BROKERS", "").strip()
    if not brokers:
        return NoopPublisher()
    return KafkaPublisher(brokers)

