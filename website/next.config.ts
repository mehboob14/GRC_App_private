import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
  // `next dev` would otherwise write AGENTS.md and CLAUDE.md into this folder.
  agentRules: false,
};

export default nextConfig;
