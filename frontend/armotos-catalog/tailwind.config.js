/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx}',
    './components/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        armotos: {
          yellow: '#FFD700',
          red: '#DC2626',
          dark: '#1F2937'
        }
      }
    },
  },
  plugins: [],
}
