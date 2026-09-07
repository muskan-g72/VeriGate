import { LoaderCircle, Play, RefreshCw } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { projectsApi, testSuitesApi, verificationRunsApi } from '../api/client'
import { useAuth } from '../auth/useAuth'
import { VerificationStatusBadge } from '../components/VerificationRuns'
import { formatRunDate, runProgress, verificationLabels } from '../verification'
import { filterRuns, loadRuns, runsEmptyState, runStatuses, summarizeRuns } from '../runs'

const loadingLabels = { projects: 'Loading projects...', suites: 'Loading test suites...', runs: 'Loading verification runs...' }
const emptyMessages = {
  projects: ['No projects yet', 'Create a project before running verifications.'],
  suites: ['No test suites available yet.', 'Add a test suite in Test Library to begin.'],
  runs: ['No verification runs yet.', 'Start a verification from a test suite in Test Library.'],
  incomplete: ['No runs available to display', 'Some records could not be loaded. Retry to see the complete history.'],
  filtered: ['No runs match these filters.', 'Try a different project, status, or search.'],
}

export function RunsPage() {
  const { logout } = useAuth()
  const [params, setParams] = useSearchParams()
  const [data, setData] = useState(null)
  const [stage, setStage] = useState('projects')
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const request = useRef(null)
  useEffect(() => {
    let active = true
    // Share the in-flight load during StrictMode's effect replay as well.
    if (!request.current || request.current.attempt !== attempt) {
      const current = { attempt, notify: null }
      current.promise = loadRuns({ listProjects: projectsApi.list, listSuites: testSuitesApi.list, listRuns: verificationRunsApi.list },
        (nextStage) => current.notify?.(nextStage))
      request.current = current
    }
    const current = request.current
    current.notify = (nextStage) => { if (active) setStage(nextStage) }
    current.promise
      .then((loaded) => { if (active) { setData(loaded); setStage('ready') } })
      .catch((error) => {
        if (!active) return
        if (error.code === 'unauthorized') logout('Your session expired. Sign in again.')
        else { setError(error.message); setStage('error') }
      })
    return () => { active = false; current.notify = null }
  }, [attempt, logout])

  function reload() { setData(null); setError(''); setStage('projects'); setAttempt((value) => value + 1) }
  function filter(key, value) {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    setParams(next, { replace: true })
  }
  const projectId = data?.projects.some((project) => project.id === params.get('projectId')) ? params.get('projectId') : ''
  const status = runStatuses.includes(params.get('status')) ? params.get('status') : ''
  const search = params.get('search') || ''
  const sort = params.get('sort') === 'oldest' ? 'oldest' : 'newest'
  const visible = data ? filterRuns(data.runs, { projectId, status, search, sort }) : []
  const counts = data ? summarizeRuns(data.runs) : null
  const empty = data ? runsEmptyState(data, projectId) : null
  const loading = stage !== 'ready' && stage !== 'error'

  return <main className="library-page runs-page">
    <section className="library-heading"><div><p className="eyebrow">Verification execution</p><h2>Runs</h2><p>Track verification runs across projects and test suites.</p></div>
      <button className="secondary-button" onClick={reload} disabled={loading}><RefreshCw />Refresh runs</button>
    </section>
    {loading && <div className="projects-state" role="status"><LoaderCircle className="spinner" /><p>{loadingLabels[stage]}</p></div>}
    {error && <div className="projects-state projects-state--error" role="alert"><p>{error}</p><button className="secondary-button" onClick={reload}>Retry</button></div>}
    {data && <>
      {data.failures.length > 0 && <section className="runs-warning" role="alert"><div><strong>Some runs could not be loaded</strong><p>Showing available records. Totals may be incomplete.</p><ul>{data.failures.map((failure) => <li key={`${failure.projectId}-${failure.suiteId || 'suites'}`}>{failure.label}: {failure.message}</li>)}</ul></div><button className="secondary-button" onClick={reload}>Retry loading</button></section>}
      <section aria-label="Run totals" className="runs-metrics">{[['total', 'Total Runs'], ...runStatuses.map((value) => [value, verificationLabels[value]])].map(([key, label]) => <article key={key}><span>{label}</span><strong>{counts[key]}</strong></article>)}</section>
      <p className="runs-caption">Totals across all loaded runs. Filters apply to the list below.</p>
      {data.projects.length > 0 && <div className="runs-filters">
        <div className="field"><label htmlFor="runs-project">Project</label><select id="runs-project" value={projectId} onChange={(event) => filter('projectId', event.target.value)}><option value="">All projects</option>{data.projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}</select></div>
        <div className="field"><label htmlFor="runs-status">Status</label><select id="runs-status" value={status} onChange={(event) => filter('status', event.target.value)}><option value="">All statuses</option>{runStatuses.map((value) => <option key={value} value={value}>{verificationLabels[value]}</option>)}</select></div>
        <div className="field runs-search"><label htmlFor="runs-search">Search runs or suites</label><input id="runs-search" value={search} onChange={(event) => filter('search', event.target.value)} placeholder="Find a run or test suite..." /></div>
        <div className="field"><label htmlFor="runs-sort">Sort</label><select id="runs-sort" value={sort} onChange={(event) => filter('sort', event.target.value)}><option value="newest">Most recent first</option><option value="oldest">Oldest first</option></select></div>
      </div>}
      <p className="runs-caption" role="status">{visible.length} of {data.runs.length} loaded runs</p>
      {visible.length === 0 ? <section className="projects-empty"><div><Play /></div><h3>{emptyMessages[empty][0]}</h3><p>{emptyMessages[empty][1]}</p>
        {empty === 'filtered' ? <button onClick={() => setParams({})}>Clear filters</button> : empty === 'incomplete' ? <button onClick={reload}>Retry loading</button> : <Link className="library-link-button" to={empty === 'projects' ? '/app/projects' : `/app/test-library${projectId ? `?projectId=${projectId}` : ''}`}>{empty === 'projects' ? 'Open projects' : 'Open Test Library'}</Link>}
      </section> : <section className="runs-list" aria-label="Verification runs">{visible.map((run) => <RunCard key={run.id} run={run} runsSearch={params.toString()} />)}</section>}
    </>}
  </main>
}

function RunCard({ run, runsSearch }) {
  const progress = runProgress(run)
  const outcomes = ['passed', 'failed', 'blocked', 'skipped', 'pending'].filter((status) => Number.isInteger(run[`${status}_count`]) && run[`${status}_count`] >= 0)
  return <article className={`run-card run-card--${run.status}`}>
    <header><div><p className="run-context">{run.project_name} / {run.suite_name}</p><h3>{run.name}</h3></div><VerificationStatusBadge status={run.status} /></header>
    <div className="verification-dates"><span>Created: {formatRunDate(run.created_at)}</span>{run.started_at && <span>Started: {formatRunDate(run.started_at)}</span>}{run.completed_at && <span>Completed: {formatRunDate(run.completed_at)}</span>}</div>
    <footer><div className="run-progress"><p>{run.status === 'pending' ? 'Not started' : progress ? `${progress.executed} / ${progress.total} executed` : 'Result counts unavailable'}</p>
      {progress && progress.total > 0 && <progress aria-label={`Executed test cases: ${run.name}`} value={progress.executed} max={progress.total} />}
      {outcomes.length > 0 && <p className="run-outcomes">{outcomes.map((status) => `${run[`${status}_count`]} ${status}`).join(' · ')}</p>}
    </div><Link className="library-link-button" aria-label={`Open Run: ${run.name}`} to={`/app/verification-runs/${run.id}`} state={{ runsSearch }}>Open Run</Link></footer>
  </article>
}
