---
name: verity-auth-redesign
description: "Verity auth screens rebuilt (uncommitted, 2026-09-14) on features/iam/auth-kit; control map hero replaced the framework marquee"
metadata: 
  node_type: memory
  type: project
  originSessionId: f9330b17-d5d7-425a-8820-282896af2e69
  modified: 2026-09-14T14:50:24.495Z
---

All signed out screens (sign in, MFA, workspace choice, sign up, check email, forgot, reset, verify, invite, MFA enroll, recovery codes) use `frontend/src/features/iam/auth-kit/`: AuthField/AuthPasswordField (caps lock, live policy checklist mirroring backend DEFAULT policy), FailureAlert + `describeAuthFailure(error, context)` (replaced the deleted `describeAuthError`), OtpInput (auto submit, paste), EmailSuggestion (OSA distance typo fix), SsoOptions (Soon), ControlMap hero (4 real controls mapped to SOC 2/ISO/NIST/HIPAA/PCI/GDPR refs). AuthSubmitButton (`vx-cta` CSS) is the primary everywhere; `CtaLink` for navigating primaries.

Recovery codes display with a space; `normalizeRecoveryCode` restores the hyphen the server hashed. Backend has no login rate limit or lockout yet, so no countdown UI. Reset/invite checklist uses default rules; stricter tenant policy errors land on the field from the server.

**Why:** user asked for next level B2B auth UX. **How to apply:** extend the kit, don't reintroduce TextField/ErrorBanner on auth pages. Related: [[feedback-speed-and-standout-copy]], [[verity-error-handling]].
