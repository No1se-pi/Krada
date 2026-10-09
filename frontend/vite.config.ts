import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const apiUrl = process.env.VITE_API_URL ?? env.VITE_API_URL ?? 'http://localhost:8000/api/v1';
  const apiOrigin = new URL(apiUrl).origin;
  const securityHeaders = {
    'Content-Security-Policy': [
      "default-src 'self'",
      "script-src 'self' https://st.max.ru",
      "style-src 'self' 'unsafe-inline'",
      "font-src 'self'",
      "img-src 'self' data: https:",
      `connect-src 'self' ${apiOrigin}`,
      "base-uri 'none'",
      "frame-ancestors 'self' https://max.ru https://*.max.ru",
    ].join('; '),
    'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
    'Referrer-Policy': 'no-referrer',
    'X-Content-Type-Options': 'nosniff',
  };

  return {
    plugins: [react()],
    // Keep local/preview behavior aligned with the headers required from a production proxy.
    server: { headers: securityHeaders },
    preview: { headers: securityHeaders },
  };
});
