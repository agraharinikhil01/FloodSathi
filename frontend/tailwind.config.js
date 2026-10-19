/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        darkBg: "#0B1220",
        darkCard: "#131E32",
        darkMuted: "#1E293B",
        lightBg: "#F6F8FC",
        lightCard: "#FFFFFF",
        lightMuted: "#E2E8F0",
        brand: {
          cyan: "#22D3EE",
          blue: "#3B82F6",
          dark: "#1D4ED8",
        },
        risk: {
          low: "#22C55E",      // Green / Aman
          medium: "#EAB308",   // Yellow / Waspada
          high: "#F97316",     // Orange / Siaga
          severe: "#EF4444",   // Red / Awas
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.5rem',
      }
    },
  },
  plugins: [],
}
