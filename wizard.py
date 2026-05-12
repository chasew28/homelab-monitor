import sys
from hlm_cli.wizard import main

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.stdout.write("\n  Cancelled.\n")
        sys.exit(0)

