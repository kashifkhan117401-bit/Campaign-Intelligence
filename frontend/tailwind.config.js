/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      colors: {
        navy: {
          950: "#070B14",
          900: "#0B1120",
          850: "#0F172A",
          800: "#141E33",
        },
      },
      boxShadow: {
        glow: "0 0 32px -8px rgba(99, 102, 241, 0.35)",
      },
    },
  },
  plugins: [],
};
