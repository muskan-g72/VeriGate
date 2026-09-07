export const issueStatuses = { open: 'Open', in_progress: 'In Progress', resolved: 'Resolved', closed: 'Closed' }
export const issueSeverities = { low: 'Low', medium: 'Medium', high: 'High', critical: 'Critical' }
export const canCreateIssue = (status) => status === 'failed' || status === 'blocked'

export function issueDraft(result, testCase) {
  return {
    title: `${testCase?.title || 'Verification'} - ${result.status}`.slice(0, 180),
    description: [
      testCase?.description,
      testCase?.steps && `Steps:\n${testCase.steps}`,
      testCase?.expected_result && `Expected result:\n${testCase.expected_result}`,
      result.actual_result && `Actual result:\n${result.actual_result}`,
      result.notes && `Notes:\n${result.notes}`,
    ].filter(Boolean).join('\n\n'),
    severity: 'medium',
  }
}
