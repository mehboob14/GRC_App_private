# ADR-0004: Evidence anchors to controls, not to requirements

**Status:** Accepted
**Source:** Data Model and ER Design, Section 5

## Context

The platform ships SOC 2 first and adds ISO 27001, HIPAA, and GDPR later on the same engine.
Evidence collected once should satisfy every framework it applies to.

## Decision

Evidence maps to controls. Requirement coverage is derived through the control-requirement map.

## Alternatives considered

**Map evidence directly to framework requirements.** Rejected: every evidence item would need
re-attaching each time a framework is added.

## Consequences

A new framework instantly inherits all previously collected evidence. This is the mechanism behind
collect-once-satisfy-many, a core product claim. Requirement coverage is always a join, never a
stored value.
