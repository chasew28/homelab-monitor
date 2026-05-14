import os
import sys
import subprocess
import textwrap
from pathlib import Path

import yaml

from hlm_cli.updater import get_current_version, check_for_update, perform_update

HERE = Path(__file__).resolve().parent


def cmd_run():
    env = os.environ.copy()
    env["HLM_CONFIG_DIR"] = os.getcwd()
    subprocess.run([sys.executable, str(HERE / "server.py")], env=env)


def cmd_setup():
    subprocess.run([sys.executable, str(HERE / "wizard.py")])


def cmd_agent():
    subprocess.run([sys.executable, str(HERE / "agent.py")])


def cmd_link():
    args = sys.argv[2:]
    if not args or args[0] in ("-h", "--help"):
        print("Usage: hlm link [user@]host [options]")
        print()
        print("Links a remote machine to your homelab monitor. SSHes in, installs")
        print("the agent, starts it as a systemd service, and adds it to config.yml.")
        print()
        print("Options:")
        print("  -p, --port <port>       SSH port (default: 22)")
        print("  --agent-port <port>     Agent port (default: 5100)")
        print("  --name <name>           Node name (default: remote hostname)")
        print("  --docker                Enable Docker monitoring on this node")
        print("  -y, --yes               Skip confirmation")
        print()
        print("Examples:")
        print("  hlm link 192.168.1.10")
        print("  hlm link admin@192.168.1.10 --docker")
        print("  hlm link 192.168.1.10 --name NAS --agent-port 5200")
        sys.exit(1 if not args else 0)

    target = args[0]
    ssh_port = "22"
    agent_port = "5100"
    node_name = None
    docker = False
    skip_confirm = False

    i = 1
    while i < len(args):
        if args[i] in ("-p", "--port") and i + 1 < len(args):
            ssh_port = args[i + 1]
            i += 2
        elif args[i] == "--agent-port" and i + 1 < len(args):
            agent_port = args[i + 1]
            i += 2
        elif args[i] == "--name" and i + 1 < len(args):
            node_name = args[i + 1]
            i += 2
        elif args[i] == "--docker":
            docker = True
            i += 1
        elif args[i] in ("-y", "--yes"):
            skip_confirm = True
            i += 1
        else:
            print(f"Unknown option: {args[i]}")
            sys.exit(1)

    if "@" in target:
        ssh_user, host = target.split("@", 1)
    else:
        ssh_user = os.environ.get("USER", "root")
        host = target

    print(f"  Linking {ssh_user}@{host} (port {ssh_port})")
    if not skip_confirm:
        resp = input("  Proceed? [Y/n] ").strip().lower()
        if resp and resp != "y":
            print("  Cancelled.")
            sys.exit(0)

    remote_script = textwrap.dedent(f"""\
        set -e
        VENV="$HOME/.hlm/agent"
        echo "  → Creating venv at $VENV"
        python3 -m venv "$VENV" 2>/dev/null || {{ echo "  ✗ Failed to create venv"; exit 1; }}
        echo "  → Installing homelab-monitor"
        "$VENV/bin/pip" install git+https://github.com/chasew28/homelab-monitor.git --quiet 2>&1 | tail -1
        echo "  → Starting agent on port {agent_port}"
        AGENT_PORT={agent_port} nohup "$VENV/bin/hlm" agent > "$VENV/agent.log" 2>&1 &
        AGENT_PID=$!
        sleep 2
        if kill -0 $AGENT_PID 2>/dev/null; then
            echo "  ✓ Agent running (PID $AGENT_PID)"
        else
            echo "  ✗ Agent failed to start — check $VENV/agent.log"
            exit 1
        fi
        # Try to set up systemd
        if command -v systemctl &>/dev/null; then
            sudo tee /etc/systemd/system/hlm-agent.service > /dev/null << UNIT
        [Unit]
        Description=Homelab Monitor Agent
        After=network.target

        [Service]
        Type=simple
        User=$USER
        ExecStart=$VENV/bin/hlm agent
        Environment=AGENT_PORT={agent_port}
        Restart=always
        RestartSec=5

        [Install]
        WantedBy=multi-user.target
        UNIT
            sudo systemctl daemon-reload
            sudo systemctl enable --now hlm-agent 2>/dev/null || true
            echo "  ✓ systemd service enabled (hlm-agent)"
        fi
        hostname
    """)

    ssh_cmd = [
        "ssh",
        "-p", ssh_port,
        "-o", "ConnectTimeout=10",
        "-o", "StrictHostKeyChecking=accept-new",
        f"{ssh_user}@{host}",
        "bash -s",
    ]

    try:
        result = subprocess.run(
            ssh_cmd,
            input=remote_script,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except FileNotFoundError:
        print("  ✗ ssh not found — is it installed?")
        sys.exit(1)

    if result.returncode != 0:
        print(f"  ✗ SSH failed (exit code {result.returncode})")
        if result.stderr:
            for line in result.stderr.strip().split("\n"):
                print(f"    {line}")
        sys.exit(1)

    output_lines = result.stdout.strip().split("\n")
    remote_hostname = output_lines[-1].strip() if output_lines else host
    for line in output_lines[:-1]:
        print(f"  {line}")

    final_name = node_name or remote_hostname
    print(f"\n  ✓ {final_name} ({host}) is linked and running on port {agent_port}")

    config_path = Path.cwd() / "config.yml"
    if config_path.exists():
        cfg = yaml.safe_load(config_path.read_text()) or {"title": "My Homelab", "nodes": []}
        if "nodes" not in cfg:
            cfg["nodes"] = []
        exists = any(n.get("host") == host for n in cfg["nodes"])
        if exists:
            print(f"  → {host} already in config.yml, skipping update")
        else:
            cfg["nodes"].append({
                "name": final_name,
                "host": host,
                "agent_port": int(agent_port),
                "docker": docker,
                "services": [],
            })
            with open(config_path, "w") as f:
                yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True)
            print(f"  → Added {final_name} to config.yml")
    else:
        print(f"  → No config.yml found in {Path.cwd()} — create one with 'hlm setup'")
        print(f"  → Then add this node manually:")
        print(f"      - name: \"{final_name}\"")
        print(f"        host: \"{host}\"")
        print(f"        agent_port: {agent_port}")
        print(f"        docker: {str(docker).lower()}")
        print(f"        services: {{}}")


def cmd_update():
    state = check_for_update(force=True)
    if state.get("available"):
        print(f"  Update available: {state['current']} → {state['latest']}")
        resp = input("  Install now? [Y/n] ").strip().lower()
        if resp and resp != "y":
            print("  Cancelled.")
            sys.exit(0)
    else:
        print(f"  Already up-to-date (v{state.get('current', '?')})")
        resp = input("  Reinstall anyway? [y/N] ").strip().lower()
        if resp != "y":
            sys.exit(0)

    print(f"  Updating...")
    ok, result = perform_update()
    if ok:
        print(f"  ✓ Updated to v{result}")
    else:
        print(f"  ✗ Update failed:\n{result}")
        sys.exit(1)


def main():
    cmds = {
        "run": (cmd_run, "Start the monitoring dashboard"),
        "setup": (cmd_setup, "Interactive configuration wizard"),
        "agent": (cmd_agent, "Start remote agent for secondary machines"),
        "link": (cmd_link, "Link a remote node via SSH (install + configure agent)"),
        "update": (cmd_update, "Check for updates and upgrade"),
    }

    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        print("Usage: hlm <command>\n")
        for name, (_, doc) in cmds.items():
            print(f"  {name:<8} {doc}")
        print()
        sys.exit(1)

    cmds[sys.argv[1]][0]()
