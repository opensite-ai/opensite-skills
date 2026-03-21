---
name: automation-builder
description: >
  Browser and system automation patterns for engineers building scripts that interact
  with Cloudflare-protected SPAs, React file upload flows, and session-authenticated
  dashboards. Also covers media automation tool selection (ffmpeg, ImageMagick, Sharp)
  and shell script best practices. Use when scripting any headless or headed browser
  interaction, file upload pipeline, or batch media processing task.
---

# Automation Builder

## Tool Selection Framework

Before writing any automation code, choose the simplest tool that satisfies the constraint.

| Task | Best Tool | Why |
|------|-----------|-----|
| Upload to Cloudflare-protected SPA | Playwright + real browser binary | Headless Chromium is fingerprinted and blocked |
| Scrape publicly accessible HTML | `curl` + `grep`/`jq` | Zero overhead, no browser needed |
| Interact with a documented REST API | `curl`, axios, or SDK | API > scraping, always |
| Batch image resize/format conversion | Sharp (Node.js) or ImageMagick | Sharp: fast, Node-native; ImageMagick: richer CLI |
| Video transcoding, thumbnails, clips | `ffmpeg` | Industry standard, no JS overhead |
| Complex multi-step browser flows | Playwright | Best selectors, TypeScript support, `filechooser` API |
| Quick one-off read-only DOM check | Puppeteer | Lighter than Playwright for read-only tasks |

**Decision rule**: API → shell tools → headless browser → real browser. Each step up adds complexity and brittleness. Never reach for a browser when `curl` works.

---

## Real Browser vs. Headless: Why It Matters

Cloudflare Bot Management, Akamai Bot Manager, and similar services fingerprint browsers at multiple layers simultaneously:

| Detection Signal | Headless Chromium | Real Brave/Chrome |
|-----------------|-------------------|-------------------|
| `navigator.webdriver` | `true` | `undefined` |
| Chrome DevTools Protocol | Port open, detectable | Closed |
| Canvas fingerprint | Distinct from retail Chrome | Matches real browser |
| User-Agent string | Playwright's bundled version | Real browser version |
| TLS/JA3 fingerprint | Differs from retail Chrome | Matches retail Chrome |

Playwright's `--headless=new` mode is still fingerprinted. When the target uses any serious bot protection, use a real browser binary in visible window mode.

### Launching with a Real Browser Binary

```typescript
import { chromium } from 'playwright';
import { existsSync } from 'fs';

const BRAVE  = '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser';
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const REAL_BROWSER = existsSync(BRAVE) ? BRAVE : existsSync(CHROME) ? CHROME : undefined;

const browser = await chromium.launch({
  headless: false,              // Visible window eliminates headless signals
  executablePath: REAL_BROWSER, // Real binary, not Playwright's bundled Chromium
  args: [
    '--no-first-run',
    '--no-default-browser-check',
    '--window-size=1280,900',
    '--disable-blink-features=AutomationControlled', // Hides navigator.webdriver
  ],
});

// Always create a fresh context — not the user's existing profile
const context = await browser.newContext({
  // Match the actual UA of the binary you're using
  userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
});
```

