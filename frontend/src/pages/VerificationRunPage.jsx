import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { projectsApi, testCasesApi, testSuitesApi, verificationRunsApi } from '../api/client'
import { useAuth } from '../auth/useAuth'
import { formatRunDate } from '../verification'
import { VerificationStatusBadge } from '../components/VerificationRuns'
import { VerificationResultCard } from '../components/VerificationResultCard'

export function VerificationRunPage() {
  const { runId } = useParams()
  return <VerificationRun key={runId} runId={runId} />
}

function VerificationRun({ runId }) {
  const { logout } = useAuth()
  const [run, setRun] = useState(null)
  const [suite, setSuite] = useState(null)
  const [project, setProject] = useState(null)
  const [cases, setCases] = useState([])
  const [error, setError] = useState('')
  const [summaryError, setSummaryError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const [savingId, setSavingId] = useState(null)
  const busy = useRef(false)
  const mounted = useRef(true)
  useEffect(() => { mounted.current = true; return () => { mounted.current = false } }, [])
  useEffect(() => {
    let active = true
    async function load() {
      try {
        const detail = await verificationRunsApi.read(runId)
        const [definition, testCases] = await Promise.all([testSuitesApi.read(detail.test_suite_id), testCasesApi.list(detail.test_suite_id)])
        const owner = await projectsApi.read(definition.project_id)
        if (active) { setRun(detail); setSuite(definition); setCases(testCases); setProject(owner) }
      } catch (error) {
        if (!active) return
        if (error.code === 'unauthorized') logout('Your session expired. Sign in again.')
        else setError(error.status === 422 ? 'Invalid verification run ID.' : error.message)
      }
    }
    load()
    return () => { active = false }
  }, [runId, attempt, logout])

  async function refreshSummary() {
    const updated = await verificationRunsApi.read(runId)
    if (mounted.current) { setRun(updated); setSummaryError('') }
  }
  async function saveResult(resultId, data) {
    if (busy.current) return
    busy.current = true; setSavingId(resultId)
    try {
      const saved = await verificationRunsApi.updateResult(resultId, data)
      if (!mounted.current) return
      setRun((current) => ({ ...current, results: current.results.map((result) => result.id === saved.id ? saved : result) }))
      try { await refreshSummary() }
      catch (error) {
        if (error.code === 'unauthorized') logout('Your session expired. Sign in again.')
        else if (mounted.current) setSummaryError(`Result saved, but run status could not be refreshed. ${error.message}`)
      }
    } catch (error) {
      if (error.code === 'unauthorized') logout('Your session expired. Sign in again.')
      throw error
    } finally { busy.current = false; if (mounted.current) setSavingId(null) }
  }
  async function retrySummary() {
    if (busy.current) return
    busy.current = true; setSavingId('summary')
    try { await refreshSummary() } catch (error) {
      if (error.code === 'unauthorized') logout('Your session expired. Sign in again.')
      else setSummaryError(error.message)
    } finally { busy.current = false; if (mounted.current) setSavingId(null) }
  }
  const back = suite ? `/app/test-library?projectId=${suite.project_id}&suiteId=${suite.id}` : '/app/test-library'
  return <main className="library-page verification-page"><Link className="library-link-button" to={back}>Back to Test Library</Link>
    {error ? <div className="projects-state projects-state--error" role="alert"><p>{error}</p><button onClick={() => { setError(''); setAttempt((value) => value + 1) }}>Retry</button></div> : !run ? <div className="projects-state" role="status">Loading verification run...</div> : <>
      <section className="verification-summary"><p className="eyebrow">{project?.name} / {suite?.name}</p><div className="verification-title"><h2>{run.name}</h2><VerificationStatusBadge status={run.status} /></div>
        <div className="verification-dates"><span>Created: {formatRunDate(run.created_at)}</span>{run.started_at && <span>Started: {formatRunDate(run.started_at)}</span>}{run.completed_at && <span>Completed: {formatRunDate(run.completed_at)}</span>}</div>
        <p aria-live="polite">{run.total_cases - run.pending_count} / {run.total_cases} completed</p><progress aria-label="Executed test cases" value={run.total_cases - run.pending_count} max={run.total_cases || 1} />
        <p>{run.passed_count} passed · {run.failed_count} failed · {run.blocked_count} blocked · {run.skipped_count} skipped · {run.pending_count} pending</p>
        {summaryError && <div className="form-alert" role="alert"><span>{summaryError}</span><button className="secondary-button" disabled={Boolean(savingId)} onClick={retrySummary}>Refresh status</button></div>}
      </section>
      <section className="verification-results" aria-label="Test execution results">{run.results.length === 0 && <p>This run has no results.</p>}{run.results.map((result) => <VerificationResultCard key={result.id} result={result} testCase={cases.find((item) => item.id === result.test_case_id)} saving={savingId === result.id} disabled={Boolean(savingId)} onSave={saveResult} />)}</section>
    </>}
  </main>
}

