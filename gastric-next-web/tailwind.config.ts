import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: "#0e7490", // Teal-700
        "primary-hover": "#155e75",
        sidebar: "#0f172a", // Slate-900
        accent: "#38bdf8", // Sky-400
        success: "#10b981",
        warning: "#f59e0b",
        danger: "#ef4444",
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        serif: ['"Times New Roman"', 'serif'], // For reports
      },
    },
  },
  plugins: [],
};
export default config;

