/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        forest: {
          50: '#F0F6F3',
          100: '#DCEBE3',
          200: '#B8D7C7',
          300: '#8EBFA7',
          400: '#5BA382',
          500: '#348663',
          600: '#23694D',
          700: '#174A3A', // Primary Brand
          800: '#0F352A', // Primary Dark
          900: '#082119',
        },
        amber: {
          50: '#FDF8EC',
          100: '#FBEED2',
          200: '#F6DBA2',
          300: '#F0C56E',
          400: '#E4AB3D',
          500: '#D99A2B', // Accent Gold
          600: '#BC7D1D',
          700: '#955E17',
          800: '#754716',
          900: '#5E3815',
        },
        sand: {
          50: '#FAF9F6',
          100: '#F7F5EF', // Background Off-White
          200: '#EFECE3',
          300: '#E0DDD2',
          400: '#C7C3B6',
          500: '#A9A496',
          600: '#7E7A6E',
          700: '#5C584E',
          800: '#3D3A33',
          900: '#202522', // Charcoal Text
        },
        status: {
          healthy: '#2E7D32',
          warning: '#ED6C02',
          critical: '#D32F2F',
          info: '#0288D1',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Courier New', 'monospace'],
      },
    },
  },
  plugins: [],
}
