import type { NextConfig } from "next";

// Static export: the demo is plain files, free to host anywhere.
// On GitHub Pages the site lives under /node-verdict.
const basePath = process.env.PAGES_BASE_PATH ?? "";

const nextConfig: NextConfig = {
  output: "export",
  basePath,
  images: { unoptimized: true },
  trailingSlash: true,
};

export default nextConfig;
