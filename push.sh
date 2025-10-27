#!/usr/bin/env bash
set -euo pipefail

ARG="${1-}"

smart_mv() {
  # Usage: smart_mv SRC DST
  local SRC="$1" DST="$2"
  if [[ -e "$SRC" ]]; then
    if git ls-files --error-unmatch "$SRC" >/dev/null 2>&1; then
      git mv -f "$SRC" "$DST"
    else
      mv -f "$SRC" "$DST"
    fi
  else
    echo "Note: $SRC not found; nothing to rename." >&2
  fi
}

COMMIT_MSG="automatic push"

case "$ARG" in
  --all)
    smart_mv "test_config.json" "no_config.json"
    COMMIT_MSG="$COMMIT_MSG (--all: test_config.json → no_config.json)"
    ;;
  "")
    if [[ -e "no_config.json" ]]; then
      smart_mv "no_config.json" "test_config.json"
      COMMIT_MSG="$COMMIT_MSG (default: no_config.json → test_config.json)"
    else
      echo "Note: neither no_config.json nor no_config.son found; nothing to rename." >&2
    fi
    ;;
  *)
    echo "Usage: $0 [--all]"
    exit 2
    ;;
esac

# Keep your original workflow
echo "a" >> a.txt

# Avoid bare 'git checkout' (it's invalid). If you meant to discard changes, do it explicitly.
# git checkout -- .    # or: git restore --source=HEAD --worktree --staged .

git add -A
git commit -m "$COMMIT_MSG" || true
git push upstream master