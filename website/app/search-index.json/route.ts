import { buildSearchIndex } from "@/lib/docs";

export const dynamic = "force-static";

/** The documentation search index, generated at build time from the MDX source. */
export function GET() {
  return Response.json(buildSearchIndex());
}
