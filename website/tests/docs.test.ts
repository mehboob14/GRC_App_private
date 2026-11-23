import assert from "node:assert/strict";
import { test } from "node:test";
import { buildSearchIndex, getAllDocs, getDocContent, getToc, legacyRedirects, validateDocs } from "../lib/docs";
import { docsOrder } from "../content/docs/nav";

test("every documentation page validates: front matter, links, fragments, screenshots, components", () => {
  assert.doesNotThrow(() => validateDocs());
  assert.equal(getAllDocs().length, docsOrder.length);
});

test("every page compiles to a component", async () => {
  for (const page of getAllDocs()) {
    const Content = await getDocContent(page.slug);
    assert.equal(typeof Content, "function", page.slug);
  }
});

test("old chapter addresses redirect to pages that exist", () => {
  for (const [old, target] of Object.entries(legacyRedirects)) assert.ok(docsOrder.includes(target), `${old} -> ${target}`);
});

test("contents rails list each page's sections", () => {
  const toc = getToc("compliance/controls");
  assert.ok(toc.length >= 3);
  assert.ok(toc.every((item) => item.id && item.text && (item.depth === 2 || item.depth === 3)));
});

test("the search index covers every page with section text", () => {
  const index = buildSearchIndex();
  assert.equal(index.length, docsOrder.length);
  for (const doc of index) {
    assert.ok(doc.sections.length > 0, `${doc.slug} has no searchable sections`);
    assert.ok(doc.sections.some((section) => section.text.length > 40), `${doc.slug} has no body text`);
  }
});
