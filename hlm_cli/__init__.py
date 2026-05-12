import sys
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent


def cmd_run():
    subprocess.run([sys.executable, str(HERE / "app.py")])


def cmd_setup():
    subprocess.run([sys.executable, str(HERE / "wizard.py")])


def cmd_agent():
    subprocess.run([sys.executable, str(HERE / "agent.py")])


def main():
    cmds = {
        "run": cmd_run,
        "setup": cmd_setup,
        "agent": cmd_agent,
    }

    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        print("Usage: hlm <command>")
        print()
        for name, fn in cmds.items():
            print(f"  {name:<8} {fn.__doc__ or ''}")
        print()
        sys.exit(1)

    cmds[sys.argv[1]]()
