#!/usr/bin/env python3
"""Verify the bahn.expert HAFAS v2 API for all four commute routes.

Run this once from your laptop (or Pi via SSH add-on) before deploying the HA
sensors.  It confirms:
  1. Station names resolve correctly (or shows the EVA fallback to paste into
     commute.yaml).
  2. The JSON response shape matches what the HA value_templates expect.
  3. Print the first 3 connections per route so you can eyeball correctness.

Usage:
    pip install httpx
    python test_db_api.py
"""

from __future__ import annotations

import logging
import sys

import httpx

from utils.db_parser import Connection, parse_journeys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
)
log = logging.getLogger(__name__)

BASE = "https://bahn.expert/api/hafas/v2"

# Routes matching commute.yaml — name first, EVA fallback if name fails.
ROUTES: list[dict[str, str]] = [
    {"from": "Solln", "to": "Kaufering", "label": "Morning A: Solln → Kaufering"},
    {"from": "München Hbf", "to": "Kaufering", "label": "Morning B: Hbf → Kaufering"},
    {"from": "Kaufering", "to": "München Hbf", "label": "Return C: Kaufering → Hbf"},
    {"from": "Kaufering", "to": "Solln", "label": "Return D: Kaufering → Solln"},
]

EVA_IDS: dict[str, str] = {
    "Solln": "8005292",
    "München Hbf": "8000261",
    "Kaufering": "8003336",
}


def fetch_journeys(
    client: httpx.Client,
    from_station: str,
    to_station: str,
    use_eva: bool = False,
) -> dict:
    """Call /journeys and return raw JSON."""
    if use_eva:
        from_station = EVA_IDS.get(from_station, from_station)
        to_station = EVA_IDS.get(to_station, to_station)

    url = f"{BASE}/journeys"
    params = {"from": from_station, "to": to_station}
    log.info("GET %s  params=%s", url, params)
    resp = client.get(url, params=params, timeout=20)
    resp.raise_for_status()
    return resp.json()


def print_connection(idx: int, conn: Connection) -> None:
    """Pretty-print a single connection."""
    segs = conn.segments
    if not segs:
        print(f"  [{idx}] (no segments)")
        return

    dep = segs[0].departure
    arr = segs[-1].arrival
    trains = " → ".join(s.train_name for s in segs)
    delay_str = f"+{dep.delay_minutes}min" if dep.delay_minutes else "on time"
    cancel_str = " *** CANCELLED ***" if conn.cancelled else ""

    print(
        f"  [{idx}] {dep.time_hhmm} → {arr.time_hhmm}  "
        f"({trains})  {delay_str}{cancel_str}"
    )
    if conn.messages:
        for m in conn.messages:
            print(f"       ⚠ {m}")


def test_route(client: httpx.Client, route: dict[str, str]) -> bool:
    """Test one route. Returns True if name-based lookup works."""
    print(f"\n{'=' * 60}")
    print(f"  {route['label']}")
    print(f"{'=' * 60}")

    # Try station names first
    try:
        raw = fetch_journeys(client, route["from"], route["to"], use_eva=False)
        connections = parse_journeys(raw)
        log.info("Name-based lookup OK — %d journeys returned", len(connections))
        for i, c in enumerate(connections[:3]):
            print_connection(i + 1, c)
        return True
    except httpx.HTTPStatusError as exc:
        log.warning(
            "Name-based lookup failed (HTTP %d). Retrying with EVA IDs...",
            exc.response.status_code,
        )
    except Exception as exc:
        log.warning("Name-based lookup failed: %s. Retrying with EVA IDs...", exc)

    # Fallback to EVA numbers
    try:
        raw = fetch_journeys(client, route["from"], route["to"], use_eva=True)
        connections = parse_journeys(raw)
        log.info("EVA-based lookup OK — %d journeys returned", len(connections))
        for i, c in enumerate(connections[:3]):
            print_connection(i + 1, c)

        print(
            f"\n  ⚠  Name lookup failed — paste these EVA IDs into commute.yaml:"
        )
        print(f"      {route['from']} = {EVA_IDS.get(route['from'], '?')}")
        print(f"      {route['to']}   = {EVA_IDS.get(route['to'], '?')}")
        return False
    except Exception as exc:
        log.error("EVA-based lookup also failed: %s", exc)
        return False


def print_json_paths(raw: dict) -> None:
    """Show the JSON paths the HA templates rely on, with live values."""
    journeys = raw.get("journeys", [])
    if not journeys:
        print("  (no journeys to inspect)")
        return

    j = journeys[0]
    segs = j.get("segments", j.get("legs", []))
    seg = segs[0] if segs else {}

    print("\n  JSON paths used by commute.yaml value_templates:")
    print(f"    journeys[0].segments[0].departure.time     = {seg.get('departure', {}).get('time', 'MISSING')}")
    print(f"    journeys[0].segments[0].departure.delay    = {seg.get('departure', {}).get('delay', 'MISSING')}")
    print(f"    journeys[0].segments[0].departure.platform = {seg.get('departure', {}).get('platform', 'MISSING')}")
    print(f"    journeys[0].cancelled                      = {j.get('cancelled', 'MISSING')}")
    print(f"    journeys[0].messages                       = {j.get('messages', 'MISSING')}")
    print(f"    journeys[0].duration                       = {j.get('duration', 'MISSING')}")

    # Check for alternative key names
    if "legs" in j and "segments" not in j:
        print("\n  ⚠  Response uses 'legs' instead of 'segments'!")
        print("     Update commute.yaml: segments → legs")


def main() -> None:
    print("bahn.expert HAFAS v2 API — commute route verification")
    print(f"Base URL: {BASE}")

    all_ok = True
    with httpx.Client() as client:
        for route in ROUTES:
            name_ok = test_route(client, route)
            if not name_ok:
                all_ok = False

        # Inspect raw JSON structure on first route for path verification
        print(f"\n{'=' * 60}")
        print("  JSON structure inspection (first route)")
        print(f"{'=' * 60}")
        try:
            raw = fetch_journeys(client, ROUTES[0]["from"], ROUTES[0]["to"])
            print_json_paths(raw)
        except Exception as exc:
            log.error("Could not inspect JSON: %s", exc)

    print(f"\n{'=' * 60}")
    if all_ok:
        print("  ✓ All routes resolved by station name.")
        print("    commute.yaml is ready to deploy as-is.")
    else:
        print("  ⚠ Some routes needed EVA IDs (see above).")
        print("    Update the station names in commute.yaml before deploying.")
    print(f"{'=' * 60}\n")

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
