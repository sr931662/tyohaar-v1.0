# Tyohaar — Web Frontend

The marketing website for **Tyohaar**, the home for life's celebrations.
Built with **React + Vite** and **Framer Motion**, styled with **CSS Modules** and a token-driven
theme system (two skins: *Warm Light* and *Festival of Lights*).

---

## Getting started

```bash
cd client
npm install
npm run dev      # http://localhost:5173
npm run build    # production build → dist/
npm run preview  # preview the production build
```

> Requires Node 18+.

---

## Project structure

```
client/
├─ index.html              # fonts + root; data-theme lives on <html>
├─ vite.config.js          # add an /api proxy here when the backend is ready
├─ public/
│  └─ diya.svg             # favicon (the brand spark)
└─ src/
   ├─ main.jsx             # entry — wraps <App> in <ThemeProvider>
   ├─ App.jsx              # composes the page sections
   ├─ index.css            # design tokens (both themes) + base styles
   ├─ context/
   │  └─ ThemeContext.jsx  # light/dark theme, persisted to localStorage
   ├─ lib/
   │  └─ motion.js         # shared Framer Motion variants & viewport config
   ├─ data/                # content (swap for API/CMS later)
   │  ├─ occasions.js
   │  ├─ steps.js
   │  ├─ vendors.js
   │  ├─ testimonials.js
   │  └─ nav.js
   └─ components/
      ├─ ui/               # Button, Diya, Logo, Emblem, Placeholder,
      │                    # SectionHeading, Reveal, ThemeToggle
      ├─ layout/           # Navbar (responsive + mobile sheet), Footer
      └─ sections/         # Hero, Marquee, Occasions, HowItWorks,
                           # Vendors, Memories, Testimonials, CTA
```

Each component owns a co-located `*.module.css`. Class names are referenced as
`styles.foo` and never leak globally.

---

## Design system

All colour, type, spacing, radii, shadows and easing are **CSS custom properties** defined in
`src/index.css`. Two themes are declared via `:root[data-theme="light"]` (default) and
`:root[data-theme="dark"]` — toggled by `ThemeContext` and the `ThemeToggle` control.

- **Type** — Yeseva One (display) · Plus Jakarta Sans (UI) · Tiro Devanagari Hindi (signature)
- **Motif** — the *arch / toran* (rounded doorway) and the *diya* (a dot of light)
- **Tints** — `saffron`, `rose`, `leaf`, `gold` (use as `var(--saffron)` etc.)

To restyle globally, edit the tokens — components inherit automatically.

---

## Images

`<Placeholder>` renders arch-topped, tinted stand-ins with monospace labels. **Replacing these
with real photography is the single biggest visual upgrade.** Drop images into `public/` (or
import them) and swap the `<Placeholder>` instances in the section components.

---

## Connecting the backend (Node.js)

1. Add a dev proxy in `vite.config.js`:
   ```js
   server: { proxy: { '/api': 'http://localhost:4000' } }
   ```
2. Replace the static arrays in `src/data/*` with `fetch('/api/...')` calls
   (a small `src/lib/api.js` + React Query / SWR is a clean next step).

---

## Accessibility & performance

- Honours `prefers-reduced-motion` (animations collapse to instant).
- Semantic landmarks, `:focus-visible` rings, `aria` on interactive controls.
- Fluid type/space via `clamp()`; fully responsive down to ~360px.
- Fonts preconnected; theme persisted to avoid flash.
