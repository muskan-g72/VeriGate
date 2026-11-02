import assert from 'node:assert/strict'
import test from 'node:test'
import { defaultComparisonCategories, filterComparisonRows, formatDuration, formatDurationDelta } from '../src/runComparison.js'

test('comparison duration formatters round to at most two decimal places and handle nulls', () => {
  assert.equal(formatDuration(1.234), '1.23s')
  assert.equal(formatDuration(1.2), '1.2s')
  assert.equal(formatDuration(null), '—')
  assert.equal(formatDurationDelta(0.30000000000000004), '+0.3s')
  assert.equal(formatDurationDelta(-1.239), '-1.24s')
  assert.equal(formatDurationDelta(null), '—')
})

test('comparison category filters retain defaults and reveal every selected category', () => {
  const rows = ['regressed', 'changed_other', 'added', 'removed', 'improved', 'unchanged'].map((category) => ({ category, title: category }))

  assert.deepEqual(filterComparisonRows(rows, defaultComparisonCategories).map((row) => row.category), ['regressed', 'changed_other'])
  for (const category of ['added', 'removed', 'improved', 'unchanged']) {
    assert.deepEqual(filterComparisonRows(rows, new Set([category])).map((row) => row.category), [category])
  }
  assert.equal(rows.length, 6)
})
