---
phase: 2
plan: 1
wave: 1
---

# 2-01 Financial Core (NPV/IRR)

Implement the core mathematical logic for Rent vs Buy comparison.

## Context
Needs to handle multi-year cash flows and discounted valuations.

## Tasks

### <task> [Constants & Utils](file:///d:/rVb/src/logic/constants.js)
Define cross-city constants and reusable utility functions for mortgage calculations (EMI).

<verify>
Test-Path "src/logic/constants.js"
</verify>
</task>

### <task> [Buy Scenario Engine](file:///d:/rVb/src/logic/buyEngine.js)
Calculate cash outflows for owners: EMI, Maintenance, Property Tax, Stamp Duty/Reg, and final Sale Value (Net of taxes).

<verify>
Test-Path "src/logic/buyEngine.js"
</verify>
</task>

### <task> [Rent Scenario Engine](file:///d:/rVb/src/logic/rentEngine.js)
Calculate cash outflows for renters: Rent, Annual Hike, and Opportunity Cost (Investment of downpayment in equities).

<verify>
Test-Path "src/logic/rentEngine.js"
</verify>
</task>

### <task> [Comparison Summary (NPV)](file:///d:/rVb/src/logic/comparer.js)
Create a function that compares the two scenarios and returns NPV/IRR metrics.

<verify>
Test-Path "src/logic/comparer.js"
</verify>
</task>
