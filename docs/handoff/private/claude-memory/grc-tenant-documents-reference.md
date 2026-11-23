---
name: grc-tenant-documents-reference
description: "Reusable document/policy code in the GRC-Tenant repo, for building Verity's documents module"
metadata: 
  node_type: memory
  type: reference
  originSessionId: d5f1663f-14a9-4f46-8f2f-956fdfa856a3
  modified: 2026-08-23T15:22:14.947Z
---

Reference codebase for building Verity's Documents & Policies module: `C:\Users\HP\OneDrive\Documents\GRC-Tenant` (Next.js 14 + FastAPI + SQLAlchemy; the module is called "Governance"). Surveyed 2026-08-23. See [[verity-multiframework-design]] / the documents plan.

**Directly reusable (near drop-in):**
- Rich-text editor: `grc-frontend/src/app/(dashboard)/governance/documents/_RichTextEditor.tsx` — TipTap (`@tiptap/react`, `starter-kit`, `extension-link`, `tiptap-markdown`), markdown-in/markdown-out. BUT minimal: no image upload, no color, no font-family, H1-H3 only. Verity needs those (per client screenshot) → reuse the scaffold, switch output markdown→**HTML** (markdown can't carry color/fonts), add `@tiptap/extension-image` + `text-style` + `color` + `font-family`. Sanitize with DOMPurify on render.
- Markdown renderer + AI-markdown normalizer: `grc-frontend/src/components/governance/GovernanceDocumentMarkdown.tsx` (react-markdown + remark-gfm).
- File viewer pattern: `grc-frontend/src/components/evidence/EvidenceViewer.tsx` — PDF via `<iframe>` blob URL (native browser zoom, no react-pdf), images via img, xlsx via SheetJS, docx/pdf→HTML via backend `/view-html`.

**Reference-only (coupled to their project, mirror don't copy):**
- Data model: `backend/grc/models/_13_governance_document_management_enhanced.py` — well-designed: documents + versions(change_type major/minor/patch) + reviewers + approval_steps(sequence, single/any/all) + audit_logs + review_history + link tables (control/risk/regulatory/asset) + signoff_assignments + signatures. Advanced/AI extras to defer: policy-statement parsing (`_18`), gap-analysis (`_19`), attestation campaigns (`_27`), config-driven workflows (`_20`, uses @xyflow/react React Flow).
- Backend API: `backend/grc/modules/governance/routers/documents.py` — upload, `/view-html` (PyPDF2 for pdf, python-docx for docx→HTML), `/export` (markdown→PDF), lifecycle, bulk ops. Storage = local disk (Verity should use its own ObjectStore instead).
- Frontend register/detail: `governance/documents/page.tsx` + `documents/_workspace/` (RegisterTable, LibraryTree, LifecycleBoard kanban, AttentionRail, RowActionsMenu); detail `documents/[id]/page.tsx` (3.9k lines; tabs viewer/statements/mappings/gap-analysis/sign-off/discussion/review-history). Harvest sub-components, not whole pages.
