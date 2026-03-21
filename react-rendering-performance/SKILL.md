---
name: react-rendering-performance
description: >
  React 19+ rendering performance: React Compiler diagnostics, profiler-driven
  optimization, useTransition for non-blocking updates, the new Activity and
  ViewTransition components, resource preloading APIs, and when to actually reach
  for useMemo/useCallback vs letting the Compiler handle it. Use when debugging
  slow renders, optimizing user-perceived performance, or implementing smooth
  navigation transitions in React 19+ applications.
---

# React Rendering Performance

Performance work without measurement is guessing. The correct sequence: measure with the Profiler, identify the bottleneck type, then apply the right tool. Memoizing everything is not a strategy.

---

## React 19 Compiler: What Changed

React Compiler (stable in React 19) automatically memoizes components, values, and callbacks. It analyzes the component tree statically and inserts `useMemo`, `useCallback`, and `React.memo` where they would help — without you writing them.

### What the Compiler Handles Automatically

```jsx
// ❌ Old React 18: Manual memoization required
const expensiveResult = useMemo(() => compute(data), [data]);
const stableCallback = useCallback(() => onSelect(id), [id, onSelect]);
const MemoizedChild = React.memo(({ value }) => <div>{value}</div>);

// ✅ React 19 + Compiler: Write normal code, Compiler memoizes when beneficial
const expensiveResult = compute(data);  // Compiler inserts memo if compute is expensive
const handleSelect = () => onSelect(id); // Compiler stabilizes if beneficial
function Child({ value }) { return <div>{value}</div>; } // Compiler adds memo if needed
```

### When You Still Need Manual Memoization

The Compiler cannot memoize:
- Third-party library calls with opaque costs
- References that must be stable for external reasons (WebSocket listeners, event emitters)
- Computations the Compiler cannot prove are pure

```jsx
// Use manual memo for external listener stability
const stableHandler = useCallback((event) => {
  externalEventEmitter.emit('change', event);
}, []); // Compiler may not stabilize this without the hint

useEffect(() => {
  externalEventEmitter.on('input', stableHandler);
  return () => externalEventEmitter.off('input', stableHandler);
}, [stableHandler]);
```

### Diagnosing Compiler Output

```bash
# Install the Compiler (Next.js 15+ enables it automatically)
npm install --save-dev babel-plugin-react-compiler

# Check which components the Compiler skipped and why
# In browser console after enabling compiler logging:
# REACT_COMPILER_DEVTOOLS=true npm run dev
```

The Compiler skips components that:
- Mutate props or state directly
- Use `arguments` object
- Call hooks conditionally
- Have unrecognized patterns

Fix the anti-pattern to let the Compiler optimize it.

---

## Chrome DevTools: React Performance Tracks (React 19.2)

React 19.2 adds React-specific lanes to Chrome's Performance panel, showing scheduler priorities, render timing, and effect execution directly alongside browser-level data.

```
Performance Panel → Record → Interact → Stop
                                        ↓
Look for the "React" track group (new in 19.2):
  - "Render" lanes: component tree render time per update
  - "Commit" lanes: DOM mutation and effect duration
  - "Scheduler" lanes: task priority and yielding behavior
```

Correlate React render timing with "Long Tasks" in the browser track to find renders that block the main thread.

---

## React Profiler: Finding Real Bottlenecks

Use the React DevTools Profiler to find which component is slow before writing any optimization code.

```jsx
import { Profiler } from 'react';

function onRenderCallback(
  id,             // Component name
  phase,          // "mount" | "update" | "nested-update"
  actualDuration, // Time for this render in ms
  baseDuration,   // Estimated time without memoization
  startTime,
  commitTime,
) {
  if (actualDuration > 16) { // > 16ms = missed a frame
    console.warn(`[Profiler] Slow render in ${id}: ${actualDuration.toFixed(1)}ms (phase: ${phase})`);
  }
}

// Wrap the component tree you're investigating
<Profiler id="OrderList" onRender={onRenderCallback}>
  <OrderList orders={orders} />
</Profiler>
```

### Reading Profiler Output

