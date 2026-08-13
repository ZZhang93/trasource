import test from 'node:test'
import assert from 'node:assert/strict'
import {
  backendFetch,
  getBackendAuthHeaders,
  setBackendAuthToken,
} from '../../src/api/client.ts'

test('backend authentication header is present only while a token is configured', () => {
  setBackendAuthToken('  secret-token  ')
  assert.deepEqual(getBackendAuthHeaders(), { 'X-Trasource-Token': 'secret-token' })

  setBackendAuthToken('')
  assert.deepEqual(getBackendAuthHeaders(), {})
})

test('backendFetch attaches auth without leaking it to another origin', async () => {
  const originalFetch = globalThis.fetch
  let observedToken = ''
  globalThis.fetch = async (_input, init) => {
    observedToken = new Headers(init?.headers).get('X-Trasource-Token') || ''
    return new Response('{}', { status: 200 })
  }

  try {
    setBackendAuthToken('secret-token')
    await backendFetch('/api/health')
    assert.equal(observedToken, 'secret-token')
    assert.throws(
      () => backendFetch('https://example.com/api'),
      /only accepts local backend URLs/,
    )
  } finally {
    setBackendAuthToken('')
    globalThis.fetch = originalFetch
  }
})
