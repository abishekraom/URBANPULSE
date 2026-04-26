---
phase: 3
plan: 1
wave: 1
---

# 3-01 Stochastic Engine (Monte Carlo)

Implement simulation-based risk analysis for Rent vs Buy decisions.

## Context
 deterministic models can be misleading; investors need to see the "probability of success" under market volatility.

## Tasks

### <task> [Monte Carlo Logic](file:///d:/rVb/src/logic/stochasticEngine.js)
Implement a simulation runner that applies random variance to property appreciation and equity returns based on standard deviation.

<verify>
Test-Path "src/logic/stochasticEngine.js"
</verify>
</task>

### <task> [Store Integration (Stochastic)](file:///d:/rVb/src/store/useFinancialStore.jsx)
Integrate the stochastic engine into the financial store and add simulation parameters (volatility).

<verify>
Select-String -Path "src/store/useFinancialStore.jsx" -Pattern "stochasticResults"
</verify>
</task>

### <task> [Stochastic Dashboard View](file:///d:/rVb/src/components/StochasticView.jsx)
Build a dashboard component to display "Probability of Winning" and distribution histograms.

<verify>
Test-Path "src/components/StochasticView.jsx"
</verify>
</task>
