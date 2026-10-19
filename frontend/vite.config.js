import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Port 5173 is the origin the backend allows in CORS, so do not let Vite pick another one.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, strictPort: true },
});
