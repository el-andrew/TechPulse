#!/bin/sh
set -eu

if [ "${RUN_INIT_DB:-1}" = "1" ]; then
  attempts="${INIT_DB_ATTEMPTS:-20}"
  delay_seconds="${INIT_DB_DELAY_SECONDS:-3}"
  current=1
  until python -m app.main init-db; do
    if [ "$current" -ge "$attempts" ]; then
      echo "database initialization failed after ${current} attempts" >&2
      exit 1
    fi
    echo "database not ready, retrying in ${delay_seconds}s (${current}/${attempts})" >&2
    current=$((current + 1))
    sleep "$delay_seconds"
  done
fi

exec "$@"
