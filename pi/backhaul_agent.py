#!/usr/bin/env python3
"""Report Pi-to-backend backhaul health using HTTP requests to FastAPI."""

from __future__ import annotations

import argparse
import json
import signal
import statistics
import threading
import time
from typing import Any
from urllib.request import Request, urlopen


def probe(target: str, probe_url: str, count: int, timeout_seconds: float) -> dict[str, Any]:
    """Measure successful HTTP GET round trips without using the telemetry endpoint."""

    latency_values: list[float] = []
    for _ in range(count):
        started_at = time.perf_counter()
        try:
            with urlopen(probe_url, timeout=timeout_seconds) as response:
                response.read()
            latency_values.append((time.perf_counter() - started_at) * 1_000)
        except Exception:
            # Count failed HTTP/TCP attempts as lost probes; keep the loop running.
            continue

    packet_loss = (count - len(latency_values)) / count * 100

    return {
        "reachable": bool(latency_values),
        "latency_ms": round(statistics.median(latency_values), 3) if latency_values else None,
        "packet_loss_percent": round(packet_loss, 1),
        "target": target,
    }


def post(endpoint: str, payload: dict[str, Any]) -> None:
    request = Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=5) as response:
        response.read()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", default="192.168.1.10")
    parser.add_argument("--probe-url", default="http://192.168.1.10:8000/api/state")
    parser.add_argument("--endpoint", default="http://192.168.1.10:8000/api/telemetry/backhaul")
    parser.add_argument("--interval", type=float, default=5.0)
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--timeout", type=float, default=1.0)
    args = parser.parse_args()
    if args.count < 1:
        parser.error("--count must be at least 1")
    if args.interval <= 0:
        parser.error("--interval must be greater than 0")

    stop_event = threading.Event()

    def request_stop(_signum: int, _frame: object) -> None:
        stop_event.set()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    while not stop_event.is_set():
        started_at = time.monotonic()
        try:
            payload = probe(args.target, args.probe_url, args.count, args.timeout)
            post(args.endpoint, payload)
            print(json.dumps(payload), flush=True)
        except Exception as error:  # Keep probing after transient network/backend failures.
            print(f"backhaul probe error: {error}", flush=True)
        stop_event.wait(max(0, args.interval - (time.monotonic() - started_at)))


if __name__ == "__main__":
    main()
