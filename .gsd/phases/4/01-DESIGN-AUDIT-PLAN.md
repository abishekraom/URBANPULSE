---
phase: 4
plan: 1
wave: 1
---

# 4-01 Design Audit & Bloomberg Polish

Refine the UI to match the "HSE Terminal" vision with premium aesthetics.

## Context
The terminal should look "WOW" at first glance.

## Tasks

### <task> [Typography & Colors](file:///d:/rVb/src/index.css)
Refine the color palette (Bloomberg Gold/Amber) and ensure monospace consistency.

<verify>
Select-String -Path "src/index.css" -Pattern "terminal-gold"
</verify>
</task>

### <task> [Micro-Animations](file:///d:/rVb/src/components/Dashboard.jsx)
Add subtle enter animations for dashboard tiles using `framer-motion`.

<verify>
Select-String -Path "src/components/Dashboard.jsx" -Pattern "motion.div"
</verify>
</task>

### <task> [Ticker Realism](file:///d:/rVb/src/components/TerminalLayout.jsx)
Enhance the ticker with real-looking data points (Stocks/REITs).

<verify>
Select-String -Path "src/components/TerminalLayout.jsx" -Pattern "REIT"
</verify>
</task>
