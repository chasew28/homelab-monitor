#!/usr/bin/env python3
import json
import os
import subprocess
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import yaml
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from hlm_cli.integrations import INTEGRATIONS
from hlm_cli.updater import check_for_update

app = Flask(__name__, static_folder=None)
CORS(app)

HERE = Path(__file__).parent.resolve()

def find_config():
    config_dir = Path(os.environ.get("HLM_CONFIG_DIR", os.getcwd()))
    candidates = [
        config_dir / "config.yml",
        HERE.parent / "config.yml",
        Path.home() / ".config" / "homelab-monitor" / "config.yml",
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]

CONFIG_PATH = find_config()
DASHBOARD_DIR = HERE / "dashboard"

_NODE_KEYS = ["name", "host", "agent_port", "docker", "services"]
_SVC_KEYS = ["name", "url", "auth"]


def _order_cfg(data):
    result = {}
    for k in ("title", "nodes"):
        if k in data:
            result[k] = data[k]
    ordered_nodes = []
    for node in result.get("nodes", []):
        onode = {}
        for k in _NODE_KEYS:
            if k in node:
                onode[k] = node[k]
        onode["services"] = [{k: s[k] for k in _SVC_KEYS if k in s} for s in node.get("services", [])]
        ordered_nodes.append(onode)
    result["nodes"] = ordered_nodes
    return result


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


def enrich_service(url, auth=None):
    for integration in INTEGRATIONS:
        try:
            result = integration.fetch(url, auth)
            if result:
                return result
        except Exception:
            continue
    return None


@app.route("/api/services")
def services():
    cfg = load_config()
    results = []
    for node in cfg.get("nodes", []):
        for svc in node.get("services", []):
            status, latency = check_service(svc["url"])
            entry = {
                "name": svc["name"],
                "url": svc["url"],
                "status": status,
                "latency_ms": latency,
                "host": node["name"],
            }
            enrichment = enrich_service(svc["url"], svc.get("auth"))
            if enrichment:
                entry["type"] = enrichment["type"]
                entry["service_name"] = enrichment["name"]
                entry["stats"] = enrichment.get("stats")
                entry["authError"] = enrichment.get("authError", False)
            results.append(entry)
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
            info = get_local_docker_info()
            if isinstance(info, list):
                results[node["name"]] = info
    return jsonify(results)


@app.route("/api/config", methods=["GET", "PUT"])
def config_info():
    if request.method == "PUT":
        try:
            data = _order_cfg(request.get_json(force=True))
            with open(CONFIG_PATH, "w") as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            return jsonify({"status": "ok"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    cfg = load_config()
    if cfg is None:
        cfg = {"title": "Homelab Monitor", "nodes": []}
    return jsonify(cfg)


@app.route("/api/update")
def update_check():
    state = check_for_update()
    return jsonify(state)
def health():
    return jsonify({"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()})


@app.route("/")
@app.route("/<path:path>")
def dashboard(path="index.html"):
    file_path = DASHBOARD_DIR / path
    if file_path.is_file():
        return send_from_directory(str(DASHBOARD_DIR), path)
    return send_from_directory(str(DASHBOARD_DIR), "index.html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    state = check_for_update()
    if state.get("available"):
        print(f"  Update available: v{state['current']} → v{state['latest']}")
        print(f"  Run 'hlm update' to upgrade\n")
    print(f"Homelab Monitor starting on http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port)
