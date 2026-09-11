import {
  Clock,
  ExternalLink,
  GitBranch,
  GitCommit,
  GitPullRequest,
  LoaderCircle,
  RefreshCw,
  Search,
  ShieldAlert,
  ShieldCheck,
  User,
} from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { githubApi, projectsApi } from '../api/client'
import { useAuth } from '../auth/useAuth'
import { VerificationStatusBadge } from '../components/VerificationRuns'
import { formatDuration, formatRunDate } from '../verification'

export function GitHubPrsPage() {
  const { logout } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const [projects, setProjects] = useState([])
  const [prRuns, setPrRuns] = useState([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState('')

  const selectedProjectId = searchParams.get('project_id') || ''
  const selectedStatus = searchParams.get('status') || 'all'
  const searchQuery = searchParams.get('q') || ''

  const loadData = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true)
    setError('')

    try {
      const [projs, runs] = await Promise.all([
        projectsApi.list(),
        githubApi.listPrVerifications(selectedProjectId || null),
      ])
      setProjects(projs || [])
      setPrRuns(runs || [])
    } catch (err) {
      if (err.code === 'unauthorized') {
        logout('Your session expired. Sign in again.')
      } else {
        setError(err.message || 'Failed to load PR verifications.')
      }
    } finally {
      setLoading(false)
      if (isRefresh) setRefreshing(false)
    }
  }, [logout, selectedProjectId])

  useEffect(() => {
    let active = true
    Promise.all([
      projectsApi.list(),
      githubApi.listPrVerifications(selectedProjectId || null),
    ])
      .then(([projs, runs]) => {
        if (!active) return
        setProjects(projs || [])
        setPrRuns(runs || [])
        setLoading(false)
      })
      .catch((err) => {
        if (!active) return
        if (err.code === 'unauthorized') {
          logout('Your session expired. Sign in again.')
        } else {
          setError(err.message || 'Failed to load PR verifications.')
          setLoading(false)
        }
      })
    return () => {
      active = false
    }
  }, [logout, selectedProjectId])

  function updateFilter(key, value) {
    const next = new URLSearchParams(searchParams)
    if (value && value !== 'all') {
      next.set(key, value)
    } else {
      next.delete(key)
    }
    setSearchParams(next, { replace: true })
  }

  // Filter runs by status & search
  const filteredRuns = prRuns.filter((run) => {
    if (selectedStatus === 'passed' && (run.status !== 'completed' || run.failed_count > 0)) {
      return false
    }
    if (selectedStatus === 'failed' && run.failed_count === 0) {
      return false
    }
    if (selectedStatus === 'running' && run.status !== 'in_progress' && run.status !== 'pending') {
      return false
    }
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase()
      const titleMatch = (run.pr_title || run.name || '').toLowerCase().includes(query)
      const numMatch = String(run.pr_number || '').includes(query)
      const branchMatch = (run.pr_source_branch || '').toLowerCase().includes(query)
      const shaMatch = (run.pr_commit_sha || '').toLowerCase().includes(query)
      const authorMatch = (run.pr_author || '').toLowerCase().includes(query)
      const repoMatch = (run.pr_repository || '').toLowerCase().includes(query)
      if (!titleMatch && !numMatch && !branchMatch && !shaMatch && !authorMatch && !repoMatch) {
        return false
      }
    }
    return true
  })

  // Metrics calculation
  const totalPrs = prRuns.length
  const passedPrs = prRuns.filter((r) => r.status === 'completed' && r.failed_count === 0).length
  const failedPrs = prRuns.filter((r) => r.failed_count > 0).length
  const runningPrs = prRuns.filter((r) => r.status === 'in_progress' || r.status === 'pending').length
  const passRate = totalPrs > 0 ? Math.round((passedPrs / totalPrs) * 100) : 0

  return (
    <main className="library-page github-prs-page">
      <section className="library-heading">
        <div>
          <p className="eyebrow">Continuous Verification</p>
          <h2>GitHub PR Verifications</h2>
          <p>
            Automated test executions triggered by GitHub Pull Requests with instant proof of
            verification, status checks, and AI failure diagnostics.
          </p>
        </div>
        <div className="heading-actions">
          <button
            type="button"
            className="secondary-button"
            onClick={() => loadData(true)}
            disabled={refreshing || loading}
          >
            {refreshing ? <LoaderCircle size={15} className="spin" /> : <RefreshCw size={15} />}
            <span>Refresh</span>
          </button>
        </div>
      </section>

      {/* Metric cards */}
      <section className="runs-metrics github-metrics">
        <article>
          <span>Total PR Verifications</span>
          <strong>{totalPrs}</strong>
        </article>
        <article className="metric-passed">
          <span>Passed PRs</span>
          <strong>{passedPrs}</strong>
        </article>
        <article className="metric-failed">
          <span>Failed PRs</span>
          <strong>{failedPrs}</strong>
        </article>
        <article>
          <span>Active In-Flight</span>
          <strong>{runningPrs}</strong>
        </article>
        <article>
          <span>PR Pass Rate</span>
          <strong>{passRate}%</strong>
        </article>
      </section>

      {/* Filter toolbar */}
      <section className="runs-toolbar github-toolbar">
        <div className="search-box">
          <Search size={16} />
          <input
            type="search"
            placeholder="Search PR title, #, branch, commit SHA, author..."
            value={searchQuery}
            onChange={(e) => updateFilter('q', e.target.value)}
          />
        </div>

        <div className="filter-group">
          <label htmlFor="project-filter">Project:</label>
          <select
            id="project-filter"
            value={selectedProjectId}
            onChange={(e) => updateFilter('project_id', e.target.value)}
          >
            <option value="">All Projects</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label htmlFor="status-filter">Status:</label>
          <select
            id="status-filter"
            value={selectedStatus}
            onChange={(e) => updateFilter('status', e.target.value)}
          >
            <option value="all">All Statuses</option>
            <option value="passed">Passed</option>
            <option value="failed">Failed</option>
            <option value="running">In Progress / Pending</option>
          </select>
        </div>
      </section>

      {/* Main content body */}
      {error ? (
        <div className="projects-state projects-state--error" role="alert">
          <p>{error}</p>
          <button type="button" className="secondary-button" onClick={() => loadData()}>
            Retry
          </button>
        </div>
      ) : loading ? (
        <div className="projects-state" role="status">
          <LoaderCircle size={24} className="spin" />
          <p>Loading GitHub pull request verifications...</p>
        </div>
      ) : filteredRuns.length === 0 ? (
        <div className="projects-state github-empty-state">
          <GitPullRequest size={42} className="empty-icon" />
          <h3>No GitHub PR Verifications Found</h3>
          <p>
            {prRuns.length === 0
              ? 'Connect your GitHub repository to automatically verify Pull Requests with VeriGate Playwright tests.'
              : 'No pull request verifications match your current search or status filters.'}
          </p>
          {prRuns.length === 0 && (
            <div className="github-setup-guide">
              <h4>Quick Setup Guide:</h4>
              <ol>
                <li>
                  Go to{' '}
                  <Link to="/app/projects">
                    <strong>Projects</strong>
                  </Link>{' '}
                  and open your project dashboard.
                </li>
                <li>
                  Under <strong>GitHub Integration</strong>, enter your repository name (e.g.{' '}
                  <code>owner/repo</code>) and save.
                </li>
                <li>
                  In your GitHub repository settings, add a Webhook pointing to your backend:
                  <div className="code-snippet">
                    <code>
                      {window.location.port === '5173'
                        ? `${window.location.protocol}//${window.location.hostname}:8000/api/v1/github/webhook`
                        : `${window.location.origin}/api/v1/github/webhook`}
                    </code>
                  </div>
                  <small style={{ color: 'var(--muted)', display: 'block', marginTop: '0.25rem' }}>
                    Tip for local testing: use an HTTPS tunnel like <code>ngrok http 8000</code>.
                  </small>
                </li>
                <li>
                  Set Content Type to <code>application/json</code> and trigger on{' '}
                  <strong>Pull requests</strong>.
                </li>
              </ol>
            </div>
          )}
        </div>
      ) : (
        <section className="github-prs-list" aria-label="GitHub PR Verifications">
          {filteredRuns.map((run) => {
            const hasFailures = run.failed_count > 0
            const isFinished = run.status === 'completed'

            return (
              <article
                key={run.id}
                className={`github-pr-card ${hasFailures ? 'has-failures' : isFinished ? 'is-passed' : 'is-pending'}`}
              >
                <div className="pr-card-header">
                  <div className="pr-badge-group">
                    <span className="pr-number-badge">
                      <GitPullRequest size={14} />
                      #{run.pr_number || 'PR'}
                    </span>
                    <h3 className="pr-title">{run.pr_title || run.name}</h3>
                  </div>
                  <div className="pr-header-meta">
                    <VerificationStatusBadge status={run.status} />
                    {run.pr_url && (
                      <a
                        href={run.pr_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="github-ext-link"
                        title="Open Pull Request on GitHub"
                      >
                        <ExternalLink size={15} />
                        <span>GitHub</span>
                      </a>
                    )}
                  </div>
                </div>

                <div className="pr-card-details">
                  <div className="pr-meta-item">
                    <GitBranch size={14} />
                    <span>
                      <code>{run.pr_source_branch || 'branch'}</code> &rarr;{' '}
                      <code>{run.pr_target_branch || 'main'}</code>
                    </span>
                  </div>
                  {run.pr_commit_sha && (
                    <div className="pr-meta-item">
                      <GitCommit size={14} />
                      <code className="commit-sha">{run.pr_commit_sha.slice(0, 7)}</code>
                    </div>
                  )}
                  {run.pr_author && (
                    <div className="pr-meta-item">
                      <User size={14} />
                      <span>@{run.pr_author}</span>
                    </div>
                  )}
                  {run.pr_repository && (
                    <div className="pr-meta-item repo-pill">
                      <span>{run.pr_repository}</span>
                    </div>
                  )}
                  <div className="pr-meta-item pr-duration">
                    <Clock size={14} />
                    <span>Duration: {formatDuration(run.started_at, run.completed_at)}</span>
                  </div>
                  <div className="pr-meta-item pr-timestamp">
                    <span>{formatRunDate(run.created_at)}</span>
                  </div>
                </div>

                <div className="pr-card-footer">
                  <div className="pr-results-counts">
                    {hasFailures ? (
                      <span className="stat-pill failed">
                        <ShieldAlert size={14} />
                        {run.failed_count} failed
                      </span>
                    ) : (
                      <span className="stat-pill passed">
                        <ShieldCheck size={14} />
                        {run.passed_count} passed
                      </span>
                    )}
                    <span className="stat-detail">
                      {run.passed_count} / {run.total_cases} tests passed
                    </span>
                  </div>

                  <div className="pr-card-actions">
                    <Link
                      to={`/app/verification-runs/${run.id}`}
                      className="primary-button pr-view-btn"
                    >
                      View Verification
                    </Link>
                  </div>
                </div>
              </article>
            )
          })}
        </section>
      )}
    </main>
  )
}
