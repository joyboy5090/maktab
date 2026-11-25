/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: "#1E40AF",
          hover: "#1D4ED8",
          light: "#DBEAFE",
        },
        secondary: {
          DEFAULT: "#10B981",
          hover: "#059669",
          light: "#D1FAE5",
        },
        surface: "#FFFFFF",
        appBg: "#F3F4F6",
      },
      fontFamily: {
        sans: ["Inter", "Roboto", "sans-serif"],
      },
    },
  },
  plugins: [],
};
