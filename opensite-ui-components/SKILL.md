---
name: opensite-ui-components
description: OpenSite UI component library patterns. Use when creating, editing, or reviewing components in @opensite/ui (opensite-ai/opensite-ui), the Semantic UI Engine, page-speed-* libraries, or the ui-library showcase (opensite-ai/ui-library). Covers component registration patterns, Tailwind CSS v4, Radix UI, framer-motion, ShadCN conventions, and the block/skin architecture.
---

# OpenSite UI Components Skill

You are working in the OpenSite Semantic UI Engine — the `@opensite/ui` library (`github.com/opensite-ai/opensite-ui`) and its showcase application (`github.com/opensite-ai/ui-library`). This is a tree-shakable, abstract-styled component library powering the Semantic Site Builder.

## Stack

```
@opensite/ui@3.x
├── React 18 (peerDep)
├── Tailwind CSS v4 (consumer-configured)
├── Radix UI primitives (@radix-ui/react-*)
├── class-variance-authority (CVA) for variants
├── tailwind-merge (twMerge) for class conflicts
├── framer-motion / motion for animations
├── embla-carousel-react for carousels
├── @page-speed/* sub-libraries (router, forms, img, video, etc.)
└── tsup for bundling (tree-shakable ESM + CJS)
```

## Component Architecture

Every component follows the CVA (class-variance-authority) variant pattern. Never hardcode Tailwind classes directly — always use `cva` for variant-based styling:

```typescript
// src/components/ui/button.tsx
import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const buttonVariants = cva(
  // Base styles — always applied
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-all disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 shrink-0 outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px]",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground shadow-xs hover:bg-primary/90",
        destructive: "bg-destructive text-white shadow-xs hover:bg-destructive/90 focus-visible:ring-destructive/20",
        outline: "border bg-background shadow-xs hover:bg-accent hover:text-accent-foreground",
        secondary: "bg-secondary text-secondary-foreground shadow-xs hover:bg-secondary/80",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-9 px-4 py-2 has-[>svg]:px-3",
        sm: "h-8 rounded-md gap-1.5 px-3 has-[>svg]:px-2.5",
        lg: "h-10 rounded-md px-6 has-[>svg]:px-4",
        icon: "size-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button"
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button, buttonVariants }
```

## Block Registration Pattern

All UI blocks (page sections) are registered in `src/registry.ts`. A block is a self-contained section with schema, component, and metadata:

```typescript
// src/hero-split-image.ts (example block registration)
import type { BlockDefinition } from "./types"

export const heroSplitImage: BlockDefinition = {
  id: "hero-split-image",
  name: "Hero Split Image",
  category: "hero",
  description: "A hero section with text on the left and image on the right",
  tags: ["hero", "split", "image", "landing"],
  component: () => import("./components/blocks/hero/HeroSplitImage"),
  defaultProps: {
    heading: "Build something amazing",
    subheading: "The platform for modern teams",
    ctaText: "Get started",
    ctaHref: "#",
    imageUrl: "",
    imageAlt: "",
  },
  schema: {
    heading: { type: "text", label: "Heading", required: true },
    subheading: { type: "text", label: "Subheading" },
    ctaText: { type: "text", label: "CTA Button Text" },
    ctaHref: { type: "url", label: "CTA URL" },
    imageUrl: { type: "image", label: "Hero Image" },
    imageAlt: { type: "text", label: "Image Alt Text" },
  },
}
```

## Skin System (@page-speed/skins)

Skins provide theme tokens that components consume via CSS variables. Never hardcode colors — always reference CSS variable tokens:

```typescript
// CSS variable convention (Tailwind v4 compatible)
// Background: bg-background, text-foreground
// Primary: bg-primary, text-primary-foreground
// Secondary: bg-secondary, text-secondary-foreground
// Accent: bg-accent, text-accent-foreground
// Muted: bg-muted, text-muted-foreground
// Destructive: bg-destructive, text-white
// Border: border-border
// Ring: ring-ring

// Example — correct usage
<div className="bg-background text-foreground border border-border rounded-lg p-4">
  <h2 className="text-foreground font-semibold">Title</h2>
  <p className="text-muted-foreground text-sm">Subtitle</p>
</div>

// Example — incorrect (hardcoded colors break skin switching)
<div className="bg-white text-gray-900 border border-gray-200">  // ❌ WRONG
```

