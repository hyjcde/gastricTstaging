import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    // 允许通过内部 API 路由加载图片
    remotePatterns: [],
    // 允许本地 API 路由
    unoptimized: false,
    // 图片格式优化
    formats: ['image/avif', 'image/webp'],
    // 设备尺寸断点
    deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048, 3840],
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384],
  },
};

export default nextConfig;
