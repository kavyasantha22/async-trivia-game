#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./push.sh          # remove test_config.json from .gitignore (if present)
#   ./push.sh --all    # ensure test_config.json is ignored and untracked

ARG="${1-}"

case "$ARG" in
  --all)
    # Ensure .gitignore exists and contains the line exactly once
    touch .gitignore
    if ! grep -qxF 'test_config.json' .gitignore; then
      echo 'test_config.json' >> .gitignore
    fi
    # If the file is tracked, stop tracking it (but keep working copy)
    if git ls-files --error-unmatch test_config.json >/dev/null 2>&1; then
      git rm --cached test_config.json
    fi
    ;;
  "" )
    # Remove the exact line from .gitignore, if present (portable macOS/Linux sed)
    if [[ -f .gitignore ]]; then
      sed -i.bak '/^test_config\.json$/d' .gitignore && rm -f .gitignore.bak
    fi
    ;;
  *)
    echo "Unknown argument: $ARG"
    echo "Usage: $0 [--all]"
    exit 2
    ;;
esac

# Your original workflow
echo "a" >> a.txt

# NOTE: a bare `git checkout` is invalid and will error out.
# If you intended to discard local changes, use one of:
#   git checkout -- .
#   git restore --source=HEAD --worktree --staged .
# (Left out here to avoid unintended resets.)

# Stage .gitignore changes explicitly (in case only it changed)
git add .gitignore || true
git add .

git commit -m "automatic push" || true
git push upstream master