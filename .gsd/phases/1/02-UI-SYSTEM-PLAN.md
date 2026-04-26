---
phase: 1
plan: 2
wave: 2
---

# 1-02 Bloomberg UI Foundation

Establish the Bloomberg design system and build the Splash Screen.

## Context
Requires high-density monospace typography and a specific black/cyan/amber palette.

## Tasks

### <task> [Design Tokens](file:///d:/rVb/src/index.css)
Create the core `index.css` with Bloomberg design tokens (CSS variables).

<verify>
Select-String -Path "src/index.css" -Pattern "--terminal-black"
</verify>
</task>

### <task> [Terminal Layout Component](file:///d:/rVb/src/components/TerminalLayout.jsx)
Build a reusable layout component that defines the grid and main regions (Header, Main, Sidebar, Footer/Ticker).

<verify>
Test-Path "src/components/TerminalLayout.jsx"
</verify>
</task>

### <task> [Splash Screen](file:///d:/rVb/src/components/SplashScreen.jsx)
Implement the "HSE Terminal" loading splash screen with micro-animations.

<verify>
Test-Path "src/components/SplashScreen.jsx"
</verify>
</task>

### <task> [App Integration](file:///d:/rVb/src/App.jsx)
Integrate the Layout and Splash Screen in the main `App.jsx`.

<verify>
Select-String -Path "src/App.jsx" -Pattern "TerminalLayout"
</verify>
</task>
