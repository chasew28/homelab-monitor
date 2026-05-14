# Project Context

## Repo
- GitHub: https://github.com/chasew28/homelab-monitor
- Installed via `pip install git+https://github.com/chasew28/homelab-monitor.git`
- Dashboard symlinked: `dashboard/` -> `hlm_cli/dashboard/` (always edit `hlm_cli/dashboard/index.html`)

## Infrastructure
- Pi 2 (nas): 192.168.1.165, SSH as `admin`, password Chase2008$
  - AdGuard Home on port 3000, admin/Chase2008$
  - Dashboard live at http://192.168.1.165:5001
- Pi 1 (ballista): 127.0.0.1 in config, has services on localhost:5000 and :8080
- Tailscale available if needed

## Features Built (Session 2)
- **Setup wizard** (`hlm_cli/wizard.py`): Uses "Machine" not "Node", clearer prompts
- **Hide unused sections**: Docker section hides if no containers/errors
- **Windows installer** (`install.ps1`): PowerShell equivalent of install.sh
- **Settings UI**: ⚙ button on dashboard → modal to edit title/machines/services with auth
- **Service integrations** (`hlm_cli/integrations.py`): Plugin system with AdGuard Home (Basic auth), hits `/control/stats` for queries/blocked stats
- **Auth per service**: Settings supports None / Basic / Token, saved to config.yml
- **Auto-update** (`hlm_cli/updater.py`): `hlm update` CLI, daily GitHub release check, dashboard banner
- **Cleanup**: Removed root `agent.py`, `app.py`, `wizard.py` wrappers; fixed Dockerfile

## Config format
```yaml
title: "My Homelab"
nodes:
  - name: "Machine name"
    host: "127.0.0.1"
    agent_port:   # null = local, number = remote agent port
    docker: true
    services:
      - name: "AdGuard Home"
        url: "http://localhost:3000"
        auth:
          type: basic          # or "token" or omitted
          username: admin
          password: secret
```

## Conventions
- Dark theme dashboard (#000 bg, monospace, glassmorphism)
- Vanilla JS, no frameworks
- Flask backend, Python stdlib remote agent
- `sort_keys=False` in yaml.dump for clean field ordering

## Priorities (Future)
- More service integrations (Pi-hole, Plex, qBittorrent, etc.)
- Auto-detect services on the network
