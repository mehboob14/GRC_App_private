import type { MetadataRoute } from "next";
import { getSiteConfig } from "@/lib/site-config";

export const dynamic = "force-static";

export default function robots(): MetadataRoute.Robots {
  const { siteUrl } = getSiteConfig();
  return { rules: { userAgent: "*", allow: "/" }, sitemap: `${siteUrl}/sitemap.xml` };
}
