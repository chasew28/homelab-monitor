#!/usr/bin/env python3
import json
import os
import subprocess
import time
import urllib.request
from datetime import datetime
from pathlib import Path

import yaml
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder=None)
CORS(app)

HERE = Path(__file__).parent.resolve()

def find_config():
    config_dir = Path(os.environ.get("HLM_CONFIG_DIR", os.getcwd()))
    candidates = [
        config_dir / "config.yml",
        HERE / "config.yml",
        Path.home() / ".config" / "homelab-monitor" / "config.yml",
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]

CONFIG_PATH = find_config()
DASHBOARD_DIR = HERE / "dashboard"


def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def check_service(url, timeout=5):
    status = "down"
    latency = None
    start = time.time()
    try:
        code = urllib.request.urlopen(url, timeout=timeout).getcode()
        latency = round((time.time() - start) * 1000)
        status = "up" if code < 400 else "degraded"
    except Exception:
        status = "down"
    return status, latency


def get_local_system_info():
    import psutil
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    uptime_sec = time.time() - psutil.boot_time()
    temp = None
    try:
        result = subprocess.run(
            ["cat", "/sys/class/thermal/thermal_zone0/temp"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            temp = round(int(result.stdout.strip()) / 1000, 1)
    except Exception:
        pass
    return {
        "cpu_percent": cpu,
        "cpu_temp": temp,
        "ram_percent": ram.percent,
        "ram_used": ram.used,
        "ram_total": ram.total,
        "disk_percent": disk.percent,
        "disk_used": disk.used,
        "disk_total": disk.total,
        "uptime_seconds": int(uptime_sec),
        "hostname": os.uname().nodename,
    }


def get_local_docker_info():
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{json .}}"],
            capture_output=True, text=True, timeout=10
        )
        containers = []
        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            c = json.loads(line)
            containers.append({
                "name": c.get("Names"),
                "image": c.get("Image"),
                "status": c.get("Status"),
                "state": c.get("State"),
                "ports": c.get("Ports"),
            })
        return containers
    except Exception as e:
        return {"error": str(e)}


def fetch_agent_system_info(host, port):
    try:
        url = f"http://{host}:{port}/api/system"
        resp = urllib.request.urlopen(url, timeout=5)
        return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}


@app.route("/api/services")
def services():
    cfg = load_config()
    results = []
    for node in cfg.get("nodes", []):
        for svc in node.get("services", []):
            status, latency = check_service(svc["url"])
            results.append({
                "name": svc["name"],
                "url": svc["url"],
                "status": status,
                "latency_ms": latency,
                "host": node["name"],
            })
    return jsonify(results)


@app.route("/api/system")
def system_info():
    cfg = load_config()
    nodes = {}
    for node in cfg.get("nodes", []):
        name = node["name"]
        host = node["host"]
        agent_port = node.get("agent_port")
        if host == "127.0.0.1" or not agent_port:
            try:
                nodes[name] = get_local_system_info()
            except Exception as e:
                nodes[name] = {"error": str(e)}
        else:
            nodes[name] = fetch_agent_system_info(host, agent_port)
    return jsonify(nodes)


@app.route("/api/docker")
def docker_status():
    cfg = load_config()
    results = {}
    for node in cfg.get("nodes", []):
        if node.get("docker") and (node["host"] == "127.0.0.1" or not node.get("agent_port")):
            results[node["name"]] = get_local_docker_info()
    return jsonify(results)


@app.route("/api/config")
def config_info():
    cfg = load_config()
    return jsonify({
        "title": cfg.get("title", "Homelab Monitor"),
        "nodes": [
            {"name": n["name"], "host": n["host"]}
            for n in cfg.get("nodes", [])
        ],
    })


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "timestamp": datetime.utcnow().isoformat()})


@app.route("/")
@app.route("/<path:path>")
def dashboard(path="index.html"):
    file_path = DASHBOARD_DIR / path
    if file_path.is_file():
        return send_from_directory(str(DASHBOARD_DIR), path)
    return send_from_directory(str(DASHBOARD_DIR), "index.html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    print(f"Homelab Monitor starting on http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port)
