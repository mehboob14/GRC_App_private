# AI features and their limits

AI appears in three places: document drafting (Phase 2), scan report parsing (Phase 1), and risk
mitigation proposals (Phase 3).

## The rule that governs all of them

**AI drafts. Humans decide.** Nothing AI produces is published, approved, or acted on without a
person reviewing it. AI makes no compliance decisions.

This is not caution for its own sake. The product's value is that an auditor can trust its output.
One AI-authored policy published without review, or one AI-asserted control pass, destroys that
permanently.

## Implementation requirements

- **Origin is recorded.** AI-authored content is marked (`origin = ai_draft`) and stays marked
  through its lifecycle. An auditor must be able to tell what was machine-generated.
- **The same approval gate.** AI drafts pass through the identical human review and approval path as
  manual content. There is no separate, lighter path for AI output.
- **No autonomous state changes.** AI never marks a control passing, never closes a finding, never
  approves evidence, never changes a risk score.
- **Report parsing produces proposals, not records.** AI-parsed scan findings land as a reviewable
  set. A person confirms before instances are created.
- **Prompts and outputs are logged** with the tenant, actor, model, and version, so a bad draft is
  traceable.
- **Tenant data never leaves the deployment boundary** without an explicit, documented decision.
  Confirm the provider's data-handling terms before any tenant content is sent, and record it as an
  ADR.

## Failure handling

AI calls are external calls: timeouts, circuit breaker, and a fallback that degrades to the manual
path. A provider outage must never block a user from writing their own policy. Treat the AI provider
exactly like any other third party — it is not special, and it is not reliable.
