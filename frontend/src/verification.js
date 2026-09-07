export const verificationLabels = { pending: 'Pending', in_progress: 'In Progress', completed: 'Completed', passed: 'Passed', failed: 'Failed', blocked: 'Blocked', skipped: 'Skipped' }
export const formatRunDate = (value) => value ? new Date(value).toLocaleString() : '—'

