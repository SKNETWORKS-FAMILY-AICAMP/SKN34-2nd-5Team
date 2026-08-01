import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    proxy: {
      // auth_service runs as its own FastAPI app (default port 8100, see
      // auth_service/README.md). Proxying keeps React and auth same-origin
      // in dev so the HttpOnly session cookie and CSRF cookie both work
      // without cross-origin cookie config (REACT_INTEGRATION.md §9).
      "/auth": {
        target: "http://127.0.0.1:8100",
        changeOrigin: true,
      },
    },
  },
});