import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { fileURLToPath } from "node:url";

// O servidor do Vite é só para desenvolvimento. O produto é o build estático
// servido pelo FastAPI na mesma origem da API (plano §6).
const apiPort = process.env.COSCIP_API_PORT ?? "8765";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    outDir: fileURLToPath(new URL("../api/coscip_api/static", import.meta.url)),
    emptyOutDir: true,
    sourcemap: false,
  },
  server: {
    host: "localhost",
    port: 5173,
    strictPort: true,
    proxy: {
      "/v1": { target: `http://127.0.0.1:${apiPort}`, changeOrigin: false },
    },
  },
});
