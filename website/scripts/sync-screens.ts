/**
 * Converts product screenshots into the optimised WebP files the docs and
 * module pages use, and writes their manifest (dimensions + element boxes for
 * walkthrough hotspots).
 *
 *   npx tsx scripts/sync-screens.ts --from <dir-with-png-and-manifest.json>
 *
 * The source is a capture run from the application with demonstration data
 * (see README, "Screenshots"). Captures are taken at 1440×900 CSS pixels and
 * 2× density; we keep 2× for sharpness and let the browser scale.
 */
import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import sharp from "sharp";

const root = path.resolve(import.meta.dirname, "..");
const args = process.argv.slice(2);
const fromIndex = args.indexOf("--from");
const from = fromIndex >= 0 ? path.resolve(args[fromIndex + 1]) : path.resolve(root, "../docs/user-guide/images");
const outDir = path.join(root, "public/docs/screens");
const manifestPath = path.join(root, "content/docs/screens.json");

interface Element { key: string; label: string; x: number; y: number; w: number; h: number }
interface Entry { width: number; height: number; title?: string; elements?: Element[]; dark?: boolean }

const captureManifest: Record<string, { title?: string; elements?: Element[]; width?: number; height?: number }> = {};
const manifestFile = path.join(from, "manifest.json");
if (existsSync(manifestFile)) {
  const list = JSON.parse(readFileSync(manifestFile, "utf8")) as { name: string; title?: string; elements?: Element[]; width?: number; height?: number }[];
  for (const item of list) captureManifest[item.name] = item;
}

mkdirSync(outDir, { recursive: true });
const manifest: Record<string, Entry> = existsSync(manifestPath) ? JSON.parse(readFileSync(manifestPath, "utf8")) : {};

const files = readdirSync(from).filter((file) => file.endsWith(".png"));
for (const file of files) {
  const name = file.replace(/\.png$/, "");
  const input = path.join(from, file);
  const meta = await sharp(input).metadata();
  // CSS size: captures are 2x; the old guide images are 1x at 1440 wide.
  const scale = (meta.width ?? 1440) > 2000 ? 2 : 1;
  let image = sharp(input);
  if (scale === 1 && meta.width === 1440 && meta.height === 900) {
    // The original guide captures show the app's temporary third-party mark at
    // x=24..50, y=24..49. Paint the Verity mark over it; fresh captures already
    // carry the Verity mark and skip this.
    const [red, green, blue] = await sharp(input).extract({ left: 10, top: 20, width: 1, height: 1 }).removeAlpha().raw().toBuffer();
    const background = `#${[red, green, blue].map((value) => value.toString(16).padStart(2, "0")).join("")}`;
    const opacity = (red + green + blue) / 3 < 210 ? 0.4 : 1;
    const patch = Buffer.from(`<svg xmlns="http://www.w3.org/2000/svg" width="43" height="44" viewBox="0 0 43 44">
      <rect width="43" height="44" fill="${background}"/>
      <svg x="8.5" y="9" width="26" height="26" viewBox="0 0 32 32" opacity="${opacity}">
        <path d="M16 2.5 28 9.25 16 16 4 9.25Z" fill="#7DD3FC"/><path d="M4 9.25 16 16v13.5L4 22.75Z" fill="#0EA5E9"/><path d="M16 16 28 9.25v13.5L16 29.5Z" fill="#0369A1"/>
        <path d="m9.6 16.4 4.6 4.4 8.6-9.6" fill="none" stroke="#fff" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </svg>`);
    image = sharp(await sharp(input).composite([{ input: patch, left: 15, top: 13 }]).png().toBuffer());
  }
  await image.webp({ quality: 84, effort: 6, smartSubsample: true }).toFile(path.join(outDir, `${name}.webp`));
  const capture = captureManifest[name.replace(/\.dark$/, "")];
  manifest[name] = {
    width: Math.round((meta.width ?? 1440) / scale),
    height: Math.round((meta.height ?? 900) / scale),
    ...(capture?.title ? { title: capture.title } : {}),
    ...(capture?.elements?.length && !name.endsWith(".dark") ? { elements: capture.elements } : {}),
  };
}

const sorted = Object.fromEntries(Object.entries(manifest).sort(([a], [b]) => a.localeCompare(b)));
writeFileSync(manifestPath, `${JSON.stringify(sorted, null, 2)}\n`);
console.log(`Synced ${files.length} screenshot(s) from ${path.relative(process.cwd(), from)} to public/docs/screens`);
