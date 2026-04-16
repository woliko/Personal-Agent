# CLAUDE.md

Conventions for Claude Code when editing this repo. Keep this file short;
prefer linking to the canonical source over duplicating it here.

## What this repo is

Home Assistant + Claude API personal-agent stack, running on a Raspberry Pi.
Each agent is a self-contained HA package under `ha-config/packages/`.
`scripts/` is local dev only (never executed by HA).

## Layout at a glance

- `ha-config/packages/*.yaml` — one file per agent. Must be standalone so
  it can be dropped into `/config/packages/` without side effects.
- `scripts/` — Python dev tools. `scripts/utils/` is importable; `scripts/tests/`
  is pytest. Production code never imports from here.
- `docs/` — architecture, agent specs, deploy runbooks.

## HA package conventions

- **Always namespace** entities with the agent name (`commute_*`, `brief_*`).
- **EVA IDs, not station names** in REST sensor URLs — names can change
  upstream; numeric IDs are stable.
- **DRY via YAML anchors** (`&name` / `<<: *name`) when 2+ sensors share the
  same template. HA's safe_load supports them.
- **Numeric attributes** in template sensors must be `| int(0)` cast,
  otherwise they serialise as strings and break downstream comparisons.
- **Cancellation is per-leg** in v6.db.transport.rest (`legs[i].cancelled`),
  not on the journey root. Parse accordingly.
- **Delays are in seconds** in v6 (`departureDelay`, `arrivalDelay`).
  Divide by 60 before displaying or comparing to minute thresholds.
- **Time slicing is not timezone-safe** — use
  `iso | as_datetime | as_local | strftime('%H:%M')` for display.
- **Model IDs** live in `input_text` helpers (`commute_model_sonnet`,
  `commute_model_opus`) so they can be rotated without a restart. Do not
  hard-code model strings in `rest_command` payloads.
- **Secrets** come from `/config/secrets.yaml` via `!secret <key>`. Never
  check in `secrets.yaml` or put API keys in a package file. `.gitignore`
  already excludes `.env` and `secrets.yaml`.

## Testing

- Unit tests: `cd scripts && python -m pytest tests/`
- Live API probe: `cd scripts && python test_db_api.py`
- YAML well-formedness: HA's Developer Tools → Check Configuration after
  copying a package to `/config/packages/`.

## Where state lives

- API results: `sensor.db_*` (REST), `sensor.commute_*_status` (template)
- User-toggled: `input_boolean.commute_day`, `input_datetime.alarm_time`
- Last outputs: `input_text.commute_morning_summary`,
  `input_text.commute_last_alert_fingerprint`
- Config knobs: `input_number.commute_delay_threshold_min`,
  `input_text.commute_model_{sonnet,opus}`

## Adding a new agent

1. Create `ha-config/packages/<agent>.yaml`. Copy the header comment style
   from `commute.yaml` (API docs, response shape, modes).
2. Namespace every entity with `<agent>_`.
3. Reuse `rest_command.claude_api` from `commute.yaml` (do not redefine it);
   when a second agent needs it, factor it out into `ha-config/packages/claude.yaml`
   and delete the copy from `commute.yaml`.
4. Add a row to the status table in `README.md` and to `docs/agent-specs.md`.
5. If the agent talks to a new external API, add a smoke-test script under
   `scripts/` with matching unit tests under `scripts/tests/`.

## Branch + commit conventions

- Work on `claude/<task>-<id>` branches (already enforced by the harness).
- Commit messages: lowercase type prefix (`feat:`, `fix:`, `docs:`,
  `refactor:`). See `git log` for examples.
- Never amend a commit that has been pushed; create a new one.
