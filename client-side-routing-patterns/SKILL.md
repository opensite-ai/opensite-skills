---
name: client-side-routing-patterns
description: >
  Client-side routing patterns using the History API — managing URL state without
  full page reloads, building provider-optional routing hooks, SSR-safe browser API
  access, scroll behavior, and parameter parsing. Covers both the architectural
  patterns (custom routechange events, popstate listeners) and practical hook design
  for zero-dependency routing libraries. Use when building or extending routing
  systems, debugging navigation bugs, or working with @page-speed/router patterns.
---

# Client-Side Routing Patterns

Modern client-side routing is built on two browser primitives: `history.pushState` / `history.replaceState` and the `popstate` event. Understanding these directly makes every router less magical and easier to debug.

---

## History API Fundamentals

```javascript
// pushState: add a new history entry (browser Back button goes back)
history.pushState(
  { key: 'some-state' }, // State object (serializable; retrieve via history.state)
  '',                    // Title — browsers ignore this; pass empty string
  '/new-path?q=foo',     // URL to display
);

// replaceState: update current entry without creating a Back entry
history.replaceState(state, '', '/same-path?q=updated');

// Reading current state
const currentState = history.state;  // { key: 'some-state' }
const currentUrl = window.location.href;
const pathname = window.location.pathname;
const search = window.location.search;    // '?q=foo'
const hash = window.location.hash;       // '#section-2'
```

### The `popstate` Event

`popstate` fires when the user navigates backward or forward via the browser buttons, or when `history.go()` is called. It does **not** fire on `pushState` or `replaceState` calls — those are silent by default.

```javascript
window.addEventListener('popstate', (event) => {
  // event.state is whatever was passed to pushState/replaceState
  console.log('Navigated to:', window.location.pathname, 'State:', event.state);
  syncAppToCurrentUrl(); // Update your UI to match the new URL
});
```

---

## Custom `routechange` Event Pattern

Since `pushState` and `replaceState` don't fire any browser event, routing libraries need to dispatch their own. The standard pattern:

```javascript
// When performing programmatic navigation:
function navigate(path, options = {}) {
  const { replace = false, state = {} } = options;

  if (replace) {
    history.replaceState(state, '', path);
  } else {
    history.pushState(state, '', path);
  }

  // Dispatch a custom event so all listeners know the URL changed
  window.dispatchEvent(new PopStateEvent('routechange', { state }));
}

// Listeners subscribe to both popstate (user back/forward) and routechange (programmatic)
function subscribeToNavigation(callback) {
  window.addEventListener('popstate', callback);
  window.addEventListener('routechange', callback);

  return () => {
    window.removeEventListener('popstate', callback);
    window.removeEventListener('routechange', callback);
  };
}
```

This keeps the listening code uniform — it doesn't matter whether the URL changed from a button click, `history.back()`, or a programmatic `navigate()` call.

---

## SSR-Safe Browser API Access

Routing code runs in both Node.js (SSR/build) and the browser. `window`, `location`, and `history` do not exist in Node.js — guard every access.

```javascript
// Pattern 1: isBrowser guard
export const isBrowser = typeof window !== 'undefined';

export function getCurrentPath() {
  return isBrowser ? window.location.pathname : '/';
}

// Pattern 2: ssrSafe wrapper — returns fallback when not in browser
export function ssrSafe(browserFn, fallback) {
  return isBrowser ? browserFn() : fallback;
}

const currentUrl = ssrSafe(() => window.location.href, 'http://localhost/');

// Pattern 3: In React hooks — only access browser APIs in effects (not render)
function useCurrentPath() {
  const [path, setPath] = useState(() =>
    typeof window !== 'undefined' ? window.location.pathname : '/'
  );

  useEffect(() => {
    const unsubscribe = subscribeToNavigation(() => {
      setPath(window.location.pathname);
    });
    return unsubscribe;
  }, []);

  return path;
}
```

---

## Provider-Optional Hook Design

The best routing hooks work with or without a provider — they fall through to direct browser API calls when no RouterContext is present. This makes them usable in any context without requiring wrapper setup.

