# Homelab Monitor

A self-hosted monitoring dashboard for your homelab. Track service health, system resources (CPU, RAM, disk, temperature), and Docker containers across multiple machines — all in one place.

## Quick Install

```bash
bash <(curl -sSL https://raw.githubusercontent.com/chasew28/homelab-monitor/main/install.sh)

# Create a project folder and set it up
mkdir my-monitor && cd my-monitor
hlm setup     # interactive config wizard

# Link remote nodes (Pi, NAS, etc.)
hlm link admin@192.168.1.10 --docker

# Start the dashboard
hlm run       # → http://localhost:5001
```

## Commands

| Command | What it does |
|---------|-------------|
| `hlm setup` | Interactive wizard to configure your nodes & services |
| `hlm run` | Start the monitoring dashboard on port 5001 |
| `hlm agent` | Start the remote agent (for secondary machines) |
| `hlm link [user@]host` | Link a remote node via SSH (install agent + add to config) |

## Features

- **Service health checks** — HTTP monitoring with latency tracking
- **Multi-node system stats** — CPU, RAM, disk, temperature, uptime per machine
- **Docker container status** — Running containers with image, status, ports
- **Live auto-refresh** — Dashboard updates every 15 seconds
- **Distributed architecture** — Central server + lightweight agents on remote nodes
- **Fully configurable** — Define your nodes and services in `config.yml`

## Linking Remote Nodes

```bash
# From the main server, link a remote Pi/NAS:
hlm link admin@192.168.1.10 --name NAS
hlm link 192.168.1.20 --docker    # default user: current $USER
hlm link root@10.0.0.5 -p 2222 --agent-port 5200
```

This SSHes into the remote machine, installs the agent, starts it as a systemd service, and adds the node to your local `config.yml` — all in one command.

## Architecture

```
┌─────────────────────┐
│  Dashboard (browser) │
│  http://localhost:5001 │
└────────┬────────────┘
         │
┌────────▼────────────┐
│  Main Server (Flask) │
│  - Serves dashboard  │
│  - Checks services   │
│  - Collects local    │
│    system stats      │
│  - Fetches from      │
│    remote agents     │
└────────┬────────────┘
         │
┌────────▼────────────┐
│  Remote Agent        │
│  (one per extra node) │
│  - Exposes system    │
│    stats via HTTP    │
│  - Port 5100         │
└─────────────────────┘
```

## Quick Start

### 1. Run the setup wizard (recommended)

```bash
hlm setup
```

This interactively configures your nodes, services, and writes `config.yml` for you.

### 2. Or configure manually

Edit `config.yml` to define your nodes and services:

```yaml
title: "My Homelab"

nodes:
  - name: "Main Server"
    host: "127.0.0.1"
    agent_port:           # null = collect stats locally
    docker: true          # show docker containers
    services:
      - name: "Cockpit"
        url: "http://localhost:9090"
      - name: "Grafana"
        url: "http://localhost:3000"

  - name: "NAS"
    host: "192.168.1.10"
    agent_port: 5100      # runs the agent script
    docker: false
    services:
      - name: "AdGuard Home"
        url: "http://192.168.1.10:3000"
```

### 3. Run Agents (Remote Nodes)

On each additional machine, install hlm the same way:

```bash
bash <(curl -sSL https://raw.githubusercontent.com/chasew28/homelab-monitor/main/install.sh)
hlm agent
# → listens on port 5100
```

Or run as a systemd service:

```bash
# systemd service file
sudo cat > /etc/systemd/system/homelab-agent.service << 'EOF'
[Unit]
Description=Homelab Monitor Agent
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/homelab-agent
ExecStart=/usr/bin/python3 /opt/homelab-agent/agent.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now homelab-agent
```

### 4. Docker (Optional)

```bash
docker build -t homelab-monitor .
docker run -d \
  --name homelab-monitor \
  -p 5001:5001 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v $(pwd)/config.yml:/app/config.yml \
  homelab-monitor
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Dashboard frontend |
| `GET /api/health` | Health check |
| `GET /api/config` | Dashboard config (title, nodes) |
| `GET /api/services` | Service health status |
| `GET /api/system` | System stats per node |
| `GET /api/docker` | Docker container status per node |

## Project Structure

```
homelab-monitor/
├── hlm_cli/            # CLI package (provides `hlm` command)
│   ├── __init__.py
│   └── __main__.py
├── app.py              # Main server (Flask)
├── agent.py            # Remote node agent
├── wizard.py           # Interactive setup wizard
├── config.yml          # Your configuration
├── requirements.txt    # Python dependencies
├── pyproject.toml      # Package config (hlm CLI entry point)
├── Dockerfile          # Container build
├── docker-compose.yml  # Docker Compose
├── dashboard/
│   └── index.html      # Frontend
└── README.md
```
