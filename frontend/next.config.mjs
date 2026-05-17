/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1",
    NEXT_PUBLIC_DEMO_IMPORTER_PK: process.env.NEXT_PUBLIC_DEMO_IMPORTER_PK || "",
    NEXT_PUBLIC_DEMO_EXPORTER_PK: process.env.NEXT_PUBLIC_DEMO_EXPORTER_PK || "",
  },
};

export default nextConfig;
