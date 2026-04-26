---
phase: 3
plan: 2
wave: 1
---

# 3-02 CLI Command System

Build the "Command Bar" interactive system for the terminal.

## Context
The Bloomberg experience is keyboard-first. Users should be able to tune the model via commands.

## Tasks

### <task> [Command Parser](file:///d:/rVb/src/logic/commandParser.js)
Implement a simple command parser (e.g., `BUY 20000000`, `CITY BLR`) that maps strings to store actions.

<verify>
Test-Path "src/logic/commandParser.js"
</verify>
</task>

### <task> [CLI UI Integration](file:///d:/rVb/src/components/TerminalLayout.jsx)
Connect the header's command input to the parser and display feedback in the UI.

<verify>
Select-String -Path "src/components/TerminalLayout.jsx" -Pattern "onKeyDown"
</verify>
</task>

### <task> [Help System](file:///d:/rVb/src/components/CommandHelp.jsx)
Build an overlay or sidebar section that lists available commands.

<verify>
Test-Path "src/components/CommandHelp.jsx"
</verify>
</task>
