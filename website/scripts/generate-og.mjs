/**
 * Regenerates public/og.png (1200×630) from the running site, so the social
 * card uses the site's own fonts and hero art.
 *
 *   npm run dev                                   # in one terminal
 *   npx -y -p playwright@1.56.1 node scripts/generate-og.mjs [http://localhost:3001]
 */
import { chromium } from "playwright";
import path from "node:path";

const base = process.argv[2] ?? "http://localhost:3001";
const out = path.resolve(import.meta.dirname, "../public/og.png");

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1200, height: 630 }, deviceScaleFactor: 1, reducedMotion: "reduce" });
await page.goto(`${base}/`, { waitUntil: "networkidle" });
const art = await page.evaluate(() => document.querySelector("svg.iso-hero")?.outerHTML ?? "");
const mark = await page.evaluate(() => document.querySelector("header svg")?.outerHTML ?? "");
await page.evaluate(({ art, mark }) => {
  document.body.innerHTML = `
    <div style="position:fixed;inset:0;display:flex;background:linear-gradient(180deg,#E6ECF2 0%,#F3F6F9 60%,#FFFFFF 100%);font-family:Inter,sans-serif;overflow:hidden">
      <div style="position:relative;z-index:1;display:flex;flex-direction:column;justify-content:center;padding:0 0 0 72px;width:640px">
        <div style="display:flex;align-items:center;gap:10px;color:#0B0F17">${mark.replace(/width="\\d+"/, 'width="36"').replace(/height="\\d+"/, 'height="36"')}<span style="font-size:30px;font-weight:600;letter-spacing:-0.035em">verity</span></div>
        <p style="margin:56px 0 0;font-family:'JetBrains Mono Variable',monospace;font-size:15px;letter-spacing:0.14em;text-transform:uppercase;color:#5D6878">Compliance as a service, end to end</p>
        <h1 style="margin:18px 0 0;font-family:'Source Serif 4 Variable',Georgia,serif;font-weight:400;font-size:64px;line-height:1.04;letter-spacing:-0.02em;color:#0B0F17">Your source of truth for compliance and security</h1>
        <p style="margin:28px 0 0;font-size:20px;line-height:1.5;color:#363F4E">Frameworks, evidence, policies, risk, vendors, assets and vulnerabilities in one connected platform.</p>
      </div>
      <div style="position:absolute;right:-60px;top:110px;width:700px">${art}</div>
    </div>`;
}, { art, mark });
await page.waitForTimeout(300);
await page.screenshot({ path: out });
await browser.close();
console.log(`Wrote ${out}`);
