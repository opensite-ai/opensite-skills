#!/usr/bin/env bash
# =============================================================================
# OpenSite / Toastability — Perplexity Computer Skills Sync
#
# Perplexity stores skills in the cloud, so symlinks can't work.
# This script packages each skill as a zip and uploads via the Perplexity API.
#
# Requirements:
#   - PERPLEXITY_API_KEY in environment or .env file in this directory
#   - curl, zip
#
# Usage:
#   ./sync-perplexity.sh              # upload all skills
#   ./sync-perplexity.sh --changed-only  # upload only git-modified skills
#   ./sync-perplexity.sh octane-rust-axum   # upload one specific skill
# =============================================================================
set -euo pipefail

SKILLS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHANGED_ONLY=0
SPECIFIC_SKILL=""

# Load .env if present
if [ -f "$SKILLS_DIR/.env" ]; then
  set -a; source "$SKILLS_DIR/.env"; set +a
fi

if [ -z "${PERPLEXITY_API_KEY:-}" ]; then
  echo "Error: PERPLEXITY_API_KEY is not set."
  echo "  Export it: export PERPLEXITY_API_KEY=pplx-..."
  echo "  Or add it to $SKILLS_DIR/.env"
  exit 1
fi

# Parse args
for arg in "$@"; do
  case $arg in
    --changed-only) CHANGED_ONLY=1 ;;
    *) SPECIFIC_SKILL="$arg" ;;
  esac
done

# Determine which skills to upload
if [ -n "$SPECIFIC_SKILL" ]; then
  SKILLS_TO_UPLOAD=("$SKILLS_DIR/$SPECIFIC_SKILL")
elif [ "$CHANGED_ONLY" = "1" ]; then
  echo "Detecting git-changed skills since last commit..."
  mapfile -t changed_files < <(git -C "$SKILLS_DIR" diff --name-only HEAD~1 HEAD 2>/dev/null || git -C "$SKILLS_DIR" status --short | awk '{print $2}')
  SKILLS_TO_UPLOAD=()
  for f in "${changed_files[@]}"; do
    skill_name=$(echo "$f" | cut -d'/' -f1)
    skill_path="$SKILLS_DIR/$skill_name"
    if [ -f "$skill_path/SKILL.md" ]; then
      SKILLS_TO_UPLOAD+=("$skill_path")
    fi
  done
  # Deduplicate
  mapfile -t SKILLS_TO_UPLOAD < <(printf '%s\n' "${SKILLS_TO_UPLOAD[@]}" | sort -u)
else
  mapfile -t SKILLS_TO_UPLOAD < <(find "$SKILLS_DIR" -maxdepth 1 -mindepth 1 -type d | sort)
fi

TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         Perplexity Computer — Skills Sync                    ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

UPLOADED=0
SKIPPED=0
FAILED=0

for skill_path in "${SKILLS_TO_UPLOAD[@]}"; do
  skill_name=$(basename "$skill_path")
  
  # Must have SKILL.md
  if [ ! -f "$skill_path/SKILL.md" ]; then
    continue
  fi

  echo -n "  Uploading $skill_name... "

  # Build zip with SKILL.md at root
  zip_path="$TMP_DIR/$skill_name.zip"
  (cd "$skill_path" && zip -qr "$zip_path" .)

  # Check size
  size_bytes=$(wc -c < "$zip_path" | tr -d ' ')
  if [ "$size_bytes" -gt 10485760 ]; then
    echo "SKIPPED (zip exceeds 10MB limit: ${size_bytes} bytes)"
    ((SKIPPED++))
    continue
  fi

  # Upload via Perplexity API
  # POST /api/skills/upload  (multipart form-data)
  response=$(curl -s -w "\n%{http_code}" \
    -X POST "https://www.perplexity.ai/api/skills/upload" \
    -H "Authorization: Bearer $PERPLEXITY_API_KEY" \
    -F "file=@$zip_path;type=application/zip" \
    -F "name=$skill_name" 2>&1)

  http_code=$(echo "$response" | tail -n1)
  body=$(echo "$response" | head -n-1)

  if [[ "$http_code" =~ ^2 ]]; then
    echo "OK (HTTP $http_code)"
    ((UPLOADED++))
  else
    echo "FAILED (HTTP $http_code)"
    echo "    Response: $body"
    ((FAILED++))
  fi
done

echo ""
echo "══════════════════════════════════════════════════════════════"
echo "  Results: $UPLOADED uploaded, $SKIPPED skipped, $FAILED failed"
echo ""
echo "  View skills at: https://www.perplexity.ai/computer/skills"
echo "══════════════════════════════════════════════════════════════"
echo ""

# Exit with error code if any failed
[ "$FAILED" -eq 0 ] || exit 1
