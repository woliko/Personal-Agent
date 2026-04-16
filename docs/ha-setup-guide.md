# HA Setup Guide — Commute Agent

Step-by-step deployment of Agent 1 on the Raspberry Pi running HA OS.

## Prerequisites

- Home Assistant OS running, accessible via Tailscale at `100.71.189.93:8123`
- Telegram bot already configured in HA (integration + `telegram_bot:` in config)
- Anthropic API key

## 1. Verify the bahn.expert API

From your laptop (or Pi SSH add-on):

```bash
cd scripts
pip install -r requirements.txt
python test_db_api.py
```

If any station names fail, the script prints EVA IDs to paste into
`commute.yaml` before deploying.

## 2. Add secrets

SSH into the Pi or use the File Editor add-on. Edit `/config/secrets.yaml`:

```yaml
anthropic_api_key: sk-ant-api03-YOUR-KEY-HERE
```

## 3. Enable packages

In `/config/configuration.yaml`, add (if not already present):

```yaml
homeassistant:
  packages: !include_dir_named packages
```

## 4. Deploy the commute package

Copy `ha-config/packages/commute.yaml` to `/config/packages/commute.yaml`.

Options:
- **Samba add-on**: browse to `\\100.71.189.93\config\packages\`
- **SCP via Tailscale**: `scp ha-config/packages/commute.yaml root@100.71.189.93:/config/packages/`
- **VS Code add-on**: paste file contents directly
- **File Editor add-on**: create file in the HA UI

## 5. Validate and restart

1. Go to **Developer Tools → Check Configuration** — must show green.
2. **Restart Home Assistant** (Settings → System → Restart).

## 6. Verify entities exist

After restart, go to **Developer Tools → States** and confirm these entities:

- `input_boolean.commute_day`
- `input_datetime.alarm_time`
- `sensor.db_solln_kaufering`
- `sensor.db_hbf_kaufering`
- `sensor.db_kaufering_return_hbf`
- `sensor.db_kaufering_return_solln`
- `sensor.commute_solln_kaufering_status`
- `sensor.commute_hbf_kaufering_status`
- `sensor.commute_return_hbf_status`
- `sensor.commute_return_solln_status`

## 7. End-to-end test

1. **Manual sensor refresh:**
   Developer Tools → Services → `script.commute_refresh_all` → Call.
   Wait 10 s, then check sensor states — they should show departure times.

2. **Telegram check-in:**
   Open your Telegram bot and send `/office`.
   Expected: bot replies with both routes, suggested alarm time.

3. **Disruption alert (mock):**
   While `commute_day` is on, if any route is delayed >5 min, you'll get a
   Telegram alert automatically.

4. **Daily reset:**
   At 19:00, `commute_day` should flip to off automatically.

## Rollback

Delete `/config/packages/commute.yaml` and restart HA. No other state is
affected — helper entities will disappear after a restart.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Sensors stuck on `unknown` | Check HA logs for REST errors; verify `curl "https://bahn.expert/api/hafas/v2/journeys?from=Solln&to=Kaufering"` works from the Pi |
| `/office` doesn't trigger | Confirm `telegram_bot:` platform is in your HA config and the bot user matches |
| Claude API call fails | Check `secrets.yaml` key; look for `rest_command.claude_api` errors in HA logs |
| Template sensors show `unknown` | REST sensors haven't updated yet — call `script.commute_refresh_all` first |