A fresh browser context (not the user's existing Brave profile) keeps personal sessions clean and makes automation reproducible.

---

## Session Cookie Injection

Internal tools and authenticated dashboards often use session cookies. Inject the cookie rather than automating the login flow — login pages frequently have CAPTCHAs, 2FA, or rate limits.

```typescript
await context.addCookies([{
  name: '__Secure-next-auth.session-token', // Cookie name from DevTools
  value: process.env.SESSION_COOKIE!,       // Never hardcode; always read from env
  domain: 'www.example.com',               // Must match exactly
  path: '/',
  httpOnly: true,
  secure: true,
  sameSite: 'Lax',
}]);
```

**Extracting a session cookie:**
1. Log in normally in Chrome or Brave
2. `F12` → Application → Cookies → your domain
3. Copy the session cookie Value
4. Add to `.env` (always gitignore `.env`)

**Detecting expiry early** — validate immediately after navigation:

```typescript
const page = await context.newPage();
await page.goto(TARGET_URL, { waitUntil: 'domcontentloaded' });

const url = page.url();
if (url.includes('/login') || url.includes('/sign-in') || url.includes('/auth')) {
  throw new Error('Session cookie expired — grab a fresh one from DevTools and update .env');
}
```

---

## SPA Readiness Patterns

SPAs render asynchronously. Using `page.waitForTimeout()` creates tests that are simultaneously too slow (when the app is fast) and too brittle (when the network is slow). Always wait for a specific signal instead.

### Initial Page Load

```typescript
// networkidle: no pending requests for 500ms — reliable for SPA initial load
await page.goto(URL, { waitUntil: 'networkidle', timeout: 30_000 });
```

`networkidle` can hang indefinitely on apps with WebSocket connections or polling. Always apply a `.catch()` and fall through to element-based waiting:

```typescript
await page.waitForLoadState('networkidle', { timeout: 15_000 }).catch(() => {
  // Acceptable — some SPAs never reach networkidle; check for element directly
});
await page.locator('button').filter({ hasText: /upload/i })
  .waitFor({ state: 'visible', timeout: 10_000 });
```

### Hydration Race Condition

React apps may paint a button in the DOM before hydration attaches event listeners. A click on a not-yet-hydrated button silently does nothing.

```typescript
// Wait for the element, then optionally add a small hydration buffer
await page.locator('[data-testid="upload-btn"]').waitFor({ state: 'visible' });

// If the button exists but clicks silently fail, you hit hydration timing.
// A 500ms buffer after networkidle is the pragmatic fix — document why:
await page.waitForTimeout(500); // hydration buffer: React attaches handlers after paint
```

### Element Disappearance as Success Signal

When a form or modal closes on success, wait for it to disappear rather than waiting for a success toast (toasts are often ephemeral and race-prone):

```typescript
const dropZone = page.locator('[role="button"]').filter({ hasText: /drag.*upload/i });
await dropZone.waitFor({ state: 'visible', timeout: 10_000 });

// ... trigger upload ...

// Success = modal closes = dropZone gone
await dropZone.waitFor({ state: 'hidden', timeout: 30_000 });
```

---

## React File Upload: The `filechooser` Pattern

React controls file inputs via synthetic events. Setting `input.files` directly via JavaScript DOM mutation does **not** fire React's `onChange` — the upload silently does nothing.

```typescript
// ❌ Wrong — bypasses React's synthetic event system
const input = page.locator('input[type="file"]');
await input.setInputFiles('/path/to/file.zip'); // React never sees this

// ✅ Correct — intercepts the OS file picker that React opens
const dropZone = page.locator('[role="button"]')
  .filter({ hasText: /drag your file here|click to upload/i })
  .first();

await dropZone.waitFor({ state: 'visible', timeout: 10_000 });

// waitForEvent must be registered BEFORE the click — use Promise.all
const [fileChooser] = await Promise.all([
  page.waitForEvent('filechooser', { timeout: 8_000 }),
  dropZone.click(), // This triggers the OS file chooser
]);

// setFiles on the intercepted chooser fires React's onChange correctly
await fileChooser.setFiles('/path/to/file.zip');
```

**Why `Promise.all`?** The `waitForEvent` listener must be registered before the click fires. If you `await click()` first, the `filechooser` event fires and is lost before the `waitForEvent` resolves. `Promise.all` starts both operations atomically.

### Handling Replacement Confirmation Dialogs

Some SPAs show a "Replace existing?" dialog after upload:

```typescript
const confirmBtn = page.locator('[role="dialog"] button')
  .filter({ hasText: /replace|upload and replace|confirm/i });

const hasConfirm = await confirmBtn.isVisible({ timeout: 3_000 }).catch(() => false);
if (hasConfirm) {
  await confirmBtn.click();
  await page.waitForTimeout(500); // dialog animation
}
```

---

## Automation Error Handling

### Screenshot on Failure

```typescript
async function withScreenshotOnError(
  page: Page,
  label: string,
  fn: () => Promise<void>,
): Promise<void> {
  try {
    await fn();
  } catch (err) {
    const path = `./debug-${label}-${Date.now()}.png`;
    await page.screenshot({ path, fullPage: true });
    console.error(`Screenshot saved: ${path}`);
    throw err;
  }
}
```

### Escape Key Recovery

Always dismiss stuck modals before moving to the next task:

```typescript
await page.keyboard.press('Escape').catch(() => {});
await page.waitForTimeout(400); // modal animation
```

### Error Classification in Loops

```typescript
let failed = 0;
for (const item of items) {
  try {
    await processItem(page, item);
  } catch (err) {
    const msg = (err as Error).message.split('\n')[0].substring(0, 120);
    console.log(`FAILED ${item.name}: ${msg}`);
    await page.keyboard.press('Escape').catch(() => {}); // recover
    failed++;
  }
}
process.exit(failed > 0 ? 1 : 0);
```

---

## Shell Script Automation Patterns

### Safety Header

```bash
#!/usr/bin/env bash
set -euo pipefail
# -e: exit immediately on non-zero exit code
# -u: treat unset variables as an error (catches typos like $DIIR)
# -o pipefail: a pipeline fails if any command in it fails
```

### Temp Directory with Guaranteed Cleanup

```bash
WORK_DIR=$(mktemp -d)
trap 'rm -rf "$WORK_DIR"' EXIT  # Always runs, even if the script errors out

# Use WORK_DIR for all intermediate artifacts
zip -qr "$WORK_DIR/bundle.zip" ./src/
```

### Safe Array Handling

```bash
# mapfile (bash 4+) handles filenames with spaces correctly
mapfile -t FILES < <(find ./skills -maxdepth 2 -name "SKILL.md" | sort)

for f in "${FILES[@]:-}"; do
  [ -n "$f" ] || continue  # Skip empty elements from empty arrays
  echo "Processing: $f"
done
```

### Persistent vs. Temporary Directories

```bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Persistent: survives between runs (compiled assets, node_modules, caches)
CACHE_DIR="$SCRIPT_DIR/.cache"
mkdir -p "$CACHE_DIR"

# Temporary: cleaned up after every run
TEMP_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_DIR"' EXIT
```

### Loading .env Safely

```bash
if [ -f "$SCRIPT_DIR/.env" ]; then
  set -a; source "$SCRIPT_DIR/.env"; set +a
fi

if [ -z "${SESSION_COOKIE:-}" ]; then
  echo "Error: SESSION_COOKIE is not set. Add it to .env"
  exit 1
fi
```

---

## Media Automation: Tool Selection

### ffmpeg — Video and Audio

Use for: transcoding, thumbnail extraction, format conversion, clip trimming, audio extraction.

```bash
# Extract thumbnail at 5 seconds
ffmpeg -i input.mp4 -ss 00:00:05 -frames:v 1 thumbnail.jpg

# Convert to web-optimized H.264
ffmpeg -i input.mov \
  -c:v libx264 -crf 23 -preset fast \
  -c:a aac -b:a 128k \
  -movflags +faststart \
  output.mp4

# Batch convert .mov → .mp4
for f in *.mov; do
  ffmpeg -i "$f" -c:v libx264 -crf 23 -preset fast "${f%.mov}.mp4"
done

# Extract audio
ffmpeg -i input.mp4 -q:a 0 -map a output.mp3
```

### ImageMagick — Batch Image Processing

Use for: bulk format conversion, compositing, text overlays, complex color operations, PDF rasterization.

```bash
# Resize all JPEGs to max 1200px wide, in-place
mogrify -resize '1200x>' -quality 85 *.jpg

# Convert PNG to WebP
convert input.png -quality 80 output.webp

# Strip EXIF metadata (reduces size, removes GPS)
mogrify -strip *.jpg

# Add watermark in bottom-right corner
convert base.jpg -gravity SouthEast -geometry +10+10 watermark.png -composite output.jpg
```

### Sharp — Node.js Real-Time Image Processing

Use for: server-side transforms in Node.js/TypeScript, dynamic resize on upload, generating format variants.

```typescript
import sharp from 'sharp';

// Generate responsive format variants from an upload buffer
async function generateVariants(input: Buffer, outputDir: string): Promise<void> {
  const sizes = [
    { name: 'sm',   width: 640  },
    { name: 'md',   width: 1024 },
    { name: 'lg',   width: 1536 },
    { name: 'full', width: 2560 },
  ];

  await Promise.all(
    sizes.flatMap(({ name, width }) => [
      sharp(input)
        .resize(width, null, { withoutEnlargement: true })
        .webp({ quality: 80 })
        .toFile(`${outputDir}/${name}.webp`),
      sharp(input)
        .resize(width, null, { withoutEnlargement: true })
        .avif({ quality: 60 })
        .toFile(`${outputDir}/${name}.avif`),
    ]),
  );
}

// Center-crop to square
const cropped = await sharp(input)
  .resize(400, 400, { fit: 'cover', position: 'center' })
  .jpeg({ quality: 85, progressive: true })
  .toBuffer();
```

**Sharp vs. ImageMagick**: Sharp is 10–50x faster for Node.js services (libvips underneath). Use Sharp for real-time server-side processing. Use ImageMagick for rich batch CLI workflows where its broader format support matters.

---

## Complete Example: Cloudflare-Protected SPA Upload

```typescript
// scripts/upload-protected.ts
import { chromium, type Page } from 'playwright';
import { existsSync } from 'fs';
import { basename } from 'path';
import 'dotenv/config';

const BRAVE = '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser';
const { SESSION_COOKIE, TARGET_URL } = process.env;

if (!SESSION_COOKIE || !TARGET_URL) {
  throw new Error('SESSION_COOKIE and TARGET_URL must be set in .env');
}

async function upload(page: Page, filePath: string): Promise<boolean> {
  await page.goto(TARGET_URL!, { waitUntil: 'domcontentloaded', timeout: 30_000 });
  await page.waitForLoadState('networkidle', { timeout: 15_000 }).catch(() => {});

  const uploadBtn = page.locator('button, [role="button"]')
    .filter({ hasText: /upload|add file/i })
    .first();
  await uploadBtn.waitFor({ state: 'visible', timeout: 10_000 });

  const [fileChooser] = await Promise.all([
    page.waitForEvent('filechooser', { timeout: 8_000 }),
    uploadBtn.click(),
  ]);
  await fileChooser.setFiles(filePath);

  // Handle optional replacement confirmation
  const confirmBtn = page.locator('[role="dialog"] button')
    .filter({ hasText: /replace|confirm/i });
  if (await confirmBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
    await confirmBtn.click();
  }

  try {
    await uploadBtn.waitFor({ state: 'hidden', timeout: 30_000 });
    return true;
  } catch {
    await page.screenshot({ path: `./debug-${Date.now()}.png`, fullPage: true });
    return false;
  }
}

async function main() {
  const filePath = process.argv[2];
  if (!filePath || !existsSync(filePath)) {
    throw new Error(`File not found: ${filePath}`);
  }

  const browser = await chromium.launch({
    headless: false,
    executablePath: existsSync(BRAVE) ? BRAVE : undefined,
    args: ['--no-first-run', '--disable-blink-features=AutomationControlled'],
  });

  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
  });

  await context.addCookies([{
    name: 'session',
    value: SESSION_COOKIE!,
    domain: new URL(TARGET_URL!).hostname,
    path: '/',
    httpOnly: true,
    secure: true,
    sameSite: 'Lax',
  }]);

  const page = await context.newPage();

  console.log(`Uploading ${basename(filePath)}...`);
  const ok = await upload(page, filePath);

  await browser.close();
  console.log(ok ? 'Done.' : 'FAILED — see debug screenshot.');
  process.exit(ok ? 0 : 1);
}

main().catch(console.error);
```

---

## Anti-Patterns

| Anti-Pattern | Why It Fails | Fix |
|---|---|---|
| `page.waitForTimeout(3000)` | Flaky on fast machines, fails on slow ones | Wait for a specific element state |
| Setting `input.files` via DOM | React synthetic events don't fire | Use `page.waitForEvent('filechooser')` |
| Playwright bundled Chromium against Cloudflare | Fingerprinted and blocked | Use real Brave/Chrome binary, headed mode |
| Automating login instead of injecting cookies | CAPTCHAs, 2FA, rate limits | Inject session cookie from DevTools |
| Scraping when an API exists | Brittle to UI changes | Use the API |
| Not cleaning up temp files | Disk fills up; secrets in temp dirs | `trap 'rm -rf "$WORK_DIR"' EXIT` |
| Hardcoding session cookies in scripts | Secrets in version history | Always read from env vars / `.env` |
| No error recovery between iterations | One failure kills the whole batch | Catch per-item, recover with Escape key |
