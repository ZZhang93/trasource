import test from 'node:test'
import assert from 'node:assert/strict'
import {
  matchExtractionRecord,
  parseCitationRecordId,
  parseExtractionEntries,
} from '../../src/utils/extraction.ts'

function record(id: number, overrides: Record<string, unknown> = {}) {
  return {
    id,
    source_file: `source-${id}.pdf`,
    file_type: 'pdf',
    doc_type: 'paper',
    year: '1962',
    date: '',
    page: '',
    title: `Title ${id}`,
    author: 'Author',
    pub_year: '1962',
    publisher: '',
    chapter: '',
    section: '',
    page_num: '12',
    interviewee: '',
    interview_date: '',
    interview_location: '',
    content: 'This is the exact original passage used for fallback matching.',
    relevance_score: 1,
    ...overrides,
  }
}

test('parses Chinese and English record ID labels', () => {
  assert.deepEqual(parseCitationRecordId('[引用：记录 ID：123 / 1962]'), { present: true, id: 123 })
  assert.deepEqual(parseCitationRecordId('[Citation: Record ID: 456 / 1962]'), { present: true, id: 456 })
  assert.deepEqual(parseCitationRecordId('[Citation: 1962 / source]'), { present: false, id: null })
})

test('an explicit record ID only matches the context whitelist exactly', () => {
  const records = [record(12), record(34)]
  assert.equal(matchExtractionRecord('same body', '[引用：记录ID：34 / 1962]', records)?.id, 34)

  // Even an exact text match must not bypass an explicit ID that is outside the context.
  assert.equal(
    matchExtractionRecord(records[0].content, '[引用：记录ID：999 / 1962 / Title 12]', records),
    null,
  )
})

test('a malformed explicit ID never falls back to fuzzy matching', () => {
  const records = [record(12)]
  assert.equal(
    matchExtractionRecord(records[0].content, '[引用：记录ID：unknown / Title 12]', records),
    null,
  )
})

test('legacy citations without IDs retain conservative fallback matching', () => {
  const records = [record(12), record(34, { title: 'Different title', content: 'Other material' })]
  assert.equal(
    matchExtractionRecord(records[0].content, '[引用：1962 / Title 12]', records)?.id,
    12,
  )
})

test('parses independent output lines into ID-bound entries', () => {
  const records = [record(12), record(34)]
  const output = [
    'First passage ———— **[引用：记录ID：12 / 1962 / Title 12]**',
    'Second passage ———— **[Citation: Record ID: 34 / 1962 / Title 34]**',
  ].join('\n')
  const entries = parseExtractionEntries(output, records)
  assert.equal(entries.length, 2)
  assert.deepEqual(entries.map(entry => entry.record?.id), [12, 34])
})

test('keeps a wrapped passage together when its citation is on the next line', () => {
  const records = [record(12)]
  const output = [
    'First half of a long passage',
    'continues on the next line',
    '———— **[引用：记录ID：12 / 1962 / Title 12]**',
  ].join('\n')
  const entries = parseExtractionEntries(output, records)
  assert.equal(entries.length, 1)
  assert.equal(entries[0].body, 'First half of a long passage\ncontinues on the next line')
  assert.equal(entries[0].record?.id, 12)
})
