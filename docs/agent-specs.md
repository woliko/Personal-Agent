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

Direction-based. `/office` always outbound, `/home` always inbound — no
time-aware dispatch, the user chooses the command.

| Command | Behaviour |
|---|---|
| `/office` | Live overview of the next 3 Munich → Kaufering departures on both routes (Solln direct, via Hbf + cycle) |
| `/office tomorrow` | Same overview for tomorrow from 06:00 + derived alarm (earliest non-cancelled Solln − 45 min) |
| `/home` | Live overview of the next 3 Kaufering → Munich departures on both directions |

Replies are a plain-text overview, one departure per line, with delays and
cancellations marked. Claude is **not** called from any command path —
the user picks their own route.

### State machine

- `commute_day` is flipped **on** only by `/office tomorrow` and only when
  an earliest non-cancelled Solln departure exists. No fallback alarm —
  if no departure is viable, `commute_day` stays off and the message says so.
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
