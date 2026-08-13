import { spawnSync } from 'node:child_process'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')

const candidates = process.platform === 'win32'
  ? [[process.env.TRASOURCE_PYTHON, []], [join(root, '.venv', 'Scripts', 'python.exe'), []], ['py', ['-3']], ['python', []]]
  : [[process.env.TRASOURCE_PYTHON, []], [join(root, '.venv', 'bin', 'python'), []], ['python3', []], ['python', []]]

for (const [command, prefix] of candidates) {
  if (!command) continue
  const result = spawnSync(command, [
    ...prefix,
    '-m', 'unittest', 'discover', '-s', 'tests/backend', '-v',
  ], { stdio: 'inherit' })
  if (!result.error) process.exit(result.status ?? 1)
}

process.stderr.write('Python interpreter not found. Set TRASOURCE_PYTHON or install Python 3.10+.\n')
process.exit(1)
