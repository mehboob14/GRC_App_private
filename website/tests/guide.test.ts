import assert from "node:assert/strict";
import { readdirSync } from "node:fs";
import { test } from "node:test";
import path from "node:path";
import sharp from "sharp";
import { getGuidePages, getSearchEntries, imageInfo, resolveGuideHref, validateGuide } from "../lib/guide";

test("every published guide chapter and screenshot is reachable", () => {
  const pages = getGuidePages();
  assert.equal(pages.length, 14);
  assert.doesNotThrow(() => validateGuide(pages));
  const image = imageInfo("controls-register.png");
  assert.ok(image.width > 0 && image.height > 0);
});

test("guide links retain chapter and heading destinations", () => {
  const pages = getGuidePages();
  const source = pages.find((page) => page.slug === "02-finding-your-way-around");
  assert.ok(source);
  assert.equal(
    resolveGuideHref(source, "12-settings-and-administration.md#roles-and-what-they-allow", pages),
    "/docs/12-settings-and-administration/#roles-and-what-they-allow",
  );
  assert.throws(() => resolveGuideHref(source, "../CLAUDE.md", pages), /missing guide target/);
  assert.throws(() => resolveGuideHref(source, "javascript:alert(1)", pages), /disallowed link/);
});

test("search covers chapters and sections without depending on browser APIs", () => {
  const entries = getSearchEntries();
  assert.ok(entries.some((entry) => entry.title === "Evidence" && entry.body.toLowerCase().includes("control")));
  assert.ok(entries.some((entry) => entry.href.includes("#")));
});

test("generated screenshot branding changes only the mark region", async () => {
  const filenames = readdirSync(path.resolve("../docs/user-guide/images")).filter((name) => name.endsWith(".png"));
  assert.equal(filenames.length, 43);
  for (const filename of filenames) {
    const source = await sharp(path.resolve("../docs/user-guide/images", filename)).ensureAlpha().raw().toBuffer();
    const output = await sharp(path.resolve("public/guide-images", filename)).ensureAlpha().raw().toBuffer();
    assert.equal(source.length, output.length);
    let changed = 0;
    for (let y = 0; y < 900; y++) {
      for (let x = 0; x < 1440; x++) {
        const offset = (y * 1440 + x) * 4;
        if (source[offset] === output[offset] && source[offset + 1] === output[offset + 1] && source[offset + 2] === output[offset + 2]) continue;
        assert.ok(x >= 15 && x < 58 && y >= 13 && y < 57, `${filename}: pixel outside brand patch changed at ${x},${y}`);
        changed++;
      }
    }
    assert.ok(changed > 0, `${filename}: mark was not replaced`);
  }
});
