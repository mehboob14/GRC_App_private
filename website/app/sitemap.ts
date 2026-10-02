import type { MetadataRoute } from "next";
import { getSiteConfig } from "@/lib/site-config";
import { modules } from "@/content/catalog";
import { industries } from "@/content/navigation";
import { docsOrder } from "@/content/docs/nav";

export const dynamic = "force-static";

export default function sitemap(): MetadataRoute.Sitemap {
  const { siteUrl } = getSiteConfig();
  const paths = [
    "/",
    "/platform/",
    ...modules.map((item) => `/platform/${item.slug}/`),
    ...industries.map((item) => `/solutions/${item.slug}/`),
    "/frameworks/",
    "/why-verity/",
    "/pricing/",
    "/security/",
    "/demo/",
    "/docs/",
    ...docsOrder.map((slug) => `/docs/${slug}/`),
  ];
  return paths.map((path) => ({ url: `${siteUrl}${path}` }));
}
