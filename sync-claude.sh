#!/usr/bin/env bash
# =============================================================================
# OpenSite / Toastability — Claude Desktop Skills Sync
#
# Claude has no public REST API for skill uploads — the upload UI is
# protected by Cloudflare and requires a real browser session.
# This script uses Playwright (real Brave browser, headed) to upload via the UI.
#
# Requirements:
#   - Node.js 18+
#   - Brave Browser at /Applications/Brave Browser.app
#   - CLAUDE_SESSION_COOKIE in .env (see below)
#
# Getting your session cookie:
#   1. Log in to claude.ai in Brave
#   2. Press F12 → Application tab → Cookies → https://claude.ai
#   3. Find "sessionKey", copy its Value
#   4. Add to .env:  CLAUDE_SESSION_COOKIE="<paste here>"
#
# Usage:
#   ./sync-claude.sh                   # upload all skills
#   ./sync-claude.sh --changed-only    # only git-modified skills
#   ./sync-claude.sh octane-rust-axum  # one specific skill
# =============================================================================
set -euo pipefail

SKILLS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLAYWRIGHT_HOME="$SKILLS_DIR/.playwright"

CHANGED_ONLY=0
SPECIFIC_SKILL=""

# Load .env if present
if [ -f "$SKILLS_DIR/.env" ]; then
  set -a; source "$SKILLS_DIR/.env"; set +a
fi

