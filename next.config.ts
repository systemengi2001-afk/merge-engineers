import type { NextConfig } from 'next';

const isGitHubPages = process.env.GITHUB_ACTIONS === 'true';

const nextConfig: NextConfig = {
  env: {
    NEXT_PUBLIC_BASE_PATH: isGitHubPages ? '/merge-engineers' : '',
  },
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
