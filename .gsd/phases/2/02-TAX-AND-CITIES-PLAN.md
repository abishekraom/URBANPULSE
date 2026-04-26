---
phase: 2
plan: 2
wave: 1
---

# 2-02 Indian Tax & City Data

Integrate specific Indian tax laws and city datasets.

## Context
Crucial for accurate India-specific outcomes (HRA vs Section 24).

## Tasks

### <task> [Indian Tax Module](file:///d:/rVb/src/logic/taxation.js)
Implement HRA exemption calculator, Section 24 (Interest) and Section 80C (Principal) deductions.

<verify>
Test-Path "src/logic/taxation.js"
</verify>
</task>

### <task> [City Dataset](file:///d:/rVb/src/data/cities.js)
Establish a registry for Tier 1 cities with Stamp Duty, Registration, and yield defaults.

<verify>
Test-Path "src/data/cities.js"
</verify>
</task>

### <task> [State Management Integration](file:///d:/rVb/src/store/useFinancialStore.js)
Create a store (using React Context or simple state) to handle global parameters (Property Price, Loan Term, Interest Rate).

<verify>
Test-Path "src/store/useFinancialStore.js"
</verify>
</task>
