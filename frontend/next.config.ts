import type { NextConfig } from "next";
import path from "path";
import { loadEnvConfig } from "@next/env";

// Load NEXT_PUBLIC_* vars from project root .env (not just frontend/)
loadEnvConfig(path.join(__dirname, ".."));

const nextConfig: NextConfig = {
  reactStrictMode: true,
};

export default nextConfig;
