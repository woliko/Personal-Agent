#!/usr/bin/env python3
"""Verify the v6.db.transport.rest API for all four commute routes.

Run this once from your laptop (or Pi via SSH add-on) before deploying the HA
sensors. It confirms:
  1. EVA IDs resolve the expected station names via /locations.
  2. /journeys returns the legs[] structure the HA value_templates expect.
  3. Prints the first 3 connections per route so you can eyeball correctness.

Usage:
    pip install -r requirements.txt
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

BASE = "https://v6.db.transport.rest"

# EVA IDs are the source of truth — commute.yaml uses them directly in URLs.
# Station names below are for logs only; the API is never queried by name.
STATIONS: dict[str, str] = {
    "8005292": "Solln",
    "8000261": "München Hbf",
    "8003336": "Kaufering",
}

# Routes matching commute.yaml.
ROUTES: list[dict[str, str]] = [
    {"from": "8005292", "to": "8003336", "label": "Morning A: Solln → Kaufering"},
    {"from": "8000261", "to": "8003336", "label": "Morning B: Hbf → Kaufering"},
    {"from": "8003336", "to": "8000261", "label": "Return C: Kaufering → Hbf"},
    {"from": "8003336", "to": "8005292", "label": "Return D: Kaufering → Solln"},
]


def resolve_location(client: httpx.Client, eva_id: str) -> str | None:
    """Look up an EVA ID via /locations?query=<id>. Returns the first match's name."""
    resp = client.get(
        f"{BASE}/locations",
        params={"query": eva_id, "results": 1},
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data:
        return None
    # /locations returns a list of location objects directly.
    return data[0].get("name")


def fetch_journeys(
    client: httpx.Client,
    from_eva: str,
    to_eva: str,
    results: int = 3,
) -> dict:
    """Call /journeys and return raw JSON."""
    params = {"from": from_eva, "to": to_eva, "results": results}
    log.info("GET %s/journeys  params=%s", BASE, params)
    resp = client.get(f"{BASE}/journeys", params=params, timeout=20)
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
    for seg in segs:
        for m in seg.messages:
            print(f"       ⚠ {m}")


def verify_station_names(client: httpx.Client) -> bool:
    """Confirm each EVA ID resolves to the expected station name."""
    print(f"\n{'=' * 60}")
    print("  Station ID resolution (/locations)")
    print(f"{'=' * 60}")
    all_ok = True
    for eva, expected in STATIONS.items():
        try:
            actual = resolve_location(client, eva)
        except Exception as exc:
            log.error("Lookup failed for %s: %s", eva, exc)
            all_ok = False
            continue
        if actual and expected.lower() in actual.lower():
            print(f"  ✓ {eva}  →  {actual}")
        else:
            print(f"  ✗ {eva}  →  {actual!r} (expected to contain {expected!r})")
            all_ok = False
    return all_ok


def test_route(client: httpx.Client, route: dict[str, str]) -> bool:
    """Test one route. Returns True if /journeys returned usable data."""
    print(f"\n{'=' * 60}")
    print(f"  {route['label']}")
    print(f"{'=' * 60}")

    try:
        raw = fetch_journeys(client, route["from"], route["to"])
        connections = parse_journeys(raw)
        log.info("Lookup OK — %d journeys returned", len(connections))
        for i, c in enumerate(connections[:3]):
            print_connection(i + 1, c)
        return bool(connections)
    except httpx.HTTPStatusError as exc:
        log.error("Journeys lookup failed (HTTP %d): %s", exc.response.status_code, exc)
        return False
    except Exception as exc:
        log.error("Journeys lookup failed: %s", exc)
        return False


def print_json_paths(raw: dict) -> None:
    """Show the JSON paths the HA templates rely on, with live values."""
    journeys = raw.get("journeys", [])
    if not journeys:
        print("  (no journeys to inspect)")
        return

    j = journeys[0]
    legs = j.get("legs", [])
    leg = legs[0] if legs else {}
    line = leg.get("line") or {}

    print("\n  JSON paths used by commute.yaml value_templates:")
    print(f"    journeys[0].legs[0].departure         = {leg.get('departure', 'MISSING')}")
    print(f"    journeys[0].legs[0].plannedDeparture  = {leg.get('plannedDeparture', 'MISSING')}")
    print(f"    journeys[0].legs[0].departureDelay    = {leg.get('departureDelay', 'MISSING')}  (seconds)")
    print(f"    journeys[0].legs[0].cancelled         = {leg.get('cancelled', 'MISSING')}")
    print(f"    journeys[0].legs[0].line.name         = {line.get('name', 'MISSING')}")
    print(f"    journeys[0].legs[0].remarks           = {leg.get('remarks', 'MISSING')}")

    # If the API ever regresses to the old /segments name, flag it loudly.
    if "segments" in j and "legs" not in j:
        print("\n  ⚠  Response uses 'segments' instead of 'legs'!")
        print("     Update commute.yaml: legs → segments")


def main() -> None:
    print("v6.db.transport.rest — commute route verification")
    print(f"Base URL: {BASE}")

    all_ok = True
    with httpx.Client(headers={"User-Agent": "personal-agent/1.0"}) as client:
        if not verify_station_names(client):
            all_ok = False

        for route in ROUTES:
            if not test_route(client, route):
                all_ok = False

        # Inspect raw JSON structure on first route for path verification.
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
        print("  ✓ All routes and station IDs verified.")
        print("    commute.yaml is ready to deploy as-is.")
    else:
        print("  ⚠ Some routes failed (see above).")
        print("    Fix before deploying commute.yaml.")
    print(f"{'=' * 60}\n")

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
