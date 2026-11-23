---
name: verity-design-reskin
description: "The platform now runs the client's \"Verity\" design system end-to-end — where the spec lives, what was built, env quirks of the HP machine"
metadata: 
  node_type: memory
  type: project
  originSessionId: 71542734-f989-4a03-83ae-7affc8e35c43
  modified: 2026-08-08T08:24:46.298Z
---

**2026-08-08: full Verity reskin shipped.** The client's 6 design HTML files (Downloads; self-unpacking React bundles — decompress via the extractor pattern in scratchpad/design) were synthesized into `docs/VERITY-DESIGN-SPEC.md` (~90KB: tokens, chrome, 22 frames + 6 alt dashboards, chart guide). The whole frontend now implements it.

Key facts:
- **Design language:** accent #0284C7, bg #F4F5F7, elevated #FFF, Sora display + Inter body, status set pass #059669 / fail #E11D48 / review #D97706 / pending #5B72B3 / na #64748B. Full dark theme (`.dark` AND `[data-theme=dark]`). All tokens in `frontend/src/index.css` (single-file reskin architecture, legacy aliases kept).
- **Product renders as "Verity"** (per the client's own designs) — sidebar wordmark, login, index.html title.
- Chrome: 240px sidebar (design nav groups + Workspace group for extra pages), 56px topbar (tenant switcher, ⌘K, bell). New pages: Evidence (frame 05), Findings (13), Settings (18). New overlays: `components/Overlays.jsx` (⌘K palette + notifications popover), control quick-look drawer (in Controls), new-risk modal, bulk bar. All 14 legacy pages reskinned to their frames by a parallel workflow; all data wiring preserved (verified: build clean, 19 routes render, zero console errors, dark tokens exact, login+TOTP flow works end-to-end).
- Frame 03 (full control detail page) intentionally folded into the frame-04 drawer; ERM sidebar item not built (no design, no backend).

**HP machine env quirks:** project moved to `C:\Users\HP\OneDrive\Desktop\Platform\grc-s`. Port 8000 is occupied by the user's separate audio-to-text app — DO NOT kill it; our backend runs on **8001** (vite proxy updated accordingly). The backend venv had to be rebuilt with local Python 3.12 (old venv pointed at the Admin machine). Backend enforces **admin MFA (TOTP)**; demo secret is shown on the login page; compute codes with pure-Python HMAC when verifying flows. Launch config: `.claude/launch.json` → `npm run dev --prefix frontend` on 5173.
