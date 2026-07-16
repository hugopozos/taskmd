/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      colors: {
        surface: '#141414',
        'surface-hover': '#1a1a1a',
        border: '#27272a',
      },
    },
  },
  plugins: [],
}
