# ha-config/

Home Assistant configuration files organised as **packages** — one file per
agent. This keeps each agent self-contained and easy to add/remove.

## How to deploy

1. Copy `packages/` to `/config/packages/` on the Pi (Samba, SCP, or the
   VS Code HA add-on).

2. In `/config/configuration.yaml`, ensure this block exists:

   ```yaml
   homeassistant:
     packages: !include_dir_named packages
   ```

3. Add required secrets to `/config/secrets.yaml`:

   ```yaml
   anthropic_api_key: sk-ant-...
   ```

4. Developer Tools → Check Configuration → Restart.

## Packages

| File | Agent | Description |
|---|---|---|
| `commute.yaml` | 1 — Daily Commute | Helpers, REST sensors, automations, scripts for Solln ↔ Kaufering commute |
