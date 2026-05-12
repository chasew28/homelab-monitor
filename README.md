# Homelab Monitor

A self-hosted monitoring dashboard for your homelab. Track service health, system resources (CPU, RAM, disk, temperature), and Docker containers across multiple machines — all in one place.

## One-Liner Install

```bash
curl -sSL https://raw.githubusercontent.com/chasew28/homelab-monitor/main/setup.py | python3
```

This will install dependencies and launch an interactive terminal wizard to configure your nodes and services. After setup, run `python app.py` to start the monitor.

## Features

- **Service health checks** — HTTP monitoring with latency tracking
- **Multi-node system stats** — CPU, RAM, disk, temperature, uptime per machine
- **Docker container status** — Running containers with image, status, ports
- **Live auto-refresh** — Dashboard updates every 15 seconds
- **Distributed architecture** — Central server + lightweight agents on remote nodes
- **Fully configurable** — Define your nodes and services in `config.yml`

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
python setup.py
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

### 2. Install & Run (Main Server)

```bash
pip install -r requirements.txt
python app.py
# → http://localhost:5001
```

### 3. Run Agents (Remote Nodes)

On each additional machine:

```bash
# Install psutil if needed
pip install psutil

# Run the agent
python agent.py
# → listens on port 5100
```

Or run as a service:

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
├── app.py              # Main server (Flask)
├── agent.py            # Remote node agent
├── setup.py            # Interactive setup wizard
├── config.yml          # Your configuration
├── requirements.txt    # Python dependencies
├── Dockerfile          # Container build
├── docker-compose.yml  # Docker Compose
├── dashboard/
│   └── index.html      # Frontend
└── README.md
```
