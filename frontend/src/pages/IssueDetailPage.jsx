import { useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { issuesApi } from '../api/client'
import { useAuth } from '../auth/useAuth'
import { IssueForm, IssueStatusBadge } from '../components/IssueForm'
import { formatRunDate } from '../verification'

export function IssueDetailPage() {
  const { issueId } = useParams()
  return <IssueDetail key={issueId} issueId={issueId} />
}

function IssueDetail({ issueId }) {
  const { logout } = useAuth()
  const { state } = useLocation()
  const [issue, setIssue] = useState(null)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    let active = true
    issuesApi.read(issueId).then((item) => { if (active) setIssue(item) }).catch((error) => {
      if (!active) return
      if (error.code === 'unauthorized') logout('Your session expired. Sign in again.')
      else setError(error.status === 422 ? 'Invalid issue ID.' : error.message)
    })
    return () => { active = false }
  }, [issueId, attempt, logout])
  async function save(data) {
    try { const saved = await issuesApi.update(issueId, data); setIssue(saved); return saved }
    catch (error) { if (error.code === 'unauthorized') logout('Your session expired. Sign in again.'); throw error }
  }
  const runId = state?.resultId === issue?.verification_result_id && /^[0-9a-f-]{36}$/i.test(state?.runId || '') ? state.runId : null
  return <main className="library-page issues-page"><Link className="library-link-button" to={issue ? `/app/issues?projectId=${issue.project_id}` : '/app/issues'}>Back to Issues</Link>
    {error ? <div className="projects-state projects-state--error" role="alert"><p>{error}</p><button onClick={() => { setError(''); setAttempt((value) => value + 1) }}>Retry</button></div> : !issue ? <div className="projects-state" role="status">Loading issue...</div> : <section className="verification-summary issue-detail"><header className="verification-title"><h2>{issue.title}</h2><IssueStatusBadge status={issue.status} /></header>
      <div className="verification-dates"><span>Created: {formatRunDate(issue.created_at)}</span><span>Updated: {formatRunDate(issue.updated_at)}</span>{issue.resolved_at && <span>Resolved: {formatRunDate(issue.resolved_at)}</span>}</div>
      <p className="issue-reference">Verification result: <code>{issue.verification_result_id}</code></p>{runId && <Link className="library-link-button" to={`/app/verification-runs/${runId}#result-${issue.verification_result_id}`}>Open verification run</Link>}
      <IssueForm initial={{ title: issue.title, description: issue.description || '', severity: issue.severity, status: issue.status }} editing onSave={save} />
    </section>}
  </main>
}
