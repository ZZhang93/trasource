import { spawnSync } from 'node:child_process'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')

const candidates = process.platform === 'win32'
  ? [[process.env.TRASOURCE_PYTHON, []], [join(root, '.venv', 'Scripts', 'python.exe'), []], ['python', []], ['py', ['-3']]]
  : [[process.env.TRASOURCE_PYTHON, []], [join(root, '.venv', 'bin', 'python'), []], ['python3', []], ['python', []]]

for (const [command, prefix] of candidates) {
  if (!command) continue
  // A Python launcher can exist while pointing at a different interpreter
  // from the one where the backend dependencies were installed (notably
  // `py -3` versus `python` on GitHub's Windows runners). Probe the runtime
  // before selecting it so an unrelated global Python cannot shadow the
  // configured environment.
  const probe = spawnSync(command, [
    ...prefix,
    '-c', 'import duckdb, fastapi; from google import genai',
  ], { cwd: root, stdio: 'ignore' })
  if (probe.error || probe.status !== 0) continue

  const result = spawnSync(command, [
    ...prefix,
    '-m', 'unittest', 'discover', '-s', 'tests/backend', '-v',
  ], { cwd: root, stdio: 'inherit' })
  process.exit(result.status ?? 1)
}

process.stderr.write(
  'No Python interpreter with the backend dependencies was found. ' +
  'Set TRASOURCE_PYTHON or install requirements-build.txt.\n',
)
process.exit(1)
