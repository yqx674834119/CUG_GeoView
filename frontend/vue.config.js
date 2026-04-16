const { defineConfig } = require('@vue/cli-service')
const YAML = require('yaml')
const fs = require('fs')
const path = require('path')

const configPath = path.resolve(__dirname, '../config.yaml')
let devServer

if (fs.existsSync(configPath)) {
  const file = fs.readFileSync(configPath, 'utf8')
  const config = YAML.parse(file)

  devServer = {
    host: config.host.frontend,
    port: config.port.frontend,
  }
}

module.exports = defineConfig({
  transpileDependencies: true,
  ...(devServer ? { devServer } : {}),

  // transpileDependencies: ['@arcgis']
})
