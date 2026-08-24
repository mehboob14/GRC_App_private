# ADR-0012: Rich-text editor and document viewer stack

**Status:** Accepted
**Source:** Documents & Policies module (Stage 4), client design references

## Context

The Documents & Policies module lets a tenant author policies in-app and view uploaded
policy files (PDF/Word). The client's reference UI shows a full rich-text editor
(headings, lists, text colour, blockquote, images, fonts, undo/redo) opened in a
dedicated tab, and a content viewer with zoom controls. We had no editor or viewer
dependency in the frontend, and the shipped design system hand-rolls its own visuals
(no component libraries), so this is a deliberate exception.

## Decision

**Authoring: TipTap (ProseMirror), storing HTML.** Add `@tiptap/react` + `@tiptap/pm`
+ `@tiptap/starter-kit` and the extensions the design needs: `extension-image`,
`extension-text-style` (which in TipTap v3 also provides `Color` and `FontFamily`),
`extension-link`, `extension-placeholder`. Content is stored as **HTML**, not markdown:
the design requires text colour, fonts and inline images, which markdown cannot carry.
HTML is sanitised with **DOMPurify** on render.

**Viewing uploaded files: PDF.js and mammoth, added when files exist.** The viewer for
uploaded PDF/Word will use `pdfjs-dist` (react-pdf) for PDFs and `mammoth` for docx→HTML.
These are **deferred to Stage 5** (backend file storage): there is no file to render from
the Stage 1-4 mock, so adding them now would ship unused code. Authored-HTML documents are
viewed now with a zoomable sanitised-HTML "paper" container.

The reference implementation in the `GRC-Tenant` repo also chose TipTap; we reuse its
scaffold but switch markdown→HTML and add the colour/font/image extensions it lacked.

## Alternatives considered

**Markdown authoring (as GRC-Tenant does).** Rejected: markdown cannot represent text
colour, font family, or arbitrary inline images, all of which the client design requires.

**Lexical / Slate / Quill / CKEditor.** Rejected: TipTap is MIT, ProseMirror-based,
React-first, matches the reference codebase, and has first-party extensions for every
toolbar control in the design. CKEditor's rich features carry licensing strings.

**`<iframe>` for PDF (native browser zoom), no pdf.js.** Considered for simplicity; the
design calls for in-app zoom controls and a consistent chrome, so PDF.js is preferred.
Revisit if PDF.js bundle size becomes a problem.

## Consequences

TipTap adds ~10 packages to the frontend. Stored policy content is HTML and MUST be
sanitised (DOMPurify) wherever it is rendered — an unsanitised render is an XSS hole, since
content is user-authored. The editor opens as a full-screen route outside the app shell.
PDF.js/mammoth land with the backend file-serving slice (Stage 5), documented there.

**Revisit when:** collaborative editing (multiple cursors) is needed — that would push
toward TipTap's Yjs/collab layer or a hosted service.