## cn() Utility

Always use `cn()` (tailwind-merge + clsx) to merge className props:

```typescript
// src/lib/utils.ts
import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// Usage in components
<div className={cn(
  "base-classes",
  variant === "primary" && "primary-classes",
  isLoading && "opacity-50 pointer-events-none",
  className  // Always accept and merge external className prop
)}>
```

## Animation Patterns (Framer Motion)

Standard animation patterns used across the library:

```typescript
// Fade in from below (most common)
import { motion } from "framer-motion"

const fadeInUp = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.4, ease: "easeOut" }
}

// Stagger children
const staggerContainer = {
  animate: { transition: { staggerChildren: 0.1 } }
}

// Usage
<motion.div
  initial="initial"
  animate="animate"
  variants={staggerContainer}
>
  {items.map((item, i) => (
    <motion.div key={i} variants={fadeInUp}>
      {item}
    </motion.div>
  ))}
</motion.div>

// Respect reduced motion
import { useReducedMotion } from "framer-motion"

function AnimatedComponent() {
  const prefersReducedMotion = useReducedMotion()
  return (
    <motion.div
      animate={prefersReducedMotion ? undefined : { y: [0, -10, 0] }}
    />
  )
}
```

## @page-speed/img Usage

Always use `@page-speed/img` instead of Next.js `Image` or HTML `img` in library components:

```typescript
import { Img } from "@page-speed/img"

// Basic usage
<Img
  src={imageUrl}
  alt={imageAlt}
  width={800}
  height={450}
  className="w-full h-auto rounded-lg object-cover"
  loading="lazy"
/>

// With aspect ratio container
<div className="relative aspect-video overflow-hidden rounded-lg">
  <Img
    src={imageUrl}
    alt={imageAlt}
    fill
    className="object-cover"
  />
</div>
```

## tsup Build Configuration

The library uses `tsup` for bundling. Never change the build config without understanding tree-shaking implications:

```typescript
// tsup.config.ts
import { defineConfig } from "tsup"

export default defineConfig({
  entry: ["src/index.ts"],
  format: ["cjs", "esm"],
  dts: true,
  splitting: true,       // Enable code splitting for tree-shaking
  sourcemap: true,
  clean: true,
  treeshake: true,
  external: [            // Never bundle peerDeps
    "react",
    "react-dom",
    "@radix-ui/*",
  ],
})
```

## Component Testing Pattern

```typescript
// src/__tests__/Button.test.tsx
import { render, screen, userEvent } from "@testing-library/react"
import { Button } from "../components/ui/button"

describe("Button", () => {
  it("renders with default variant", () => {
    render(<Button>Click me</Button>)
    expect(screen.getByRole("button", { name: "Click me" })).toBeInTheDocument()
  })

  it("calls onClick handler", async () => {
    const onClick = vi.fn()
    render(<Button onClick={onClick}>Click me</Button>)
    await userEvent.click(screen.getByRole("button"))
    expect(onClick).toHaveBeenCalledTimes(1)
  })

  it("renders as child with asChild", () => {
    render(<Button asChild><a href="/test">Link</a></Button>)
    expect(screen.getByRole("link")).toHaveAttribute("href", "/test")
  })
})
```

## New Component Checklist

Before adding a new component:

- [ ] Uses CVA for variants, not ad-hoc className strings
- [ ] Accepts and merges `className` prop via `cn()`
- [ ] Uses CSS variable tokens, not hardcoded colors
- [ ] Forwards `ref` if it renders a DOM element
- [ ] Uses `@page-speed/img` for images, not `<img>` or Next.js `Image`
- [ ] Has TypeScript types exported alongside component
- [ ] Exports from `src/index.ts` (tree-shakable named export)
- [ ] Has at least one test covering render + interaction
- [ ] Respects `prefersReducedMotion` for all animations
- [ ] Works with all skin themes (test with at least 2 skins)
