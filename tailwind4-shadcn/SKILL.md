---
name: tailwind4-shadcn
description: >
  Tailwind CSS v4 and ShadCN UI patterns for OpenSite. Use when working with
  Tailwind CSS v4 configuration, CSS variables, ShadCN component customization,
  theming, the style dashboard (inspired by tweakcn), or migrating components
  from Tailwind v3 to v4. Also applies to the v0-clone / Semantic UI Builder
  dashboard.
compatibility: >
  Requires Tailwind CSS v4, Node.js, and a React or Next.js codebase using the
  ShadCN stack.
metadata:
  opensite-category: frontend
  opensite-scope: ui
  opensite-visibility: public
---
# Tailwind CSS v4 + ShadCN Skill

## Skill Resources
- Activation and cross-agent notes: [references/activation.md](references/activation.md)
- Template: [templates/theme-change-brief.md](templates/theme-change-brief.md)

You are working in an OpenSite application that uses Tailwind CSS v4 with ShadCN UI. The `opensite-ai/ui-library` showcase, `Toastability/app` (dashtrack-cms), and all UI-related repos use this stack.

## Tailwind CSS v4 Key Changes

Tailwind v4 is a complete rewrite. The most important changes from v3:

### CSS-First Configuration (No More tailwind.config.js)

In Tailwind v4, configuration lives in CSS, not JavaScript:

```css
/* src/app/globals.css */
@import "tailwindcss";

/* Theme customization using @theme directive */
@theme {
  --color-primary: oklch(0.6 0.2 240);
  --color-primary-foreground: oklch(0.98 0 0);
  --color-secondary: oklch(0.96 0.01 240);
  --color-secondary-foreground: oklch(0.2 0.02 240);
  --color-background: oklch(1 0 0);
  --color-foreground: oklch(0.15 0.01 240);
  --color-muted: oklch(0.96 0.01 240);
  --color-muted-foreground: oklch(0.55 0.02 240);
  --color-accent: oklch(0.96 0.01 240);
  --color-accent-foreground: oklch(0.2 0.02 240);
  --color-destructive: oklch(0.6 0.22 22);
  --color-border: oklch(0.9 0.01 240);
  --color-input: oklch(0.9 0.01 240);
  --color-ring: oklch(0.6 0.2 240);
  --color-card: oklch(1 0 0);
  --color-card-foreground: oklch(0.15 0.01 240);
  --color-popover: oklch(1 0 0);
  --color-popover-foreground: oklch(0.15 0.01 240);

  /* Typography */
  --font-sans: "Inter", system-ui, sans-serif;
  --font-mono: "JetBrains Mono", "Fira Code", monospace;

  /* Border radius */
  --radius: 0.5rem;
  --radius-sm: calc(var(--radius) - 4px);
  --radius-md: calc(var(--radius) - 2px);
  --radius-lg: var(--radius);
  --radius-xl: calc(var(--radius) + 4px);
}

/* Dark mode overrides */
@media (prefers-color-scheme: dark) {
  @theme {
    --color-background: oklch(0.1 0.01 240);
    --color-foreground: oklch(0.95 0 0);
    /* ... */
  }
}

/* Or use class-based dark mode */
.dark {
  --color-background: oklch(0.1 0.01 240);
  --color-foreground: oklch(0.95 0 0);
}
```

### PostCSS Configuration for v4

```javascript
// postcss.config.mjs
export default {
  plugins: {
    "@tailwindcss/postcss": {},
  },
}
```

### v4 Utility Differences

| v3 | v4 |
|----|-----|
| `bg-white` | `bg-background` (CSS var) |
| `text-gray-900` | `text-foreground` |
| `text-gray-500` | `text-muted-foreground` |
| `divide-gray-200` | `divide-border` |
| `ring-blue-500` | `ring-ring` |
| `rounded-lg` | `rounded-lg` (same) |
| `shadow-sm` | `shadow-xs` (renamed) |
| `shadow` | `shadow-sm` (renamed) |
| `shadow-md` | `shadow-md` (same) |

### Arbitrary Values Still Work

```html
<!-- v4 still supports arbitrary values -->
<div class="grid-cols-[1fr_2fr] gap-[1.5rem] bg-[oklch(0.95_0_0)]">
```

## ShadCN UI Configuration

The `components.json` schema controls ShadCN behavior. For ui-library:

```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "new-york",
  "rsc": true,
  "tsx": true,
  "tailwind": {
    "config": "",
    "css": "src/app/globals.css",
    "baseColor": "neutral",
    "cssVariables": true,
    "prefix": ""
  },
  "iconLibrary": "lucide",
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "hooks": "@/hooks"
  }
}
```

