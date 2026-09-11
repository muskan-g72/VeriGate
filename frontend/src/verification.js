export const verificationLabels = { pending: 'Pending', in_progress: 'In Progress', completed: 'Completed', passed: 'Passed', failed: 'Failed', blocked: 'Blocked', skipped: 'Skipped' }
export function runProgress(run) {
  if (!Number.isInteger(run.total_cases) || !Number.isInteger(run.pending_count)
    || run.total_cases < 0 || run.pending_count < 0 || run.pending_count > run.total_cases) return null
  return { executed: run.total_cases - run.pending_count, total: run.total_cases }
}
export const formatRunDate = (value) => value ? new Date(value).toLocaleString() : '—'

export function formatDuration(startedAt, completedAt) {
  if (!startedAt) return '—'
  const start = new Date(startedAt).getTime()
  const end = completedAt ? new Date(completedAt).getTime() : Date.now()
  if (isNaN(start) || isNaN(end) || end < start) return '—'
  const diffSec = Math.round((end - start) / 1000)
  if (diffSec < 1) return '< 1s'
  if (diffSec < 60) return `${diffSec}s`
  const minutes = Math.floor(diffSec / 60)
  const seconds = diffSec % 60
  if (minutes < 60) {
    return seconds > 0 ? `${minutes}m ${seconds}s` : `${minutes}m`
  }
  const hours = Math.floor(minutes / 60)
  const remMinutes = minutes % 60
  return remMinutes > 0 ? `${hours}h ${remMinutes}m` : `${hours}h`
}

