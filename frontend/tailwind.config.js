/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      // Add custom colors here
      colors: {
        'primary-blue': { // Define shades for more flexibility
          light: '#60a5fa', // Lighter blue for backgrounds/hover
          DEFAULT: '#3b82f6', // Main blue for buttons
          dark: '#2563eb', // Darker blue for hover/active
        },
        'accent-green': {
          light: '#d1fae5', // Backgrounds
          DEFAULT: '#10b981', // Main color
          dark: '#059669', // Hover/text
        },
         'accent-red': {
          light: '#fee2e2', // Backgrounds
          DEFAULT: '#ef4444', // Main color
          dark: '#dc2626', // Hover/text
        },
        'neutral': { // Greys
          50: '#f9fafb',
          100: '#f3f4f6',
          200: '#e5e7eb',
          300: '#d1d5db',
          400: '#9ca3af',
          500: '#6b7280', // Medium grey text
          600: '#4b5563', // Slightly darker text
          700: '#374151', // Headings/Labels
          800: '#1f2937', // Darker Headings
          900: '#11182c',
        }
      },
      // You can also extend fonts if you want to add a custom one
      // fontFamily: {
      //   sans: ['Inter', 'system-ui', 'sans-serif'], // Keep Inter as default
      // },
    },
  },
  plugins: [],
}