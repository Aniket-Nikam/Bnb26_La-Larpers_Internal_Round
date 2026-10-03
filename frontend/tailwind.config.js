/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        canvas: "rgb(var(--canvas))",
        surface: "rgb(var(--surface))",
        ink: "rgb(var(--ink))",
        primary: {
          DEFAULT: "rgb(var(--primary))",
          foreground: "#FFFFFF",
        },
        success: "rgb(var(--success))",
        warning: "rgb(var(--warning))",
        error: "rgb(var(--error))",
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      }
    },
  },
  plugins: [],
}
