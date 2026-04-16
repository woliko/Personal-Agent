"""Unit tests for utils.db_parser.

Fixtures are minimal hand-built v6.db.transport.rest /journeys shapes. Run with:
    cd scripts && python -m pytest tests/
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow `python -m pytest tests/` from scripts/ without installing a package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.db_parser import (  # noqa: E402
    DEFAULT_DELAY_THRESHOLD_MIN,
    parse_connection,
    parse_journeys,
    parse_segment,
)


def _leg(
    *,
    departure: str = "2025-01-15T07:23:00+01:00",
    planned_departure: str = "2025-01-15T07:23:00+01:00",
    departure_delay: int | None = 0,
    arrival: str = "2025-01-15T08:10:00+01:00",
    arrival_delay: int | None = 0,
    cancelled: bool = False,
    line_name: str = "RE 9",
    remarks: list[dict] | None = None,
    departure_platform: str | None = "12",
) -> dict:
    return {
        "departure": departure,
        "plannedDeparture": planned_departure,
        "departureDelay": departure_delay,
        "departurePlatform": departure_platform,
        "plannedDeparturePlatform": departure_platform,
        "arrival": arrival,
        "plannedArrival": arrival,
        "arrivalDelay": arrival_delay,
        "arrivalPlatform": "3",
        "cancelled": cancelled,
        "line": {"name": line_name, "product": "regional"},
        "remarks": remarks or [],
    }


def _journey(legs: list[dict]) -> dict:
    return {"legs": legs, "refreshToken": "tok"}


def test_parse_segment_on_time():
    seg = parse_segment(_leg())
    assert seg.departure.time_hhmm == "07:23"
    assert seg.departure.delay_minutes == 0
    assert seg.cancelled is False
    assert seg.train_name == "RE 9"
    assert seg.messages == []


def test_parse_segment_delay_seconds_to_minutes():
    # 600 seconds = 10 minutes
    seg = parse_segment(_leg(departure_delay=600))
    assert seg.departure.delay_minutes == 10


def test_parse_segment_missing_delay_defaults_to_zero():
    seg = parse_segment(_leg(departure_delay=None))
    assert seg.departure.delay_minutes == 0


def test_parse_segment_remarks_extract_text():
    seg = parse_segment(
        _leg(
            remarks=[
                {"type": "warning", "text": "Construction work"},
                {"type": "hint", "text": "Barrier free"},
                {"type": "status"},  # no text → dropped
            ]
        )
    )
    assert seg.messages == ["Construction work", "Barrier free"]


def test_parse_segment_cancelled_is_on_segment_not_departure():
    seg = parse_segment(_leg(cancelled=True))
    assert seg.cancelled is True


def test_parse_connection_status_ok():
    conn = parse_connection(_journey([_leg(departure_delay=60)]))  # 1 min delay
    assert conn.status == "ok"
    assert conn.cancelled is False


def test_parse_connection_status_delayed_above_threshold():
    # 360s = 6 min, threshold is 5
    conn = parse_connection(_journey([_leg(departure_delay=360)]))
    assert conn.status == "delayed"


def test_parse_connection_status_not_delayed_at_threshold():
    # 300s = 5 min, threshold is 5 (strictly greater)
    conn = parse_connection(_journey([_leg(departure_delay=300)]))
    assert conn.status == "ok"


def test_parse_connection_custom_threshold():
    conn = parse_connection(
        _journey([_leg(departure_delay=120)]),  # 2 min
        delay_threshold_min=1,
    )
    assert conn.status == "delayed"


def test_parse_connection_cancelled_overrides_delay():
    conn = parse_connection(_journey([_leg(cancelled=True, departure_delay=60)]))
    assert conn.status == "cancelled"
    assert conn.cancelled is True


def test_parse_connection_multi_leg_cancellation():
    # Cancellation on any leg marks the connection cancelled.
    conn = parse_connection(
        _journey([_leg(cancelled=False), _leg(cancelled=True, line_name="S 7")])
    )
    assert conn.cancelled is True
    assert conn.status == "cancelled"


def test_parse_connection_empty_legs_status_unknown():
    conn = parse_connection({"legs": []})
    assert conn.status == "unknown"
    assert conn.segments == []


def test_parse_journeys_empty_response():
    assert parse_journeys({}) == []
    assert parse_journeys({"journeys": []}) == []


def test_parse_journeys_full_response():
    response = {
        "journeys": [
            _journey([_leg(departure_delay=0)]),
            _journey([_leg(departure_delay=600)]),  # 10 min delay
        ]
    }
    results = parse_journeys(response)
    assert len(results) == 2
    assert results[0].status == "ok"
    assert results[1].status == "delayed"


def test_train_name_falls_back_to_tripid_when_line_missing():
    leg = _leg()
    leg.pop("line")
    leg["tripId"] = "1|12345|0|81|15012025"
    seg = parse_segment(leg)
    assert seg.train_name == "1|12345|0|81|15012025"


def test_train_name_falls_back_when_line_has_empty_name():
    leg = _leg()
    leg["line"] = {}
    leg["tripId"] = "fallback-trip"
    seg = parse_segment(leg)
    assert seg.train_name == "fallback-trip"


def test_default_threshold_exported():
    assert DEFAULT_DELAY_THRESHOLD_MIN == 5
