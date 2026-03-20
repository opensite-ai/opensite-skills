#!/usr/bin/env bash
# =============================================================================
# OpenSite / Toastability — Perplexity Computer Skills Sync
#
# Perplexity has no public REST API for skill uploads — the upload UI is
# protected by Cloudflare and requires a real browser session.
# This script uses Playwright (real Brave browser, headed) to upload via the UI.
# Playwright's bundled headless Chromium is detected and blocked by Cloudflare;
# using the real Brave binary with a visible window bypasses this.
#
# Requirements:
#   - Node.js 18+
#   - Brave Browser at /Applications/Brave Browser.app
#   - PERPLEXITY_SESSION_COOKIE in .env (see below)
#
# Getting your session cookie:
#   1. Log in to perplexity.ai in Brave (or any browser)
#   2. Press F12 → Application tab → Cookies → https://www.perplexity.ai
#   3. Find "__Secure-next-auth.session-token", copy its Value
#   4. Add to .env:  PERPLEXITY_SESSION_COOKIE="<paste here>"
#
# Usage:
#   ./sync-perplexity.sh                   # upload all skills
#   ./sync-perplexity.sh --changed-only    # only git-modified skills
#   ./sync-perplexity.sh octane-rust-axum  # one specific skill
# =============================================================================
set -euo pipefail

SKILLS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Playwright is installed persistently here (survives between runs)
PLAYWRIGHT_HOME="$SKILLS_DIR/.playwright"

CHANGED_ONLY=0
SPECIFIC_SKILL=""

# Load .env if present
if [ -f "$SKILLS_DIR/.env" ]; then
  set -a; source "$SKILLS_DIR/.env"; set +a
fi

# Validate credentials
if [ -z "${PERPLEXITY_SESSION_COOKIE:-}" ]; then
  echo ""
  echo "Error: PERPLEXITY_SESSION_COOKIE is not set."
  echo ""
  echo "  1. Log in to perplexity.ai in Chrome/Edge (Google login is fine)"
  echo "  2. Press F12 → Application → Cookies → https://www.perplexity.ai"
  echo "  3. Find '__Secure-next-auth.session-token', copy the Value"
  echo "  4. Add to .env:  PERPLEXITY_SESSION_COOKIE=\"<value>\""
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
  mapfile -t SKILLS_TO_UPLOAD < <(find "$SKILLS_DIR" -maxdepth 1 -mindepth 1 -type d ! -name ".playwright" ! -name ".git" | sort)
fi

# Build zip files into a PERSISTENT temp directory (not cleaned up until after node runs)
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
echo "║         Perplexity Computer — Skills Sync                    ║"
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
UPLOAD_SCRIPT="$PLAYWRIGHT_HOME/upload.mjs"
cat > "$UPLOAD_SCRIPT" << 'JSEOF'
import { chromium } from 'playwright';
import { basename } from 'path';
import { existsSync } from 'fs';

const SESSION_COOKIE = process.env.PERPLEXITY_SESSION_COOKIE;
const SKILL_ZIPS = process.env.SKILL_ZIPS.split('\n').filter(Boolean);
const SKILLS_URL = 'https://www.perplexity.ai/account/org/skills';

if (!SESSION_COOKIE) {
  console.error('Error: PERPLEXITY_SESSION_COOKIE not set');
  process.exit(1);
}

// Use the real Brave binary so Cloudflare sees a genuine browser fingerprint.
// Playwright's bundled headless Chromium is trivially detected and blocked.
const BRAVE = '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser';
const hasBrave = existsSync(BRAVE);

const browser = await chromium.launch({
  headless: false,           // visible window — eliminates headless detection signals
  executablePath: hasBrave ? BRAVE : undefined,
  args: [
    '--no-first-run',
    '--no-default-browser-check',
    '--window-size=1280,900',
    '--disable-blink-features=AutomationControlled',  // hides navigator.webdriver
  ],
});
const context = await browser.newContext({
  // Match Brave's real user agent on macOS arm64
  userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
});

await context.addCookies([{
  name: '__Secure-next-auth.session-token',
  value: SESSION_COOKIE,
  domain: 'www.perplexity.ai',
  path: '/',
  httpOnly: true,
  secure: true,
  sameSite: 'Lax',
}]);

const page = await context.newPage();

