export const verificationLabels = { pending: 'Pending', in_progress: 'In Progress', completed: 'Completed', passed: 'Passed', failed: 'Failed', blocked: 'Blocked', skipped: 'Skipped' }
export function runProgress(run) {
  if (!Number.isInteger(run.total_cases) || !Number.isInteger(run.pending_count)
    || run.total_cases < 0 || run.pending_count < 0 || run.pending_count > run.total_cases) return null
  return { executed: run.total_cases - run.pending_count, total: run.total_cases }
}
export const formatRunDate = (value) => value ? new Date(value).toLocaleString() : '—'

