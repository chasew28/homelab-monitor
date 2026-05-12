#!/usr/bin/env bash
set -euo pipefail

REPO="chasew28/homelab-monitor"
BRANCH="main"
VENV_DIR="$HOME/.hlm/venv"
BIN_DIR="$HOME/.local/bin"
HLM_BIN="$VENV_DIR/bin/hlm"
SYMLINK="$BIN_DIR/hlm"

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${CYAN}═══ Homelab Monitor Installer ═══${NC}"

if ! command -v python3 &>/dev/null; then
  echo -e "${YELLOW}Error: python3 is required but not found.${NC}"
  exit 1
fi

echo -e "  ${CYAN}→${NC} Creating virtual environment at $VENV_DIR"
mkdir -p "$VENV_DIR"
python3 -m venv "$VENV_DIR"

echo -e "  ${CYAN}→${NC} Installing from github.com/$REPO"
"$VENV_DIR/bin/pip" install "git+https://github.com/$REPO.git" --quiet 2>&1 | tail -1

mkdir -p "$BIN_DIR"
ln -sf "$HLM_BIN" "$SYMLINK"
echo -e "  ${GREEN}✓${NC} Installed hlm to $SYMLINK"

if ! echo "$PATH" | tr ':' '\n' | grep -q "$BIN_DIR"; then
  echo ""
  echo -e "  ${YELLOW}→${NC} Add $BIN_DIR to your PATH:"
  echo -e "    ${CYAN}export PATH=\"\$HOME/.local/bin:\$PATH\"${NC}"
  echo -e "    ${YELLOW}(add that line to ~/.bashrc or ~/.zshrc to make it permanent)${NC}"
fi

echo ""
echo -e "  ${GREEN}✓${NC} Ready! Create a project folder and run:"
echo -e "    ${CYAN}mkdir my-monitor && cd my-monitor${NC}"
echo -e "    ${CYAN}hlm setup${NC}"
echo -e "    ${CYAN}hlm run${NC}"
echo ""
echo -e "  ${YELLOW}On remote nodes, run:${NC}"
echo -e "    ${CYAN}hlm agent${NC}"
