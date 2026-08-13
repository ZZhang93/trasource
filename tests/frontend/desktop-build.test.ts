import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import {
  hasRealAppleSigningIdentity,
  tauriBuildArgs,
} from '../../scripts/run-desktop-build.mjs'

test('ad-hoc macOS builds enforce a non-hardened final override', () => {
  assert.equal(hasRealAppleSigningIdentity('-'), false)
  const args = tauriBuildArgs({
    platform: 'darwin',
    identity: '-',
    passthrough: [
      '--config',
      JSON.stringify({ bundle: { macOS: { hardenedRuntime: true } } }),
      '--bundles',
      'dmg',
    ],
  })
  assert.deepEqual(JSON.parse(args.at(-1)), {
    bundle: { macOS: { hardenedRuntime: false } },
  })
  assert.equal(args.at(-2), '--config')

  const config = JSON.parse(readFileSync(
    new URL('../../src-tauri/tauri.conf.json', import.meta.url),
    'utf8',
  ))
  assert.equal(config.bundle.macOS.hardenedRuntime, false)
})

test('Developer ID builds enforce hardened runtime after passthrough config', () => {
  const args = tauriBuildArgs({
    platform: 'darwin',
    identity: 'Developer ID Application: Example (TEAMID1234)',
    passthrough: [
      '--config',
      JSON.stringify({ bundle: { macOS: { hardenedRuntime: false } } }),
      '--bundles',
      'dmg',
    ],
  })
  assert.equal(args.at(-2), '--config')
  assert.deepEqual(JSON.parse(args.at(-1)), {
    bundle: { macOS: { hardenedRuntime: true } },
  })
})

test('the signing override stays before runner arguments', () => {
  const args = tauriBuildArgs({
    platform: 'darwin',
    identity: '-',
    passthrough: ['--bundles', 'dmg', '--', '--runner-argument'],
  })
  const separator = args.indexOf('--')
  assert.equal(args[separator - 2], '--config')
  assert.deepEqual(JSON.parse(args[separator - 1]), {
    bundle: { macOS: { hardenedRuntime: false } },
  })
})

test('non-macOS builds do not receive macOS signing overrides', () => {
  assert.deepEqual(
    tauriBuildArgs({
      platform: 'win32',
      identity: 'Developer ID Application: Example (TEAMID1234)',
      passthrough: [],
    }),
    ['build'],
  )
})
