import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { issuesApi, projectsApi } from '../api/client'
import { useAuth } from '../auth/useAuth'
import { chooseProject, rememberProject } from '../testLibrary/projectSelection'
import { issueSeverities, issueStatuses } from '../issues'
import { IssueStatusBadge } from '../components/IssueForm'
import { formatRunDate } from '../verification'

export function IssuesPage() {
  const { logout } = useAuth()
  const [params, setParams] = useSearchParams()
  const [projects, setProjects] = useState(null)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    let active = true
    projectsApi.list().then((items) => { if (active) setProjects(items) }).catch((error) => {
      if (!active) return
      if (error.code === 'unauthorized') logout('Your session expired. Sign in again.')
      else setError(error.message)
    })
    return () => { active = false }
  }, [attempt, logout])
  const projectId = projects ? (projects.some((item) => item.id === params.get('projectId')) ? params.get('projectId') : chooseProject(projects)) : ''
  return <main className="library-page issues-page"><section className="library-heading"><div><p className="eyebrow">Verification findings</p><h2>Issues</h2><p>Track failed and blocked checks through resolution.</p></div>{projects?.length > 0 && <label>Project<select value={projectId} onChange={(event) => { rememberProject(event.target.value); setParams({ projectId: event.target.value }) }}>{projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}</select></label>}</section>
    {error ? <div className="projects-state projects-state--error" role="alert"><p>{error}</p><button onClick={() => { setError(''); setAttempt((value) => value + 1) }}>Retry</button></div> : !projects ? <div className="projects-state" role="status">Loading projects...</div> : !projects.length ? <section className="projects-empty"><h3>No projects yet</h3><p>Create a project and execute verification tests to report issues.</p><Link className="library-link-button" to="/app/projects">Open projects</Link></section> : <ProjectIssues key={projectId} projectId={projectId} />}
  </main>
}

function ProjectIssues({ projectId }) {
  const { logout } = useAuth()
  const [issues, setIssues] = useState(null)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const [status, setStatus] = useState('')
  const [severity, setSeverity] = useState('')
  const [search, setSearch] = useState('')
  useEffect(() => {
    let active = true
    issuesApi.listForProject(projectId).then((items) => { if (active) setIssues(items) }).catch((error) => {
      if (!active) return
      if (error.code === 'unauthorized') logout('Your session expired. Sign in again.')
      else setError(error.message)
    })
    return () => { active = false }
  }, [projectId, attempt, logout])
  if (error) return <div className="projects-state projects-state--error" role="alert"><p>{error}</p><button onClick={() => { setError(''); setAttempt((value) => value + 1) }}>Retry</button></div>
  if (!issues) return <div className="projects-state" role="status">Loading issues...</div>
  if (!issues.length) return <section className="projects-empty"><h3>No issues reported</h3><p>Open a verification run and choose Create Issue on a Failed or Blocked result.</p><Link className="library-link-button" to={`/app/test-library?projectId=${projectId}`}>Open Test Library</Link></section>
  const filtered = issues.filter((issue) => (!status || issue.status === status) && (!severity || issue.severity === severity) && issue.title.toLowerCase().includes(search.trim().toLowerCase()))
  return <><div className="issue-filters"><div className="field"><label htmlFor="issue-search">Search title</label><input id="issue-search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Find an issue..." /></div><div className="field"><label htmlFor="status-filter">Status</label><select id="status-filter" value={status} onChange={(event) => setStatus(event.target.value)}><option value="">All statuses</option>{Object.entries(issueStatuses).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></div><div className="field"><label htmlFor="severity-filter">Severity</label><select id="severity-filter" value={severity} onChange={(event) => setSeverity(event.target.value)}><option value="">All severities</option>{Object.entries(issueSeverities).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></div></div>
    <p className="result-count" role="status">{filtered.length} / {issues.length} issues</p>
    {!filtered.length && <div className="projects-state"><p>No issues match these filters.</p><button onClick={() => { setStatus(''); setSeverity(''); setSearch('') }}>Clear filters</button></div>}
    <div className="issue-list">{filtered.map((issue) => <article className="issue-card" key={issue.id}><div><div className="issue-badges"><span className={`priority priority--${issue.severity}`}>{issueSeverities[issue.severity]}</span><IssueStatusBadge status={issue.status} /></div><h3><Link to={`/app/issues/${issue.id}`}>{issue.title}</Link></h3><div className="verification-dates"><span>Created: {formatRunDate(issue.created_at)}</span>{issue.resolved_at && <span>Resolved: {formatRunDate(issue.resolved_at)}</span>}</div></div><Link className="library-link-button" to={`/app/issues/${issue.id}`} aria-label={`Open issue: ${issue.title}`}>Open Issue</Link></article>)}</div>
  </>
}
