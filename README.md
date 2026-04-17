# Personal Agent

Personal AI assistant running on Home Assistant OS (Raspberry Pi) + Claude artifacts.
Home Assistant is the agent runtime (scheduler, state store, notification bus);
Claude artifacts render the dashboard and chat surface.

## Status

| Agent | Status |
|---|---|
| 1. Daily Commute | In progress (this branch) |
| 2. Morning Brief | Planned |
| 3. Home Control | Planned |
| 4. Email Triage | Planned |
| 5. Industry Radar | Planned |

## Layout

```
ha-config/packages/     # Per-agent HA packages (drop-in to /config/packages/)
scripts/                # Local dev & API probes (run from laptop or Pi SSH add-on)
scripts/tests/          # Unit tests (pytest)
docs/                   # Architecture, agent specs, deploy runbooks
CLAUDE.md               # Conventions for Claude Code when editing this repo
```

Start here: [`docs/architecture.md`](docs/architecture.md) then
[`docs/agent-specs.md`](docs/agent-specs.md) then
[`docs/ha-setup-guide.md`](docs/ha-setup-guide.md) to deploy.

## Running the commute agent

1. `cp .env.example .env` and fill in keys.
2. `cd scripts && pip install -r requirements.txt`
3. `python test_db_api.py` — exercises v6.db.transport.rest for all four
   routes and resolves the pinned EVA IDs.
4. `python -m pytest tests/` — unit-tests the parser against fixture data.
5. Follow [`docs/ha-setup-guide.md`](docs/ha-setup-guide.md) to drop
   `ha-config/packages/commute.yaml` onto the Pi.
6. Telegram commands:
   - `/office` — time-aware (morning recommendation, afternoon return, or
     tomorrow's alarm depending on the hour)
   - `/office now` / `/office tomorrow` — force the mode
   - `/home` — next return connection from Kaufering, any time
