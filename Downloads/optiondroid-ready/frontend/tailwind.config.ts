import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: {
          base:    "#0a0b0d",
          surface: "#111318",
          raised:  "#181b22",
          border:  "#242830",
          hover:   "#1e2229",
        },
        text: {
          primary:   "#e8eaf0",
          secondary: "#8b909e",
          muted:     "#555b6a",
        },
        call: {
          DEFAULT: "#22c55e",
          dim:     "#166534",
          bg:      "#052e16",
        },
        put: {
          DEFAULT: "#ef4444",
          dim:     "#991b1b",
          bg:      "#2d0a0a",
        },
        accent: {
          DEFAULT: "#6366f1",
          hover:   "#818cf8",
          dim:     "#312e81",
        },
        warn:    "#f59e0b",
        success: "#22c55e",
        danger:  "#ef4444",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
      fontSize: {
        "2xs": ["0.625rem", { lineHeight: "1rem" }],
      },
      animation: {
        "pulse-fast": "pulse 0.8s cubic-bezier(0.4,0,0.6,1) infinite",
        "fade-in":    "fadeIn 0.15s ease-out",
      },
      keyframes: {
        fadeIn: {
          from: { opacity: "0", transform: "translateY(4px)" },
          to:   { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
