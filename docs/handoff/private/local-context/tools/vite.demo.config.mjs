// Demo only: the frontend dev server pointed at the demo API on 8111 (8001 is another project's).
import react from "file:///C:/Development/Verity_GRC_Platform/frontend/node_modules/@vitejs/plugin-react/dist/index.js";

export default {
  root: "C:/Development/Verity_GRC_Platform/frontend",
  plugins: [react()],
  resolve: { alias: { "@": "C:/Development/Verity_GRC_Platform/frontend/src" } },
  server: {
    port: 5175,
    strictPort: true,
    proxy: { "/api": { target: "http://127.0.0.1:8111", changeOrigin: true } },
  },
};