- **`actualDuration` >> `baseDuration`**: Memoization is working but a dependency changed unnecessarily — track down the unstable reference
- **`actualDuration` ≈ `baseDuration`**: Component renders fully every time — check if it should be memoized or if its parent re-renders too often
- **High `baseDuration`**: The component's own render logic is expensive — profile the inner computation

---

## `useTransition` for Non-Blocking Updates

Marking a state update as a Transition tells React it's non-urgent — the browser can interrupt it to handle user input (like typing) without waiting for the transition to finish.

```jsx
import { useTransition, useState } from 'react';

function SearchResults() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [isPending, startTransition] = useTransition();

  function handleSearch(input) {
    // Typing the query is urgent — update immediately
    setQuery(input);

    // Rendering 10,000 search results is non-urgent — can be interrupted
    startTransition(() => {
      setResults(filterResults(input, allData));
    });
  }

  return (
    <>
      <input value={query} onChange={e => handleSearch(e.target.value)} />
      {isPending ? (
        <div aria-label="Loading results...">Searching...</div>
      ) : (
        <ResultList results={results} />
      )}
    </>
  );
}
```

### React 19: `useTransition` Now Accepts Async Functions

```jsx
const [isPending, startTransition] = useTransition();

async function handleSubmit(formData) {
  startTransition(async () => {
    // Async actions in transitions: React keeps isPending=true until resolved
    const result = await submitToServer(formData);
    setServerResult(result);
  });
}
```

---

## `useActionState` for Async Form Performance

Replaces the `isLoading` / `isError` / `result` state pattern with a single hook. Eliminates redundant state updates that trigger unnecessary re-renders.

```jsx
import { useActionState } from 'react';

// ❌ Old pattern: 3 state variables, each triggers a render
const [isLoading, setIsLoading] = useState(false);
const [error, setError] = useState(null);
const [result, setResult] = useState(null);

// ✅ React 19: single hook, single render per state change
const [state, submitAction, isPending] = useActionState(
  async (prevState, formData) => {
    const name = formData.get('name');
    const result = await createRestaurant({ name });
    return { success: true, restaurant: result };
  },
  null, // initial state
);
```

---

## `useOptimistic`: Instant UI Updates

For mutations where you're confident the server will succeed, apply the update immediately and roll back only on failure.

```jsx
import { useOptimistic } from 'react';

function ReviewList({ reviews, onAddReview }) {
  const [optimisticReviews, addOptimisticReview] = useOptimistic(
    reviews,
    (currentReviews, newReview) => [...currentReviews, newReview],
  );

  async function handleSubmit(formData) {
    const optimisticEntry = {
      id: crypto.randomUUID(),
      text: formData.get('text'),
      rating: Number(formData.get('rating')),
      pending: true,
    };

    addOptimisticReview(optimisticEntry); // Instant UI update

    try {
      await onAddReview(formData); // If this fails, React reverts automatically
    } catch {
      // React automatically rolls back to the original reviews array
    }
  }

  return (
    <ul>
      {optimisticReviews.map(r => (
        <li key={r.id} style={{ opacity: r.pending ? 0.6 : 1 }}>
          {r.text}
        </li>
      ))}
    </ul>
  );
}
```

---

## `useEffectEvent`: Stop Unnecessary Effect Re-runs

Effects that close over props/state re-run when those values change, even when the closure behavior doesn't need to change. `useEffectEvent` separates "event logic" from "effect dependencies" (React 19.2).

```jsx
import { useEffect, useEffectEvent } from 'react';

function Analytics({ userId, currentTheme }) {
  // ❌ Without useEffectEvent: theme changes cause reconnect
  useEffect(() => {
    const socket = connect(userId);
    socket.on('event', (data) => {
      // currentTheme is captured here, causing effect to re-run when theme changes
      logEvent({ data, theme: currentTheme });
    });
    return () => socket.disconnect();
  }, [userId, currentTheme]); // theme in deps = reconnect on theme change

  // ✅ useEffectEvent: theme reads are "event" logic, not effect deps
  const onEvent = useEffectEvent((data) => {
    logEvent({ data, theme: currentTheme }); // reads latest theme without being a dep
  });

  useEffect(() => {
    const socket = connect(userId);
    socket.on('event', onEvent); // stable reference, but always reads latest theme
    return () => socket.disconnect();
  }, [userId]); // only reconnects when userId changes
}
```

