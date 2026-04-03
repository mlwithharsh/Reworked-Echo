import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  cacheDir: '.vite-cache',
  build: {
    rollupOptions: {
      input: {
        main: 'index.html',
        chat: 'chat.html',
        about: 'about.html',
      },
    },
    emptyOutDir: false,
  },
})
