#!/usr/bin/env bash
# ---------------------------------------------------------------
# MicrobeGraph — pre-push safety gate
#
# WHY THIS EXISTS:
#   .gitignore tells Git what to ignore. This script checks what Git
#   is ACTUALLY tracking, right now. Two independent checks, because a
#   secret published once is public forever.
#
# USAGE:  git add -A  &&  ./check-public-safe.sh      (run before every push)
#         Windows:  git add -A ; bash check-public-safe.sh
#
# RUN "git add -A" FIRST. This script inspects what Git is TRACKING
# (git ls-files). A brand-new file that has never been staged is invisible
# to Git, and therefore invisible to this check. Staging first means the
# gate inspects exactly what you are about to publish.
# ---------------------------------------------------------------

set -uo pipefail
problems=0

echo "MicrobeGraph pre-push safety check"
echo "-----------------------------------"

# --- 1. Is any secret-shaped file being tracked by Git? -----------
echo -n "1. Secret files not tracked ......... "
tracked_secrets=$(git ls-files | grep -E '(^|/)\.env$|secrets\.toml$|\.pem$|\.key$' || true)
if [ -n "$tracked_secrets" ]; then
  echo "FAIL"
  echo "   Git is tracking these secret files:"
  echo "$tracked_secrets" | sed 's/^/     /'
  echo "   Fix: git rm --cached <file>   then commit."
  problems=$((problems+1))
else
  echo "OK"
fi

# --- 2. Does any tracked file contain something that looks like a key? ---
echo -n "2. No key-shaped strings ............ "
# sk-ant-... = Anthropic; ghp_ = GitHub token; long quoted value after api_key.
# .env.example is excluded because it holds empty placeholders on purpose.
hits=$(git grep -nIE '(sk-ant-[A-Za-z0-9_-]{10,}|ghp_[A-Za-z0-9]{20,}|api[_-]?key[[:space:]]*=[[:space:]]*["'"'"'][A-Za-z0-9]{16,})' \
        -- ':!.env.example' ':!check-public-safe.sh' ':!docs/*' 2>/dev/null || true)
if [ -n "$hits" ]; then
  echo "FAIL"
  echo "$hits" | sed 's/^/     /'
  problems=$((problems+1))
else
  echo "OK"
fi

# --- 3. Is the data folder or a database being tracked? -----------
echo -n "3. Data/database not tracked ........ "
tracked_data=$(git ls-files | grep -E '^data/|\.duckdb$|\.sqlite$|\.db$' || true)
if [ -n "$tracked_data" ]; then
  echo "FAIL"
  echo "$tracked_data" | head -5 | sed 's/^/     /'
  echo "   Fix: git rm -r --cached data/   then commit."
  problems=$((problems+1))
else
  echo "OK"
fi

# --- 4. Any hard-coded local paths that would break for others? ---
echo -n "4. No hard-coded local paths ........ "
paths=$(git grep -nIE '(/Users/[a-zA-Z]|/home/[a-zA-Z]|C:\\\\Users\\\\)' \
        -- ':!docs/*' ':!check-public-safe.sh' ':!README.md' 2>/dev/null || true)
if [ -n "$paths" ]; then
  echo "WARN"
  echo "$paths" | head -5 | sed 's/^/     /'
  echo "   These work on your machine only. Use relative paths instead."
else
  echo "OK"
fi

# --- 4b. Is the private scratch folder being tracked? -------------
echo -n "4b. Private .dev/ not tracked ....... "
if git ls-files | grep -qE '^\.dev/'; then
  echo "FAIL"
  echo "   .dev/ holds personal working notes and must never be published."
  echo "   Fix: git rm -r --cached .dev   then commit."
  problems=$((problems+1))
else
  echo "OK"
fi

# --- 5. Are the language environments being tracked? --------------
# Both are large, machine-specific, and rebuildable from their lockfiles:
# .venv/ from requirements.lock.txt, renv/library/ from renv.lock.
echo -n "5. .venv not tracked ................ "
if git ls-files | grep -qE '^\.venv/'; then
  echo "FAIL"
  echo "   Fix: git rm -r --cached .venv   then commit."
  problems=$((problems+1))
else
  echo "OK"
fi

echo -n "5b. renv/library not tracked ........ "
if git ls-files | grep -qE '^renv/(library|staging|sandbox)/'; then
  echo "FAIL"
  echo "   The R package library is hundreds of MB and rebuildable from renv.lock."
  echo "   Fix: git rm -r --cached renv/library   then commit."
  problems=$((problems+1))
else
  echo "OK"
fi

echo "-----------------------------------"
if [ "$problems" -eq 0 ]; then
  echo "SAFE TO PUSH"
  exit 0
else
  echo "NOT SAFE TO PUSH — $problems problem(s) above. Fix, then re-run."
  exit 1
fi
