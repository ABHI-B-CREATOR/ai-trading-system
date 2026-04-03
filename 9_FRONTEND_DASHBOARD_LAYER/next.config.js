/**
 * Next.js config file
 * NOTE: This project uses Vite, not Next.js
 * This file is kept for reference only
 * 
 * Frontend config is in: vite.config.ts
 * TypeScript config is in: tsconfig.json
 */

/* Deprecated - Using Vite instead */
const nextConfig = {
  reactStrictMode: true,
  experimental: {
    appDir: true
  },
  env: {
    BACKEND_URL: "http://localhost:8000",
    WS_URL: "ws://localhost:8765"
  }
}

module.exports = nextConfig
