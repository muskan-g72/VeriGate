export const comparisonCategories = ['regressed', 'changed_other', 'added', 'removed', 'improved', 'unchanged']
export const defaultComparisonCategories = new Set(['regressed', 'changed_other'])

function rounded(value) {
  return Number(Number(value).toFixed(2))
}

export function formatDuration(value) {
  if (value == null || !Number.isFinite(Number(value))) return '—'
  return `${rounded(value)}s`
}

export function formatDurationDelta(value) {
  if (value == null || !Number.isFinite(Number(value))) return '—'
  const valueRounded = rounded(value)
  return `${valueRounded > 0 ? '+' : ''}${valueRounded}s`
}

export function filterComparisonRows(rows, activeCategories, search = '') {
  const query = search.toLowerCase()
  return rows.filter((row) => (!activeCategories.size || activeCategories.has(row.category))
    && (row.title || '').toLowerCase().includes(query))
}
