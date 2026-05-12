/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    fontFamily: {
      sans: ['Inter', 'sans-serif'],
      display: ['"Plus Jakarta Sans"', 'sans-serif'],
      mono: ['"JetBrains Mono"', 'monospace'],
    },
    extend: {
      colors: {
        background: '#090a0f',
        surface: '#11131c',
        'surface-lowest': '#141620',
        'surface-low': '#191b24',
        'surface-container': '#1d1f29',
        'surface-high': '#282933',
        'surface-highest': '#32343e',
        'on-surface': '#e1e1ef',
        'on-surface-variant': '#c7c4d7',
        
        primary: {
          DEFAULT: '#8891ff',
          container: '#4a54e1',
          on: '#ffffff',
          'on-fixed': '#eef0ff',
          glow: 'rgba(136, 145, 255, 0.4)'
        },
        secondary: {
          DEFAULT: '#b9c7e0',
          container: '#3c4a5e'
        },
        tertiary: {
          DEFAULT: '#00e696',
          glow: 'rgba(0, 230, 150, 0.3)'
        },
        error: {
          DEFAULT: '#ff4f64',
          container: '#93000a',
          glow: 'rgba(255, 79, 100, 0.3)'
        },
        outline: {
          DEFAULT: '#908fa0',
          variant: '#3e4157'
        }
      },
      borderRadius: {
        md: '0.375rem',
        xl: '0.75rem',
        '2xl': '1rem',
        '3xl': '1.5rem',
      },
      boxShadow: {
        ambient: '0 20px 40px rgba(0, 0, 0, 0.4)',
        'glow-primary': '0 0 20px rgba(136, 145, 255, 0.4)',
        'glow-tertiary': '0 0 20px rgba(0, 230, 150, 0.3)',
      },
      animation: {
        'shimmer': 'shimmer 2.5s infinite linear',
        'float': 'float 6s ease-in-out infinite',
        'pulse-glow': 'pulse-glow 3s ease-in-out infinite',
        'aurora': 'aurora 15s ease infinite alternate',
      },
      keyframes: {
        shimmer: {
          '0%': { transform: 'translateX(-150%) skewX(-15deg)' },
          '100%': { transform: 'translateX(200%) skewX(-15deg)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        'pulse-glow': {
          '0%, 100%': { opacity: '0.5', transform: 'scale(1)' },
          '50%': { opacity: '1', transform: 'scale(1.05)' },
        },
        aurora: {
          '0%': { backgroundPosition: '0% 50%', filter: 'hue-rotate(0deg)' },
          '50%': { backgroundPosition: '100% 50%', filter: 'hue-rotate(30deg)' },
          '100%': { backgroundPosition: '0% 50%', filter: 'hue-rotate(0deg)' },
        }
      }
    },
  },
  plugins: [],
}
