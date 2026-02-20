import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          DEFAULT: "#0B1120",
          light: "#1E293B",
        },
        cyan: {
          DEFAULT: "#06B6D4",
          light: "#22D3EE",
        },
      },
    },
  },
  plugins: [],
};

export default config;