---

## `<Activity>`: Background Preloading and State Preservation

`<Activity>` (React 19.2) renders hidden UI — preloading data, CSS, and components for the next navigation destination without impacting visible performance. It also preserves form state when users navigate away.

```jsx
import { Activity } from 'react';

function App({ currentRoute }) {
  return (
    <>
      {/* Visible content */}
      <Activity mode={currentRoute === 'home' ? 'visible' : 'hidden'}>
        <HomePage />
      </Activity>

      {/* Preloaded but hidden — data fetches run in background */}
      <Activity mode={currentRoute === 'orders' ? 'visible' : 'hidden'}>
        <OrdersPage />
      </Activity>
    </>
  );
}
```

**`mode` values:**
- `"visible"`: Rendered and in the DOM
- `"hidden"`: Rendered but hidden — state preserved, data prefetched, not painted

Use `<Activity>` for navigation destinations the user is likely to visit next. Avoid wrapping large, rarely-visited pages — the background renders cost CPU.

---

## `<ViewTransition>`: Coordinated Animations (React 19.2 experimental)

`<ViewTransition>` integrates React's rendering with the browser's native View Transition API for smooth page-to-page animations.

```jsx
import { ViewTransition } from 'react';
import { startTransition } from 'react';

function NavLink({ href, children }) {
  return (
    <a
      href={href}
      onClick={(e) => {
        e.preventDefault();
        startTransition(() => {
          navigate(href); // Your router's navigate function
        });
      }}
    >
      {children}
    </a>
  );
}

// Wrap the animated element
function PageContent({ route }) {
  return (
    <ViewTransition>
      <div key={route}>
        {/* Content changes trigger view transition animation */}
        <RouteContent route={route} />
      </div>
    </ViewTransition>
  );
}
```

The view transition only fires when the state update is wrapped in `startTransition`. Non-transition updates render immediately without animation.

---

## Resource Preloading APIs

React 19 added `react-dom` APIs for preloading resources before they're requested, reducing waterfall latency:

```jsx
import { preload, preinit, prefetchDNS, preconnect } from 'react-dom';

function App() {
  // Preload font — triggers <link rel="preload"> immediately
  preload('/fonts/Inter.woff2', { as: 'font', crossOrigin: 'anonymous' });

  // Preconnect to external API — establishes TCP+TLS before first request
  preconnect('https://api.stripe.com');

  // Prefetch DNS — faster than nothing, cheaper than preconnect
  prefetchDNS('https://cdn.analytics.com');

  // Preinit a script — download AND execute immediately
  preinit('/scripts/analytics.js', { as: 'script' });

  return <App />;
}
```

These calls are **idempotent** — safe to call multiple times; the browser deduplicates. Call them as early as possible in the tree.

---

## Common Performance Mistakes

| Mistake | Symptom | Fix |
|---------|---------|-----|
| Manual `useMemo`/`useCallback` everywhere in React 19 | Over-memoization, harder-to-read code | Let the Compiler handle it; only add manual memo for external stability requirements |
| Expensive computation in render (no memo) | High `baseDuration` in Profiler | `useMemo` for pure computations; `startTransition` for deferred renders |
| State updates for urgent and non-urgent work combined | Typing feels sluggish | Split urgent updates (typing) from non-urgent (filtering results) with `useTransition` |
| New object/array literals in JSX props | Child re-renders every time | Move stable data outside component or use the Compiler; avoid `{}` inline |
| `useEffect` deps include theme/locale | Effect fires too often | `useEffectEvent` for values that are read but don't trigger reconnects |
| No `<Activity>` on predictable navigation destinations | Visible load flash on navigation | Wrap likely-next pages in `<Activity mode="hidden">` |
| Missing `key` on list items | React reconciles wrong elements | Always provide stable, unique keys — never array index for sortable/filterable lists |
