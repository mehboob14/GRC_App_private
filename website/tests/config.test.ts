import assert from "node:assert/strict";
import { test } from "node:test";
import { optionalHttpsUrl } from "../lib/site-config";
import { parseInterest } from "../components/site/demo-form";

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
