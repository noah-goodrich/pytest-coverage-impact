# Confidence in Priority Calculation

Confidence intervals are already included in priority calculation.

## Current Implementation

```
Priority = (Impact Score × Confidence) / (Complexity × Effort)
```

Where:
- `confidence = 1.0 - interval_width` (narrower interval = higher confidence)
- Confidence ranges from 0.0 (low) to 1.0 (high)

## How It Works

- **High confidence** (narrow interval): Priority score multiplied by high confidence → higher priority
- **Low confidence** (wide interval): Priority score multiplied by low confidence → lower priority
- **Uncertain predictions** are automatically deprioritized

## Example

```
Function A: Impact=100, Complexity=0.5, Confidence=0.9
→ Priority = (100 × 0.9) / (0.5 × 2.0) = 90.0

Function B: Impact=100, Complexity=0.5, Confidence=0.3
→ Priority = (100 × 0.3) / (0.5 × 2.0) = 30.0
```

Function A (high confidence) is prioritized over Function B (low confidence), even with same impact/complexity.

## Display

Terminal shows complexity with interval: `0.65 [±0.15]`
- Narrower interval = higher confidence = higher priority weight
