import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    rollupOptions: {
      output: {
        manualChunks: { react: ["react", "react-dom", "react-router-dom", "@tanstack/react-query"], charts: ["recharts"] },
      },
    },
  },
  server: {
    port: 5173,
    // Same-origin API in dev, so the httpOnly refresh cookie works without CORS tricks.
    proxy: { "/api": "http://localhost:8000" },
  },
});
