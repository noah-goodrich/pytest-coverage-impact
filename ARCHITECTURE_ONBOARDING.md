# Architecture Onboarding Strategy

This project is moving towards a strict Clean Architecture.
Follow this 3-Phase Refactor Plan to achieve compliance without stopping development.

## Phase 1: Package Organization (Structure)
**Goal**: Eliminate "God Files" and "Root Soup".
- [ ] Fix W9011 (Deep Structure): Move root-level logic files into sub-packages.
- [ ] Fix W9010 (God File): Split files containing multiple heavy components or mixed layers.

## Phase 2: Layer Separation (Boundaries)
**Goal**: Enforce strict dependency rules.
- [ ] Fix W9001-9004: Ensure Domain/use_cases do not import Infrastructure.
- [ ] Introduce Dependency Injection using Protocols.

## Phase 3: Coupling Hardening (Internal Quality)
**Goal**: Reduce complexity and coupling.
- [ ] Fix W9006 (Law of Demeter): Resolve chained calls.
- [ ] Ensure all I/O is isolated in Infrastructure.

---
**Configuration Note**:
This project uses `pylint-clean-architecture` in **Architecture-Only Mode** (style checks disabled)
because other tools (ruff/black/flake8) are detected.