```javascript
import { useContext } from 'react';
import { RouterContext } from './RouterProvider';

// Hook reads from context if available, falls back to browser APIs
export function usePathname() {
  const ctx = useContext(RouterContext);

  // If inside a RouterProvider, use context value (reactive to updates)
  if (ctx) return ctx.pathname;

  // If outside a provider (SSR, tests, isolated usage), read directly
  return typeof window !== 'undefined' ? window.location.pathname : '/';
}

export function useSearchParams() {
  const ctx = useContext(RouterContext);
  if (ctx) return ctx.searchParams;
  return typeof window !== 'undefined'
    ? new URLSearchParams(window.location.search)
    : new URLSearchParams();
}
```

### Memoized Context Value

When building a `RouterProvider`, memoize the context value to prevent re-renders in every consumer on every navigation:

```jsx
function RouterProvider({ children }) {
  const [urlState, setUrlState] = useState(getCurrentUrlState);

  useEffect(() => {
    const update = () => setUrlState(getCurrentUrlState());

    window.addEventListener('popstate', update);
    window.addEventListener('routechange', update);

    return () => {
      window.removeEventListener('popstate', update);
      window.removeEventListener('routechange', update);
    };
  }, []);

  // Memoize so object identity only changes when URL actually changes
  const contextValue = useMemo(() => ({
    pathname: urlState.pathname,
    search: urlState.search,
    hash: urlState.hash,
    searchParams: new URLSearchParams(urlState.search),
    navigate,
  }), [urlState]);

  return (
    <RouterContext.Provider value={contextValue}>
      {children}
    </RouterContext.Provider>
  );
}

function getCurrentUrlState() {
  if (typeof window === 'undefined') {
    return { pathname: '/', search: '', hash: '' };
  }
  return {
    pathname: window.location.pathname,
    search: window.location.search,
    hash: window.location.hash,
  };
}
```

---

## Path Matching and Parameter Extraction

```javascript
// Match a path pattern against the current URL
// Returns null if no match, or an object of extracted params
export function matchPath(pattern, pathname) {
  // Convert :param segments to named capture groups
  const regexStr = pattern
    .replace(/:[^/]+/g, '([^/]+)')  // :id → ([^/]+)
    .replace(/\*/g, '(.*)');         // * → (.*)

  const paramNames = (pattern.match(/:[^/]+/g) || [])
    .map(p => p.slice(1)); // strip leading ':'

  const match = pathname.match(new RegExp(`^${regexStr}$`));
  if (!match) return null;

  const params = Object.fromEntries(
    paramNames.map((name, i) => [name, decodeURIComponent(match[i + 1])])
  );

  return { params, pathname };
}

// Usage
matchPath('/restaurants/:id/menu', '/restaurants/42/menu');
// → { params: { id: '42' }, pathname: '/restaurants/42/menu' }

matchPath('/restaurants/:id/menu', '/restaurants/42/orders');
// → null
```

### `useRouteMatch` Hook

```javascript
export function useRouteMatch(pattern) {
  const pathname = usePathname();
  return useMemo(() => matchPath(pattern, pathname), [pattern, pathname]);
}

export function useIsActive(pattern, exact = false) {
  const pathname = usePathname();
  if (exact) return pathname === pattern;
  return pathname.startsWith(pattern);
}

// Usage in NavLink component
function NavLink({ to, children, exact }) {
  const isActive = useIsActive(to, exact);
  const navigate = useNavigate();

  return (
    <a
      href={to}
      aria-current={isActive ? 'page' : undefined}
      onClick={(e) => {
        e.preventDefault();
        navigate(to);
      }}
    >
      {children}
    </a>
  );
}
```

---

## Search Parameter Management

