#!/usr/bin/env python3
"""Discover real devices on Pi client-facing interfaces and send them to Aero Connect."""

from __future__ import annotations

import argparse
import json
import signal
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen


DEFAULT_ENDPOINT = "http://192.168.1.10:8000/api/clients"
DNSMASQ_LEASE_PATHS = (
    Path("/var/lib/misc/dnsmasq.leases"),
    Path("/var/lib/dnsmasq/dnsmasq.leases"),
)
ACTIVE_NEIGHBOUR_STATES = {"REACHABLE", "DELAY", "PROBE", "PERMANENT"}
IGNORED_NEIGHBOUR_STATES = {"FAILED", "INCOMPLETE", "NOARP", "NONE"}


def run_json_command(*args: str) -> list[dict[str, Any]]:
    """Run an ip command and return its JSON list, without changing networking."""

    try:
        result = subprocess.run(
            args,
            check=True,
            capture_output=True,
            text=True,
            timeout=3,
        )
        payload = json.loads(result.stdout)
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return []
    return payload if isinstance(payload, list) else []


def wireless_interfaces() -> list[str]:
    """Return interfaces reported by iw; never assume a wlan device name."""

    try:
        result = subprocess.run(
            ("iw", "dev"),
            check=True,
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return []

    interfaces: list[str] = []
    for line in result.stdout.splitlines():
        fields = line.strip().split()
        if len(fields) == 2 and fields[0] == "Interface":
            interfaces.append(fields[1])
    return interfaces


def dhcp_hostnames() -> dict[tuple[str, str], str]:
    """Read dnsmasq leases when available; no lease entry is fabricated."""

    hostnames: dict[tuple[str, str], str] = {}
    for lease_path in DNSMASQ_LEASE_PATHS:
        try:
            lines = lease_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            fields = line.split()
            if len(fields) < 4:
                continue
            mac, ip, hostname = fields[1].lower(), fields[2], fields[3]
            if hostname != "*":
                hostnames[(ip, mac)] = hostname
    return hostnames


def reverse_hostname(ip: str) -> str | None:
    """Use the configured resolver opportunistically, never derive an identity."""

    try:
        result = subprocess.run(
            ("getent", "hosts", ip),
            check=True,
            capture_output=True,
            text=True,
            timeout=1,
        )
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    fields = result.stdout.split()
    return fields[1] if len(fields) > 1 else None


def discover_clients(interfaces: list[str]) -> list[dict[str, str | None]]:
    """Build a client scan only from neighbour records on selected interfaces."""

    lease_names = dhcp_hostnames()
    seen: set[tuple[str, str, str]] = set()
    clients: list[dict[str, str | None]] = []
    scanned_at = datetime.now(timezone.utc).isoformat()

    for interface in interfaces:
        for neighbour in run_json_command("ip", "-json", "neigh", "show", "dev", interface):
            ip = neighbour.get("dst")
            mac = neighbour.get("lladdr")
            state = str(neighbour.get("state", "")).upper()
            if not isinstance(ip, str) or not isinstance(mac, str) or state in IGNORED_NEIGHBOUR_STATES:
                continue
            key = (interface, ip, mac.lower())
            if key in seen:
                continue
            seen.add(key)
            hostname = lease_names.get((ip, mac.lower())) or reverse_hostname(ip)
            clients.append(
                {
                    "ip": ip,
                    "mac": mac.lower(),
                    "hostname": hostname,
                    "status": "CONNECTED" if state in ACTIVE_NEIGHBOUR_STATES else "STALE",
                    "interface": interface,
                    "last_seen": scanned_at,
                }
            )
    return clients


def post(endpoint: str, clients: list[dict[str, str | None]]) -> None:
    request = Request(
        endpoint,
        data=json.dumps({"clients": clients}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=5) as response:
        response.read()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--interval", type=float, default=3.0)
    parser.add_argument(
        "--interface",
        action="append",
        dest="interfaces",
        help="Client-facing interface to scan; repeat to scan more than one.",
    )
    args = parser.parse_args()
    if args.interval <= 0:
        parser.error("--interval must be greater than 0")

    stop_event = threading.Event()

    def request_stop(_signum: int, _frame: object) -> None:
        stop_event.set()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    while not stop_event.is_set():
        started_at = time.monotonic()
        interfaces = args.interfaces or wireless_interfaces()
        if not interfaces:
            print("no client-facing Wi-Fi interface found; sending an empty scan", flush=True)
        try:
            clients = discover_clients(interfaces)
            post(args.endpoint, clients)
            print(f"client scan sent interfaces={interfaces} clients={len(clients)}", flush=True)
        except Exception as error:
            print(f"client discovery error: {error}", flush=True)
        stop_event.wait(max(0, args.interval - (time.monotonic() - started_at)))


if __name__ == "__main__":
    main()
