#!/usr/bin/env python3
import os
import subprocess
import sys
import shutil
from pathlib import Path

HERE = Path(__file__).parent.resolve()
CONFIG_PATH = Path(os.environ.get("HLM_CONFIG_DIR", os.getcwd())) / "config.yml"

C = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "purple": "\033[38;5;99m",
    "green": "\033[38;5;76m",
    "yellow": "\033[38;5;221m",
    "red": "\033[38;5;196m",
    "cyan": "\033[38;5;81m",
    "grey": "\033[38;5;245m",
    "bg": "\033[48;5;235m",
}


def p(text, color="", end="\n"):
    sys.stdout.write(f"{color}{text}{C['reset']}{end}")
    sys.stdout.flush()


def boxed(text, color=C["cyan"]):
    width = shutil.get_terminal_size().columns
    line = f"{color}{'─' * (width - 2)}{C['reset']}"
    p(f"╭{line}╮")
    p(f"│ {color}{C['bold']}{text:^{width-4}}{C['reset']} │")
    p(f"╰{line}╯")


def prompt(label, default="", secret=False):
    default_str = f" [{default}]" if default else ""
    while True:
        val = input(f"  {C['cyan']}?{C['reset']} {label}{C['grey']}{default_str}{C['reset']}: ")
        if not val and default:
            return default
        if val:
            return val
        if default == "":
            return ""


def yn(label, default=True):
    hint = "Y/n" if default else "y/N"
    val = input(f"  {C['cyan']}?{C['reset']} {label} {C['grey']}({hint}){C['reset']}: ").strip().lower()
    if not val:
        return default
    return val == "y"


def install_deps():
    req = HERE / "requirements.txt"
    if not req.exists():
        p("  requirements.txt not found, skipping", C["yellow"])
        return
    p(f"\n  {C['yellow']}⏳{C['reset']} Installing dependencies...\n")
    r = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(req)],
        capture_output=True, text=True
    )
    if r.returncode == 0:
        p(f"  {C['green']}✓{C['reset']} Dependencies installed\n")
    else:
        p(f"  {C['red']}✗{C['reset']} Install failed:\n{r.stderr}", C["red"])


def collect_nodes():
    nodes = []
    p(f"\n  A {C['cyan']}node{C['reset']} is a machine on your network — a Raspberry Pi, server, NAS, or your main PC.")
    p(f"  {C['grey']}Each node can have services (web apps, databases, etc.) that we'll check.{C['reset']}")
    p(f"  {C['grey']}(Ctrl+C to cancel at any time){C['reset']}\n")
    i = 1
    while True:
        p(f"\n  {C['purple']}── Machine {i} ──{C['reset']}")
        name = prompt("Name for this machine", f"Machine {i}")
        host = prompt("IP address or hostname (e.g. 192.168.1.10)", "127.0.0.1")
        is_local = host in ("127.0.0.1", "localhost")
        if is_local:
            local = yn("Collect system stats (CPU, RAM, disk) from this machine?", True)
            agent_port = None if local else prompt("Agent port (remote agent listens here)", "5100")
            docker = yn("Monitor Docker containers on this machine?", True)
        else:
            local = yn("Run a monitoring agent on this remote machine?", False)
            if local:
                agent_port = prompt("Agent port (must match the agent's AGENT_PORT)", "5100")
                docker = yn("Monitor Docker containers on this machine?", False)
            else:
                agent_port = None
                docker = False

        services = []
        p(f"\n  {C['grey']}── Services for {name} ──{C['reset']}")
        p(f"  {C['grey']}Services are web apps or sites running on this machine we'll check are alive.{C['reset']}")
        j = 1
        while True:
            svc_name = prompt(f"  Service {j} name", "My App")
            svc_url = prompt(f"  Service {j} URL (e.g. http://192.168.1.10:8080)", "http://localhost:8080")
            services.append({"name": svc_name, "url": svc_url})
            j += 1
            if not yn(f"  Add another service?", False):
                break

        nodes.append({
            "name": name,
            "host": host,
            "agent_port": agent_port if agent_port else None,
            "docker": docker,
            "services": services,
        })
        i += 1
        if not yn("Add another machine?", i <= 2):
            break
    return nodes


def ask_title():
    p("")
    return prompt("Dashboard title", "Homelab Monitor")


def write_config(title, nodes):
    lines = [f'title: "{title}"\n', "\n", "nodes:\n"]
    for n in nodes:
        lines.append(f'  - name: "{n["name"]}"\n')
        lines.append(f'    host: "{n["host"]}"\n')
        ap = n.get("agent_port")
        if ap:
            lines.append(f"    agent_port: {ap}\n")
        else:
            lines.append(f"    agent_port:\n")
        lines.append(f"    docker: {str(n['docker']).lower()}\n")
        lines.append(f"    services:\n")
        for s in n.get("services", []):
            lines.append(f'      - name: "{s["name"]}"\n')
            lines.append(f'        url: "{s["url"]}"\n')
    CONFIG_PATH.write_text("".join(lines))
    return CONFIG_PATH


def main():
    os.system("clear" if os.name == "posix" else "cls")

    boxed("Homelab Monitor — Setup")
    p(f"\n  {C['grey']}This will guide you through adding machines and services to monitor.{C['reset']}")
    p(f"  {C['grey']}You can always edit {C['cyan']}config.yml{C['grey']} manually later.{C['reset']}\n")

    title = ask_title()
    nodes = collect_nodes()

    path = write_config(title, nodes)

    p(f"\n  {C['green']}{'─' * 40}{C['reset']}")
    p(f"  {C['green']}✓{C['reset']} Config written to {C['cyan']}{path}{C['reset']}")
    p(f"  {C['green']}{'─' * 40}{C['reset']}")
    p(f"\n  {C['bold']}Machines configured:{C['reset']}")
    for n in nodes:
        tag = f"{C['green']}local{C['reset']}" if n["host"] in ("127.0.0.1", "localhost") else f"{C['cyan']}remote{C['reset']}"
        n_services = len(n["services"])
        p(f"    • {n['name']}  {C['grey']}({n['host']}, {tag}, {n_services} service{'s' if n_services != 1 else ''}){C['reset']}")

    p(f"\n  {C['bold']}To start:{C['reset']}")
    p(f"    {C['cyan']}hlm run{C['reset']}")
    p(f"\n  {C['dim']}Or run with Docker:{C['reset']}")
    p(f"    docker compose up{C['reset']}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        p(f"\n\n  {C['yellow']}Setup cancelled.{C['reset']}\n")
        sys.exit(0)
