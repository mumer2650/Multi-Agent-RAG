/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Outfit', 'sans-serif'],
      },
      animation: {
        'glow': 'glow 4s ease-in-out infinite alternate',
        'fade-in': 'fadeIn 0.8s ease-out forwards',
      },
      keyframes: {
        glow: {
          '0%': { boxShadow: '0 0 10px 1px rgba(59, 130, 246, 0.2), 0 0 10px 1px rgba(168, 85, 247, 0.2)' },
          '100%': { boxShadow: '0 0 30px 8px rgba(59, 130, 246, 0.5), 0 0 30px 8px rgba(168, 85, 247, 0.5)' },
        },
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(-10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        }
      }
    },
  },
  plugins: [],
}