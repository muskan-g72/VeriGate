export const requirementPriorities = ['critical', 'high', 'medium', 'low']
export const requirementCategories = ['functional', 'non-functional', 'security', 'performance', 'compliance', 'other']
export const requirementStatuses = ['draft', 'approved', 'deprecated']
export const coverageLabels = { untested: 'Untested', passing: 'Passing', failing: 'Failing', not_passing: 'Not passing' }

export function formatCoverageStatus(status) {
  return coverageLabels[status] || 'Untested'
}

export function filterTraceabilityItems(items, { search = '', coverage = '', unresolved = false } = {}) {
  const query = search.trim().toLowerCase()
  return items.filter((item) => (!query || `${item.requirement_key} ${item.title}`.toLowerCase().includes(query))
    && (!coverage || item.coverage_status === coverage)
    && (!unresolved || Number(item.unresolved_issue_count || 0) > 0))
}

export function paginationOffset(page, limit) {
  return Math.max(0, page - 1) * limit
}

export function latestVerifiedAt(testCases = []) {
  const stamps = testCases.map((item) => item.latest_run_completed_at).filter(Boolean).map((value) => new Date(value).getTime()).filter(Number.isFinite)
  return stamps.length ? new Date(Math.max(...stamps)).toISOString() : null
}