# Validate credentials
if [ -z "${CLAUDE_SESSION_COOKIE:-}" ]; then
  echo ""
  echo "Error: CLAUDE_SESSION_COOKIE is not set."
  echo ""
  echo "  1. Log in to claude.ai in Brave"
  echo "  2. Press F12 → Application → Cookies → https://claude.ai"
  echo "  3. Find 'sessionKey', copy the Value"
  echo "  4. Add to .env:  CLAUDE_SESSION_COOKIE=\"<value>\""
  echo ""
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
  echo "Detecting git-changed skills..."
  mapfile -t changed_files < <(git -C "$SKILLS_DIR" diff --name-only HEAD~1 HEAD 2>/dev/null || git -C "$SKILLS_DIR" status --short | awk '{print $2}')
  SKILLS_TO_UPLOAD=()
  for f in "${changed_files[@]:-}"; do
    [ -n "$f" ] || continue
    skill_name=$(echo "$f" | cut -d'/' -f1)
    skill_path="$SKILLS_DIR/$skill_name"
    if [ -f "$skill_path/SKILL.md" ]; then
      SKILLS_TO_UPLOAD+=("$skill_path")
    fi
  done
  if [ ${#SKILLS_TO_UPLOAD[@]} -gt 0 ]; then
    mapfile -t SKILLS_TO_UPLOAD < <(printf '%s\n' "${SKILLS_TO_UPLOAD[@]}" | sort -u)
  fi
else
  mapfile -t SKILLS_TO_UPLOAD < <(find "$SKILLS_DIR" -maxdepth 1 -mindepth 1 -type d ! -name ".playwright" ! -name ".git" ! -name "steps" ! -name "claude-desktop-steps" | sort)
fi

# Build zip files
ZIP_DIR="$SKILLS_DIR/.skill-zips-tmp"
rm -rf "$ZIP_DIR"
mkdir -p "$ZIP_DIR"

SKILL_ZIPS=()
for skill_path in "${SKILLS_TO_UPLOAD[@]:-}"; do
  [ -n "$skill_path" ] || continue
  skill_name=$(basename "$skill_path")
  [ -f "$skill_path/SKILL.md" ] || continue
  zip_path="$ZIP_DIR/$skill_name.zip"
  (cd "$skill_path" && zip -qr "$zip_path" .)
  size_bytes=$(wc -c < "$zip_path" | tr -d ' ')
  if [ "$size_bytes" -gt 10485760 ]; then
    echo "  SKIP $skill_name (zip > 10MB: ${size_bytes} bytes)"
    continue
  fi
  SKILL_ZIPS+=("$zip_path")
done

if [ ${#SKILL_ZIPS[@]} -eq 0 ]; then
  echo "No skills to upload."
  rm -rf "$ZIP_DIR"
  exit 0
fi

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         Claude Desktop — Skills Sync                         ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "  Uploading ${#SKILL_ZIPS[@]} skill(s) via browser automation..."
echo ""

# ── Install Playwright into persistent directory ────────────────────────────
if [ ! -f "$PLAYWRIGHT_HOME/node_modules/.bin/playwright" ]; then
  echo "  Installing Playwright (one-time, ~200MB)..."
  mkdir -p "$PLAYWRIGHT_HOME"
  cd "$PLAYWRIGHT_HOME"
  echo '{"name":"playwright-runner","version":"1.0.0","private":true}' > package.json
  npm install playwright > /dev/null 2>&1
  PLAYWRIGHT_BROWSERS_PATH="$PLAYWRIGHT_HOME/browsers" node node_modules/.bin/playwright install chromium 2>&1 | grep -v "^$" || true
  cd "$SKILLS_DIR"
  echo "  Playwright ready."
  echo ""
fi

# ── Write upload script ──────────────────────────────────────────────────────
UPLOAD_SCRIPT="$PLAYWRIGHT_HOME/upload-claude.mjs"
cat > "$UPLOAD_SCRIPT" << 'JSEOF'
import { chromium } from 'playwright';
import { basename } from 'path';
import { existsSync } from 'fs';

const SESSION_COOKIE = process.env.CLAUDE_SESSION_COOKIE;
const SKILL_ZIPS = process.env.SKILL_ZIPS.split('\n').filter(Boolean);
const SKILLS_URL = 'https://claude.ai/customize/skills';

if (!SESSION_COOKIE) {
  console.error('Error: CLAUDE_SESSION_COOKIE not set');
  process.exit(1);
}

const BRAVE = '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser';
const hasBrave = existsSync(BRAVE);

const browser = await chromium.launch({
  headless: false,
  executablePath: hasBrave ? BRAVE : undefined,
  args: [
    '--no-first-run',
    '--no-default-browser-check',
    '--window-size=1280,900',
    '--disable-blink-features=AutomationControlled',
  ],
});
const context = await browser.newContext({
  userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
});

await context.addCookies([{
  name: 'sessionKey',
  value: SESSION_COOKIE,
  domain: 'claude.ai',
  path: '/',
  httpOnly: true,
  secure: true,
  sameSite: 'Lax',
}]);

const page = await context.newPage();

console.log('  Navigating to skills page...');
await page.goto(SKILLS_URL, { waitUntil: 'networkidle', timeout: 30000 });

// claude.ai is a SPA — /customize sometimes loads before the router
// pushes to /customize/skills. Give it a moment then verify.
if (!page.url().includes('/skills')) {
  await page.goto(SKILLS_URL, { waitUntil: 'networkidle', timeout: 30000 });
}

const currentUrl = page.url();
if (currentUrl.includes('/login') || currentUrl.includes('/auth') || !currentUrl.includes('claude.ai')) {
  console.error('\n  Error: Session cookie is invalid or expired.');
  console.error('  1. Open Brave → claude.ai → log in');
  console.error('  2. F12 → Application → Cookies → claude.ai → find "sessionKey"');
  console.error('  3. Copy the value into .env as CLAUDE_SESSION_COOKIE="..."');
  await browser.close();
  process.exit(1);
}

console.log(`  Authenticated. Current URL: ${currentUrl}`);
console.log('');

let uploaded = 0;
let updated = 0;
let failed = 0;

// Wait for the page to fully settle — confirmed by the "Add skill" button being visible.
// selector: button[aria-label="Add skill"] (Radix dropdown trigger with + icon)
async function waitForPageReady() {
  await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
  await page.locator('button[aria-label="Add skill"]')
    .waitFor({ state: 'visible', timeout: 15000 });
}

// Step 1+2: click the "+" button → click "Upload a skill" in the dropdown.
// Selectors confirmed from HTML inspection:
//   button[aria-label="Add skill"]  — the Radix dropdown trigger
//   [role="menuitem"] "Upload a skill"  — the upload option
async function openUploadModal() {
  await page.locator('button[aria-label="Add skill"]').click();
  await page.waitForTimeout(400);

  await page.locator('[role="menuitem"]')
    .filter({ hasText: 'Upload a skill' })
    .first()
    .waitFor({ state: 'visible', timeout: 5000 });

  await page.locator('[role="menuitem"]')
    .filter({ hasText: 'Upload a skill' })
    .first()
    .click();

  await page.waitForTimeout(600);
}

// Step 3 + post-upload: click the dashed upload button, intercept the file chooser,
// set the file, then handle both outcomes:
//   - New skill   → modal closes automatically
//   - Duplicate   → "Replace [name] skill?" dialog appears → click "Upload and replace"
//
// Confirmed selectors:
//   button "Drag and drop or click to upload"  — the dashed upload zone (it's a <button>)
//   button "Upload and replace"                — the confirmation button in the replace dialog
async function uploadFile(zipPath) {
  const uploadZone = page.locator('button')
    .filter({ hasText: /drag and drop or click to upload/i })
    .first();

  await uploadZone.waitFor({ state: 'visible', timeout: 10000 });

  // Intercept the file chooser before clicking — prevents the OS dialog from opening
  const [fileChooser] = await Promise.all([
    page.waitForEvent('filechooser', { timeout: 8000 }),
    uploadZone.click(),
  ]);
  await fileChooser.setFiles(zipPath);

  // Give the server a moment to process / detect a name collision
  await page.waitForTimeout(2500);

  // If a duplicate was detected, Claude shows a "Replace [skill] skill?" confirmation.
  // Just click "Upload and replace" and we're done — no extra logic needed.
  const replaceBtn = page.locator('button')
    .filter({ hasText: /upload and replace/i })
    .first();
  const hasReplace = await replaceBtn.isVisible({ timeout: 4000 }).catch(() => false);

  if (hasReplace) {
    await replaceBtn.click();
    await page.waitForTimeout(2000);
    return { ok: true, wasUpdate: true };
  }

  // New skill path: wait for the modal to close (upload zone disappears = success)
  try {
    await uploadZone.waitFor({ state: 'hidden', timeout: 25000 });
    return { ok: true, wasUpdate: false };
  } catch {
    const errorText = await page.locator('[role="dialog"]')
      .filter({ hasText: /error|invalid|failed/i })
      .first().textContent({ timeout: 2000 }).catch(() => null);
    return { ok: false, reason: errorText ?? 'modal still open after 25s' };
  }
}

for (const zipPath of SKILL_ZIPS) {
  const skillName = basename(zipPath, '.zip');
  process.stdout.write(`  Syncing ${skillName}... `);

  try {
    if (SKILL_ZIPS.indexOf(zipPath) > 0) {
      await page.goto(SKILLS_URL, { waitUntil: 'networkidle', timeout: 30000 });
    }
    await waitForPageReady();

    await openUploadModal();
    const result = await uploadFile(zipPath);

    await page.keyboard.press('Escape').catch(() => {});
    await page.waitForTimeout(500);

    if (result.ok) {
      if (result.wasUpdate) { console.log('updated'); updated++; }
      else                  { console.log('uploaded'); uploaded++; }
    } else {
      console.log(`FAILED: ${result.reason}`);
      failed++;
    }
  } catch (err) {
    const msg = err.message.split('\n')[0].substring(0, 100);
    console.log(`FAILED: ${msg}`);
    await page.keyboard.press('Escape').catch(() => {});
    failed++;
  }
}

await browser.close();

console.log('');
console.log(`  Results: ${uploaded} new, ${updated} updated, ${failed} failed`);
if (uploaded + updated > 0) {
  console.log(`  View at: ${SKILLS_URL}`);
}
process.exit(failed > 0 ? 1 : 0);
JSEOF

# ── Run the upload ────────────────────────────────────────────────────────────
SKILL_ZIPS_LIST=$(printf '%s\n' "${SKILL_ZIPS[@]}")

SKILL_ZIPS="$SKILL_ZIPS_LIST" \
CLAUDE_SESSION_COOKIE="${CLAUDE_SESSION_COOKIE}" \
PLAYWRIGHT_BROWSERS_PATH="$PLAYWRIGHT_HOME/browsers" \
node "$UPLOAD_SCRIPT" 2>&1

EXIT_CODE=$?
rm -rf "$ZIP_DIR"
exit $EXIT_CODE
