"""AI drafting and proposal generation.

**AI drafts. Humans decide.** Rule 8 in CLAUDE.md, and the limit that governs
everything this module will ever contain. Nothing produced here is published, approved,
or acted on without a person reviewing it: AI never marks a control passing, never
closes a finding, never approves evidence, never changes a risk score. Content authored
here is marked ``origin = ai_draft``, stays marked through its whole lifecycle so an
auditor can tell what was machine-generated, and passes through the *identical* human
approval gate as content a person wrote — there is no separate, lighter path for AI
output. The product's value is that an auditor can trust its output, and one
AI-authored policy published without review destroys that permanently.

This change ships the traced client and nothing else. AI features are Phase 2; see
docs/architecture/ai-features.md.
"""
