import type { NextConfig } from 'next';

const isGitHubPages = process.env.GITHUB_ACTIONS === 'true';

const nextConfig: NextConfig = {
  ...(isGitHubPages
    ? {
        output: 'export',
        basePath: '/merge-engineers',
        assetPrefix: '/merge-engineers/',
        trailingSlash: true,
      }
    : {}),
};

export default nextConfig;

