import os
import sys
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent


def cmd_run():
    env = os.environ.copy()
    env["HLM_CONFIG_DIR"] = os.getcwd()
    subprocess.run([sys.executable, str(HERE / "app.py")], env=env)


def cmd_setup():
    subprocess.run([sys.executable, str(HERE / "wizard.py")])


def cmd_agent():
    subprocess.run([sys.executable, str(HERE / "agent.py")])


def main():
    cmds = {
        "run": (cmd_run, "Start the monitoring dashboard"),
        "setup": (cmd_setup, "Interactive configuration wizard"),
        "agent": (cmd_agent, "Start remote agent for secondary machines"),
    }

    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        print("Usage: hlm <command>\n")
        for name, (_, doc) in cmds.items():
            print(f"  {name:<8} {doc}")
        print()
        sys.exit(1)

    cmds[sys.argv[1]][0]()
