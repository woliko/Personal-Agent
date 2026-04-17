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
time-aware dispatch, the user chooses the command. Each command also
subscribes the relevant direction to disruption alerts so pings only fire
for the leg you care about right now.

| Command | Behaviour |
|---|---|
| `/office` | Subscribe outbound alerts + unsubscribe return. Live overview of the next 3 Munich → Kaufering departures on both routes (Solln direct, via Hbf + cycle) |
| `/office_tmr` | Subscribe outbound alerts for tomorrow from 06:00 + derive alarm (earliest non-cancelled Solln − 45 min). Only subscribes when viable; otherwise stays off |
| `/home` | Subscribe return alerts + unsubscribe outbound. Live overview of the next 3 Kaufering → Munich departures on both directions |
| `/quiet` | Unsubscribe both directions. Use when WFH / weekend / already home |

Replies are a plain-text overview, one departure per line, with delays and
cancellations marked. Claude is **not** called from any command path —
the user picks their own route.

### State machine

Two independent booleans (`commute_outbound_alerts`,
`commute_return_alerts`) drive polling and disruption alerts:

- **`/office`** → outbound ON, return OFF.
- **`/office_tmr`** → outbound ON (only when a non-cancelled Solln
  departure exists; no fallback alarm), return OFF, alarm time set.
- **`/home`** → return ON, outbound OFF.
- **`/quiet`** → both OFF.
- **14:00 auto-switch**: if outbound is still ON at 14:00, flip to return
  (outbound OFF, return ON). Models "I'm in the office now, thinking about
  the way home".
- **19:00 daily reset**: both OFF (time-based proxy for "home by now";
  upgrade to a `device_tracker` + `zone.home` condition once the HA
  Companion app is wired up).

Background automations gated on the subscription booleans:

- **Morning poll** (05:00–07:00, every 5 min): refresh outbound sensors
  only while `commute_outbound_alerts=on`.
- **Return poll** (16:00–18:00, every 10 min): refresh inbound sensors
  only while `commute_return_alerts=on`.
- **Disruption alert**: Telegram push on `delayed` / `cancelled`, gated
  per direction (return-route sensors check the return boolean, outbound
  sensors check the outbound one). Deduped per (route, date, hour).

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
