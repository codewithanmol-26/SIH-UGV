#!/usr/bin/env bash
# One-time dev environment setup for both backend and frontend.
# Does not start either server — see docs/development.md for that.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "== Backend =="
cd "$ROOT_DIR/backend"
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
[ -f .env ] || cp "$ROOT_DIR/.env.example" .env
echo "Backend deps installed. Activate with: source backend/.venv/bin/activate"

echo
echo "== Frontend =="
cd "$ROOT_DIR/frontend"
npm install
echo "Frontend deps installed."

echo
echo "Done. Next:"
echo "  Terminal 1: cd backend && source .venv/bin/activate && python main.py"
echo "  Terminal 2: cd frontend && npm run dev"
