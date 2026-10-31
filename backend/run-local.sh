#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ -f ".venv/bin/activate" ]; then
	# shellcheck disable=SC1091
	source ".venv/bin/activate"
fi

if [ -f ".env" ]; then
	set -a
	# shellcheck disable=SC1091
	source ".env"
	set +a
fi

export APP_ENV="${APP_ENV:-dev}"
uvicorn app.main:app --host 0.0.0.0 --port 8000
