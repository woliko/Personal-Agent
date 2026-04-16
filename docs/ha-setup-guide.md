# HA Setup Guide — Commute Agent

Step-by-step deployment of Agent 1 on the Raspberry Pi running HA OS.

> `100.x.y.z` below is a placeholder — substitute your own Pi's Tailscale IP.
> `secrets.yaml` must live on the Pi (`/config/secrets.yaml`) and is
> explicitly ignored in this repo's `.gitignore` — never sync it from the Pi
> to the repo.

## Prerequisites

- Home Assistant OS running, accessible via Tailscale at `100.x.y.z:8123`
- Telegram bot already configured in HA (integration + `telegram_bot:` in config)
- Anthropic API key
- **iPhone deploy:** Tailscale app installed + connected, Safari or Chrome

---

## iPhone-from-abroad deploy (VS Code add-on + SSH)

Everything below runs from your iPhone over Tailscale. No laptop needed.

### What you'll use

| Tool | How to access |
|---|---|
| HA web UI | Safari → `http://100.x.y.z:8123` |
| VS Code add-on | Safari → HA sidebar → Studio Code Server (or `http://100.x.y.z:8123/api/hassio/ingress/<addon-slug>`) |
| SSH | Termius app (or any iOS SSH client) → `root@100.x.y.z` port 22 |
| Telegram | Telegram app (for testing `/office`) |

### Step 1 — Connect Tailscale

Open the **Tailscale** app on your iPhone. Make sure the VPN toggle is on and
you can see `100.x.y.z` in your device list. Test by opening
`http://100.x.y.z:8123` in Safari — you should see the HA login screen.

### Step 2 — Test the DB API from the Pi

Open your SSH app (Termius, Blink, etc.) and connect:

```
Host: 100.x.y.z
User: root
Port: 22
Auth: password (your Terminal & SSH add-on password)
```

Once connected, verify the v6 DB REST API works from the Pi:

```bash
curl -s "https://v6.db.transport.rest/journeys?from=8005292&to=8003336&results=3" | head -c 500
```

You should see JSON with a `"journeys"` array where each journey has a
`"legs"` list. Confirm your EVA IDs match the stations you expect:

```bash
curl -s "https://v6.db.transport.rest/locations?query=8005292&results=1"
# → should return Solln
```

`commute.yaml` uses EVA IDs directly in the sensor URLs (no station names),
so you don't need to edit the package unless you're changing routes.

### Step 3 — Add your Anthropic API key to secrets

In the SSH session:

```bash
# Check if secrets.yaml exists
cat /config/secrets.yaml

# Add the key (append if file exists, create if not)
echo 'anthropic_api_key: sk-ant-api03-YOUR-KEY-HERE' >> /config/secrets.yaml
```

Or use **VS Code add-on** (see Step 4) to edit `/config/secrets.yaml` — easier
to manage if there are existing secrets.

### Step 4 — Enable the packages directory

Open **VS Code add-on** from the HA sidebar (Studio Code Server).

Open `/config/configuration.yaml` and add this block if it doesn't exist:

```yaml
homeassistant:
  packages: !include_dir_named packages
```

> **Tip:** VS Code on iPhone works best in landscape mode. Use the Safari
> address bar "Aa" menu → Request Desktop Website for a better editing
> experience.

Create the packages directory via SSH if it doesn't exist:

```bash
mkdir -p /config/packages
```

### Step 5 — Deploy commute.yaml

This is the main step. Two options:

**Option A — VS Code add-on (recommended for iPhone):**

1. In VS Code, right-click the `packages/` folder → New File → name it `commute.yaml`
2. Open a second Safari tab with the raw file from GitHub:
   `https://github.com/woliko/Personal-Agent/raw/claude/setup-commute-agent-6jJ5R/ha-config/packages/commute.yaml`
3. Select All → Copy the contents
4. Back in the VS Code tab → paste into `commute.yaml` → Save (Cmd+S or the
   menu)

**Option B — SSH (curl from GitHub):**

```bash
curl -sL "https://raw.githubusercontent.com/woliko/Personal-Agent/claude/setup-commute-agent-6jJ5R/ha-config/packages/commute.yaml" \
  -o /config/packages/commute.yaml
```

Verify:

```bash
head -20 /config/packages/commute.yaml
```

> `commute.yaml` already pins EVA IDs (Solln=8005292, München Hbf=8000261,
> Kaufering=8003336) directly in the sensor URLs. To swap in different
> stations, change the EVA IDs at the top of the `rest:` section.

### Step 6 — Validate and restart HA

In Safari, go to the HA web UI (`http://100.x.y.z:8123`):

1. **Developer Tools** (bottom menu) → **YAML** tab → **Check Configuration**
   - Must show: "Configuration valid!"
   - If errors appear: go back to VS Code and fix the YAML (error message
     tells you the line number)

2. On the same YAML tab → click **Restart** (under "Restart Home Assistant")
   - Or: **Settings → System → Restart**
   - Wait ~60s for HA to come back

### Step 7 — Verify entities loaded

After restart, in the HA web UI:

**Developer Tools → States** → filter for `commute` or `db_`

