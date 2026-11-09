import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  ...(process.env.STANDALONE ? { output: "standalone" as const } : {}), // small self-contained server, set by the Dockerfile
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