// Navigate to org skills page (direct "Upload skill" button — no dropdown)
console.log('  Navigating to org skills page...');
await page.goto(SKILLS_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
await page.waitForTimeout(3000);

const currentUrl = page.url();
if (currentUrl.includes('/login') || currentUrl.includes('sign-in')) {
  console.error('\n  Error: Session cookie is invalid or expired.');
  console.error('  Please grab a fresh cookie from your browser (F12 → Application → Cookies)');
  await browser.close();
  process.exit(1);
}

console.log(`  Authenticated. Current URL: ${currentUrl}`);
console.log('');

let uploaded = 0;
let updated = 0;
let failed = 0;

// Wait for the page to fully settle after navigation (SPA needs networkidle)
async function waitForPageReady() {
  await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
  // Confirm the "Upload skill" button is present before proceeding
  await page.locator('button').filter({ hasText: /upload skill/i }).first()
    .waitFor({ state: 'visible', timeout: 15000 });
}

// Click the drop-zone and intercept the native file chooser.
// This is the correct approach for React-controlled file inputs:
// React's onChange fires from the file-chooser event, NOT from direct DOM mutations.
async function uploadViaFileChooser(zipPath) {
  const dropZone = page.locator('[role="button"]')
    .filter({ hasText: /drag your file here|click to upload/i })
    .first();

  await dropZone.waitFor({ state: 'visible', timeout: 10000 });

  // Intercept the file chooser before clicking so the OS dialog never opens
  const [fileChooser] = await Promise.all([
    page.waitForEvent('filechooser', { timeout: 8000 }),
    dropZone.click(),
  ]);
  await fileChooser.setFiles(zipPath);

  // Wait for the modal to close (drop-zone disappears = upload succeeded)
  // or for an error message to appear. Allow up to 30s for network upload.
  try {
    await dropZone.waitFor({ state: 'hidden', timeout: 30000 });
    return { ok: true };
  } catch {
    const errorText = await page.locator('[role="dialog"], [role="modal"], main')
      .filter({ hasText: /error|invalid|failed/i })
      .first()
      .textContent({ timeout: 2000 })
      .catch(() => null);
    return { ok: false, reason: errorText ?? 'modal still open after 30s' };
  }
}

// Check whether a skill already exists by searching the list.
async function findExistingSkill(skillName) {
  const searchInput = page.locator('input[placeholder*="Search"]').first();
  const hasSearch = await searchInput.isVisible({ timeout: 3000 }).catch(() => false);

  if (hasSearch) {
    await searchInput.fill(skillName);
    await page.waitForTimeout(1200);
  }

  // A skill row contains the slug as its primary label — use a broad text match
  // after searching so the list is already filtered
  const rows = page.locator('div, li, article').filter({ hasText: skillName });
  const count = await rows.count();

  if (hasSearch) {
    await searchInput.clear();
    await page.waitForTimeout(600);
  }

  return count > 0;
}

// Open the upload modal for an existing skill via its ⋮ menu.
// Returns true when the update/upload menu item was found and clicked.
async function openUpdateModal(skillName) {
  const skillRow = page.locator('div, li, article')
    .filter({ hasText: skillName })
    .first();

  // Radix dropdown trigger — the last button in the row
  const menuTrigger = skillRow.locator('button[aria-haspopup="menu"], button').last();
  await menuTrigger.waitFor({ state: 'visible', timeout: 8000 });
  await menuTrigger.click();
  await page.waitForTimeout(600);

  const updateItem = page.locator('[role="menuitem"]')
    .filter({ hasText: /update|upload|replace|edit/i })
    .first();
  const found = await updateItem.isVisible({ timeout: 4000 }).catch(() => false);

  if (!found) {
    await page.keyboard.press('Escape');
    await page.waitForTimeout(400);
    return false;
  }

  await updateItem.click();
  await page.waitForTimeout(800);
  return true;
}

// Open the upload modal for a brand-new skill.
async function openCreateModal() {
  const uploadBtn = page.locator('button').filter({ hasText: /upload skill/i }).first();
  await uploadBtn.waitFor({ state: 'visible', timeout: 10000 });
  await uploadBtn.click();
  await page.waitForTimeout(800);
}

for (const zipPath of SKILL_ZIPS) {
  const skillName = basename(zipPath, '.zip');
  process.stdout.write(`  Syncing ${skillName}... `);

  try {
    // Navigate fresh for every skill so the list is fully loaded
    if (SKILL_ZIPS.indexOf(zipPath) > 0) {
      await page.goto(SKILLS_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    }
    await waitForPageReady();

    const exists = await findExistingSkill(skillName);

    if (exists) {
      const opened = await openUpdateModal(skillName);
      if (!opened) {
        console.log('SKIPPED (no update option in menu — skill exists but cannot be updated)');
        continue;
      }
    } else {
      await openCreateModal();
    }

    const result = await uploadViaFileChooser(zipPath);

    // Dismiss any remaining modal
    await page.keyboard.press('Escape').catch(() => {});
    await page.waitForTimeout(500);

    if (result.ok) {
      if (exists) { console.log('updated'); updated++; }
      else        { console.log('uploaded'); uploaded++; }
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
PERPLEXITY_SESSION_COOKIE="${PERPLEXITY_SESSION_COOKIE}" \
PLAYWRIGHT_BROWSERS_PATH="$PLAYWRIGHT_HOME/browsers" \
node "$UPLOAD_SCRIPT" 2>&1

EXIT_CODE=$?

# Clean up zips
rm -rf "$ZIP_DIR"

exit $EXIT_CODE