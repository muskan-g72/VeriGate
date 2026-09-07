import { Link } from 'react-router-dom'
import { CreateIssueDialog } from './CreateIssueDialog'
import { canCreateIssue } from '../issues'
import { useState } from 'react'
import { VerificationStatusBadge } from './VerificationRuns'
import { formatRunDate, verificationLabels } from '../verification'

export function VerificationResultCard({ result, testCase, disabled, saving, onSave }) {
  const [creatingIssue, setCreatingIssue] = useState(false)
  const [createdIssue, setCreatedIssue] = useState(null)
  const [actualResult, setActualResult] = useState(result.actual_result || '')
  const [notes, setNotes] = useState(result.notes || '')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  async function save(status) {
    setError(''); setNotice('')
    try { await onSave(result.id, { status, actual_result: actualResult || null, notes: notes || null }); setNotice('Result saved.') }
    catch (error) { setError(error.message) }
  }
  return <article id={`result-${result.id}`} className="verification-result" aria-labelledby={`title-${result.id}`} aria-busy={saving}>
    <header><div><span className={`priority priority--${testCase?.priority}`}>{testCase?.priority || 'Test case'}</span><h3 id={`title-${result.id}`}>{testCase?.title || `Test case ${result.test_case_id}`}</h3></div><VerificationStatusBadge status={result.status} /></header>
    {testCase ? <><p className="verification-copy">{testCase.description}</p><div className="verification-definition"><div><h4>Execution steps</h4><p>{testCase.steps}</p></div><div><h4>Expected result</h4><p>{testCase.expected_result}</p></div></div></> : <p>Test definition is unavailable.</p>}
    <div className="verification-definition"><div className="field"><label htmlFor={`actual-${result.id}`}>Actual result <span>Optional</span></label><textarea id={`actual-${result.id}`} rows={3} value={actualResult} disabled={saving} onChange={(event) => setActualResult(event.target.value)} /></div><div className="field"><label htmlFor={`notes-${result.id}`}>Notes <span>Optional</span></label><textarea id={`notes-${result.id}`} rows={3} value={notes} disabled={saving} onChange={(event) => setNotes(event.target.value)} /></div></div>
    <p>Enter observations before choosing a result, or edit them later and save details.</p>
    <div className="verification-actions" aria-label="Set test result">{['passed', 'failed', 'blocked', 'skipped', 'pending'].map((status) => <button type="button" className="secondary-button" aria-pressed={result.status === status} disabled={disabled} key={status} onClick={() => save(status)}>{status === 'pending' ? 'Reset to Pending' : verificationLabels[status]}</button>)}<button className="primary-button" disabled={disabled} onClick={() => save(result.status)}>Save details</button></div>
    <p role="status">{saving ? 'Saving result...' : notice}{result.executed_at && ` Executed: ${formatRunDate(result.executed_at)}`}</p>
    {canCreateIssue(result.status) && <button className="secondary-button" disabled={disabled} onClick={() => setCreatingIssue(true)}>Create Issue</button>}
    {createdIssue && <p role="status">Issue created. <Link to={`/app/issues/${createdIssue.id}`} state={{ runId: result.verification_run_id, resultId: result.id }}>Open issue</Link> or <Link to={`/app/issues?projectId=${createdIssue.project_id}`}>view project issues</Link>.</p>}
    {creatingIssue && <CreateIssueDialog result={result} testCase={testCase} onClose={() => setCreatingIssue(false)} onCreated={(issue) => { setCreatedIssue(issue); setCreatingIssue(false) }} />}
    {error && <div className="form-alert" role="alert">{error}</div>}
  </article>
}
