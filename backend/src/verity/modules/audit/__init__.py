"""The append-only audit log. Never updated, never deleted from.

Every other module reaches the trail through ``verity.modules.audit.service`` —
``AuditService.record`` on the caller's own session — never through the repository
or the table. The module deliberately has no other public surface
(openspec/changes/add-audit-trail/proposal.md).
"""
