import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In development the UI runs on :5173 and proxies /api to the FastAPI server on :8000.
// `npm run build` writes to dist/, which the FastAPI app serves directly.
export default defineConfig({
  base: "./", // relative asset paths so the build also works under a sub-folder of another site
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": { target: "http://localhost:8000", changeOrigin: true } },
  },
  build: { outDir: "dist", sourcemap: false },
});
