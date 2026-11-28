import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  // Load public Neon URLs from project root .env without ever exposing secrets to the browser
  const rootEnv = loadEnv(mode, "..", "");
  const neonAuthUrl = rootEnv.VITE_NEON_AUTH_URL || rootEnv.NEON_AUTH_BASE_URL || "";
  const neonRealtimeUrl = rootEnv.VITE_NEON_REALTIME_URL || rootEnv.NEON_REALTIME_URL || "";

  return {
    plugins: [react()],
    define: {
      "import.meta.env.VITE_NEON_AUTH_URL": JSON.stringify(neonAuthUrl),
      "import.meta.env.VITE_NEON_REALTIME_URL": JSON.stringify(neonRealtimeUrl),
    },
    server: {
      port: 5173,
      proxy: {
        "/api": {
          target: "http://localhost:8000",
          changeOrigin: true,
        },
      },
    },
  };
});
