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

### Telegram commands

`/office` is time-aware. The mode is picked from the local hour unless an
explicit arg overrides:

| Command | Behaviour |
|---|---|
| `/office` (hour < 14) | `live_morning` — polled outbound sensors, Claude recommends next train |
| `/office` (14 ≤ hour < 19) | `live_return` — polled inbound sensors, Claude recommends |
| `/office` (hour ≥ 19) | `tomorrow` — explicit 06:00 lookup, Claude suggests alarm |
| `/office now` | force `live_morning` |
| `/office tomorrow` | force `tomorrow` |
| `/home` | always `live_return` |

Replies contain **only** Claude's recommendation — no raw sensor dump.

### State machine

- `commute_day` is flipped **on** only in tomorrow mode and only when Claude
  returns a viable `ALARM=HH:MM` line. No fallback alarm — if no route is
  viable, `commute_day` stays off and the user is told to toggle it manually.
- `commute_day=on` enables the background automations:
  - **Morning poll** (05:00–07:00, every 5 min): refresh outbound sensors.
  - **Return poll** (16:00–18:00, every 10 min): refresh inbound sensors.
  - **Disruption alert**: Telegram push on `delayed` / `cancelled`, deduped
    per (route, date, hour).
- **Daily reset** at 19:00: `commute_day` → off (opt-in each evening).

### Signal vs. noise

`remarks[]` from hafas-client v6 mixes `type=warning` (service disruptions)
with `type=hint` / `type=status` (WC, bike, alcohol-ban etc.). The template
sensors filter to `type=='warning'` only, so the `messages` attribute and
Claude prompts stay focused on actionable disruptions.

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
