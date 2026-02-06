
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [react()],
    build: {
        rollupOptions: {
            input: {
                daily: resolve(__dirname, 'daily.html'),
            },
            output: {
                entryFileNames: `assets/[name]-[hash]-v3.js`,
                chunkFileNames: `assets/[name]-[hash]-v3.js`,
                assetFileNames: `assets/[name]-[hash]-v3.[ext]`
            }
        },
    },
})
