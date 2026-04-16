"""Parse v6.db.transport.rest /journeys responses into structured data.

Mirrors the jinja2 template logic in ha-config/packages/commute.yaml so we
have parity between the local test script and what HA actually sees.

API: https://v6.db.transport.rest (hafas-client v6 shape).

Notes on the v6 response shape:
  * Top level: { "journeys": [ { "legs": [...], "refreshToken": "..." } ] }
  * `legs[i].cancelled` is a per-leg boolean (not on the departure object).
  * `legs[i].departureDelay` / `arrivalDelay` are in **seconds**.
  * Disruption text lives in `legs[i].remarks[].text` (not `messages`).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

log = logging.getLogger(__name__)

# Default delay threshold (minutes) above which we classify a leg as "delayed".
# Mirrors input_number.commute_delay_threshold_min in commute.yaml.
DEFAULT_DELAY_THRESHOLD_MIN = 5


@dataclass
class Departure:
    time: str            # ISO-8601 datetime string (real-time)
    planned_time: str    # ISO-8601 datetime string (schedule)
    time_hhmm: str       # "HH:MM" for display
    delay_minutes: int   # derived from departureDelay (seconds)
    platform: str


@dataclass
class Arrival:
    time: str
    planned_time: str
    time_hhmm: str
    delay_minutes: int
    platform: str


@dataclass
class Segment:
    departure: Departure
    arrival: Arrival
    train_name: str
    messages: list[str]
    cancelled: bool  # per-leg cancellation flag from v6 API


@dataclass
class Connection:
    segments: list[Segment]
    cancelled: bool
    messages: list[str]
    status: str  # "ok" | "delayed" | "cancelled" | "unknown"


def _hhmm(iso: str) -> str:
    """Extract HH:MM from an ISO-8601 datetime string. Timezone-agnostic slicing."""
    try:
        return iso[11:16]
    except (IndexError, TypeError):
        return "??:??"


def _safe_int(val: Any, default: int = 0) -> int:
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _seconds_to_minutes(seconds: Any) -> int:
    """v6 API reports delay in seconds; HA & humans think in minutes."""
    return _safe_int(seconds) // 60


def _train_name(raw_leg: dict[str, Any]) -> str:
    """Best-effort train label. v6 puts it in leg.line.name."""
    line = raw_leg.get("line") or {}
    return line.get("name") or raw_leg.get("tripId") or "?"


def parse_segment(
    raw: dict[str, Any],
    delay_threshold_min: int = DEFAULT_DELAY_THRESHOLD_MIN,
) -> Segment:
    dep_time = raw.get("departure", "")
    planned_dep = raw.get("plannedDeparture", dep_time)
    arr_time = raw.get("arrival", "")
    planned_arr = raw.get("plannedArrival", arr_time)

    departure = Departure(
        time=dep_time,
        planned_time=planned_dep,
        time_hhmm=_hhmm(dep_time),
        delay_minutes=_seconds_to_minutes(raw.get("departureDelay")),
        platform=str(raw.get("departurePlatform") or raw.get("plannedDeparturePlatform") or ""),
    )
    arrival = Arrival(
        time=arr_time,
        planned_time=planned_arr,
        time_hhmm=_hhmm(arr_time),
        delay_minutes=_seconds_to_minutes(raw.get("arrivalDelay")),
        platform=str(raw.get("arrivalPlatform") or raw.get("plannedArrivalPlatform") or ""),
    )

    remarks = raw.get("remarks") or []
    messages = [r.get("text", "") for r in remarks if r.get("text")]

    return Segment(
        departure=departure,
        arrival=arrival,
        train_name=_train_name(raw),
        messages=messages,
        cancelled=bool(raw.get("cancelled", False)),
    )


def parse_connection(
    raw: dict[str, Any],
    delay_threshold_min: int = DEFAULT_DELAY_THRESHOLD_MIN,
) -> Connection:
    """Parse a single journey object from the /journeys response."""
    legs_raw = raw.get("legs", [])
    segments = [parse_segment(s, delay_threshold_min) for s in legs_raw]

    cancelled = any(s.cancelled for s in segments)

    # Connection-level messages are rare in v6, but surface them if present.
    top_remarks = raw.get("remarks") or []
    messages = [r.get("text", "") for r in top_remarks if r.get("text")]

    # Status is driven by the first leg — what matters for "am I going to
    # miss the train?".
    first_delay = segments[0].departure.delay_minutes if segments else 0

    if cancelled:
        status = "cancelled"
    elif first_delay > delay_threshold_min:
        status = "delayed"
    elif segments:
        status = "ok"
    else:
        status = "unknown"

    return Connection(
        segments=segments,
        cancelled=cancelled,
        messages=messages,
        status=status,
    )


def parse_journeys(
    response_json: dict[str, Any],
    delay_threshold_min: int = DEFAULT_DELAY_THRESHOLD_MIN,
) -> list[Connection]:
    """Parse the full /journeys API response into a list of Connections."""
    raw_journeys = response_json.get("journeys", [])
    if not raw_journeys:
        log.warning("No journeys found in response")
        return []
    return [parse_connection(j, delay_threshold_min) for j in raw_journeys]
