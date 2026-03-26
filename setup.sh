#!/usr/bin/env bash
# =============================================================================
# OpenSite Agent Skills Setup
# Sets up symlinks from all supported AI agent platforms to this shared repo.
# Run from anywhere; SKILLS_DIR is resolved to the repo root automatically.
# =============================================================================
set -euo pipefail

SKILLS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLATFORMS=()

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         OpenSite Agent Skills Setup                          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Source: $SKILLS_DIR"
echo ""

# Helper: create symlink for one skill into a target directory
link_skill() {
  local skill_path="$1"
  local target_dir="$2"
  local skill_name
  skill_name="$(basename "$skill_path")"

  # Skip non-skill entries (README, CLAUDE.md, scripts)
  [[ -f "$skill_path/SKILL.md" ]] || return 0

  mkdir -p "$target_dir"
  ln -sfn "$skill_path" "$target_dir/$skill_name"
  echo "  ✓ $skill_name → $target_dir/$skill_name"
}

# ── Claude Code ──────────────────────────────────────────────────────────────
CLAUDE_SKILLS="$HOME/.claude/skills"
if command -v claude &>/dev/null || [ -d "$HOME/.claude" ]; then
  echo "── Claude Code ──────────────────────────────────────────────"
  mkdir -p "$CLAUDE_SKILLS"
  for skill in "$SKILLS_DIR"/*/; do
    link_skill "$skill" "$CLAUDE_SKILLS"
  done
  # CLAUDE.md root context
  if [ -f "$SKILLS_DIR/CLAUDE.md" ]; then
    ln -sfn "$SKILLS_DIR/CLAUDE.md" "$HOME/.claude/CLAUDE.md"
    echo "  ✓ CLAUDE.md → $HOME/.claude/CLAUDE.md"
  fi
  PLATFORMS+=("Claude Code")
else
  echo "── Claude Code — SKIPPED (not installed)"
fi
echo ""

# ── Codex ────────────────────────────────────────────────────────────────────
CODEX_SKILLS="$HOME/.codex/skills"
if command -v codex &>/dev/null || [ -d "$HOME/.codex" ]; then
  echo "── Codex ─────────────────────────────────────────────────────"
  mkdir -p "$CODEX_SKILLS"
  for skill in "$SKILLS_DIR"/*/; do
    link_skill "$skill" "$CODEX_SKILLS"
  done
  PLATFORMS+=("Codex")
else
  echo "── Codex — SKIPPED (not installed)"
fi
echo ""

# ── Cursor ───────────────────────────────────────────────────────────────────
CURSOR_SKILLS="$HOME/.cursor/skills"
if command -v cursor &>/dev/null || [ -d "$HOME/.cursor" ]; then
  echo "── Cursor ────────────────────────────────────────────────────"
  mkdir -p "$CURSOR_SKILLS"
  for skill in "$SKILLS_DIR"/*/; do
    link_skill "$skill" "$CURSOR_SKILLS"
  done
  PLATFORMS+=("Cursor")
else
  echo "── Cursor — SKIPPED (not installed)"
fi
echo ""

# ── GitHub Copilot ───────────────────────────────────────────────────────────
COPILOT_SKILLS="$HOME/.copilot/skills"
if command -v gh &>/dev/null || [ -d "$HOME/.copilot" ]; then
  echo "── GitHub Copilot ────────────────────────────────────────────"
  mkdir -p "$COPILOT_SKILLS"
  for skill in "$SKILLS_DIR"/*/; do
    link_skill "$skill" "$COPILOT_SKILLS"
  done
  PLATFORMS+=("GitHub Copilot")
else
  echo "── GitHub Copilot — SKIPPED (not installed)"
fi
echo ""

# ── Factory/Droid ────────────────────────────────────────────────────────────
FACTORY_SKILLS="$HOME/.factory/skills"
if command -v droid &>/dev/null || [ -d "$HOME/.factory" ]; then
  echo "── Factory/Droid ─────────────────────────────────────────────"
  mkdir -p "$FACTORY_SKILLS"
  for skill in "$SKILLS_DIR"/*/; do
    link_skill "$skill" "$FACTORY_SKILLS"
  done
  PLATFORMS+=("Factory/Droid")
else
  echo "── Factory/Droid — SKIPPED (not installed)"
fi
echo ""

# ── Repo-level (optional) ────────────────────────────────────────────────────
if [ "${LINK_REPO:-0}" = "1" ]; then
  echo "── Repo-level (.agents/skills) ───────────────────────────────"
  REPO_SKILLS=".agents/skills"
  mkdir -p "$REPO_SKILLS"
  for skill in "$SKILLS_DIR"/*/; do
    link_skill "$skill" "$REPO_SKILLS"
  done
  echo ""
fi

# ── Summary ──────────────────────────────────────────────────────────────────
SKILL_COUNT=$(find "$SKILLS_DIR" -name "SKILL.md" | wc -l | tr -d ' ')
echo "══════════════════════════════════════════════════════════════"
if [ ${#PLATFORMS[@]} -gt 0 ]; then
  echo "  Linked $SKILL_COUNT skills across: ${PLATFORMS[*]}"
else
  echo "  No platforms detected. Install Claude Code, Codex, Copilot (gh), Cursor, or Factory/Droid first."
  echo "  Then re-run this script."
fi
echo ""
echo "  To update skills: edit files in $SKILLS_DIR"
echo "  Changes are live immediately (no reinstall needed)."
echo ""
echo "  To Sync Perplexity Cloud Skills: run ./sync-perplexity.sh"
echo "  To Sync Claude Desktop Skills: run ./sync-claude.sh"
echo "══════════════════════════════════════════════════════════════"
echo ""
