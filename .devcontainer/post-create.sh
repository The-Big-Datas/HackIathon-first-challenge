#!/usr/bin/env bash
set -e

echo "=== hackIAthon PreAuth dev container ==="

# .env
if [ ! -f /workspace/.env ] && [ -f /workspace/.env.example ]; then
  cp /workspace/.env.example /workspace/.env
  echo "Created .env from .env.example — fill in your API keys."
fi

# Streamlit secrets
if [ ! -f /workspace/frontend/.streamlit/secrets.toml ]; then
  mkdir -p /workspace/frontend/.streamlit
  cp /workspace/frontend/.streamlit/secrets.toml.example \
     /workspace/frontend/.streamlit/secrets.toml 2>/dev/null || true
fi

echo ""
echo "Claude Code auth:"
echo "  Run 'claude' and follow the sign-in prompt."
echo "  Auth persists in the named volume — no re-login after rebuild."
echo ""
echo "Start services:"
echo "  Backend:  uvicorn app.main:app --reload --port 8000"
echo "  Frontend: cd frontend && streamlit run app.py"
echo "  Static:   cd frontend && python -m http.server 3000"
