import type { MetadataRoute } from "next";
import { getGuidePages, guidePath } from "@/lib/guide";
import { getSiteConfig } from "@/lib/site-config";

export const dynamic = "force-static";

export default function sitemap(): MetadataRoute.Sitemap {
  const { siteUrl } = getSiteConfig();
  return ["/", "/demo/", ...getGuidePages().map((page) => guidePath(page.slug))].map((path) => ({ url: `${siteUrl}${path}` }));
}
