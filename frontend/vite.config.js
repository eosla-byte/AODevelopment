
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'
import { fileURLToPath } from 'url'
import { dirname } from 'path'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [react()],
    build: {
        rollupOptions: {
            input: {
                daily: resolve(__dirname, 'daily.html'),
            },
            output: {
                entryFileNames: `assets/[name]-[hash]-v4.js`,
                chunkFileNames: `assets/[name]-[hash]-v4.js`,
                assetFileNames: `assets/[name]-[hash]-v4.[ext]`
            }
        },
    },
})
