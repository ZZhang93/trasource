import { spawnSync } from 'node:child_process'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')

export function hasRealAppleSigningIdentity(identity) {
  const normalized = (identity || '').trim()
  return normalized !== '' && normalized !== '-'
}

export function tauriBuildArgs({
  platform = process.platform,
  identity = process.env.APPLE_SIGNING_IDENTITY,
  passthrough = process.argv.slice(2),
} = {}) {
  const args = ['build', ...passthrough]
  if (platform === 'darwin') {
    const runnerSeparator = args.indexOf('--')
    const insertAt = runnerSeparator === -1 ? args.length : runnerSeparator
    args.splice(
      insertAt,
      0,
      '--config',
      JSON.stringify({
        bundle: {
          macOS: {
            hardenedRuntime: hasRealAppleSigningIdentity(identity),
          },
        },
      }),
    )
  }
  return args
}

function run() {
  const tauriCli = join(root, 'node_modules', '@tauri-apps', 'cli', 'tauri.js')
  const result = spawnSync(process.execPath, [tauriCli, ...tauriBuildArgs()], {
    cwd: root,
    env: process.env,
    stdio: 'inherit',
  })
  if (result.error) throw result.error
  process.exit(result.status ?? 1)
}

const entryPath = process.argv[1] ? pathToFileURL(resolve(process.argv[1])).href : ''
if (entryPath === import.meta.url) run()
