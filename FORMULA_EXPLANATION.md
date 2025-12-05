# Formula Explanation

How impact and priority scores are calculated.

## Formulas

### 1. Impact (Call Frequency)
```
impact = direct_calls + indirect_calls
```
Counts how many functions call this function (directly + indirectly). Higher = more important.

### 2. Impact Score
```
impact_score = impact × (1.0 - coverage_pct)
```
Combines call frequency with coverage gap. High impact + low coverage = high priority.

### 3. Priority Score
```
priority = (impact_score × confidence) / ((complexity + 0.1) × (effort + 0.1))
```
Where `effort = 1.0 + (complexity × 2.0)`. Prioritizes high impact, low complexity, high confidence.

## Key Points

- **Impact = 0**: Function has no callers (entry point, unused, or external callers)
- **Impact Score = 0**: Function has no impact OR is fully covered
- **Priority = 0**: Function has zero impact score (filtered out unless all functions have zero impact)

## Method Call Resolution

Plugin automatically resolves method calls like `logger.error()` to actual definitions (e.g., `SnowfortLogger.error()`) for accurate impact calculation.
