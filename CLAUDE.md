# Rules

## MANDATORY: Follow user's method exactly
When the user describes a specific computation/geometric method, implement it VERBATIM. Never substitute with own heuristic or "equivalent" approach.

Before writing code:
1. Restate the user's method in pseudocode
2. Get confirmation
3. Then implement exactly as stated

If unsure how to implement, ASK. Do not silently replace.

Use known landmark coordinates for deterministic selection. Never use mesh-average heuristics (body_cx, mean X, etc.) when exact landmark positions are available.

## MANDATORY: First-principles development
Never patch symptoms. Every implementation must follow this order:

1. **Test first** — Write a test with measurable success criteria BEFORE writing implementation code
2. **Diagnose with data** — Run failing code through the test, get numbers. Don't guess from screenshots
3. **Design to eliminate failure** — Don't fix symptoms; design so the failure mode is structurally impossible
4. **Verify with test** — Numbers prove correctness, not "looks good"

Never do screenshot → guess → patch → screenshot → guess → patch cycles.
