import { readFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const readJson = path => JSON.parse(readFileSync(join(root, path), 'utf8'))

const packageJson = readJson('package.json')
const packageLock = readJson('package-lock.json')
const tauriConfig = readJson('src-tauri/tauri.conf.json')
const cargo = readFileSync(join(root, 'src-tauri', 'Cargo.toml'), 'utf8')
const cargoLock = readFileSync(join(root, 'src-tauri', 'Cargo.lock'), 'utf8')
const server = readFileSync(join(root, 'backend', 'server.py'), 'utf8')
const expected = packageJson.version

const versions = new Map([
  ['package-lock.json', packageLock.version],
  ['package-lock.json root package', packageLock.packages?.['']?.version],
  ['src-tauri/tauri.conf.json', tauriConfig.version],
  ['src-tauri/Cargo.toml', cargo.match(/^version\s*=\s*"([^"]+)"/m)?.[1]],
  ['src-tauri/Cargo.lock root package', cargoLock.match(/\[\[package\]\]\s+name\s*=\s*"trasource"\s+version\s*=\s*"([^"]+)"/m)?.[1]],
])

let serverOccurrence = 0
for (const match of server.matchAll(/(?:version\s*=\s*|["']version["']\s*:\s*)["'](\d+\.\d+\.\d+)["']/g)) {
  serverOccurrence += 1
  versions.set(`backend/server.py occurrence ${serverOccurrence}`, match[1])
}

const failures = [...versions].filter(([, version]) => version !== expected)
if (failures.length) {
  for (const [source, version] of failures) {
    process.stderr.write(`${source}: expected ${expected}, found ${version || 'missing'}\n`)
  }
  process.exit(1)
}

process.stdout.write(`Version check passed (${expected}; ${versions.size + 1} declarations).\n`)