## Adding a New ShadCN Component

```bash
# Add directly from the ShadCN registry
npx shadcn@latest add button
npx shadcn@latest add card
npx shadcn@latest add dialog

# From Aceternity UI
npx shadcn@latest add "@aceternity/sparkles"

# From shadcnblocks (requires API key in env)
npx shadcn@latest add "@shadcnblocks/hero-with-mockup"
```

## Customizing ShadCN Components

Never modify the base ShadCN component file directly if you can avoid it. Prefer extending via variants:

```typescript
// Extending with additional variants
import { cva } from "class-variance-authority"

// Extend existing buttonVariants
const extendedButtonVariants = cva(undefined, {
  variants: {
    variant: {
      // Add new variants
      brand: "bg-brand text-brand-foreground hover:bg-brand/90",
      subtle: "bg-muted/40 text-foreground hover:bg-muted/60",
    }
  }
})

// Or create a wrapper component
export function BrandButton({ className, ...props }: ButtonProps) {
  return <Button variant="brand" className={cn("font-semibold", className)} {...props} />
}
```

## tweakcn-Inspired Style Dashboard Patterns

The `opensite-ai/tweakcn` fork is the reference for the CMS style dashboard. Key patterns:

### CSS Variable Export/Import

```typescript
// Style dashboard generates CSS like this
function generateThemeCSS(theme: ThemeConfig): string {
  const vars = Object.entries(theme.colors).map(([key, value]) => {
    return `  --color-${key}: ${value};`
  }).join("\n")

  return `@theme {\n${vars}\n}`
}

// Preview live in browser via style injection
function applyThemePreview(theme: ThemeConfig) {
  let style = document.getElementById("theme-preview")
  if (!style) {
    style = document.createElement("style")
    style.id = "theme-preview"
    document.head.appendChild(style)
  }
  style.textContent = generateThemeCSS(theme)
}
```

### Theme Presets

Store theme presets as JSON:

```typescript
interface ThemePreset {
  id: string
  name: string
  colors: {
    primary: string
    secondary: string
    background: string
    foreground: string
    accent: string
    muted: string
    border: string
    // ... all CSS vars
  }
  fonts: {
    sans: string
    mono: string
  }
  radius: string
}
```

## v0-Clone Patterns (Semantic UI Builder)

The `Toastability/v0-clone` fork informs the Semantic UI Builder dashboard. Key patterns for the AI-powered component generator:

```typescript
// Component generation prompt schema
interface ComponentGenerationRequest {
  description: string          // Natural language description
  category: ComponentCategory  // hero | features | testimonials | etc.
  skinId: string              // Which skin/theme to apply
  constraints?: {
    maxWidth?: number
    colorScheme?: "light" | "dark" | "auto"
    animationLevel?: "none" | "subtle" | "full"
  }
}

// The Octane semantic_ui_agent.rs endpoint receives this and returns:
interface GeneratedComponent {
  blockId: string           // References opensite-ui block registry
  props: Record<string, unknown>
  tailwindClasses?: string  // Any additional custom classes
  reasoning: string         // Why this block was selected
}
```

## Dark Mode Implementation

All OpenSite components must support both light and dark modes via the `next-themes` library:

```typescript
// In the app layout
import { ThemeProvider } from "next-themes"

export default function RootLayout({ children }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          {children}
        </ThemeProvider>
      </body>
    </html>
  )
}

// In components — use the theme hook
import { useTheme } from "next-themes"

function ThemeToggle() {
  const { theme, setTheme } = useTheme()
  return (
    <button onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
      Toggle theme
    </button>
  )
}
```

## tw-animate-css Integration

`tw-animate-css` provides Tailwind-compatible animation classes. Use these instead of custom CSS:

```html
<!-- Fade in -->
<div class="animate-fade-in">...</div>

<!-- Slide up -->
<div class="animate-slide-in-up">...</div>

<!-- Scale in -->
<div class="animate-scale-in">...</div>

<!-- Spin with delay -->
<div class="animate-spin delay-150">...</div>
```

## Tailwind v4 Migration Checklist (v3 → v4)

- [ ] Move `tailwind.config.js` theme to `@theme {}` block in CSS
- [ ] Replace `@tailwind base/components/utilities` with `@import "tailwindcss"`
- [ ] Update PostCSS config: `tailwindcss` → `@tailwindcss/postcss`
- [ ] Replace `shadow-sm` with `shadow-xs`, `shadow` with `shadow-sm`
- [ ] Update any JS-based `theme()` calls to use CSS `var(--*)` directly
- [ ] Remove `content` array — v4 uses automatic content detection
- [ ] Update `tw-animate-css` to latest version for v4 compatibility
