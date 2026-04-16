# Agent Specifications

## Agent 1: Daily Commute

**Status:** In progress

Context-aware train connections for a daily Solln ↔ Kaufering commute.

### Routes

| ID | Direction | From | To | Notes |
|---|---|---|---|---|
| A | Morning | Solln | Kaufering | Direct |
| B | Morning | München Hbf | Kaufering | User cycles to Hbf (+15 min buffer) |
| C | Return | Kaufering | München Hbf | User cycles home |
| D | Return | Kaufering | Solln | Direct |

### Modes

1. **Evening check-in:** User sends `/office` to Telegram bot → fetch
   next-day connections for both routes → Claude suggests alarm → sets
   `input_boolean.commute_day = on`.
2. **Morning live (05:00–07:00):** Every 5 min when `commute_day=on` → poll
   DB API → disruption alerts via Telegram.
3. **Return (16:00–18:00):** Every 10 min when `commute_day=on` → Kaufering
   departures both directions.
4. **No commute day:** Agent sleeps — no API polling.
5. **Daily reset (19:00):** `commute_day` turns off automatically.

### HA entities

See `ha-config/packages/commute.yaml` for the full list.

### API

[v6.db.transport.rest](https://v6.db.transport.rest) — free, no key,
hafas-client v6 wrapper around Deutsche Bahn.
- Journeys:  `https://v6.db.transport.rest/journeys?from=<evaId>&to=<evaId>&results=3`
- Locations: `https://v6.db.transport.rest/locations?query=<name-or-eva>`
- EVA IDs are pinned directly in `commute.yaml` (station names are never sent
  to the API, so an upstream rename can't break the sensors).
- `departureDelay` / `arrivalDelay` are in **seconds** — the template sensors
  divide by 60 to convert to minutes.

---

## Agent 2: Morning Brief

**Status:** Planned

## Agent 3: Home Control

**Status:** Planned

## Agent 4: Email Triage

**Status:** Planned

## Agent 5: Industry Radar

**Status:** Planned
