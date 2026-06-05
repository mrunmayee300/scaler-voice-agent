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
  // Inline NEXT_PUBLIC_* at build time (required for static export on Vercel)
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
    NEXT_PUBLIC_VAPI_PUBLIC_KEY: process.env.NEXT_PUBLIC_VAPI_PUBLIC_KEY,
    NEXT_PUBLIC_VAPI_ASSISTANT_ID: process.env.NEXT_PUBLIC_VAPI_ASSISTANT_ID,
    NEXT_PUBLIC_CANDIDATE_NAME: process.env.NEXT_PUBLIC_CANDIDATE_NAME,
  },
};

export default nextConfig;
