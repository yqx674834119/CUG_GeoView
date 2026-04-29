const { defineConfig } = require('@vue/cli-service')
const YAML = require('yaml')
const fs = require('fs')
const path = require('path')

const localConfigPath = path.resolve(__dirname, '../config.local.yaml')
const defaultConfigPath = path.resolve(__dirname, '../config.yaml')
const configPath = fs.existsSync(localConfigPath) ? localConfigPath : defaultConfigPath
let devServer

if (fs.existsSync(configPath)) {
  const file = fs.readFileSync(configPath, 'utf8')
  const config = YAML.parse(file)
  const backendHost = config.host?.backend || '127.0.0.1'
  const backendPort = config.port?.backend || 5008
  const backendTargetHost = backendHost === '0.0.0.0' ? '127.0.0.1' : backendHost

  devServer = {
    host: config.host.frontend,
    port: config.port.frontend,
    proxy: {
      '/api': {
        target: `http://${backendTargetHost}:${backendPort}`,
        changeOrigin: true,
      },
    },
  }
}

module.exports = defineConfig({
  publicPath: './',
  transpileDependencies: true,
  ...(devServer ? { devServer } : {}),

  // transpileDependencies: ['@arcgis']
})
