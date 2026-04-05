/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        lepidic: '#0000FF',
        acinar: '#FF0000',
        papillary: '#FFFF00',
        micropapillary: '#FF00FF',
        solid: '#800000',
        cribriform: '#00FFFF',
      },
    },
  },
  plugins: [],
};
