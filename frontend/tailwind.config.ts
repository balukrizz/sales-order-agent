import type { Config } from "tailwindcss";
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#1E293B",
        slateblue: "#334155",
        teal: { DEFAULT: "#0EA5A5", dark: "#0B8080" },
        cardline: "#E2E8F0",
      },
      boxShadow: { soft: "0 1px 3px rgba(15,23,42,.08), 0 8px 24px rgba(15,23,42,.06)" },
    },
  },
  plugins: [],
};
export default config;
