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
        sans: ['var(--font-inter)', 'system-ui', 'sans-serif'],
        serif: ['var(--font-crimson)', 'Georgia', 'Cambria', 'serif'],
      },
      colors: {
        parchment: '#f5f4ed',
        ivory: '#faf9f5',
        ink: '#141413',
        'dark-surface': '#30302e',
        'dark-elevated': '#1e1e1c',
        'dark-border': '#3d3d3a',
        terracotta: '#c96442',
        'warm-sand': '#e8e6dc',
        'olive-gray': '#5e5d59',
        'stone-gray': '#87867f',
        'warm-silver': '#b0aea5',
      },
    },
  },
  plugins: [],
};

export default config;
