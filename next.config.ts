import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  async redirects() {
    return [
      {
        source: '/podcast',
        destination: '/?utm_source=podcast&utm_medium=audio&utm_campaign=launch_2026',
        permanent: false,
      },
    ];
  },
};

export default nextConfig;
