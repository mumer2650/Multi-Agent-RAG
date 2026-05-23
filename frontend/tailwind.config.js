/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      animation: {
        'glow': 'glow 3s ease-in-out infinite alternate',
        'fade-in': 'fadeIn 0.8s ease-out forwards',
      },
      keyframes: {
        glow: {
          '0%': { boxShadow: '0 0 15px 2px rgba(59, 130, 246, 0.3), 0 0 15px 2px rgba(168, 85, 247, 0.3)' },
          '100%': { boxShadow: '0 0 25px 6px rgba(59, 130, 246, 0.6), 0 0 25px 6px rgba(168, 85, 247, 0.6)' },
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