import type { NextConfig } from "next";
import path from "path";
import { existsSync } from "fs";
import { loadEnvConfig } from "@next/env";

// Local dev: load NEXT_PUBLIC_* from project root .env
// Vercel: uses dashboard env vars only
const rootEnv = path.join(__dirname, "..", ".env");
if (existsSync(rootEnv)) {
  loadEnvConfig(path.join(__dirname, ".."));
}

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Static export — reliable on Vercel when monorepo root-dir/output settings drift
  output: "export",
  trailingSlash: true,
};

export default nextConfig;
