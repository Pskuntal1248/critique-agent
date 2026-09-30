import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Helvetica Neue"', 'Helvetica', 'Arial', 'sans-serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      colors: {
        // Palette: white, one blue accent, and solid green / red for good / bad.
        accent: {
          DEFAULT: '#88bdf2',
          hover: '#6fa9e3',
          soft: '#eef6fd',
        },
        good: '#1a8a4a',
        bad: '#d1322b',
        ink: '#111111',
        muted: '#6b6b6b',
        line: '#e4e4e4',
      },
      borderRadius: {
        DEFAULT: '2px',
        md: '2px',
        lg: '2px',
        xl: '2px',
        full: '9999px',
      },
    },
  },
  plugins: [require('@tailwindcss/typography')],
};

export default config;
