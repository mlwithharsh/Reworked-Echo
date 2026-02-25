/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: {
          DEFAULT: '#020617',
          light: '#0f172a',
          dark: '#020617',
        },
        neon: {
          purple: '#8B5CF6',
          purpleLight: '#A855F7',
          blue: '#3B82F6',
          cyan: '#22D3EE',
          pink: '#EC4899',
          red: '#EF4444',
        }
      },
      animation: {
        'pulse-glow': 'pulse-glow 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'float': 'float 6s ease-in-out infinite',
        'neon-border': 'neon-border 2s linear infinite',
      },
      keyframes: {
        'pulse-glow': {
          '0%, 100%': { opacity: 1, filter: 'drop-shadow(0 0 8px #8B5CF6)' },
          '50%': { opacity: 0.6, filter: 'drop-shadow(0 0 15px #A855F7)' },
        },
        'float': {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-20px)' },
        },
        'neon-border': {
          '0%': { borderColor: '#8B5CF6' },
          '50%': { borderColor: '#22D3EE' },
          '100%': { borderColor: '#8B5CF6' },
        }
      },
      backdropBlur: {
        xs: '2px',
      },
      boxShadow: {
        'neon-purple': '0 0 10px #8B5CF6, 0 0 20px #8B5CF6',
        'neon-blue': '0 0 10px #3B82F6, 0 0 20px #3B82F6',
        'neon-cyan': '0 0 10px #22D3EE, 0 0 20px #22D3EE',
        'glass': '0 8px 32px 0 rgba(31, 38, 135, 0.37)',
      }
    },
  },
  plugins: [],
}
