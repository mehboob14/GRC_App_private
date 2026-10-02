import { mkdirSync, readdirSync, unlinkSync, writeFileSync } from "node:fs";
import path from "node:path";
import sharp from "sharp";
import { getGuidePages, getSearchEntries, guideRoot, validateGuide } from "../lib/guide";
import { getSiteConfig } from "../lib/site-config";

async function prepareGuide(): Promise<void> {
  const pages = getGuidePages();
  validateGuide(pages);
  getSiteConfig();

  const sourceImages = path.join(guideRoot, "images");
  const targetImages = path.resolve(process.cwd(), "public/guide-images");
  const filenames = readdirSync(sourceImages).filter((name) => name.endsWith(".png"));
  mkdirSync(targetImages, { recursive: true });
  for (const old of readdirSync(targetImages)) {
    if (old.endsWith(".png") && !filenames.includes(old)) unlinkSync(path.join(targetImages, old));
  }
  for (const filename of filenames) {
    const source = path.join(sourceImages, filename);
    const metadata = await sharp(source).metadata();
    if (metadata.width !== 1440 || metadata.height !== 900) {
      throw new Error(`${filename}: screenshot layout changed; review brand replacement coordinates`);
    }
    // Current guide captures have the demo-only Vimeo mark at x=24..50, y=24..49.
    // Replace that small area in generated copies; source guide files stay intact.
    const pixel = await sharp(source).extract({ left: 10, top: 20, width: 1, height: 1 }).removeAlpha().raw().toBuffer();
    const [red, green, blue] = pixel;
    const background = `#${[red, green, blue].map((value) => value.toString(16).padStart(2, "0")).join("")}`;
    const dimmed = (red + green + blue) / 3 < 210;
    const patch = Buffer.from(`<svg xmlns="http://www.w3.org/2000/svg" width="43" height="44" viewBox="0 0 43 44">
      <rect width="43" height="44" fill="${background}"/>
      <path d="M21.5 6 36 14.3v16.4L21.5 39 7 30.7V14.3L21.5 6Z" fill="none" stroke="#1689c6" stroke-opacity="${dimmed ? ".38" : "1"}" stroke-width="2.7"/>
      <path d="m14 22 5 5 10-11" fill="none" stroke="#1689c6" stroke-opacity="${dimmed ? ".38" : "1"}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>`);
    await sharp(source).composite([{ input: patch, left: 15, top: 13 }]).png({ compressionLevel: 9 }).toFile(path.join(targetImages, filename));
  }
  writeFileSync(path.resolve(process.cwd(), "public/guide-search.json"), JSON.stringify(getSearchEntries(pages)));
  console.log(`Prepared ${pages.length} guide pages and ${filenames.length} branded screenshot copies`);
}

prepareGuide().catch((error: unknown) => {
  console.error(error);
  process.exitCode = 1;
});
