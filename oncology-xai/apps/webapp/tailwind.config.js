/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        lepidic: '#E6FF32',
        acinar: '#00FF00',
        papillary: '#0000FF',
        micropapillary: '#FFD700',
        solid: '#FF0000',
        mucinous: '#FFA500',
      },
    },
  },
  plugins: [],
};
