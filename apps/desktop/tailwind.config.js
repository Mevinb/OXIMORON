/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        bg: {
          main: '#0a0b0e',
          surface: '#12141a',
          card: '#181b23',
          cardHover: '#1f232e',
          border: '#262a36',
        },
        accent: {
          primary: '#6366f1', // Indigo
          cyan: '#06b6d4',
          emerald: '#10b981',
          rose: '#f43f5e',
          amber: '#f59e0b',
        }
      }
    },
  },
  plugins: [],
}