Confirm you see all of these (they may show `unknown` until first poll):

- `input_boolean.commute_day`
- `input_datetime.alarm_time`
- `sensor.db_solln_kaufering`
- `sensor.db_hbf_kaufering`
- `sensor.db_kaufering_return_hbf`
- `sensor.db_kaufering_return_solln`

### Step 8 — First manual refresh

**Developer Tools → Services** tab:

1. Search for `script.commute_refresh_all`
2. Tap **Call Service**
3. Wait 10 seconds
4. Go back to **States** → filter `db_` → sensors should now show departure
   times (e.g., `07:23`)

### Step 9 — Test Telegram check-in

Open **Telegram** on your iPhone and send `/office` to your HA bot.

Expected response (within ~15s):

```
🚆 Commute set for tomorrow

[Claude's route comparison + alarm suggestion]

Suggested alarm: 06:15

Solln  → Kaufering: 07:23 (ok)
Hbf    → Kaufering: 07:08 (ok)
```

If the Claude API part fails (no preview text), check:
- `secrets.yaml` has the correct `anthropic_api_key`
- SSH: `ha core logs | grep rest_command` for errors

The basic commute tracking (sensors + disruption alerts) works even without
Claude API — only the alarm suggestion and preview text need it.

### Step 10 — Verify disruption alerts

While `commute_day` is on, if any route is delayed >5 min or cancelled,
you'll get a Telegram message automatically. No action needed — just commute
on a day with DB delays (shouldn't take long).

To manually verify the automation exists:
**Settings → Automations** → search "Commute" → you should see all 5
automations.

### Step 11 — Daily reset check

At 19:00 each day, `commute_day` auto-resets to off. You can verify in
**Developer Tools → States** after 19:00, or check the automation trace:
**Settings → Automations → Commute - daily reset → Traces**.

---

## Quick reference (iPhone cheat sheet)

| Action | Where |
|---|---|
| Connect to Pi | Tailscale app → toggle on |
| Edit YAML | Safari → VS Code add-on (landscape + desktop mode) |
| SSH commands | Termius app → `root@100.x.y.z` |
| Check config | HA → Developer Tools → YAML → Check Configuration |
| Restart HA | HA → Developer Tools → YAML → Restart |
| Check states | HA → Developer Tools → States → filter `commute` |
| Call service | HA → Developer Tools → Services → `script.commute_refresh_all` |
| View logs | SSH: `ha core logs --follow` |
| Test check-in | Telegram → `/office` |

---

## Laptop deploy (alternative)

### 1. Verify the DB API

```bash
cd scripts
pip install -r requirements.txt
python test_db_api.py
```

The script resolves every pinned EVA ID against `/locations` and then exercises
`/journeys` for all four routes. Run the unit tests at the same time:

```bash
python -m pytest tests/
```

### 2. Add secrets

SSH into the Pi or use the File Editor add-on. Edit `/config/secrets.yaml`:

```yaml
anthropic_api_key: sk-ant-api03-YOUR-KEY-HERE
```

### 3. Enable packages

In `/config/configuration.yaml`, add (if not already present):

```yaml
homeassistant:
  packages: !include_dir_named packages
```

### 4. Deploy the commute package

Copy `ha-config/packages/commute.yaml` to `/config/packages/commute.yaml`.

Options:
- **Samba add-on**: browse to `\\100.x.y.z\config\packages\`
- **SCP via Tailscale**: `scp ha-config/packages/commute.yaml root@100.x.y.z:/config/packages/`
- **VS Code add-on**: paste file contents directly
- **File Editor add-on**: create file in the HA UI

### 5. Validate and restart

1. Go to **Developer Tools → Check Configuration** — must show green.
2. **Restart Home Assistant** (Settings → System → Restart).

### 6. Verify entities exist

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

### 7. End-to-end test

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

---

## Rollback

Delete `/config/packages/commute.yaml` and restart HA. No other state is
affected — helper entities will disappear after a restart.

Via SSH: `rm /config/packages/commute.yaml && ha core restart`

## Troubleshooting

| Symptom | Fix |
|---|---|
| Can't reach Pi from iPhone | Check Tailscale app is connected; try pinging `100.x.y.z` from Termius |
| VS Code add-on won't load | Try Safari desktop mode (Aa → Request Desktop Website); clear cache; or fall back to SSH |
| Sensors stuck on `unknown` | Check HA logs (`ha core logs \| grep rest`); verify `curl "https://v6.db.transport.rest/journeys?from=8005292&to=8003336"` works from Pi SSH |
| `binary_sensor.commute_api_stale` = on | v6.db.transport.rest is down or unreachable; check https://v6.db.transport.rest/ directly |
| `/office` doesn't trigger | Confirm `telegram_bot:` platform is in your HA config and the bot user matches |
| Claude API call fails | Check `secrets.yaml` key; SSH: `ha core logs \| grep rest_command` |
| Template sensors show `unknown` | REST sensors haven't updated yet — call `script.commute_refresh_all` first |
| YAML check fails after paste | iPhone paste can introduce invisible chars — try SSH `curl` method (Step 5 Option B) instead |
