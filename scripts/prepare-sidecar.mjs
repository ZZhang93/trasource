import { spawnSync } from 'node:child_process'
import { chmodSync, copyFileSync, existsSync, mkdirSync, rmSync, writeFileSync } from 'node:fs'
import { homedir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const mode = process.argv.includes('--build') ? 'build' : 'placeholder'
const devModeMarker = join(root, 'src-tauri', '.trasource-dev-mode')

if (mode === 'placeholder') writeFileSync(devModeMarker, 'tauri dev\n')
else rmSync(devModeMarker, { force: true })

function runFirst(candidates, args) {
  for (const command of candidates.filter(Boolean)) {
    const result = spawnSync(command, args, {
      cwd: root,
      encoding: 'utf8',
      stdio: mode === 'build' ? 'inherit' : ['ignore', 'pipe', 'pipe'],
    })
    if (!result.error && result.status === 0) return { command, result }
  }
  return null
}

const rustcCandidates = [
  process.env.TRASOURCE_RUSTC,
  'rustc',
  join(homedir(), '.cargo', 'bin', process.platform === 'win32' ? 'rustc.exe' : 'rustc'),
]
const rustc = runFirst(rustcCandidates, ['-vV'])
if (!rustc) {
  throw new Error('Rust toolchain not found. Install rustup or set TRASOURCE_RUSTC.')
}

// The placeholder probe captured stdout; the build-mode helper inherits it, so query once more.
const version = spawnSync(rustc.command, ['-vV'], { encoding: 'utf8' })
const hostTarget = version.stdout.match(/^host:\s+(.+)$/m)?.[1]?.trim()
const target = process.env.TAURI_ENV_TARGET_TRIPLE || hostTarget
if (!target) throw new Error('Unable to determine the Rust host target.')

if (mode === 'build' && target !== hostTarget) {
  throw new Error(
    `Cross-target sidecar build is not safe (${hostTarget} -> ${target}). ` +
    'Build on a native runner for the requested target; universal macOS builds require native sidecars for both architectures.',
  )
}

const extension = target.includes('windows') ? '.exe' : ''
const destination = join(
  root,
  'src-tauri',
  'binaries',
  `trasource-backend-${target}${extension}`,
)
mkdirSync(dirname(destination), { recursive: true })

if (mode === 'placeholder') {
  // Tauri validates externalBin before compiling even though debug builds launch Python
  // directly. The ignored placeholder satisfies that validation and is never executed.
  if (!existsSync(destination)) {
    const content = target.includes('windows')
      ? 'Trasource development placeholder\r\n'
      : '#!/bin/sh\nexit 0\n'
    writeFileSync(destination, content)
    if (!target.includes('windows')) chmodSync(destination, 0o755)
  }
  process.stdout.write(`Prepared development sidecar placeholder for ${target}.\n`)
  process.exit(0)
}

const pythonCandidates = process.platform === 'win32'
  ? [process.env.TRASOURCE_PYTHON, 'py', 'python']
  : [process.env.TRASOURCE_PYTHON, 'python3', 'python']

let selectedPython = null
for (const command of pythonCandidates.filter(Boolean)) {
  const prefix = command === 'py' ? ['-3'] : []
  const probe = spawnSync(command, [...prefix, '-c', 'import PyInstaller'], {
    cwd: root,
    stdio: 'ignore',
  })
  if (!probe.error && probe.status === 0) {
    selectedPython = { command, prefix }
    break
  }
}
if (!selectedPython) {
  throw new Error('PyInstaller is unavailable. Install build dependencies with: python3 -m pip install -r requirements-build.txt')
}

// Never reuse a user-global PyInstaller cache: stale binaries from another
// checkout, Python, or architecture make release output non-reproducible and
// can also be unwritable in sandboxed/CI environments.
const pyinstallerConfigDir = join(root, 'build', 'pyinstaller-config')
mkdirSync(pyinstallerConfigDir, { recursive: true })
const buildResult = spawnSync(selectedPython.command, [
  ...selectedPython.prefix,
  '-m', 'PyInstaller',
  'trasource-backend.spec',
  '--clean',
  '--noconfirm',
  '--distpath', 'build/sidecar-dist',
], {
  cwd: root,
  stdio: 'inherit',
  env: { ...process.env, PYINSTALLER_CONFIG_DIR: pyinstallerConfigDir },
})
if (buildResult.error || buildResult.status !== 0) {
  throw new Error(`PyInstaller build failed with ${selectedPython.command}; refusing to fall back to a different Python environment.`)
}

const source = join(root, 'build', 'sidecar-dist', `trasource-backend${process.platform === 'win32' ? '.exe' : ''}`)
if (!existsSync(source)) throw new Error(`PyInstaller output not found: ${source}`)
copyFileSync(source, destination)
if (!target.includes('windows')) chmodSync(destination, 0o755)
process.stdout.write(`Prepared release sidecar: ${destination}\n`)