```javascript
// Parse: URLSearchParams → plain object
export function parseSearchParams(search) {
  const params = new URLSearchParams(search);
  const result = {};
  for (const [key, value] of params.entries()) {
    if (key in result) {
      result[key] = Array.isArray(result[key])
        ? [...result[key], value]
        : [result[key], value];
    } else {
      result[key] = value;
    }
  }
  return result;
}

// Update search params without wiping unrelated params
export function useUpdateSearchParams() {
  const navigate = useNavigate();

  return useCallback((updates) => {
    const current = new URLSearchParams(window.location.search);

    for (const [key, value] of Object.entries(updates)) {
      if (value === null || value === undefined) {
        current.delete(key);
      } else {
        current.set(key, String(value));
      }
    }

    const newSearch = current.toString();
    navigate(
      `${window.location.pathname}${newSearch ? `?${newSearch}` : ''}`,
      { replace: true }, // Don't create a history entry for filter changes
    );
  }, [navigate]);
}

// Usage
const updateParams = useUpdateSearchParams();
updateParams({ page: 2, filter: 'pending' }); // Keeps existing params, updates these
updateParams({ filter: null });                // Removes the filter param
```

---

## Scroll Behavior

### Scroll to Top on Navigation

```javascript
function navigate(path, options = {}) {
  const { replace = false, scroll = true, hash } = options;

  history[replace ? 'replaceState' : 'pushState']({}, '', path);
  window.dispatchEvent(new PopStateEvent('routechange'));

  if (hash) {
    // Scroll to anchor after next render
    requestAnimationFrame(() => scrollToAnchor(hash));
  } else if (scroll) {
    window.scrollTo({ top: 0, behavior: 'instant' });
  }
}
```

### Scroll to Anchor

```javascript
export function scrollToAnchor(id, options = {}) {
  const { behavior = 'smooth', offset = 0 } = options;
  const element = document.getElementById(id) ?? document.querySelector(`[name="${id}"]`);

  if (!element) return;

  const top = element.getBoundingClientRect().top + window.scrollY - offset;
  window.scrollTo({ top, behavior });
}
```

### Preserve Scroll Position for Back Navigation

```javascript
// Save scroll position in history state before navigating away
function navigateWithScrollSave(to) {
  const scrollY = window.scrollY;
  history.replaceState({ ...history.state, scrollY }, '');
  navigate(to);
}

// Restore on popstate
window.addEventListener('popstate', (event) => {
  if (event.state?.scrollY !== undefined) {
    requestAnimationFrame(() => {
      window.scrollTo({ top: event.state.scrollY, behavior: 'instant' });
    });
  }
});
```

---

## `useNavigation` Core Hook

The central navigation hook wraps `pushState`/`replaceState` with scroll handling and same-path detection:

```javascript
export function useNavigate() {
  return useCallback((to, options = {}) => {
    if (!isBrowser) return;

    const { replace = false, scroll = true } = options;
    const isSamePath = to === window.location.pathname + window.location.search;

    if (isSamePath && !replace) return; // Avoid duplicate history entries

    if (replace || isSamePath) {
      history.replaceState({}, '', to);
    } else {
      history.pushState({}, '', to);
    }

    window.dispatchEvent(new PopStateEvent('routechange'));

    if (scroll) {
      window.scrollTo({ top: 0, behavior: 'instant' });
    }
  }, []);
}
```

---

## Common Routing Bugs

| Bug | Symptom | Fix |
|-----|---------|-----|
| Accessing `window` during SSR | `ReferenceError: window is not defined` | Guard with `typeof window !== 'undefined'` |
| `pushState` doesn't update UI | URL changes, component doesn't re-render | Dispatch `routechange` event after `pushState` |
| Back button doesn't work | `popstate` not subscribed | Add `popstate` listener in addition to `routechange` |
| Duplicate history entries on same-path navigate | User clicks Back and nothing happens | Check `isSamePath` before `pushState`; use `replaceState` for same-path |
| Params not decoded | Space shows as `%20` | Always `decodeURIComponent()` extracted params |
| New URLSearchParams object on every render | Consumer re-renders constantly | Memoize the URLSearchParams object in context |
| Missing cleanup in useEffect | Memory leak; double-subscription | Always return cleanup function from navigation useEffect |
