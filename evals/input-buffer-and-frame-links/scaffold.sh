#!/usr/bin/env bash
# Copy the operator's existing UFE documentation index into this run's
# temporary home, so the plugin's server answers from it instead of
# downloading the manual from the publisher's site on every run.
set -euo pipefail
real_home=$(eval echo "~$(id -un)")
if [ "$(uname)" = Darwin ]; then rel="Library/Caches/ufe-docs-mcp"; else rel=".cache/ufe-docs-mcp"; fi
src="$real_home/$rel"
if [ ! -f "$src/docs.sqlite3" ] || [ ! -f "$src/refresh-state.json" ]; then
  echo "No UFE documentation index at $src. Run 'uv run --frozen ufe-docs-mcp sync' first." >&2
  exit 1
fi
python3 - "$src/refresh-state.json" <<'EOF'
import json, sys
from datetime import datetime, timezone
state = json.load(open(sys.argv[1]))
checked = datetime.fromisoformat(state["last_successful_check_at"])
age_hours = (datetime.now(timezone.utc) - checked).total_seconds() / 3600
if age_hours > 20:
    sys.exit(f"The documentation index is {age_hours:.0f} hours old. Run 'uv run --frozen ufe-docs-mcp sync' first so eval runs do not trigger downloads.")
EOF
mkdir -p "$HOME/$rel"
cp "$src/docs.sqlite3" "$src/refresh-state.json" "$HOME/$rel/"
