---
name: Review Traceability
description: Check requirements traceability and detect any spec drift.
agent: SpecKitFlow Implementation Agent
---

# Review Traceability

@speckit-flow Please review traceability.

## Request

{{input}}

## Traceability Check

1. **Read** `specs/speckit-flow/traceability.md` for requirements matrix
2. **Compare** implemented code against requirements
3. **Detect** any spec drift:
   - Code that doesn't map to a requirement
   - Requirements without implementing tasks
   - Schema deviations from plan.md
4. **Report** findings with recommended actions

Focus on the current phase's requirements (REQ-ARCH, REQ-DAG, REQ-STATE for Phase 1).
