---
name: page-speed-library
description: page-speed-* library development patterns. Use when creating or modifying @page-speed/* packages (blocks, router, forms, img, video, skins, maps, icon, lightbox, pdf-viewer, venn-diagram, hooks, social-share, humanizer) or the opensite-hooks and pressable libraries. Covers tsup bundling, peer dependency management, and the sub-library architecture.
---

# Page-Speed Library Development Skill

You are working in the OpenSite `@page-speed/*` sub-library ecosystem — a set of focused, tree-shakable React component packages that compose into `@opensite/ui` and work together to deliver OpenSite's groundbreaking Semantic UI Design System.

## Library Inventory

| Package | Purpose | Key Dependency |
|---------|---------|----------------|
| `@page-speed/blocks` | Pre-compiled Tailwind CSS rendering runtime | `@opensite/ui` |
| `@page-speed/router` | SPA routing for site builder pages | React |
| `@page-speed/forms` | Form components with validation | React Hook Form |
| `@page-speed/img` | Optimized image component | React |
| `@page-speed/video` | Video player/embed component | React |
| `@page-speed/skins` | Theme/skin CSS variable system | CSS |
| `@page-speed/maps` | MapLibre GL map component | maplibre-gl |
| `@page-speed/icon` | SVG icon system | React |
| `@page-speed/lightbox` | Image/media lightbox | React |
| `@page-speed/pdf-viewer` | PDF rendering in browser | React |
| `@page-speed/venn-diagram` | Venn diagram visualization | React |
| `@page-speed/hooks` | Shared React hooks | React |
| `@page-speed/social-share` | Social sharing buttons | React |
| `@page-speed/humanizer` | AI content humanization (in progress) | React |
| `@opensite/hooks` | Core OpenSite hooks library | React |
| `pressable` | Accessible press/click abstraction | React |

## Standard tsup Configuration

Every `@page-speed/*` library uses this base tsup config:

```typescript
// tsup.config.ts
import { defineConfig } from "tsup"

export default defineConfig({
  entry: ["src/index.ts"],
  format: ["cjs", "esm"],
  dts: true,
  splitting: true,
  sourcemap: true,
  clean: true,
  treeshake: true,
  external: [
    "react",
    "react-dom",
    // Add any other peerDeps here
  ],
  esbuildOptions(options) {
    options.banner = {
      js: '"use client"',  // Required for Next.js RSC compatibility
    }
  },
})
```

## Package.json Template

```json
{
  "name": "@page-speed/your-package",
  "version": "0.1.0",
  "description": "Short description of what this package does",
  "main": "./dist/index.js",
  "module": "./dist/index.mjs",
  "types": "./dist/index.d.ts",
  "exports": {
    ".": {
      "import": "./dist/index.mjs",
      "require": "./dist/index.js",
      "types": "./dist/index.d.ts"
    }
  },
  "files": ["dist"],
  "sideEffects": false,
  "peerDependencies": {
    "react": ">=17.0.0",
    "react-dom": ">=17.0.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "tsup": "^8.0.1",
    "typescript": "^5.6.2",
    "vitest": "^3.0.0"
  },
  "scripts": {
    "build": "tsup",
    "dev": "tsup --watch",
    "test": "vitest",
    "type-check": "tsc --noEmit"
  }
}
```

## src/index.ts Export Pattern

Every package exports from a central `src/index.ts`. Keep it flat and explicit:

```typescript
// src/index.ts — named exports only, no barrel re-exports of internal utils
export { YourComponent, type YourComponentProps } from "./components/YourComponent"
export { AnotherComponent, type AnotherComponentProps } from "./components/AnotherComponent"
export { useYourHook } from "./hooks/useYourHook"
export type { SharedType } from "./types"

// Never export internal utilities that consumers shouldn't use
// Never use: export * from "./components"  (breaks tree-shaking)
```

## Component Pattern for Library Components

Library components should be:
1. Framework-agnostic styled (no Tailwind in lib components — let consumer apply classes)
2. Fully typed with exported prop types
3. Accessible (ARIA attributes, keyboard navigation)
4. Forwardable refs when wrapping DOM elements

```typescript
// src/components/YourComponent.tsx
"use client"  // Required for Next.js App Router compatibility

import React from "react"

export interface YourComponentProps
  extends React.HTMLAttributes<HTMLDivElement> {
  /** Primary content */
  children: React.ReactNode
  /** Optional secondary content */
  label?: string
  /** Controlled open state */
  isOpen?: boolean
  /** Callback when state changes */
  onOpenChange?: (open: boolean) => void
}

