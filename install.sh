#!/usr/bin/env bash

set -euo pipefail

PLUGIN_REPO="PostHog/codex-share-plugin"
MARKETPLACE_NAME="codex-share-plugin"
PLUGIN_NAME="codex-share-plugin"
SESSION_REPO="PostHog/agent-sessions"

usage() {
    cat <<'EOF'
Install the Codex Share Plugin.

Usage:
  bash install.sh [--codex-share-repo owner/repo]
  bash install.sh [owner/repo]

The session repository defaults to PostHog/agent-sessions.
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --codex-share-repo)
            if [[ $# -lt 2 ]]; then
                echo "Error: --codex-share-repo requires owner/repo" >&2
                exit 2
            fi
            SESSION_REPO="$2"
            shift 2
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        -*)
            echo "Error: unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
        *)
            SESSION_REPO="$1"
            shift
            ;;
    esac
done

if [[ ! "$SESSION_REPO" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]]; then
    echo "Error: session repository must use owner/repo format" >&2
    exit 2
fi

for command_name in codex gh python3; do
    if ! command -v "$command_name" >/dev/null 2>&1; then
        echo "Error: $command_name is required but was not found" >&2
        exit 1
    fi
done

if ! gh auth status >/dev/null 2>&1; then
    echo "Error: GitHub CLI is not authenticated. Run: gh auth login" >&2
    exit 1
fi

echo "Installing Codex Share Plugin..."

if codex plugin marketplace list 2>/dev/null | grep -Fq "Marketplace \`$MARKETPLACE_NAME\`"; then
    codex plugin marketplace upgrade "$MARKETPLACE_NAME"
else
    codex plugin marketplace add "$PLUGIN_REPO"
fi

codex plugin add "$PLUGIN_NAME@$MARKETPLACE_NAME"

CONFIG_PATH="${CODEX_HOME:-$HOME/.codex}/share-plugin-config.json"
python3 - "$CONFIG_PATH" "$SESSION_REPO" <<'PY'
import json
import sys
from pathlib import Path

config_path = Path(sys.argv[1]).expanduser()
config_path.parent.mkdir(parents=True, exist_ok=True)
config_path.write_text(json.dumps({"repo": sys.argv[2]}, indent=2) + "\n", encoding="utf-8")
PY

echo "Installed Codex Share Plugin."
echo "Sessions will be published to $SESSION_REPO/sessions/codex/{github-username}/"
echo "Restart Codex and start a new thread, then ask: Share this session."
