import assert from "node:assert/strict";
import { test } from "node:test";
import { optionalHttpsUrl } from "../lib/site-config";
import {
  buildDemoPayload,
  checkDemoField,
  demoErrorMessage,
  demoHref,
  firstName,
  interestSentence,
  parseInterest,
  retryAfterSeconds,
  safeInterest,
  safeSource,
  validateDemoRequest,
} from "../lib/demo";

test("optional endpoints must be HTTPS without credentials, and empty means not configured", () => {
  assert.equal(optionalHttpsUrl(undefined, "X"), null);
  assert.equal(optionalHttpsUrl("", "X"), null);
  assert.equal(optionalHttpsUrl("https://forms.example.com/demo", "X"), "https://forms.example.com/demo");
  assert.throws(() => optionalHttpsUrl("http://forms.example.com/demo", "X"), /HTTPS/);
  assert.throws(() => optionalHttpsUrl("https://user:secret@forms.example.com/", "X"), /credentials/);
  assert.throws(() => optionalHttpsUrl("not a url", "X"), /valid URL/);
});

test("demo links preselect a module interest and a pricing tier", () => {
  assert.deepEqual(parseInterest("third-party-risk"), { interests: ["third-party-risk"], tier: undefined });
  assert.deepEqual(parseInterest("pricing:regulated"), { interests: ["pricing"], tier: "regulated" });
  assert.deepEqual(parseInterest("continuous-monitoring"), { interests: [], tier: undefined });
  assert.deepEqual(parseInterest(null), { interests: [] });
});

test("every demo action is a link that carries what the visitor was reading", () => {
  assert.equal(demoHref(), "/demo/");
  assert.equal(demoHref({ source: "header" }), "/demo/?from=header");
  assert.equal(demoHref({ interest: "pricing:growth", source: "pricing-growth" }), "/demo/?interest=pricing%3Agrowth&from=pricing-growth");
});

test("what a link says is used only in the shape the endpoint accepts", () => {
  assert.equal(safeInterest("third-party-risk"), "third-party-risk");
  assert.equal(safeInterest("pricing:growth"), "pricing:growth");
  assert.equal(safeInterest("<script>alert(1)</script>"), null);
  assert.equal(safeInterest(null), null);
  assert.equal(safeSource("module-integrations"), "module-integrations");
  // The longest closing call to action is cut to the length the endpoint takes, not dropped.
  assert.equal(safeSource("module-vulnerability-management-final"), "module-vulnerability-management");
  assert.equal(safeSource("../etc"), "demo-page");
  assert.equal(safeSource(null), "demo-page");
});

test("the message starts with the topic a link named, and stays empty when it named nothing we know", () => {
  assert.equal(interestSentence("third-party-risk"), "Interested in: Third-party risk");
  assert.equal(interestSentence("pricing:growth"), "Interested in: Pricing (Growth plan)");
  assert.equal(interestSentence("pricing:no-such-plan"), "Interested in: Pricing");
  assert.equal(interestSentence("roadmap"), "");
  assert.equal(interestSentence(null), "");
});

test("the form needs a name, a work email and a company, and says what to do about each", () => {
  assert.deepEqual(validateDemoRequest({ name: "Ada Lovelace", email: "ada@example.com", company: "Analytical Engines", message: "" }), {});
  const errors = validateDemoRequest({ name: " ", email: "ada@", company: "", message: "" });
  assert.deepEqual(Object.keys(errors), ["name", "email", "company"]);
  assert.match(errors.email ?? "", /name@company\.com/);
  assert.equal(checkDemoField("name", "A"), "Enter your full name.");
  assert.equal(checkDemoField("email", "  ada@example.com  "), null);
  assert.equal(firstName("  Ada  Lovelace "), "Ada");
  assert.equal(firstName(""), "");
});

test("the request body is trimmed, snake case, and leaves empty optional fields out", () => {
  const body = buildDemoPayload(
    { name: " Ada Lovelace ", email: " ada@example.com ", company: " Analytical Engines ", message: "  " },
    { interest: null, source: "header", page: "/pricing/", website: "" },
  );
  assert.deepEqual(JSON.parse(JSON.stringify(body)), { full_name: "Ada Lovelace", email: "ada@example.com", company: "Analytical Engines", source: "header", page: "/pricing/", website: "" });
  const withTopic = buildDemoPayload(
    { name: "Ada Lovelace", email: "ada@example.com", company: "Analytical Engines", message: "Interested in: Pricing" },
    { interest: "pricing:growth", source: "pricing-growth", page: "", website: "" },
  );
  assert.equal(withTopic.interest, "pricing:growth");
  assert.equal(withTopic.message, "Interested in: Pricing");
  assert.equal(withTopic.page, undefined);
});

test("a failed request is explained as something the visitor can act on", () => {
  assert.match(demoErrorMessage(429), /Wait a few minutes/);
  assert.match(demoErrorMessage(429, 120), /Wait a few minutes/);
  // A refusal that says to come back much later means they have most likely asked already.
  assert.match(demoErrorMessage(429, 44_000), /we have it and will reply by email/);
  assert.match(demoErrorMessage(422), /Check your name, email and company/);
  assert.match(demoErrorMessage(null), /Check your connection/);
  assert.match(demoErrorMessage(502), /Check your connection/);
});

test("Retry-After is read as seconds, and ignored when it is missing or a date", () => {
  assert.equal(retryAfterSeconds("120"), 120);
  assert.equal(retryAfterSeconds("0"), 0);
  assert.equal(retryAfterSeconds(null), null);
  assert.equal(retryAfterSeconds("Wed, 21 Oct 2026 07:28:00 GMT"), null);
  assert.equal(retryAfterSeconds("-5"), null);
});
