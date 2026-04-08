#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "=== Options Analytics — Setup ==="

# ── Backend ──────────────────────────────────────────────────────────────────
echo ""
echo "► Setting up backend..."
cd "$ROOT/backend"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
  echo "  Created .venv"
fi

source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "  Python dependencies installed."

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "  ⚠  Created backend/.env from template."
  echo "     Edit it with your Robinhood credentials before starting."
fi

deactivate

# ── Frontend ─────────────────────────────────────────────────────────────────
echo ""
echo "► Setting up frontend..."
cd "$ROOT/frontend"

if command -v npm &>/dev/null; then
  npm install --legacy-peer-deps
  echo "  Node dependencies installed."
else
  echo "  ✗ npm not found. Install Node.js 18+ first."
  exit 1
fi

echo ""
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "  1. Edit backend/.env with your Robinhood credentials"
echo "  2. Start backend:   cd backend && source .venv/bin/activate && python run.py"
echo "  3. Start frontend:  cd frontend && npm run dev"
echo "  4. Open:            http://localhost:3000"
