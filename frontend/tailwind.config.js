/** @type {import('tailwindcss').Config} */
export default {
  // Dark mode toggled by adding the `dark` class on <html>.
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {},
  },
  plugins: [require('@tailwindcss/typography')],
}
