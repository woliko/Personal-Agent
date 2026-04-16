# Architecture

```
┌─────────────────────────────────────┐
│  Claude Artifact (browser/phone)    │
│  - Widget dashboard                 │
│  - Sidekick chat                    │
│  - Gmail + Calendar via MCP         │
│  - Persistent storage for configs   │
└──────────────┬──────────────────────┘
               │ HA REST API via Tailscale
┌──────────────▼──────────────────────┐
│  Home Assistant on Raspberry Pi     │
│  - Automations = agent scheduler    │
│  - REST sensors = DB, weather, APIs │
│  - REST commands = Claude API calls │
│  - Companion app = push notifs      │
│  - Device control = heat pump, etc  │
│  IP: 192.168.42.42 (VLAN 42)       │
│  Tailscale: 100.71.189.93          │
└─────────────────────────────────────┘
```

## Data flow

1. HA polls external APIs on schedule → stores in sensors.
2. HA calls Claude API for smart processing → stores results in helpers/files.
3. Claude artifact reads HA state via REST API on dashboard load.
4. Claude artifact renders widgets with live data.
5. For Gmail/Calendar: artifact uses MCP connectors directly.

## Key principles

- HA automations **are** the agent runtime — no separate scheduler.
- Companion app **is** the notification system — no Pushover/Ntfy.
- Tailscale **is** the network bridge — no port forwarding, no public endpoints.
- Claude API: Sonnet for execution tasks, Opus for judgment/synthesis.

## Network

| VLAN | Name | Contents |
|---|---|---|
| 10 | Trusted | Personal devices |
| 20 | IoT | Smart-home devices |
| 42 | Infra | Pi, camera |

- Router: UniFi Dream Machine SE (dual WAN)
- Camera: UniFi Bullet AI on VLAN 42
- Pi cannot be reached via 192.168.* through Tailscale (hairpin limitation);
  use Tailscale IP `100.71.189.93`.
