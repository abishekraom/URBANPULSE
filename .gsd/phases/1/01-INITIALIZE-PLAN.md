---
phase: 1
plan: 1
wave: 1
---

# 1-01 Initialize Vite Project

Initialize the HSE Terminal React project using Vite.

## Context
Greenfield project. Need a fast, interactive React foundation.

## Tasks

### <task> [Initialize Vite](file:///d:/rVb/package.json)
Run `npx -y create-vite@latest ./ --template react` to initialize the project in the current directory.

<verify>
Test-Path "package.json"
</verify>
</task>

### <task> [Install Dependencies](file:///d:/rVb/package.json)
Install any necessary additional packages (e.g., lightweight charts).

<verify>
Test-Path "node_modules"
</verify>
</task>

### <task> [Clean Boilerplate](file:///d:/rVb/src/App.css)
Remove unnecessary Vite boilerplate (App.css, assets, etc.) to start with a clean slate for the Bloomberg UI.

<verify>
-not (Test-Path "src/App.css")
</verify>
</task>
