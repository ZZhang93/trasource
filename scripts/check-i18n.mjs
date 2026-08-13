import { readFileSync, readdirSync, statSync } from 'node:fs'
import { dirname, extname, join, resolve, sep } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')

function dictionaryKeys(path) {
  const text = readFileSync(path, 'utf8')
  return new Set([...text.matchAll(/^\s*'([^']+)'\s*:/gm)].map(match => match[1]))
}

function walk(path) {
  const files = []
  for (const name of readdirSync(path)) {
    const child = join(path, name)
    const info = statSync(child)
    if (info.isDirectory()) files.push(...walk(child))
    else if (['.ts', '.vue'].includes(extname(child))) files.push(child)
  }
  return files
}

const zh = dictionaryKeys(join(root, 'src', 'i18n', 'zh.ts'))
const en = dictionaryKeys(join(root, 'src', 'i18n', 'en.ts'))
const failures = []

for (const key of zh) if (!en.has(key)) failures.push(`Missing in English dictionary: ${key}`)
for (const key of en) if (!zh.has(key)) failures.push(`Missing in Chinese dictionary: ${key}`)

for (const file of walk(join(root, 'src'))) {
  if (file.startsWith(`${join(root, 'src', 'i18n')}${sep}`)) continue
  const text = readFileSync(file, 'utf8')
  for (const match of text.matchAll(/\bt\(\s*['"]([^'"]+)['"]/g)) {
    if (!zh.has(match[1]) || !en.has(match[1])) {
      failures.push(`${file.slice(root.length + 1)} uses unknown translation key: ${match[1]}`)
    }
  }
}

if (failures.length) {
  process.stderr.write(`${failures.join('\n')}\n`)
  process.exit(1)
}

process.stdout.write(`i18n check passed (${zh.size} keys in both dictionaries).\n`)
