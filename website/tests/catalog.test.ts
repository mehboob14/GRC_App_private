import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";
import { githubChecks, integrationCapabilities, libraryFacts, modules } from "../content/catalog";
import { docsOrder } from "../content/docs/nav";
import { getDocMeta } from "../lib/docs";

const seed = path.resolve(process.cwd(), "../backend/src/verity/seed/content");
const manifest = (pack: string) => JSON.parse(readFileSync(path.join(seed, pack, "MANIFEST.json"), "utf8"));

test("library facts on the site match the content that ships with every workspace", () => {
  const facts = Object.fromEntries(libraryFacts.map((fact) => [fact.label, Number(fact.value)]));
  assert.equal(facts["SOC 2 criteria mapped"], manifest("soc2").counts.requirements);
  assert.equal(facts["Control templates"], manifest("soc2").counts.control_templates);
  assert.equal(facts["Policy templates"], manifest("policies").counts.document_templates);
  assert.equal(facts["Library risks"], manifest("risk_library").risks);
});

test("the GitHub checks listed are exactly the checks GitHub implements", () => {
  const checks = JSON.parse(readFileSync(path.join(seed, "automation/checks.json"), "utf8")) as { name: string; implementations: string[] }[];
  const implemented = checks.filter((check) => check.implementations.includes("github")).map((check) => check.name);
  assert.deepEqual([...githubChecks].sort(), implemented.sort());
});

test("integration statuses follow the capability content, and not-planned providers are absent", () => {
  const capabilities = JSON.parse(readFileSync(path.join(seed, "automation/capabilities.json"), "utf8")) as { providers: { name: string; status: string }[] }[];
  const status = new Map(capabilities.flatMap((capability) => capability.providers.map((provider) => [provider.name, provider.status])));
  for (const group of integrationCapabilities) {
    for (const provider of group.providers) {
      const source = status.get(provider.name);
      assert.ok(source, `${provider.name} is not in capabilities.json`);
      assert.notEqual(source, "not_planned", `${provider.name} is not planned and must not be shown`);
      assert.equal(provider.status, source === "available" ? "live" : "soon", `${provider.name} status`);
    }
  }
});

test("module slugs are unique and each module's docs page agrees on its status", () => {
  const slugs = modules.map((item) => item.slug);
  assert.equal(new Set(slugs).size, slugs.length);
  for (const item of modules) {
    if (!item.docs) continue;
    assert.ok(docsOrder.includes(item.docs), `${item.slug} points to missing docs page ${item.docs}`);
    const page = getDocMeta(item.docs)!;
    if (item.status === "soon") assert.equal(page.status, "soon", `${item.slug} is coming soon but its docs page is ${page.status}`);
    if (item.status === "live") assert.notEqual(page.status, "soon", `${item.slug} is live but its docs page says coming soon`);
  }
});