export const YourComponent = React.forwardRef<HTMLDivElement, YourComponentProps>(
  ({ children, label, isOpen, onOpenChange, className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={className}
        role="region"
        aria-label={label}
        {...props}
      >
        {children}
      </div>
    )
  }
)
YourComponent.displayName = "YourComponent"
```

## @page-speed/img Deep Dive

`@page-speed/img` is used everywhere. Key usage patterns:

```typescript
import { Img, type ImgProps } from "@page-speed/img"

// Basic image with lazy loading
<Img
  src="https://example.com/image.jpg"
  alt="Description"
  width={800}
  height={450}
  className="w-full h-auto"
/>

// Fill container (parent must be relative + overflow-hidden)
<div className="relative h-64 overflow-hidden">
  <Img
    src={imageUrl}
    alt={alt}
    fill
    className="object-cover object-center"
  />
</div>

// With blur placeholder
<Img
  src={src}
  alt={alt}
  width={400}
  height={300}
  placeholder="blur"
  blurDataURL={blurDataUrl}
/>
```

## @page-speed/hooks Usage

```typescript
import {
  useIntersectionObserver,
  useMediaQuery,
  useLocalStorage,
  useDebounce,
  useClickOutside,
} from "@page-speed/hooks"

// Intersection observer for lazy loading/animations
const { ref, isIntersecting } = useIntersectionObserver({
  threshold: 0.1,
  rootMargin: "50px",
})

// Responsive breakpoint detection
const isMobile = useMediaQuery("(max-width: 768px)")
const isTablet = useMediaQuery("(min-width: 768px) and (max-width: 1024px)")

// Click outside detection
const containerRef = useRef<HTMLDivElement>(null)
useClickOutside(containerRef, () => setIsOpen(false))
```

## @opensite/hooks Usage

```typescript
import {
  useSiteContext,
  useComponentRegistry,
  useTheme,
  useSkin,
} from "@opensite/hooks"

// Access the current site context (for site builder components)
const { siteId, accountId, locale } = useSiteContext()

// Access the component registry (for dynamic rendering)
const { getComponent, registerComponent } = useComponentRegistry()

// Access the current theme
const { theme, setTheme } = useTheme()

// Access and apply skins
const { currentSkin, applySkin } = useSkin()
```

## Testing Pattern for Libraries

```typescript
// src/__tests__/YourComponent.test.tsx
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi } from "vitest"
import { YourComponent } from "../components/YourComponent"

describe("YourComponent", () => {
  it("renders children", () => {
    render(<YourComponent>Content</YourComponent>)
    expect(screen.getByText("Content")).toBeInTheDocument()
  })

  it("calls onOpenChange when triggered", async () => {
    const onOpenChange = vi.fn()
    render(<YourComponent onOpenChange={onOpenChange}>Click me</YourComponent>)
    await userEvent.click(screen.getByText("Click me"))
    expect(onOpenChange).toHaveBeenCalledWith(true)
  })

  it("forwards ref to DOM element", () => {
    const ref = React.createRef<HTMLDivElement>()
    render(<YourComponent ref={ref}>Content</YourComponent>)
    expect(ref.current).toBeInstanceOf(HTMLDivElement)
  })
})
```

## Version Publishing Checklist

Before publishing a new version:

- [ ] Run `pnpm build` — ensure no type errors
- [ ] Run `pnpm test` — all tests pass
- [ ] Check bundle size with `size-limit` (if configured)
- [ ] Verify exports are tree-shakable (import one component, bundle size should be minimal)
- [ ] Update `CHANGELOG.md` with breaking changes
- [ ] Bump version in `package.json`
- [ ] Test in the `ui-library` showcase before publishing
- [ ] Ensure peer deps are not bundled (check dist/index.js for React imports)

## pressable Library

`pressable` is an accessibility-first press/tap interaction library:

```typescript
import { Pressable, usePressable } from "@page-speed/pressable"

// Declarative usage
<Pressable
  onPress={() => handlePress()}
  onLongPress={() => handleLongPress()}
  disabled={isLoading}
>
  {({ isPressed }) => (
    <div className={cn("cursor-pointer", isPressed && "scale-95 transition-transform")}>
      Press me
    </div>
  )}
</Pressable>
```
