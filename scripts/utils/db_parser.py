"""Parse bahn.expert HAFAS v2 journey responses into structured data.

Mirrors the jinja2 template logic in ha-config/packages/commute.yaml so we
have parity between the local test script and what HA actually sees.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)


@dataclass
class Departure:
    time: str  # ISO-8601 datetime string
    time_hhmm: str  # "HH:MM" for display
    delay_minutes: int
    platform: str
    cancelled: bool


@dataclass
class Arrival:
    time: str
    time_hhmm: str
    delay_minutes: int
    platform: str


@dataclass
class Segment:
    departure: Departure
    arrival: Arrival
    train_name: str
    messages: list[str]


@dataclass
class Connection:
    segments: list[Segment]
    duration: int  # minutes
    cancelled: bool
    messages: list[str]
    status: str  # "ok" | "delayed" | "cancelled" | "unknown"


def _hhmm(iso: str) -> str:
    """Extract HH:MM from an ISO-8601 datetime string."""
    try:
        return iso[11:16]
    except (IndexError, TypeError):
        return "??:??"


def _safe_int(val: Any, default: int = 0) -> int:
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def parse_segment(raw: dict[str, Any]) -> Segment:
    dep_raw = raw.get("departure", {})
    arr_raw = raw.get("arrival", {})

    departure = Departure(
        time=dep_raw.get("time", ""),
        time_hhmm=_hhmm(dep_raw.get("time", "")),
        delay_minutes=_safe_int(dep_raw.get("delay")),
        platform=str(dep_raw.get("platform", "")),
        cancelled=bool(raw.get("cancelled", False)),
    )
    arrival = Arrival(
        time=arr_raw.get("time", ""),
        time_hhmm=_hhmm(arr_raw.get("time", "")),
        delay_minutes=_safe_int(arr_raw.get("delay")),
        platform=str(arr_raw.get("platform", "")),
    )

    messages = []
    for m in raw.get("messages", []):
        text = m.get("text") or m.get("head") or str(m)
        messages.append(text)

    return Segment(
        departure=departure,
        arrival=arrival,
        train_name=raw.get("train", {}).get("name", raw.get("trainName", "?")),
        messages=messages,
    )


def parse_connection(raw: dict[str, Any]) -> Connection:
    """Parse a single journey object from the /journeys response."""
    segments_raw = raw.get("segments", raw.get("legs", []))
    segments = [parse_segment(s) for s in segments_raw]

    cancelled = bool(raw.get("cancelled", False)) or any(
        s.departure.cancelled for s in segments
    )

    messages: list[str] = []
    for m in raw.get("messages", []):
        text = m.get("text") or m.get("head") or str(m)
        messages.append(text)

    # Overall delay = first segment departure delay (what matters for
    # "am I going to miss the train?")
    first_delay = segments[0].departure.delay_minutes if segments else 0

    if cancelled:
        status = "cancelled"
    elif first_delay > 5:
        status = "delayed"
    elif segments:
        status = "ok"
    else:
        status = "unknown"

    return Connection(
        segments=segments,
        duration=_safe_int(raw.get("duration")),
        cancelled=cancelled,
        messages=messages,
        status=status,
    )


def parse_journeys(response_json: dict[str, Any]) -> list[Connection]:
    """Parse the full /journeys API response into a list of Connections."""
    raw_journeys = response_json.get("journeys", [])
    if not raw_journeys:
        log.warning("No journeys found in response")
        return []
    return [parse_connection(j) for j in raw_journeys]
