/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        grotesk: ['"Space Grotesk"', 'sans-serif'],
        geist: ["var(--font-geist-sans)"],
        geistmono: ["var(--font-geist-mono)"],
        overpass: ["var(--font-overpass)"],
        beanie: ["var(--font-beanie)"],
        mono: ["var(--font-mono)"],
      },
    },
  },
  plugins: [],
};