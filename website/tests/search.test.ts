import assert from "node:assert/strict";
import { test } from "node:test";
import { excerpt, search, tokenize, type IndexDoc } from "../lib/search";

const index: IndexDoc[] = [
  { slug: "risk/treatment-and-acceptance", title: "Treat or accept a risk", description: "Decide what to do about a risk.", group: "Risk", status: "live", sections: [{ id: "", heading: "Treat or accept a risk", text: "Once a risk is in the register you decide what to do about it." }, { id: "accept-a-risk", heading: "Accept a risk", text: "An acceptance needs a reason, an approver and an expiry." }] },
  { slug: "vulnerabilities/remediation", title: "Remediation and exceptions", description: "Fix findings on time.", group: "Security operations", status: "live", sections: [{ id: "exceptions-and-acceptance", heading: "Exceptions and acceptance", text: "Request an exception when a fix cannot be done yet; accept the risk with an expiry." }] },
  { slug: "risk/enterprise-risk", title: "Enterprise risk", description: "Planned enterprise risk management.", group: "Risk", status: "soon", sections: [{ id: "what-it-will-do", heading: "What it will do", text: "Key risk indicators and appetite for the whole risk programme." }] },
];

test("stop words are dropped unless nothing else is left", () => {
  assert.deepEqual(tokenize("How do I accept a risk?"), ["accept", "risk"]);
  assert.deepEqual(tokenize("the"), ["the"]);
  assert.deepEqual(tokenize("   "), []);
});

test("title matches rank above body matches, and results link to the best section", () => {
  const results = search(index, "accept risk");
  assert.equal(results[0].slug, "risk/treatment-and-acceptance");
  assert.equal(results[0].href, "/docs/risk/treatment-and-acceptance/#accept-a-risk");
  assert.ok(results.some((result) => result.slug === "vulnerabilities/remediation"));
});

test("every term must appear on the page", () => {
  assert.deepEqual(search(index, "accept appetite").map((result) => result.slug), []);
  assert.deepEqual(search(index, "appetite").map((result) => result.slug), ["risk/enterprise-risk"]);
});

test("an empty query returns nothing, and excerpts centre on the match", () => {
  assert.deepEqual(search(index, ""), []);
  const text = `${"lorem ".repeat(60)}expiry is required ${"ipsum ".repeat(60)}`;
  const snippet = excerpt(text, ["expiry"]);
  assert.ok(snippet.includes("expiry"));
  assert.ok(snippet.startsWith("…"));
});
