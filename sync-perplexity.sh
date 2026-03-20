#!/usr/bin/env bash
# =============================================================================
# OpenSite / Toastability — Perplexity Computer Skills Sync
#
# Perplexity has no public REST API for skill uploads — the upload UI is
# protected by Cloudflare and requires a real browser session.
# This script uses Playwright (headless Chromium) to upload via the UI.
#
# Requirements:
#   - Node.js 18+
#   - PERPLEXITY_SESSION_COOKIE in .env (see below)
#
# Getting your session cookie:
#   1. Log in to perplexity.ai in Chrome/Edge (via Google is fine)
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
  npm init -y > /dev/null 2>&1
  npm install playwright > /dev/null 2>&1
  node node_modules/.bin/playwright install chromium 2>&1 | grep -v "^$" || true
  cd "$SKILLS_DIR"
  echo "  Playwright ready."
  echo ""
fi

# ── Write upload script ──────────────────────────────────────────────────────
UPLOAD_SCRIPT="$PLAYWRIGHT_HOME/upload.mjs"
cat > "$UPLOAD_SCRIPT" << 'JSEOF'
import { chromium } from 'playwright';
import { basename } from 'path';

const SESSION_COOKIE = process.env.PERPLEXITY_SESSION_COOKIE;
const SKILL_ZIPS = process.env.SKILL_ZIPS.split('\n').filter(Boolean);

if (!SESSION_COOKIE) {
  console.error('Error: PERPLEXITY_SESSION_COOKIE not set');
  process.exit(1);
}

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
});

// Inject session cookie
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

// Navigate to skills page and verify we're logged in
console.log('  Navigating to skills page...');
await page.goto('https://www.perplexity.ai/computer/skills', { waitUntil: 'domcontentloaded', timeout: 30000 });
await page.waitForTimeout(2000);

// Check if we got redirected to login (session cookie invalid/expired)
const currentUrl = page.url();
if (currentUrl.includes('/login') || currentUrl.includes('sign-in')) {
  console.error('');
  console.error('  Error: Session cookie is invalid or expired.');
  console.error('  Please grab a fresh cookie from your browser (F12 → Application → Cookies)');
  await browser.close();
  process.exit(1);
}

console.log(`  Authenticated. Current URL: ${currentUrl}`);
console.log('');

let uploaded = 0;
let failed = 0;

for (const zipPath of SKILL_ZIPS) {
  const skillName = basename(zipPath, '.zip');
  process.stdout.write(`  Uploading ${skillName}... `);

  try {
    // Re-navigate to skills page for each upload (avoids stale state)
    if (SKILL_ZIPS.indexOf(zipPath) > 0) {
      await page.goto('https://www.perplexity.ai/computer/skills', { waitUntil: 'domcontentloaded', timeout: 30000 });
      await page.waitForTimeout(1500);
    }

    // Find and click "Create skill" button (try multiple selectors)
    const createBtn = page.locator('button').filter({ hasText: /create skill/i }).first();
    await createBtn.waitFor({ timeout: 10000 });
    await createBtn.click();
    await page.waitForTimeout(800);

    // Click "Upload a skill" option
    const uploadOption = page.locator('*').filter({ hasText: /upload a skill/i }).last();
    await uploadOption.waitFor({ timeout: 5000 });
    await uploadOption.click();
    await page.waitForTimeout(800);

    // Handle file upload — wait for file chooser
    const [fileChooser] = await Promise.all([
      page.waitForEvent('filechooser', { timeout: 8000 }),
      // Try clicking the visible upload area
      page.locator('input[type="file"]').first().click({ force: true }).catch(() =>
        page.locator('[class*="upload"], [class*="drop-zone"], [class*="dropzone"]').first().click()
      ),
    ]);
    await fileChooser.setFiles(zipPath);
    await page.waitForTimeout(3000);

    // Look for success or error
    const successIndicator = await page.locator('*').filter({ hasText: /success|uploaded|created/i }).first().isVisible().catch(() => false);
    const errorIndicator = await page.locator('*').filter({ hasText: /error|invalid|failed/i }).first().isVisible().catch(() => false);

    // Close modal
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);

    if (errorIndicator && !successIndicator) {
      console.log('FAILED (error shown in UI)');
      failed++;
    } else {
      console.log('OK');
      uploaded++;
    }
  } catch (err) {
    const msg = err.message.split('\n')[0].substring(0, 80);
    console.log(`FAILED: ${msg}`);
    await page.keyboard.press('Escape').catch(() => {});
    failed++;
  }
}

await browser.close();

// Clean up zips
console.log('');
console.log(`  Results: ${uploaded} uploaded, ${failed} failed`);
if (uploaded > 0) {
  console.log('  View at: https://www.perplexity.ai/computer/skills');
}
process.exit(failed > 0 ? 1 : 0);
JSEOF

# ── Run the upload ────────────────────────────────────────────────────────────
SKILL_ZIPS_LIST=$(printf '%s\n' "${SKILL_ZIPS[@]}")

SKILL_ZIPS="$SKILL_ZIPS_LIST" \
PERPLEXITY_SESSION_COOKIE="${PERPLEXITY_SESSION_COOKIE}" \
PLAYWRIGHT_BROWSERS_PATH="$PLAYWRIGHT_HOME/browsers" \
node --experimental-vm-modules "$UPLOAD_SCRIPT" 2>&1

EXIT_CODE=$?

# Clean up zips
rm -rf "$ZIP_DIR"

exit $EXIT_CODE