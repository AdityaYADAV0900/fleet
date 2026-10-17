/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // AeroPulse Light & Airy Design Tokens
        ap: {
          bg: '#FAFAFE',            // Near-white with faint lavender tint
          surface: '#FFFFFF',       // Clean card surface
          tint: '#F4F2FB',          // Subtle tint surface
          border: '#E6E2F0',        // Light 1px border
          'border-subtle': '#EDE9F5',
          
          // Typography
          heading: '#3B1D5E',       // Deep purple/indigo for headings
          body: '#6B5B84',          // Soft muted purple body text
          muted: '#8F7FA8',         // Muted secondary/meta text
          light: '#BAAFC9',         // Placeholder & subtle text

          // CTAs & Interactive
          mint: {
            DEFAULT: '#1DE9C0',     // Vibrant mint primary CTA
            hover: '#18D4AD',
            light: '#E6FCF7',
            border: '#A3F5E4',
          },
          lilac: {
            DEFAULT: '#C9A2F5',     // Soft lilac secondary CTA
            hover: '#B887F2',
            light: '#F4EBFF',
            border: '#E5D0FA',
          },
          cyan: {
            DEFAULT: '#0E7490',
            bg: '#E0F8FA',          // Info tile pale cyan
            border: '#B6EFF4',
          },
          pill: {
            DEFAULT: '#0369A1',
            bg: '#DCEFF8',          // Light-blue tag pill
            border: '#BAE0F2',
          },

          // Status Tones (Softened)
          status: {
            success: '#059669',
            'success-bg': '#ECFDF5',
            'success-border': '#A7F3D0',
            warning: '#D97706',
            'warning-bg': '#FFFBEB',
            'warning-border': '#FDE68A',
            danger: '#DC2626',
            'danger-bg': '#FEF2F2',
            'danger-border': '#FECACA',
            info: '#4F46E5',
            'info-bg': '#EEF2FF',
            'info-border': '#C7D2FE',
          },
        },
      },
      borderRadius: {
        'ap-input': '10px',
        'ap-button': '10px',
        'ap-card': '20px',
      },
      boxShadow: {
        'ap-card': '0 10px 30px -5px rgba(59, 29, 94, 0.05), 0 4px 12px -2px rgba(59, 29, 94, 0.02)',
        'ap-floating': '0 20px 40px -8px rgba(59, 29, 94, 0.08), 0 8px 16px -4px rgba(59, 29, 94, 0.03)',
        'ap-sm': '0 2px 8px 0 rgba(59, 29, 94, 0.04)',
        'ap-mint': '0 4px 16px -2px rgba(29, 233, 192, 0.35)',
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
    },
  },
  plugins: [],
}

